"""
Excel import service for importing data from Excel files.
Handles importing both training programs and listeners from Excel files.
Supports flexible column detection based on first row headers.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

import pandas as pd

from ..database.connection import DatabaseSession
from ..database.models import Listener, Program, ProgramListener


class ExcelImporter:
    """
    Import data from Excel files with flexible column detection.
    
    Automatically detects columns based on header names in the first row.
    Supports both exact matching and fuzzy matching for column names.
    """
    
    # Column mapping for Listeners sheet (lowercase keywords for matching)
    # Format: 'keyword': ('field_name', priority) - higher priority wins
    LISTENERS_KEYWORDS = {
        # Full name variations
        'фамилия имя отчество': ('full_name', 10),
        'фио': ('full_name', 9),
        'ф.и.о.': ('full_name', 8),
        'ф.и.о': ('full_name', 7),
        '№ п/п': ('number', 5),
        '№п/п': ('number', 5),
        'номер': ('number', 3),
        '№': ('number', 2),
        'n': ('number', 1),
        # Separate name parts
        'фамилия': ('last_name', 10),
        'имя': ('first_name', 10),
        'отчество': ('middle_name', 10),
        # Position
        'должность': ('position', 10),
        'место работы, должность': ('workplace', 10),  # Combined field - use as workplace
        # Workplace variations
        'наименование суда/место работы': ('workplace', 10),
        'наименование суда': ('workplace', 9),
        'место работы': ('workplace', 8),
        'организация': ('workplace', 7),
        'учреждение': ('workplace', 6),
        # Region variations
        'наименование субъекта российской федерации': ('region', 10),
        'субъект российской федерации': ('region', 9),
        'субъект рф': ('region', 8),
        'регион': ('region', 7),
        'область': ('region', 5),
        # Program reference
        'программа': ('program_name', 8),
        'наименование программы': ('program_name', 10),
        'краткое наименование программы': ('program_short_name', 10),
        # Contact info
        'телефон': ('mobile_phone', 5),
        'мобильный': ('mobile_phone', 8),
        'мобильный телефон': ('mobile_phone', 9),
        'мобильный телефон участника': ('mobile_phone', 10),
        'рабочий телефон': ('work_phone', 8),
        'рабочий телефон участника': ('work_phone', 10),
        'email': ('email', 10),
        'почта': ('email', 7),
        'эл. почта': ('email', 8),
        'эл. почта участника': ('email', 10),
        'электронная почта': ('email', 9),
        # Birth date
        'дата рождения': ('birth_date', 10),
        'дата рождения (дд. мм. гггг)': ('birth_date', 10),
        # Passport
        'паспорт': ('passport_series_number', 5),
        'серия и номер паспорта': ('passport_series_number', 10),
        'серия номер': ('passport_series_number', 8),
        'паспорт: серия, номер': ('passport_series_number', 10),
        'паспорт серия номер': ('passport_series_number', 9),
        'дата выдачи паспорта': ('passport_issue_date', 10),
        'паспорт: дата выдачи': ('passport_issue_date', 10),
        'паспорт:  дата выдачи': ('passport_issue_date', 10),  # with double space
        'кем выдан': ('passport_issued_by', 10),
        'паспорт: кем выдан': ('passport_issued_by', 10),
        'код подразделения': ('passport_department_code', 10),
        'паспорт: код-подразделения': ('passport_department_code', 10),
        'паспорт: код подразделения': ('passport_department_code', 10),
        # Addresses
        'адрес регистрации': ('registration_address', 10),
        'адрес прописки': ('registration_address', 9),
        'прописка': ('registration_address', 7),
        'место регистрации': ('registration_address', 8),
        'индекс место регистрации': ('registration_address', 10),
        'фактический адрес': ('actual_address', 10),
        'адрес проживания': ('actual_address', 9),
        'место фактического проживания': ('actual_address', 9),
        'почтовый индекс, место фактического проживания': ('actual_address', 10),
        # IDs
        'снилс': ('snils', 10),
        'инн': ('inn', 10),
        # Consent
        'принимаю условия обработки персональных данных': ('personal_data_consent', 10),
        'согласие на обработку': ('personal_data_consent', 8),
        'согласие': ('personal_data_consent', 6),
        # Notes
        'примечание': ('notes', 8),
        'примечания': ('notes', 8),
        'комментарий': ('notes', 7),
    }
    
    # Column mapping for Programs sheet (lowercase keywords for matching)
    PROGRAMS_KEYWORDS = {
        '№': ('number', 2),
        'n': ('number', 1),
        'номер': ('number', 3),
        'наименование программы': ('program_name', 10),
        'название программы': ('program_name', 9),
        'программа': ('program_name', 7),
        'краткое наименование программы': ('program_short_name', 10),
        'краткое наименование': ('program_short_name', 9),
        'краткое название': ('program_short_name', 8),
        'сокращенное название': ('program_short_name', 7),
        'основание для обучения': ('training_basis', 10),
        'основание': ('training_basis', 8),
        'период обучения': ('training_period', 10),
        'период': ('training_period', 7),
        'сроки обучения': ('training_period', 9),
        'объем программы': ('program_volume', 10),
        'объем': ('program_volume', 7),
        'объём программы': ('program_volume', 10),
        'объём': ('program_volume', 7),
        'часы': ('program_volume', 6),
        'количество часов': ('program_volume', 9),
        'форма обучения': ('education_form', 10),
        'форма': ('education_form', 6),
        'формат обучения': ('education_format', 10),
        'формат': ('education_format', 6),
        'категория слушателей': ('listener_category', 10),
        'категория': ('listener_category', 7),
        'дата отчисления': ('expulsion_date', 10),
        'дата завершения': ('expulsion_date', 9),
    }
    
    # Field display names for UI
    FIELD_DISPLAY_NAMES = {
        'number': '№ п/п',
        'full_name': 'ФИО (полностью)',
        'last_name': 'Фамилия',
        'first_name': 'Имя',
        'middle_name': 'Отчество',
        'position': 'Должность',
        'workplace': 'Место работы',
        'region': 'Субъект РФ',
        'program_name': 'Программа',
        'program_short_name': 'Краткое название программы',
        'mobile_phone': 'Мобильный телефон',
        'work_phone': 'Рабочий телефон',
        'email': 'Email',
        'birth_date': 'Дата рождения',
        'passport_series_number': 'Серия и номер паспорта',
        'passport_issue_date': 'Дата выдачи паспорта',
        'passport_issued_by': 'Кем выдан паспорт',
        'passport_department_code': 'Код подразделения',
        'registration_address': 'Адрес регистрации',
        'actual_address': 'Фактический адрес',
        'snils': 'СНИЛС',
        'inn': 'ИНН',
        'notes': 'Примечания',
        'training_basis': 'Основание обучения',
        'training_period': 'Период обучения',
        'program_volume': 'Объем программы',
        'education_form': 'Форма обучения',
        'education_format': 'Формат обучения',
        'listener_category': 'Категория слушателей',
        'expulsion_date': 'Дата отчисления',
    }
    
    def __init__(self):
        """Initialize the importer."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.detected_mapping: Dict[str, str] = {}  # Excel column -> field name
    
    def _detect_columns(
        self, 
        columns: List[str], 
        keywords: Dict[str, Tuple[str, int]]
    ) -> Dict[str, str]:
        """
        Detect field mapping from Excel column headers using keyword matching.
        
        Args:
            columns: List of column names from Excel
            keywords: Dictionary of keyword -> (field_name, priority)
            
        Returns:
            Dictionary mapping Excel column name -> field name
        """
        mapping = {}
        field_assignments = {}  # field -> (column, priority)
        
        for col in columns:
            col_lower = str(col).lower().strip()
            
            best_match = None
            best_priority = -1
            
            # Try exact match first
            if col_lower in keywords:
                field, priority = keywords[col_lower]
                best_match = field
                best_priority = priority
            else:
                # Try partial/fuzzy match
                for keyword, (field, priority) in keywords.items():
                    # Check if keyword is contained in column name
                    if keyword in col_lower or col_lower in keyword:
                        if priority > best_priority:
                            best_match = field
                            best_priority = priority
            
            if best_match:
                # Check if this field was already assigned
                if best_match in field_assignments:
                    existing_col, existing_priority = field_assignments[best_match]
                    if best_priority > existing_priority:
                        # Remove old assignment
                        del mapping[existing_col]
                        mapping[col] = best_match
                        field_assignments[best_match] = (col, best_priority)
                else:
                    mapping[col] = best_match
                    field_assignments[best_match] = (col, best_priority)
        
        return mapping
    
    def analyze_excel(
        self, 
        file_path: str, 
        sheet_name: Any = 0,
        import_type: str = 'listeners'
    ) -> Dict[str, Any]:
        """
        Analyze Excel file and detect column mapping.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index
            import_type: 'listeners' or 'programs'
            
        Returns:
            Dictionary with analysis results including detected mapping
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=10)
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'Файл пустой или не содержит данных'
                }
            
            columns = list(df.columns)
            
            # Select keywords based on import type
            keywords = self.LISTENERS_KEYWORDS if import_type == 'listeners' else self.PROGRAMS_KEYWORDS
            
            # Detect mapping
            mapping = self._detect_columns(columns, keywords)
            
            # Get sample data
            sample_data = []
            for _, row in df.head(5).iterrows():
                sample_row = {}
                for col in columns:
                    val = row[col]
                    if pd.notna(val):
                        sample_row[col] = str(val)[:50]  # Truncate for preview
                    else:
                        sample_row[col] = ''
                sample_data.append(sample_row)
            
            return {
                'success': True,
                'columns': columns,
                'detected_mapping': mapping,
                'sample_data': sample_data,
                'row_count': len(df),
                'unmapped_columns': [c for c in columns if c not in mapping]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def import_listeners(
        self, 
        file_path: str, 
        sheet_name: Any = 0,
        program_id: Optional[int] = None,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Import listeners from Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index (default: first sheet)
            program_id: Optional program ID to associate listeners with
            column_mapping: Optional custom column mapping (Excel col -> field)
        
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
            
            # Use provided mapping or detect automatically
            if column_mapping:
                self.detected_mapping = column_mapping
            else:
                self.detected_mapping = self._detect_columns(
                    list(df.columns), 
                    self.LISTENERS_KEYWORDS
                )
            
            if not self.detected_mapping:
                return {
                    'success': False,
                    'imported': 0,
                    'skipped': 0,
                    'errors': ['Не удалось определить столбцы. Проверьте заголовки в первой строке.'],
                    'warnings': []
                }
            
            with DatabaseSession() as session:
                for idx, row in df.iterrows():
                    row_num = idx + 2  # Excel row number (1-indexed + header)
                    
                    try:
                        listener, program_ref = self._create_listener_from_mapping(row)
                        
                        if listener:
                            # Check for duplicates
                            existing = session.query(Listener).filter(
                                Listener.last_name == listener.last_name,
                                Listener.first_name == listener.first_name,
                                Listener.middle_name == listener.middle_name
                            ).first()
                            
                            # Determine program to associate with
                            target_program_id = program_id
                            
                            # If program reference found in data, try to find or create program
                            if program_ref and not target_program_id:
                                program = self._find_or_create_program(session, program_ref)
                                if program:
                                    target_program_id = program.id
                            
                            if existing:
                                self.warnings.append(
                                    f"Строка {row_num}: Слушатель '{listener.full_name}' "
                                    f"уже существует (ID: {existing.id})"
                                )
                                skipped += 1
                                
                                # Associate existing listener with program if needed
                                if target_program_id:
                                    self._associate_with_program(
                                        session, existing.id, target_program_id, imported + 1
                                    )
                            else:
                                session.add(listener)
                                session.flush()  # Get the ID
                                
                                # Associate with program if specified
                                if target_program_id:
                                    self._associate_with_program(
                                        session, listener.id, target_program_id, imported + 1
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
    
    def _find_or_create_program(
        self, 
        session, 
        program_ref: str
    ) -> Optional[Program]:
        """
        Find existing program by name/short name or create new one.
        
        Args:
            session: Database session
            program_ref: Program name or short name from Excel
            
        Returns:
            Program instance or None
        """
        if not program_ref:
            return None
        
        program_ref = program_ref.strip()
        
        # Try to find by short name first
        program = session.query(Program).filter(
            Program.program_short_name == program_ref
        ).first()
        
        if program:
            return program
        
        # Try to find by full name (partial match)
        program = session.query(Program).filter(
            Program.program_name.ilike(f'%{program_ref}%')
        ).first()
        
        if program:
            return program
        
        # Create new program with this as short name
        new_program = Program(
            program_name=program_ref,
            program_short_name=program_ref[:255] if len(program_ref) > 255 else program_ref
        )
        session.add(new_program)
        session.flush()
        
        self.warnings.append(f"Создана новая программа: '{program_ref}'")
        return new_program
    
    def _create_listener_from_mapping(
        self, 
        row: pd.Series
    ) -> Tuple[Optional[Listener], Optional[str]]:
        """
        Create Listener from Excel row using detected mapping.
        
        Args:
            row: pandas Series with row data
            
        Returns:
            Tuple of (Listener instance or None, program reference or None)
        """
        data = {}
        program_ref = None
        
        # Map Excel columns to fields using detected mapping
        for excel_col, field in self.detected_mapping.items():
            if excel_col in row.index and pd.notna(row[excel_col]):
                value = row[excel_col]
                
                # Handle program reference separately
                if field in ('program_name', 'program_short_name'):
                    program_ref = str(value).strip()
                    continue
                
                # Handle date fields
                if field in ('birth_date', 'passport_issue_date'):
                    value = self._parse_date(value)
                # Handle consent field (boolean)
                elif field == 'personal_data_consent':
                    str_val = str(value).strip().lower()
                    # Accept various yes/no variations
                    value = str_val in ('да', 'yes', '1', 'true', '+', 'принимаю', 'согласен', 'согласна')
                else:
                    value = str(value).strip() if value else None
                
                if value is not None and value != '':
                    data[field] = value
        
        # Skip if no meaningful data found
        if not data or (len(data) == 1 and 'number' in data):
            return None, program_ref
        
        # Handle full_name - split into parts
        if 'full_name' in data:
            parts = data['full_name'].split()
            
            if len(parts) >= 1:
                data['last_name'] = parts[0]
            if len(parts) >= 2:
                data['first_name'] = parts[1]
            if len(parts) >= 3:
                data['middle_name'] = ' '.join(parts[2:])
            
            del data['full_name']
        
        # Remove number field (not stored in database)
        data.pop('number', None)
        
        # Validate required fields
        if 'last_name' not in data:
            raise ValueError("Фамилия обязательна для заполнения")
        if 'first_name' not in data:
            raise ValueError("Имя обязательно для заполнения")
        
        return Listener(**data), program_ref
    
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
        sheet_name: Any = 0,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Import training programs from Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index (default: first sheet)
            column_mapping: Optional custom column mapping (Excel col -> field)
        
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
            
            # Use provided mapping or detect automatically
            if column_mapping:
                self.detected_mapping = column_mapping
            else:
                self.detected_mapping = self._detect_columns(
                    list(df.columns), 
                    self.PROGRAMS_KEYWORDS
                )
            
            if not self.detected_mapping:
                return {
                    'success': False,
                    'imported': 0,
                    'skipped': 0,
                    'errors': ['Не удалось определить столбцы. Проверьте заголовки в первой строке.'],
                    'warnings': []
                }
            
            with DatabaseSession() as session:
                for idx, row in df.iterrows():
                    row_num = idx + 2
                    
                    try:
                        program = self._create_program_from_mapping(row)
                        
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
    
    def _create_program_from_mapping(self, row: pd.Series) -> Optional[Program]:
        """
        Create Program from Excel row using detected mapping.
        
        Args:
            row: pandas Series with row data
            
        Returns:
            Program instance or None if row should be skipped
        """
        data = {}
        
        # Map Excel columns to fields using detected mapping
        for excel_col, field in self.detected_mapping.items():
            if excel_col in row.index and pd.notna(row[excel_col]):
                value = row[excel_col]
                
                # Handle date fields
                if field == 'expulsion_date':
                    value = self._parse_date(value)
                else:
                    value = str(value).strip() if value else None
                
                if value:
                    data[field] = value
        
        # Skip if no meaningful data found
        if not data or (len(data) == 1 and 'number' in data):
            return None
        
        # Remove number field
        data.pop('number', None)
        
        # Validate required fields
        if 'program_name' not in data:
            raise ValueError("Наименование программы обязательно для заполнения")
        
        return Program(**data)
    
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
