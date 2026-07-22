from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey, create_engine
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pydantic import BaseModel, Field, ValidationError

Base = declarative_base()

# ==========================================
# 1. TABLAS SQLALCHEMY (ORM)
# ==========================================

class LeadModel(Base):
    __tablename__ = "leads"

    id = Column(String(50), primary_key=True)
    company_name = Column(String(150), nullable=True)
    contact_name = Column(String(150), nullable=True)
    phone_number = Column(String(30), nullable=True)
    region_city = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    preferred_language = Column(String(10), default="es")
    status = Column(String(50), default="PENDIENTE")
    attempts_counts_today = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación uno-a-muchos con los resultados de llamadas
    results = relationship("CallResultModel", back_populates="lead", cascade="all, delete-orphan")


class CallResultModel(Base):
    __tablename__ = "call_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(50), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    estado_llamada = Column(String(50), nullable=False)
    clasificacion = Column(String(50), nullable=False)
    nivel_interes = Column(String(20), nullable=False)
    motivo = Column(Text, nullable=True)
    siguiente_accion = Column(Text, nullable=True)
    observaciones = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("LeadModel", back_populates="results")



class Message(BaseModel):
    role: str
    content: str


class Observations(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    industry: Optional[str] = None
    respuesta_textual_usuario: Optional[str] = None
    transcripcion: List[Message] = Field(default_factory=list)


class CallResultSchema(BaseModel):
    lead_id: str
    estado_llamada: str
    clasificacion: str
    nivel_interes: str
    motivo: str
    siguiente_accion: str
    observaciones: Observations