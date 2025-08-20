"""
Modelos SQLAlchemy para el sistema de extracción de filings N-CSR.
Refleja el esquema de base de datos granular propuesto en el roadmap,
permitiendo un almacenamiento detallado de metadatos, documentos,
secciones, tablas y datos XBRL.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON, Boolean,
    Date, DECIMAL
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Dict, Any, List
from datetime import datetime
import enum

Base = declarative_base()

# --- Enums para Tipos y Estados ---

class ProcessingTier(str, enum.Enum):
    STANDARD = "standard"
    LIMITED = "limited"
    MINIMAL = "minimal"
    DEAD_LETTER = "dead_letter"

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

# --- Modelos Principales ---

class Filing(Base):
    """
    Modelo principal para un filing. Contiene metadatos clave y el estado general
    del procesamiento.
    """
    __tablename__ = "filings"

    filing_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    cik: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(512))
    form_type: Mapped[str] = mapped_column(String(32), index=True)
    filed_at: Mapped[datetime] = mapped_column(Date, index=True)
    period_of_report: Mapped[Optional[datetime]] = mapped_column(Date, index=True)
    
    # Nuevos campos para parsing SGML/XBRL
    acceptance_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    sic: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    state_of_incorporation: Mapped[Optional[str]] = mapped_column(String(10))
    fiscal_year_end: Mapped[Optional[str]] = mapped_column(String(10))
    business_address: Mapped[Optional[str]] = mapped_column(Text)
    business_phone: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Campos de estadísticas de parsing
    sgml_parsing_time: Mapped[Optional[float]] = mapped_column(Float)
    xbrl_parsing_time: Mapped[Optional[float]] = mapped_column(Float)
    integrated_parsing_time: Mapped[Optional[float]] = mapped_column(Float)
    xbrl_facts_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Flags de éxito del parsing
    sgml_parsed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    xbrl_parsed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    parsing_strategy: Mapped[Optional[str]] = mapped_column(String(50))  # "sgml_only", "xbrl_only", "hybrid"
    
    filing_url: Mapped[Optional[str]] = mapped_column(Text)
    filing_html_url: Mapped[Optional[str]] = mapped_column(Text)
    
    file_size_mb: Mapped[float] = mapped_column(Float, default=0.0)
    processing_status: Mapped[str] = mapped_column(String(50), default=ProcessingStatus.PENDING, index=True)
    processing_tier: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    documents: Mapped[List["FilingDocument"]] = relationship("FilingDocument", back_populates="filing", cascade="all, delete-orphan")
    fund_metadata: Mapped[Optional["FundMetadata"]] = relationship("FundMetadata", back_populates="filing", uselist=False, cascade="all, delete-orphan")
    sections: Mapped[List["NcsrSection"]] = relationship("NcsrSection", back_populates="filing", cascade="all, delete-orphan")
    tables: Mapped[List["NcsrTable"]] = relationship("NcsrTable", back_populates="filing", cascade="all, delete-orphan")
    xbrl_data: Mapped[Optional["NcsrXbrl"]] = relationship("NcsrXbrl", back_populates="filing", uselist=False, cascade="all, delete-orphan")
    xbrl_facts: Mapped[List["XbrlFact"]] = relationship("XbrlFact", back_populates="filing", cascade="all, delete-orphan")
    processing_logs: Mapped[List["ProcessingLog"]] = relationship("ProcessingLog", back_populates="filing", cascade="all, delete-orphan")
    dead_letter_entry: Mapped[Optional["DeadLetterQueue"]] = relationship("DeadLetterQueue", back_populates="filing", uselist=False, cascade="all, delete-orphan")
    processing_result: Mapped[Optional["ProcessingResult"]] = relationship("ProcessingResult", back_populates="filing", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Filing(accession_number='{self.accession_number}', cik='{self.cik}', status='{self.processing_status}')>"

class FilingDocument(Base):
    """Documentos asociados a un filing (HTML, XML, PDF, etc.)."""
    __tablename__ = "filing_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(Text)
    document_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="documents")

class FundMetadata(Base):
    """Metadatos específicos del fondo extraídos del filing."""
    __tablename__ = "fund_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), unique=True, index=True)
    fund_name: Mapped[Optional[str]] = mapped_column(String(512))
    total_net_assets: Mapped[Optional[float]] = mapped_column(DECIMAL(20, 2))
    shares_outstanding: Mapped[Optional[int]] = mapped_column(Integer)
    nav_per_share: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 4))
    expense_ratio: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 4))
    portfolio_date: Mapped[Optional[datetime]] = mapped_column(Date)
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="fund_metadata")

class NcsrSection(Base):
    """Secciones de texto extraídas del filing."""
    __tablename__ = "ncsr_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), index=True)
    section_name: Mapped[str] = mapped_column(String(256))
    section_type: Mapped[str] = mapped_column(String(50))  # 'portfolio', 'performance', etc.
    text_clean: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="sections")

class NcsrTable(Base):
    """Una tabla extraída de una sección del filing."""
    __tablename__ = "ncsr_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), index=True)
    table_type: Mapped[str] = mapped_column(String(100))  # 'portfolio_holdings', etc.
    caption: Mapped[Optional[str]] = mapped_column(String(512))
    table_html: Mapped[str] = mapped_column(Text)
    row_count: Mapped[int] = mapped_column(Integer)
    column_count: Mapped[int] = mapped_column(Integer)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="tables")
    rows: Mapped[List["NcsrTableRow"]] = relationship("NcsrTableRow", back_populates="table", cascade="all, delete-orphan")

class NcsrTableRow(Base):
    """Una fila de una tabla, normalizada en formato largo."""
    __tablename__ = "ncsr_table_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("ncsr_tables.id"), index=True)
    row_index: Mapped[int] = mapped_column(Integer)
    col_name: Mapped[str] = mapped_column(String(256))
    col_value: Mapped[str] = mapped_column(Text)
    col_type: Mapped[str] = mapped_column(String(50))  # 'currency', 'percentage', 'text'

    table: Mapped["NcsrTable"] = relationship("NcsrTable", back_populates="rows")

class NcsrXbrl(Base):
    """Datos extraídos del componente XBRL de un filing."""
    __tablename__ = "ncsr_xbrl"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), unique=True, index=True)
    xbrl_url: Mapped[str] = mapped_column(Text)
    key_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    raw_xml: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="xbrl_data")


class XbrlFact(Base):
    """Tabla para almacenar hechos XBRL individuales."""
    __tablename__ = "xbrl_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), index=True)
    
    # Campos principales del hecho XBRL
    concept: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
    unit_ref: Mapped[Optional[str]] = mapped_column(String(50))
    context_ref: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Información de período y entidad
    period_start_date: Mapped[Optional[datetime]] = mapped_column(Date)
    period_end_date: Mapped[Optional[datetime]] = mapped_column(Date)
    period_instant: Mapped[Optional[datetime]] = mapped_column(Date)
    entity_identifier: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Metadatos numéricos
    decimals: Mapped[Optional[int]] = mapped_column(Integer)
    scale: Mapped[Optional[int]] = mapped_column(Integer)
    precision: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Atributos adicionales como JSON
    additional_attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="xbrl_facts")

class ProcessingLog(Base):
    """Log detallado de las operaciones de procesamiento para trazabilidad."""
    __tablename__ = "processing_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[Optional[int]] = mapped_column(ForeignKey("filings.filing_id"), index=True)
    operation: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="processing_logs")

# --- Modelos de Soporte (ya existentes, pero mantenidos) ---

class ProcessingResult(Base):
    """Modelo para resultados de procesamiento (resumen)."""
    __tablename__ = "processing_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), unique=True, nullable=False, index=True)
    processing_tier: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    table_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    section_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="processing_result")

class DeadLetterQueue(Base):
    """Modelo para cola de reintentos de filings fallidos."""
    __tablename__ = "dead_letter_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.filing_id"), unique=True, nullable=False, index=True)
    failure_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    failure_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    original_tier: Mapped[Optional[str]] = mapped_column(String(20))
    file_size_mb: Mapped[float] = mapped_column(Float, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    retry_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_attempt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    next_retry: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    suggested_tier: Mapped[Optional[str]] = mapped_column(String(20))
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    filing: Mapped["Filing"] = relationship("Filing", back_populates="dead_letter_entry")

class ProcessingMetricsDaily(Base):
    """Modelo para métricas diarias agregadas."""
    __tablename__ = "processing_metrics_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, unique=True, nullable=False, index=True)
    total_files_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_processing_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_tables_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dead_lettered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
