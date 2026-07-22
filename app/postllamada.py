import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text, create_engine
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

# ==========================================
# 1. SQLALCHEMY TABLES (ORM)
#    Matches the real DB schema: leads, calls, agent_predictions
# ==========================================

class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(50), primary_key=True)
    company_name = Column(String(150), nullable=True)
    contact_name = Column(String(150), nullable=True)
    phone_number = Column(String(30), nullable=True)
    region = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    # NOTE: column is spelled "prefered_language" (single "r") in the DB,
    # kept identical here so the ORM maps correctly.
    prefered_language = Column(String(10), default="es")
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pendiente")
    attempts_counts_today = Column(Integer, default=0)

    # One-to-many relationships
    calls = relationship("Call", back_populates="lead", cascade="all, delete-orphan")
    predictions = relationship("AgentPrediction", back_populates="lead", cascade="all, delete-orphan")


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(50), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    call_status = Column(String(50), nullable=False)
    durations_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="calls")
    predictions = relationship("AgentPrediction", back_populates="call", cascade="all, delete-orphan")


class AgentPrediction(Base):
    __tablename__ = "agent_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(50), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=True)
    call_state = Column(String(50), nullable=False)
    lead_classification = Column(String(50), nullable=False)
    lead_interest_level = Column(String(20), nullable=False)
    classification_reason = Column(Text, nullable=True)
    recommended_next_action = Column(Text, nullable=True)
    observations = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="predictions")
    call = relationship("Call", back_populates="predictions")


# ==========================================
# 2. PYDANTIC SCHEMAS (VALIDATION DTOs)
# ==========================================

class Message(BaseModel):
    role: str
    content: str


class ObservationsSchema(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    industry: Optional[str] = None
    user_text_response: Optional[str] = None
    transcript: List[Message] = Field(default_factory=list)


class AgentPredictionSchema(BaseModel):
    lead_id: str
    call_id: Optional[int] = None
    call_state: str
    lead_classification: str
    lead_interest_level: str
    classification_reason: str
    recommended_next_action: str
    observations: ObservationsSchema
    duration_seconds: Optional[int] = 0  # only used if a new Call row needs to be created


# ==========================================
# 3. DATABASE CONFIGURATION
# ==========================================

DATABASE_URL = "postgresql://root:12345678@localhost:5432/bd_sistema_empresa"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database():
    """Creates the tables in PostgreSQL if they don't already exist."""
    Base.metadata.create_all(bind=engine)


# ==========================================
# 4. LOADING AND VALIDATION FUNCTIONS
# ==========================================

def load_data(file_path: str) -> dict:
    """Loads the JSON file and unescapes 'observations' if it comes in as a string."""
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "observations" in data and isinstance(data["observations"], str):
        try:
            data["observations"] = json.loads(data["observations"])
        except json.JSONDecodeError as e:
            raise ValueError(f"The 'observations' field in the file contains malformed JSON: {e}")

    return data


def validate_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Uppercases enum-like fields and validates types with Pydantic."""
    if not isinstance(data, dict):
        raise ValueError("The 'data' parameter must be a valid dictionary.")

    # 1. Normalize lowercase to UPPERCASE for enum-like fields
    enum_fields = ["call_state", "lead_classification", "lead_interest_level"]
    for field in enum_fields:
        if isinstance(data.get(field), str):
            data[field] = data[field].strip().upper()

    # 2. Parse observations if it is still a JSON string
    raw_observations = data.get("observations")
    if isinstance(raw_observations, str):
        try:
            data["observations"] = json.loads(raw_observations)
        except json.JSONDecodeError as e:
            raise ValueError(f"The 'observations' field contains malformed JSON: {e}")

    # 3. Validate with Pydantic
    try:
        validated_obj = AgentPredictionSchema(**data)
        return validated_obj.model_dump()
    except ValidationError as ve:
        raise ValueError(f"Pydantic validation error: {ve.errors()}")


def determine_new_lead_status(classification: str) -> str:
    """Maps the LLM classification to the lead statuses used in the DB.

    NOTE: status VALUES are kept in Spanish ('pendiente', 'no_interesado',
    'llamar_despues') because that's what's already stored in the `leads`
    table (see DEFAULT 'pendiente' and the seed INSERTs). Only the code
    identifiers were translated to English.
    """
    normalized = classification.strip().upper()


    if normalized in [ "COLD_LEAD"]:
        return "no_interesado"
    elif normalized in ["NOT_QUALIFIED", "NO_CONTACTADO" , "CALLBACK_REQUESTED", "RESPUESTA_AMBIGUA"]:
        return "llamar_despues"
    elif normalized in ["HOT_LEAD", "WARM_LEAD"]:
        return "interesado"

    return "pendiente"


def register_call_result(validated_data: Dict[str, Any]) -> dict:
    session = SessionLocal()
    try:
        lead_id = validated_data["lead_id"]

        # 1. Check that the Lead exists
        lead = session.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {
                "status": "error",
                "code": "NOT_FOUND",
                "details": f"Lead with ID '{lead_id}' does not exist in the database."
            }

        # 2. Resolve the Call row: reuse an existing one or create a new one
        call_id = validated_data.get("call_id")
        if call_id:
            call = session.query(Call).filter(Call.id == call_id, Call.lead_id == lead_id).first()
            if not call:
                return {
                    "status": "error",
                    "code": "NOT_FOUND",
                    "details": f"Call with ID '{call_id}' does not exist for lead '{lead_id}'."
                }
        else:
            call = Call(
                lead_id=lead_id,
                call_status=validated_data["call_state"],
                durations_seconds=validated_data.get("duration_seconds", 0) or 0,
            )
            session.add(call)
            session.flush()  # populates call.id before we use it below

        # 3. Compute new lead status and increment attempts
        new_status = determine_new_lead_status(validated_data["lead_classification"])
        lead.status = new_status
        lead.attempts_counts_today += 1

        # 4. Insert the prediction record
        new_prediction = AgentPrediction(
            lead_id=lead_id,
            call_id=call.id,
            call_state=validated_data["call_state"],
            lead_classification=validated_data["lead_classification"],
            lead_interest_level=validated_data["lead_interest_level"],
            classification_reason=validated_data.get("classification_reason"),
            recommended_next_action=validated_data.get("recommended_next_action"),
            observations=validated_data.get("observations"),  # stored directly as JSONB
        )
        session.add(new_prediction)

        # 5. Commit the whole transaction
        session.commit()

        # 6. Optional sales alert
        if validated_data["lead_interest_level"] == "ALTO" or validated_data["lead_classification"] in ["HOT_LEAD", "HOT"]:
            print("ALERTA IMPORTANTE CLIENTE QUE QUIERE COMPRAR DETECTADO")


        return {
            "status": "success",
            "message": "Result registered successfully.",
            "lead_id": lead_id,
            "call_id": call.id,
            "new_lead_status": new_status
        }

    except Exception as e:
        session.rollback()  # Rolls back the transaction if anything fails
        return {
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "details": f"Unexpected database error: {str(e)}",
        }
    finally:
        session.close()  # Releases the session connection




def alert_personal():
    print("se ha detectado un cliente con mucho potencial")
    print("iniciar notificacion a operador")

# ==========================================
# 6. MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    # Create tables if they don't exist yet
    #initialize_database()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, "resultado_llamada.json")
    # 1. Load and validate
    raw_data = load_data(json_path)
    validated_data = validate_data(raw_data)
    print("Validation completed successfully.")

    # 2. Persist through the ORM
    #response = register_call_result(validated_data)
    #print("Server response:")
    #print(json.dumps(response, indent=2, ensure_ascii=False))