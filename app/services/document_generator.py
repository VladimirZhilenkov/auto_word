"""
Document generator service for creating Word documents from templates.
Uses docxtpl (Jinja2-based) for template processing.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from docxtpl import DocxTemplate

from ..database.models import Listener, Program, ProgramListener
from .declension import DeclensionService, get_declension_service


def get_app_dir() -> Path:
    """Get application directory (works for both dev and compiled)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent.parent


class DocumentGenerator:
    """
    Generate Word documents from templates in templates/ folder.
    
    Uses Jinja2 templating syntax via docxtpl library.
    Supports name declension for Russian cases.
    """
    
    # Predefined template types
    TEMPLATE_TYPES = {
        'enrollment': 'О_зачислении.docx',      # О зачислении
        'admission': 'О_допуске.docx',           # О допуске к аттестации
        'graduation': 'Об_отчислении.docx',      # Об отчислении
    }
    
    def __init__(
        self, 
        templates_dir: Union[str, Path] = None,
        output_dir: Union[str, Path] = None
    ):
        """
        Initialize the document generator.
        
        Args:
            templates_dir: Directory containing Word templates
            output_dir: Directory for generated documents
        """
        app_dir = get_app_dir()
        self.templates_dir = Path(templates_dir) if templates_dir else app_dir / "templates"
        self.output_dir = Path(output_dir) if output_dir else app_dir / "docx_files"
        
        # Ensure directories exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize declension service
        self.declension = get_declension_service()
    
    def get_available_templates(self) -> List[str]:
        """
        Get list of available template files.
        
        Returns:
            List of template filenames
        """
        if not self.templates_dir.exists():
            return []
        
        templates = []
        for pattern in ['*.docx', '*.DOCX']:
            templates.extend(self.templates_dir.glob(pattern))
        
        # Filter out temporary files
        templates = [
            t.name for t in templates 
            if not t.name.startswith('~$')
        ]
        
        return sorted(templates)
    
    def generate_for_listener(
        self,
        listener: Listener,
        program: Optional[Program],
        template_name: str,
        order_number: int = 1,
        custom_context: Optional[Dict[str, Any]] = None,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Generate a document for a single listener.
        
        Args:
            listener: Listener instance
            program: Program instance (optional)
            template_name: Name of the template file
            order_number: Sequence number for the listener
            custom_context: Additional template variables
            output_filename: Custom output filename
        
        Returns:
            Path to the generated document
        """
        # Resolve template path
        template_path = self._resolve_template_path(template_name)
        
        if not template_path.exists():
            raise FileNotFoundError(f"Шаблон не найден: {template_path}")
        
        # Load template
        doc = DocxTemplate(template_path)
        
        # Prepare context
        context = self._prepare_context(listener, program, order_number)
        
        # Add custom context
        if custom_context:
            context.update(custom_context)
        
        # Render document
        doc.render(context)
        
        # Generate output filename
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self._sanitize_filename(listener.last_name)
            output_name = f"{template_path.stem}_{safe_name}_{timestamp}.docx"
            output_path = self.output_dir / output_name
        
        # Save document
        doc.save(output_path)
        
        return str(output_path)
    
    def generate_for_listener_dict(
        self,
        listener_data: Dict[str, Any],
        program_data: Optional[Dict[str, Any]],
        template_name: str,
        order_number: int = 1,
        custom_context: Optional[Dict[str, Any]] = None,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Generate a document for a listener using dictionary data.
        
        Args:
            listener_data: Listener data as dictionary
            program_data: Program data as dictionary (optional)
            template_name: Name of the template file
            order_number: Sequence number for the listener
            custom_context: Additional template variables
            output_filename: Custom output filename
        
        Returns:
            Path to the generated document
        """
        # Resolve template path
        template_path = self._resolve_template_path(template_name)
        
        if not template_path.exists():
            raise FileNotFoundError(f"Шаблон не найден: {template_path}")
        
        # Load template
        doc = DocxTemplate(template_path)
        
        # Prepare context from dictionaries
        context = self._prepare_context_from_dict(listener_data, program_data, order_number)
        
        # Add custom context
        if custom_context:
            context.update(custom_context)
        
        # Render document
        doc.render(context)
        
        # Generate output filename
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self._sanitize_filename(listener_data.get('last_name', 'listener'))
            output_name = f"{template_path.stem}_{safe_name}_{timestamp}.docx"
            output_path = self.output_dir / output_name
        
        # Save document
        doc.save(output_path)
        
        return str(output_path)
    
    def _prepare_context_from_dict(
        self,
        listener_data: Dict[str, Any],
        program_data: Optional[Dict[str, Any]],
        order_number: int
    ) -> Dict[str, Any]:
        """
        Prepare complete template context from dictionaries.
        """
        context = {}
        
        # Get all name declensions
        context.update(self.declension.get_all_declensions(
            listener_data.get('last_name', ''),
            listener_data.get('first_name', ''),
            listener_data.get('middle_name')
        ))
        
        # Add other listener fields
        context['order_number'] = order_number
        context['position'] = listener_data.get('position') or ''
        context['workplace'] = listener_data.get('workplace') or ''
        context['region'] = listener_data.get('region') or ''
        context['notes'] = listener_data.get('notes') or ''
        
        # Add program context
        if program_data:
            context['program_name'] = program_data.get('program_name') or ''
            context['program_short_name'] = program_data.get('program_short_name') or ''
            context['training_basis'] = program_data.get('training_basis') or ''
            context['training_period'] = program_data.get('training_period') or ''
            context['program_volume'] = program_data.get('program_volume') or ''
            context['education_form'] = program_data.get('education_form') or ''
            context['education_format'] = program_data.get('education_format') or ''
            context['listener_category'] = program_data.get('listener_category') or ''
            context['expulsion_date'] = program_data.get('formatted_expulsion_date') or ''
        
        # Add service context
        context.update(self._prepare_service_context())
        
        return context

    def generate_order(
        self,
        order_type: str,
        listeners_data: List[Dict[str, Any]],
        order_number: str,
        order_date: datetime,
        program_name: str = "",
        stream_name: str = "",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        contract_date: str = "",
        contract_type: str = "",
        contract_number: str = "",
        hours: int = 16,
        education_form: str = "",
        education_format: str = "",
        custom_context: Optional[Dict[str, Any]] = None,
        output_filename: Optional[str] = None,
        template_name: Optional[str] = None
    ) -> str:
        """
        Generate an order document (enrollment, admission, or graduation).
        
        Args:
            order_type: Type of order ('enrollment', 'admission', 'graduation')
            listeners_data: List of listener dictionaries with keys:
                - full_name, position, court_name, region
            order_number: Order number (e.g., '111')
            order_date: Date of the order
            program_name: Name of the program
            stream_name: Name of the stream/group
            start_date: Start date of training (for enrollment)
            end_date: End date of training (for enrollment)
            contract_date: Contract date string (e.g., '28 мая 2025 года')
            contract_type: Contract type (e.g., 'государственным контрактом...')
            contract_number: Contract number (e.g., 'б/н')
            hours: Number of training hours
            education_form: Form of education (e.g., 'очной')
            education_format: Format of education (e.g., 'с применением...')
            custom_context: Additional template variables
            output_filename: Custom output filename
            template_name: Override template name (use file from templates/)
        
        Returns:
            Path to generated document
        """
        # Get template - either custom or from predefined types
        if template_name:
            template_path = self._resolve_template_path(template_name)
        else:
            if order_type not in self.TEMPLATE_TYPES:
                raise ValueError(f"Unknown order type: {order_type}. "
                               f"Available: {list(self.TEMPLATE_TYPES.keys())}")
            template_name = self.TEMPLATE_TYPES[order_type]
            template_path = self._resolve_template_path(template_name)
        
        if not template_path.exists():
            raise FileNotFoundError(f"Шаблон не найден: {template_path}")
        
        doc = DocxTemplate(template_path)
        
        # Prepare date parts
        order_parts = get_date_parts(order_date)
        
        # Prepare context
        context = {
            # Order details
            'order_number': order_number,
            'order_day': order_parts['day'],
            'order_month': order_parts['month'],
            'order_year': order_parts['year'],
            
            # Contract details
            'contract_type': contract_type,
            'contract_number': contract_number,
            'contract_date': contract_date,
            
            # Program details
            'program_name': program_name,
            'stream_name': stream_name,
            'hours': str(hours),
            'education_form': education_form,
            'education_format': education_format,
            
            # Listeners list for table
            'listeners': listeners_data,
            'listeners_count': len(listeners_data),
        }
        
        # Add start/end dates if provided
        if start_date:
            context['start_date'] = format_date_russian(start_date)
        if end_date:
            context['end_date'] = format_date_russian(end_date)
        
        # Add service context
        context.update(self._prepare_service_context())
        
        # Add custom context
        if custom_context:
            context.update(custom_context)
        
        # Render document
        doc.render(context)
        
        # Generate output filename
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            type_names = {
                'enrollment': 'О_зачислении',
                'admission': 'О_допуске',
                'graduation': 'Об_отчислении',
                'custom': 'Документ'
            }
            type_name = type_names.get(order_type, 'Документ')
            # Use template name for custom type
            if order_type == 'custom' and template_name:
                base_name = Path(template_name).stem
                output_name = f"{order_number}_{order_date.strftime('%d.%m.%Y')}_{base_name}.docx"
            else:
                output_name = f"{order_number}_{order_date.strftime('%d.%m.%Y')}_{type_name}.docx"
            output_path = self.output_dir / output_name
        
        doc.save(output_path)
        
        return str(output_path)

    def generate_batch(
        self,
        listeners: List[Listener],
        program: Optional[Program],
        template_name: str,
        separate_files: bool = True,
        custom_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate documents for multiple listeners.
        
        Args:
            listeners: List of Listener instances
            program: Program instance (optional)
            template_name: Name of the template file
            separate_files: Generate separate file for each listener
            custom_context: Additional template variables
        
        Returns:
            List of paths to generated documents
        """
        generated_files = []
        
        for idx, listener in enumerate(listeners, start=1):
            try:
                file_path = self.generate_for_listener(
                    listener=listener,
                    program=program,
                    template_name=template_name,
                    order_number=idx,
                    custom_context=custom_context
                )
                generated_files.append(file_path)
            except Exception as e:
                # Log error but continue with other listeners
                print(f"Error generating document for {listener.full_name}: {e}")
        
        return generated_files
    
    def generate_with_table(
        self,
        listeners: List[Listener],
        program: Optional[Program],
        template_name: str,
        custom_context: Optional[Dict[str, Any]] = None,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Generate a single document with a table of listeners.
        
        The template should contain a table with Jinja2 loop:
        {%tr for listener in listeners %}
        {{ listener.order_number }}
        {{ listener.full_name }}
        ...
        {%tr endfor %}
        
        Args:
            listeners: List of Listener instances
            program: Program instance (optional)
            template_name: Template filename
            custom_context: Additional template variables
            output_filename: Custom output filename
        
        Returns:
            Path to generated document
        """
        template_path = self._resolve_template_path(template_name)
        
        if not template_path.exists():
            raise FileNotFoundError(f"Шаблон не найден: {template_path}")
        
        doc = DocxTemplate(template_path)
        
        # Prepare listeners data for table
        listeners_data = []
        for idx, listener in enumerate(listeners, start=1):
            listener_context = self._prepare_listener_context(listener, idx)
            listeners_data.append(listener_context)
        
        # Prepare main context
        context = {
            'listeners': listeners_data,
            'listeners_count': len(listeners),
        }
        
        # Add program data
        if program:
            context.update(self._prepare_program_context(program))
        
        # Add service fields
        context.update(self._prepare_service_context())
        
        # Add custom context
        if custom_context:
            context.update(custom_context)
        
        # Render document
        doc.render(context)
        
        # Generate output filename
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            program_name = self._sanitize_filename(
                program.program_short_name or "program"
            ) if program else "document"
            output_name = f"{template_path.stem}_{program_name}_{timestamp}.docx"
            output_path = self.output_dir / output_name
        
        doc.save(output_path)
        
        return str(output_path)
    
    def _resolve_template_path(self, template_name: str) -> Path:
        """Resolve template path, adding extension if needed."""
        template_path = self.templates_dir / template_name
        
        if not template_path.suffix:
            template_path = template_path.with_suffix('.docx')
        
        return template_path
    
    def _prepare_context(
        self,
        listener: Listener,
        program: Optional[Program],
        order_number: int
    ) -> Dict[str, Any]:
        """
        Prepare complete template context.
        
        Args:
            listener: Listener instance
            program: Program instance
            order_number: Sequence number
        
        Returns:
            Dictionary with all template variables
        """
        context = {}
        
        # Add listener context with declensions
        context.update(self._prepare_listener_context(listener, order_number))
        
        # Add program context
        if program:
            context.update(self._prepare_program_context(program))
        
        # Add service context
        context.update(self._prepare_service_context())
        
        return context
    
    def _prepare_listener_context(
        self,
        listener: Listener,
        order_number: int
    ) -> Dict[str, Any]:
        """Prepare listener-specific context with all declensions."""
        # Get all name declensions
        context = self.declension.get_all_declensions(
            listener.last_name,
            listener.first_name,
            listener.middle_name
        )
        
        # Add other listener fields
        context['order_number'] = order_number
        context['position'] = listener.position or ''
        context['workplace'] = listener.workplace or ''
        context['court_name'] = listener.workplace or ''  # Alias for templates
        context['region'] = listener.region or ''
        context['notes'] = listener.notes or ''
        
        return context
    
    def _prepare_program_context(self, program: Program) -> Dict[str, Any]:
        """Prepare program-specific context."""
        return {
            'program_name': program.program_name or '',
            'program_short_name': program.program_short_name or '',
            'training_basis': program.training_basis or '',
            'training_period': program.training_period or '',
            'program_volume': program.program_volume or '',
            'education_form': program.education_form or '',
            'education_format': program.education_format or '',
            'listener_category': program.listener_category or '',
            'expulsion_date': program.formatted_expulsion_date,
        }
    
    def _prepare_service_context(self) -> Dict[str, Any]:
        """Prepare service context (dates, etc.)."""
        now = datetime.now()
        
        return {
            'current_date': now.strftime("%d.%m.%Y"),
            'current_year': str(now.year),
            'current_month': now.strftime("%m"),
            'current_day': now.strftime("%d"),
            'generation_datetime': now.strftime("%d.%m.%Y %H:%M:%S"),
        }
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid characters from filename."""
        if not name:
            return "document"
        
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        result = name
        for char in invalid_chars:
            result = result.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        result = result.strip(' .')
        
        return result[:50] if result else "document"
    
    def get_template_variables(self, template_name: str) -> List[str]:
        """
        Extract variable names from a template.
        Note: This is a basic extraction, may not catch all variables.
        
        Args:
            template_name: Template filename
        
        Returns:
            List of variable names found in template
        """
        import re
        
        template_path = self._resolve_template_path(template_name)
        
        if not template_path.exists():
            return []
        
        try:
            doc = DocxTemplate(template_path)
            
            # Get the document XML
            xml_content = doc.get_docx().element.body.xml
            
            # Find all Jinja2 variables
            pattern = r'\{\{[\s]*([a-zA-Z_][a-zA-Z0-9_]*)[\s]*\}\}'
            variables = re.findall(pattern, xml_content)
            
            return sorted(set(variables))
        except Exception:
            return []


class DocumentGeneratorError(Exception):
    """Exception for document generation errors."""
    pass


# Helper functions for preparing Russian dates
MONTHS_GENITIVE = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}


def format_date_russian(date: datetime) -> str:
    """Format date in Russian style: '12 ноября 2025 г.'"""
    return f"{date.day} {MONTHS_GENITIVE[date.month]} {date.year} г."


def get_date_parts(date: datetime) -> Dict[str, str]:
    """Get date parts for templates."""
    return {
        'day': str(date.day),
        'month': MONTHS_GENITIVE[date.month],
        'year': str(date.year),
    }
