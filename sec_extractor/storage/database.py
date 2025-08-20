"""
DatabaseManager con soporte para SQLite y PostgreSQL
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from .models import (
    Base, Filing, ProcessingResult, DeadLetterQueue, FundMetadata, 
    FilingDocument, NcsrSection, NcsrTable, NcsrTableRow, NcsrXbrl, ProcessingLog
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manager de base de datos con soporte para SQLite y PostgreSQL"""

    def __init__(self, database_url: str):
        """
        Inicializa el DatabaseManager con configuración apropiada según el tipo de BD
        """
        self.database_url = database_url

        # Configuración específica según tipo de base de datos
        engine_kwargs = {'echo': False}
        if not database_url.startswith('sqlite'):
            engine_kwargs.update({
                'pool_size': 10,
                'max_overflow': 20,
                'pool_pre_ping': True
            })

        try:
            self.engine = create_engine(database_url, **engine_kwargs)
            self.SessionLocal = sessionmaker(bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
            logger.info(
                f"DatabaseManager initialized with {'SQLite' if database_url.startswith('sqlite') else 'PostgreSQL'}"
            )
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def get_session(self) -> Session:
        """Obtiene una nueva sesión de base de datos"""
        return self.SessionLocal()

    def create_or_update_filing(self, filing_meta: Dict[str, Any]) -> int:
        """Crea o actualiza un filing en la base de datos"""
        session = self.get_session()
        try:
            accession = filing_meta.get("accession_number")
            if not accession:
                raise ValueError("accession_number is required in filing_meta")

            existing_filing = session.query(Filing).filter(Filing.accession_number == accession).first()
            if existing_filing:
                for key, value in filing_meta.items():
                    if hasattr(existing_filing, key):
                        setattr(existing_filing, key, value)
                existing_filing.updated_at = datetime.utcnow()
                session.commit()
                logger.debug(f"Updated filing {existing_filing.id}")
                return existing_filing.id

            new_filing = Filing(
                accession_number=accession,
                cik=filing_meta.get("cik"),
                company_name=filing_meta.get("company_name"),
                form_type=filing_meta.get("form_type"),
                filing_date=filing_meta.get("filing_date"),
                period_of_report=filing_meta.get("period_of_report"),
                file_size_mb=filing_meta.get("file_size_mb", 0.0),
                filing_html_url=filing_meta.get("filing_html_url"),
                
                # Nuevos campos SGML/XBRL
                acceptance_datetime=filing_meta.get("acceptance_datetime"),
                sic=filing_meta.get("sic"),
                state_of_incorporation=filing_meta.get("state_of_incorporation"),
                fiscal_year_end=filing_meta.get("fiscal_year_end"),
                business_address=filing_meta.get("business_address"),
                business_phone=filing_meta.get("business_phone"),
                
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_filing)
            session.commit()
            logger.debug(f"Created new filing {new_filing.id}")
            return new_filing.id
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error creating/updating filing: {e}")
            raise
        finally:
            session.close()

    def update_filing_processing_status(self, filing_id: int, tier: str, status: str) -> bool:
        """Actualiza el status de procesamiento de un filing"""
        session = self.get_session()
        try:
            filing = session.query(Filing).filter(Filing.id == filing_id).first()
            if filing:
                filing.processing_tier = tier
                filing.processing_status = status
                filing.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating filing status: {e}")
            return False
        finally:
            session.close()

    def save_processing_result(self, filing_id: int, result: Dict[str, Any], tier: str) -> bool:
        """Guarda el resultado del procesamiento granular."""
        session = self.get_session()
        try:
            # 1. Actualizar Filing
            filing = session.query(Filing).filter(Filing.id == filing_id).first()
            if not filing:
                logger.error(f"Filing with id {filing_id} not found for saving results.")
                return False
            
            filing.processing_status = "completed" if result.get("success") else "failed"
            filing.processing_tier = tier
            filing.updated_at = datetime.utcnow()

            # 2. Guardar FundMetadata
            if result.get("fund_metadata"):
                meta = result["fund_metadata"]
                fund_metadata = FundMetadata(
                    filing_id=filing_id,
                    fund_name=meta.get("fund_name"),
                    total_net_assets=meta.get("total_net_assets"),
                    raw_data=meta
                )
                session.add(fund_metadata)

            # 3. Guardar Secciones
            for sec_data in result.get("sections", []):
                section = NcsrSection(filing_id=filing_id, **sec_data)
                session.add(section)

            # 4. Guardar Tablas y sus filas
            for table_data in result.get("tables", []):
                rows = table_data.pop("rows", [])
                table = NcsrTable(filing_id=filing_id, **table_data)
                session.add(table)
                session.flush() # Para obtener el ID de la tabla
                
                for row_data in rows:
                    row = NcsrTableRow(table_id=table.id, **row_data)
                    session.add(row)

            # 5. Guardar Resumen en ProcessingResult
            processing_summary = ProcessingResult(
                filing_id=filing_id,
                processing_tier=tier,
                success=result.get("success", False),
                tables_extracted=result.get("table_count", 0),
                sections_found=result.get("section_count", 0),
                processing_duration=result.get("processing_duration", 0.0),
                result_data=result, # Guardar el JSON completo por si acaso
                created_at=datetime.utcnow()
            )
            session.add(processing_summary)

            session.commit()
            logger.debug(f"Saved granular processing result for filing {filing_id}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving granular processing result: {e}")
            return False
        finally:
            session.close()

    def get_filing_by_accession(self, accession_number: str) -> Optional[Dict[str, Any]]:
        """Obtiene un filing por su accession number"""
        session = self.get_session()
        try:
            filing = session.query(Filing).filter(Filing.accession_number == accession_number).first()
            if filing:
                return {
                    "id": filing.id,
                    "accession_number": filing.accession_number,
                    "cik": filing.cik,
                    "company_name": filing.company_name,
                    "filing_date": filing.filing_date,
                    "period_end": filing.period_end,
                    "file_size_mb": filing.file_size_mb,
                    "processing_status": filing.processing_status,
                    "processing_tier": filing.processing_tier,
                    "created_at": filing.created_at,
                    "updated_at": filing.updated_at,
                }
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting filing by accession: {e}")
            return None
        finally:
            session.close()

    def get_daily_metrics(self, date: datetime = None) -> Dict[str, Any]:
        """Obtiene métricas diarias de procesamiento"""
        if date is None:
            date = datetime.utcnow().date()
        session = self.get_session()
        try:
            daily_results = session.query(ProcessingResult).filter(
                ProcessingResult.created_at >= datetime.combine(date, datetime.min.time()),
                ProcessingResult.created_at < datetime.combine(date, datetime.min.time()) + timedelta(days=1)
            ).all()

            metrics = {
                "date": date.isoformat(),
                "by_tier": {"standard": 0, "limited": 0, "minimal": 0},
                "totals": {
                    "processed": len(daily_results),
                    "successful": sum(1 for r in daily_results if r.success),
                    "failed": sum(1 for r in daily_results if not r.success),
                    "total_duration": sum(r.processing_duration for r in daily_results),
                    "total_tables": sum(r.tables_extracted for r in daily_results),
                },
            }

            for result in daily_results:
                if result.processing_tier in metrics["by_tier"]:
                    metrics["by_tier"][result.processing_tier] += 1

            return metrics
        except SQLAlchemyError as e:
            logger.error(f"Error getting daily metrics: {e}")
            return {}
        finally:
            session.close()

    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Limpia datos antiguos de la base de datos"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        session = self.get_session()
        try:
            old_results = session.query(ProcessingResult).filter(
                ProcessingResult.created_at < cutoff_date
            ).count()
            session.query(ProcessingResult).filter(
                ProcessingResult.created_at < cutoff_date
            ).delete()

            old_filings = session.query(Filing).filter(
                Filing.updated_at < cutoff_date,
                Filing.processing_status.in_(["completed", "failed"])
            ).count()
            session.query(Filing).filter(
                Filing.updated_at < cutoff_date,
                Filing.processing_status.in_(["completed", "failed"])
            ).delete()

            session.commit()
            cleanup_results = {"processing_results": old_results, "filings": old_filings}
            logger.info(f"Cleanup completed: {cleanup_results}")
            return cleanup_results
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error during cleanup: {e}")
            return {}
        finally:
            session.close()
