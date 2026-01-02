"""
Input validation utilities.
"""

import re
from datetime import datetime, date
from typing import Any, Optional


class ValidationError(Exception):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_required(value: Any, field_name: str) -> bool:
    """
    Validate that a value is not empty.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error message
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If value is empty
    """
    if value is None:
        raise ValidationError(f"{field_name} обязательно для заполнения", field_name)
    
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field_name} обязательно для заполнения", field_name)
    
    return True


def validate_email(email: str, required: bool = False) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email string to validate
        required: If True, raise error for empty value
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not email or not email.strip():
        if required:
            raise ValidationError("Email обязателен для заполнения", "email")
        return True
    
    email = email.strip()
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValidationError("Неверный формат email", "email")
    
    return True


def validate_phone(phone: str, required: bool = False) -> bool:
    """
    Validate Russian phone number format.
    
    Args:
        phone: Phone string to validate
        required: If True, raise error for empty value
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If phone format is invalid
    """
    if not phone or not phone.strip():
        if required:
            raise ValidationError("Телефон обязателен для заполнения", "phone")
        return True
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]+', '', phone.strip())
    
    # Check for valid Russian phone formats
    # +7XXXXXXXXXX, 8XXXXXXXXXX, or just 10 digits
    patterns = [
        r'^\+7\d{10}$',
        r'^8\d{10}$',
        r'^\d{10}$',
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True
    
    raise ValidationError("Неверный формат телефона", "phone")


def validate_date(
    value: Any, 
    field_name: str = "Дата",
    required: bool = False,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None
) -> bool:
    """
    Validate date value.
    
    Args:
        value: Date value (date, datetime, or string)
        field_name: Name of the field for error message
        required: If True, raise error for empty value
        min_date: Minimum allowed date
        max_date: Maximum allowed date
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If date is invalid or out of range
    """
    if value is None:
        if required:
            raise ValidationError(f"{field_name} обязательна для заполнения", field_name)
        return True
    
    # Convert to date if needed
    if isinstance(value, datetime):
        value = value.date()
    elif isinstance(value, str):
        value = value.strip()
        if not value:
            if required:
                raise ValidationError(f"{field_name} обязательна для заполнения", field_name)
            return True
        
        # Try to parse date string
        for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
            try:
                value = datetime.strptime(value, fmt).date()
                break
            except ValueError:
                continue
        else:
            raise ValidationError(f"Неверный формат даты для {field_name}", field_name)
    
    if not isinstance(value, date):
        raise ValidationError(f"Неверный тип данных для {field_name}", field_name)
    
    # Check range
    if min_date and value < min_date:
        raise ValidationError(
            f"{field_name} не может быть раньше {min_date.strftime('%d.%m.%Y')}",
            field_name
        )
    
    if max_date and value > max_date:
        raise ValidationError(
            f"{field_name} не может быть позже {max_date.strftime('%d.%m.%Y')}",
            field_name
        )
    
    return True


def validate_length(
    value: str,
    field_name: str,
    min_length: int = None,
    max_length: int = None
) -> bool:
    """
    Validate string length.
    
    Args:
        value: String value to validate
        field_name: Name of the field for error message
        min_length: Minimum length (optional)
        max_length: Maximum length (optional)
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If length is out of range
    """
    if not value:
        return True
    
    length = len(value.strip())
    
    if min_length is not None and length < min_length:
        raise ValidationError(
            f"{field_name} должно содержать минимум {min_length} символов",
            field_name
        )
    
    if max_length is not None and length > max_length:
        raise ValidationError(
            f"{field_name} не должно превышать {max_length} символов",
            field_name
        )
    
    return True


def validate_name(name: str, field_name: str = "Имя") -> bool:
    """
    Validate that a name contains only valid characters.
    
    Args:
        name: Name string to validate
        field_name: Name of the field for error message
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If name contains invalid characters
    """
    if not name or not name.strip():
        return True
    
    # Allow letters (including Cyrillic), spaces, hyphens, and apostrophes
    pattern = r'^[a-zA-Zа-яА-ЯёЁ\s\-\']+$'
    
    if not re.match(pattern, name.strip()):
        raise ValidationError(
            f"{field_name} содержит недопустимые символы",
            field_name
        )
    
    return True
