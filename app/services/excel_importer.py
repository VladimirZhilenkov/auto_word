"""
Excel import service for importing data from 'Для программки.xlsx'.
Handles importing both training programs and listeners from Excel files.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..database.connection import DatabaseSession
from ..database.models import Listener, Program, ProgramListener


class ExcelImporter:
    """
    Import data from Excel file 'Для программки.xlsx'.
    
    Handles two sheet types:
    - Sheet 1: Training Programs (Программы обучения)
    - Sheet 2: Listeners (Слушатели)
    """
    
    # Column mapping for Listeners sheet (lowercase for matching)
    LISTENERS_MAPPING = {
        # Full name variations
        'фамилия имя отчество': 'full_name',
        'фио': 'full_name',
        'ф.и.о.': 'full_name',
        'ф.и.о': 'full_name',
        '№ п/п': 'number',
        '№п/п': 'number',
        '№': 'number',
        'n': 'number',
        # Position
        'должность': 'position',
        # Workplace variations
        'наименование суда/место работы': 'workplace',
        'наименование суда': 'workplace',
        'место работы': 'workplace',
        'организация': 'workplace',
        # Region variations
        'наименование субъекта российской федерации': 'region',
        'субъект российской федерации': 'region',
        'субъект рф': 'region',
        'регион': 'region',
    }
    
    # Column mapping for Programs sheet (lowercase for matching)
    PROGRAMS_MAPPING = {
        '№': 'number',
        'n': 'number',
        'наименование программы': 'program_name',
        'название программы': 'program_name',
        'программа': 'program_name',
        'краткое наименование программы': 'program_short_name',
        'краткое наименование': 'program_short_name',
        'краткое название': 'program_short_name',
        'основание для обучения': 'training_basis',
        'основание': 'training_basis',
        'период обучения': 'training_period',
        'период': 'training_period',
        'объем программы': 'program_volume',
        'объем': 'program_volume',
        'объём программы': 'program_volume',
        'форма обучения': 'education_form',
        'форма': 'education_form',
        'формат обучения': 'education_format',
        'формат': 'education_format',
        'категория слушателей': 'listener_category',
        'категория': 'listener_category',
        'дата отчисления': 'expulsion_date',
    }
    
    def __init__(self):
        """Initialize the importer."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def import_listeners(
        self, 
        file_path: str, 
        sheet_name: Any = 0,
        program_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Import listeners from Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index (default: first sheet)
            program_id: Optional program ID to associate listeners with
        
        Returns:
            Dictionary with import results:
            {
                'success': bool,
                'imported': int,
                'skipped': int,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        self.errors = []
        self.warnings = []
        imported = 0
        skipped = 0
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            if df.empty:
                return {
                    'success': False,
                    'imported': 0,
                    'skipped': 0,
                    'errors': ['Файл пустой или не содержит данных'],
                    'warnings': []
                }
            
            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()
            
            with DatabaseSession() as session:
                for idx, row in df.iterrows():
                    row_num = idx + 2  # Excel row number (1-indexed + header)
                    
                    try:
                        listener = self._create_listener(row)
                        
                        if listener:
                            # Check for duplicates
                            existing = session.query(Listener).filter(
                                Listener.last_name == listener.last_name,
                                Listener.first_name == listener.first_name,
                                Listener.middle_name == listener.middle_name
                            ).first()
                            
                            if existing:
                                self.warnings.append(
                                    f"Строка {row_num}: Слушатель '{listener.full_name}' "
                                    f"уже существует (ID: {existing.id})"
                                )
                                skipped += 1
                                
                                # Associate existing listener with program if needed
                                if program_id:
                                    self._associate_with_program(
                                        session, existing.id, program_id, imported + 1
                                    )
                            else:
                                session.add(listener)
                                session.flush()  # Get the ID
                                
                                # Associate with program if specified
                                if program_id:
                                    self._associate_with_program(
                                        session, listener.id, program_id, imported + 1
                                    )
                                
                                imported += 1
                        else:
                            skipped += 1
                            
                    except ValueError as e:
                        self.errors.append(f"Строка {row_num}: {str(e)}")
                        skipped += 1
                    except Exception as e:
                        self.errors.append(f"Строка {row_num}: Ошибка - {str(e)}")
                        skipped += 1
                
                session.commit()
            
            return {
                'success': True,
                'imported': imported,
                'skipped': skipped,
                'errors': self.errors,
                'warnings': self.warnings
            }
        
        except FileNotFoundError:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'errors': [f'Файл не найден: {file_path}'],
                'warnings': []
            }
        except Exception as e:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'errors': [f'Ошибка чтения файла: {str(e)}'],
                'warnings': []
            }
    
    def _create_listener(self, row: pd.Series) -> Optional[Listener]:
        """
        Create Listener from Excel row.
        
        Args:
            row: pandas Series with row data
            
        Returns:
            Listener instance or None if row should be skipped
        """
        data = {}
        
        # Map Excel columns to fields
        for excel_col, field in self.LISTENERS_MAPPING.items():
            if excel_col in row.index and pd.notna(row[excel_col]):
                value = str(row[excel_col]).strip()
                if value:
                    data[field] = value
        
        # Skip if no data found
        if not data or (len(data) == 1 and 'number' in data):
            return None
        
        # Split full_name into parts
        if 'full_name' in data:
            parts = data['full_name'].split()
            
            if len(parts) >= 1:
                data['last_name'] = parts[0]
            if len(parts) >= 2:
                data['first_name'] = parts[1]
            if len(parts) >= 3:
                # Join remaining parts as middle name (for compound middle names)
                data['middle_name'] = ' '.join(parts[2:])
            
            del data['full_name']
        
        # Remove number field (not stored in database)
        data.pop('number', None)
        
        # Validate required fields
        if 'last_name' not in data:
            raise ValueError("Фамилия обязательна для заполнения")
        if 'first_name' not in data:
            raise ValueError("Имя обязательно для заполнения")
        
        return Listener(**data)
    
    def _associate_with_program(
        self, 
        session, 
        listener_id: int, 
        program_id: int, 
        order_number: int
    ):
        """Associate a listener with a program."""
        # Check if association already exists
        existing = session.query(ProgramListener).filter(
            ProgramListener.program_id == program_id,
            ProgramListener.listener_id == listener_id
        ).first()
        
        if not existing:
            assoc = ProgramListener(
                program_id=program_id,
                listener_id=listener_id,
                order_number=order_number,
                enrollment_date=datetime.now().date()
            )
            session.add(assoc)
    
    def import_programs(
        self, 
        file_path: str, 
        sheet_name: Any = 0
    ) -> Dict[str, Any]:
        """
        Import training programs from Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index (default: first sheet)
        
        Returns:
            Dictionary with import results
        """
        self.errors = []
        self.warnings = []
        imported = 0
        skipped = 0
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            if df.empty:
                return {
                    'success': False,
                    'imported': 0,
                    'skipped': 0,
                    'errors': ['Файл пустой или не содержит данных'],
                    'warnings': []
                }
            
            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()
            
            with DatabaseSession() as session:
                for idx, row in df.iterrows():
                    row_num = idx + 2
                    
                    try:
                        program = self._create_program(row)
                        
                        if program:
                            # Check for duplicates by name
                            existing = session.query(Program).filter(
                                Program.program_name == program.program_name
                            ).first()
                            
                            if existing:
                                self.warnings.append(
                                    f"Строка {row_num}: Программа '{program.display_name}' "
                                    f"уже существует (ID: {existing.id})"
                                )
                                skipped += 1
                            else:
                                session.add(program)
                                imported += 1
                        else:
                            skipped += 1
                            
                    except ValueError as e:
                        self.errors.append(f"Строка {row_num}: {str(e)}")
                        skipped += 1
                    except Exception as e:
                        self.errors.append(f"Строка {row_num}: Ошибка - {str(e)}")
                        skipped += 1
                
                session.commit()
            
            return {
                'success': True,
                'imported': imported,
                'skipped': skipped,
                'errors': self.errors,
                'warnings': self.warnings
            }
        
        except FileNotFoundError:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'errors': [f'Файл не найден: {file_path}'],
                'warnings': []
            }
        except Exception as e:
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'errors': [f'Ошибка чтения файла: {str(e)}'],
                'warnings': []
            }
    
    def _create_program(self, row: pd.Series) -> Optional[Program]:
        """
        Create Program from Excel row.
        
        Args:
            row: pandas Series with row data
            
        Returns:
            Program instance or None if row should be skipped
        """
        data = {}
        
        # Map Excel columns to fields
        for excel_col, field in self.PROGRAMS_MAPPING.items():
            if excel_col in row.index and pd.notna(row[excel_col]):
                value = row[excel_col]
                
                # Handle date fields
                if field == 'expulsion_date':
                    value = self._parse_date(value)
                else:
                    value = str(value).strip() if value else None
                
                if value:
                    data[field] = value
        
        # Skip if no data found
        if not data or (len(data) == 1 and 'number' in data):
            return None
        
        # Remove number field
        data.pop('number', None)
        
        # Validate required fields
        if 'program_name' not in data:
            raise ValueError("Наименование программы обязательно для заполнения")
        
        return Program(**data)
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse date from various formats."""
        if pd.isna(value):
            return None
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            value = value.strip()
            
            # Try various date formats
            date_formats = [
                '%d.%m.%Y',
                '%d/%m/%Y',
                '%Y-%m-%d',
                '%d-%m-%Y',
                '%d.%m.%y',
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        
        return None
    
    def get_sheet_names(self, file_path: str) -> List[str]:
        """Get list of sheet names from Excel file."""
        try:
            xl = pd.ExcelFile(file_path)
            return xl.sheet_names
        except Exception:
            return []
    
    def preview_data(
        self, 
        file_path: str, 
        sheet_name: Any = 0, 
        max_rows: int = 10
    ) -> Dict[str, Any]:
        """
        Preview data from Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index
            max_rows: Maximum number of rows to preview
        
        Returns:
            Dictionary with preview data
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
            
            return {
                'success': True,
                'columns': list(df.columns),
                'row_count': len(df),
                'data': df.to_dict('records')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
