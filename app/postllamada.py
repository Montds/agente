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
# 1.  TABLAS SQLALCHEMY (ORM)
#     tablas de la base de datos: leads, calls, agent_predictions
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
    prefered_language = Column(String(10), default="es")
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pendiente")
    attempts_counts_today = Column(Integer, default=0)

    #relaciones con las tablas Call y agent_predictions
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
# 2. PYDANTIC SCHEMAS para validar los tipos de datos
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

    duration_seconds: Optional[int] = 0  # esta la usaba era en la primera version del codigo, ya la podria quitar


# ==========================================
# 3. configuracion de la base de datos
# ==========================================

DATABASE_URL = "postgresql://root:12345678@localhost:5432/bd_sistema_empresa"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


#este ya no la uso lo podria quitar
def initialize_database():
    """crea la base de datos si no existe, esta lo usaba era la primera version del codigo"""
    Base.metadata.create_all(bind=engine)


# ==========================================
# 4. LOADING AND VALIDATION FUNCTIONS
# ==========================================

def load_data(file_path: str) -> dict:
    """se carga el archivo json que esta en la ruta file_path"""
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

def validate_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """se validan los datos para que cumplan el formato correcto"""
    if not isinstance(data, dict):
        raise ValueError("The 'data' parameter must be a valid dictionary.")
    enum_fields = ["call_state", "lead_classification", "lead_interest_level"]
    for field in enum_fields:
        if isinstance(data.get(field), str):
            data[field] = data[field].strip().upper()
    #se crea una instancia de AgentPredictionSchema usando los datos del json
    try:
        validated_obj = AgentPredictionSchema(**data)
        return validated_obj.model_dump()
    except ValidationError as ve:
        raise ValueError(f"Pydantic validation error: {ve.errors()}")

def determine_new_lead_status(classification: str) -> str:
    """" se asigna el estado del lead tomando en cuenta la clasificacion del lead """
    normalized = classification.strip().upper()
    if normalized in [ "COLD_LEAD"]:
        return "no_interesado"
    elif normalized in ["NOT_QUALIFIED", "NO_CONTACTADO" , "CALLBACK_REQUESTED", "RESPUESTA_AMBIGUA"]:
        return "llamar_despues"
    elif normalized in ["HOT_LEAD", "WARM_LEAD"]:
        return "interesado"

def register_call_result(validated_data: Dict[str, Any]) -> dict:
    """se guarda el resultado en la tabla agent_predicitons"""
    session = SessionLocal()
    try:
        lead_id = validated_data["lead_id"]
        lead = session.query(Lead).filter(Lead.id == lead_id).first()
        call_id = validated_data.get("call_id")
        # se asigna el nuevo estado del lead
        new_status = determine_new_lead_status(validated_data["lead_classification"])
        lead.status = new_status
        lead.attempts_counts_today += 1
        # se inserta el resultado de la prediccion del agente en la tabla "agents_predictions
        new_prediction = AgentPrediction(
            lead_id=lead_id,
            call_id=call_id,
            call_state=validated_data["call_state"],
            lead_classification=validated_data["lead_classification"],
            lead_interest_level=validated_data["lead_interest_level"],
            classification_reason=validated_data.get("classification_reason"),
            recommended_next_action=validated_data.get("recommended_next_action"),
            observations=validated_data.get("observations"),  # stored directly as JSONB
        )
        session.add(new_prediction)
        #se confirman todos los cambios hechos
        session.commit()
        is_hot_lead  = validated_data["lead_classification"] in ["HOT_LEAD", "HOT"]
        return {
            "status": "success",
            "message": "Result registered successfully.",
            "lead_id": lead_id,
            "call_id": call_id,
            "new_lead_status": new_status,
            "is_hot_lead": is_hot_lead
        }
    except Exception as e:
        session.rollback()
        return {
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "details": f"Unexpected database error: {str(e)}",
        }
    finally:
        session.close()

def trigger_hot_lead_alert(result: dict) -> None:
    """se alerta si es un un hot lead"""
    if result["status"] == "success":
        if result["is_hot_lead"]:
            print("==========================IMPORTANT ALERT: HOT LEAD DETECTADO==========================")

if __name__ == "__main__":
    print("asignando ruta del json de resultados")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, "jsons/resultado_llamada.json")
    print("cargando el json")
    raw_data = load_data(json_path)
    print("validando datos del json")
    validated_data = validate_data(raw_data)
    print("insertando el resultado en la base de datos")
    response = register_call_result(validated_data)
    print("Server response:")
    print(json.dumps(response, indent=2, ensure_ascii=False))
    #se lanza la alerta si es un cliente potencial
    trigger_hot_lead_alert(response)