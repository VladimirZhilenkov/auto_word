"""
Document Registration Service for tracking and numbering generated documents.

Provides functionality for:
- Registering generated Word documents
- Automatic sequential numbering
- Document tracking and history
- Register exports
"""

from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from ..database.connection import DatabaseSession
from ..database.models import DocumentRegister


class DocumentRegistrationService:
    """
    Service for managing document registration with automatic numbering.
    """
    
    # Document type prefixes for numbering
    TYPE_PREFIXES = {
        'enrollment': 'Зач',      # Зачисление (Enrollment)
        'admission': 'Доп',       # Допуск (Admission)
        'graduation': 'Отч',      # Отчисление (Graduation)
        'order': 'Пр',            # Приказ (Order)
        'other': 'Док',           # Другие документы
    }
    
    def __init__(self):
        """Initialize the registration service."""
        pass
    
    def register_document(
        self,
        document_type: str,
        document_path: str,
        listener_name: str,
        listener_id: Optional[int] = None,
        program_id: Optional[int] = None,
        registration_date: Optional[date] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Register a generated document with automatic numbering.
        
        Args:
            document_type: Type of document (enrollment, admission, graduation, order)
            document_path: Full path to the generated document
            listener_name: Full name of the listener
            listener_id: ID of associated listener (optional)
            program_id: ID of associated program (optional)
            registration_date: Registration date (default: today)
            metadata: Additional metadata dictionary
        
        Returns:
            Assigned document number
        """
        with DatabaseSession() as session:
            # Get next sequential number for this document type
            last_register = session.query(DocumentRegister).filter_by(
                document_type=document_type
            ).order_by(DocumentRegister.number.desc()).first()
            
            next_number = (last_register.number + 1) if last_register else 1
            
            # Create register entry
            register_entry = DocumentRegister(
                number=next_number,
                document_type=document_type,
                document_path=str(document_path),
                listener_id=listener_id,
                program_id=program_id,
                listener_name=listener_name,
                registration_date=registration_date or date.today(),
                extra_data=json.dumps(metadata or {})
            )
            
            session.add(register_entry)
            # commit is handled by context manager
            
            return next_number
    
    def get_next_number(self, document_type: str) -> int:
        """
        Get the next sequential number for a document type.
        
        Args:
            document_type: Type of document
        
        Returns:
            Next sequential number
        """
        with DatabaseSession() as session:
            last_register = session.query(DocumentRegister).filter_by(
                document_type=document_type
            ).order_by(DocumentRegister.number.desc()).first()
            
            return (last_register.number + 1) if last_register else 1
    
    def get_register_entries(
        self,
        document_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get register entries filtered by criteria.
        
        Args:
            document_type: Filter by document type (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            limit: Limit number of results (optional)
        
        Returns:
            List of register entry dictionaries
        """
        with DatabaseSession() as session:
            query = session.query(DocumentRegister)
            
            if document_type:
                query = query.filter_by(document_type=document_type)
            
            if start_date:
                query = query.filter(DocumentRegister.registration_date >= start_date)
            
            if end_date:
                query = query.filter(DocumentRegister.registration_date <= end_date)
            
            query = query.order_by(DocumentRegister.number.desc())
            
            if limit:
                query = query.limit(limit)
            
            entries = []
            for entry in query.all():
                entries.append({
                    'number': entry.number,
                    'type': entry.document_type,
                    'path': entry.document_path,
                    'listener_name': entry.listener_name,
                    'registration_date': entry.registration_date,
                    'listener_id': entry.listener_id,
                    'program_id': entry.program_id,
                    'extra_data': json.loads(entry.extra_data) if entry.extra_data else {}
                })
            
            return entries
    
    def get_register_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about registered documents.
        
        Returns:
            Dictionary with statistics
        """
        with DatabaseSession() as session:
            total = session.query(DocumentRegister).count()
            
            stats = {
                'total_documents': total,
                'by_type': {}
            }
            
            # Count by document type
            for doc_type in self.TYPE_PREFIXES.keys():
                count = session.query(DocumentRegister).filter_by(
                    document_type=doc_type
                ).count()
                if count > 0:
                    stats['by_type'][doc_type] = count
            
            # Latest registration
            latest = session.query(DocumentRegister).order_by(
                DocumentRegister.created_at.desc()
            ).first()
            
            if latest:
                stats['latest_registration'] = {
                    'number': latest.number,
                    'date': latest.registration_date.isoformat(),
                    'listener': latest.listener_name
                }
            
            return stats
    
    def export_register_to_excel(
        self,
        output_path: str,
        document_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> bool:
        """
        Export register to Excel file.
        
        Args:
            output_path: Path to output Excel file
            document_type: Filter by document type (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            
            entries = self.get_register_entries(
                document_type=document_type,
                start_date=start_date,
                end_date=end_date
            )
            
            if not entries:
                return False
            
            df = pd.DataFrame([
                {
                    'Номер': entry['number'],
                    'Тип документа': entry['type'],
                    'ФИО': entry['listener_name'],
                    'Дата регистрации': entry['registration_date'],
                    'Путь к файлу': entry['path']
                }
                for entry in entries
            ])
            
            df.to_excel(output_path, index=False, sheet_name='Регистр')
            
            return True
        
        except ImportError:
            print("pandas not available for Excel export")
            return False
        except Exception as e:
            print(f"Error exporting register: {e}")
            return False
    
    def get_formatted_number(self, document_type: str, number: int) -> str:
        """
        Get formatted document number with prefix.
        
        Args:
            document_type: Type of document
            number: Sequential number
        
        Returns:
            Formatted number like "Зач-001" or "Пр-025"
        """
        prefix = self.TYPE_PREFIXES.get(document_type, 'Док')
        return f"{prefix}-{number:04d}"

