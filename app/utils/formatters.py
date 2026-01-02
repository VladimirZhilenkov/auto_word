"""
Text and data formatting utilities.
"""

import re
from datetime import datetime, date
from typing import Optional, Union


def format_date(
    value: Union[date, datetime, str, None],
    format_str: str = "%d.%m.%Y"
) -> str:
    """
    Format a date value to string.
    
    Args:
        value: Date value to format
        format_str: Output format string
        
    Returns:
        Formatted date string or empty string
    """
    if value is None:
        return ""
    
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return ""
        
        # Try to parse
        for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
            try:
                value = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        else:
            return value  # Return original if parsing failed
    
    if isinstance(value, datetime):
        value = value.date()
    
    if isinstance(value, date):
        return value.strftime(format_str)
    
    return str(value)


def format_phone(phone: str) -> str:
    """
    Format a phone number to standard Russian format.
    
    Args:
        phone: Phone number string
        
    Returns:
        Formatted phone number
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 11:
        # Format as +7 (XXX) XXX-XX-XX
        if digits[0] in ('7', '8'):
            return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    
    elif len(digits) == 10:
        # Assume Russian number without country code
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    
    return phone


def format_full_name(
    last_name: str,
    first_name: str,
    middle_name: Optional[str] = None,
    format_type: str = "full"
) -> str:
    """
    Format a full name in various styles.
    
    Args:
        last_name: Last name (Фамилия)
        first_name: First name (Имя)
        middle_name: Middle name (Отчество)
        format_type: One of:
            - "full": Фамилия Имя Отчество
            - "short": Фамилия И.О.
            - "initials_first": И.О. Фамилия
            - "last_first": Фамилия, Имя
            
    Returns:
        Formatted name string
    """
    last_name = (last_name or "").strip()
    first_name = (first_name or "").strip()
    middle_name = (middle_name or "").strip()
    
    if format_type == "full":
        parts = [last_name, first_name]
        if middle_name:
            parts.append(middle_name)
        return " ".join(parts)
    
    elif format_type == "short":
        fi = first_name[0] if first_name else ""
        mi = middle_name[0] if middle_name else ""
        
        if mi:
            return f"{last_name} {fi}.{mi}."
        elif fi:
            return f"{last_name} {fi}."
        return last_name
    
    elif format_type == "initials_first":
        fi = first_name[0] if first_name else ""
        mi = middle_name[0] if middle_name else ""
        
        if mi:
            return f"{fi}.{mi}. {last_name}"
        elif fi:
            return f"{fi}. {last_name}"
        return last_name
    
    elif format_type == "last_first":
        if first_name:
            return f"{last_name}, {first_name}"
        return last_name
    
    return format_full_name(last_name, first_name, middle_name, "full")


def truncate_text(
    text: str,
    max_length: int = 50,
    suffix: str = "..."
) -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    
    text = text.strip()
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def format_number(
    value: Union[int, float, str],
    decimal_places: int = 0,
    thousands_separator: str = " "
) -> str:
    """
    Format a number with thousand separators.
    
    Args:
        value: Number to format
        decimal_places: Number of decimal places
        thousands_separator: Character for thousands separator
        
    Returns:
        Formatted number string
    """
    if value is None:
        return ""
    
    try:
        if isinstance(value, str):
            value = float(value.replace(",", ".").replace(" ", ""))
        
        if decimal_places == 0:
            value = int(value)
            formatted = f"{value:,}".replace(",", thousands_separator)
        else:
            formatted = f"{value:,.{decimal_places}f}".replace(",", thousands_separator)
            formatted = formatted.replace(".", ",")
        
        return formatted
        
    except (ValueError, TypeError):
        return str(value)


def format_bytes(size_bytes: int) -> str:
    """
    Format byte size to human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    
    return f"{size:.1f} {units[unit_index]}"


def clean_string(text: str) -> str:
    """
    Clean a string by removing extra whitespace.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def capitalize_words(text: str) -> str:
    """
    Capitalize first letter of each word.
    
    Args:
        text: Text to capitalize
        
    Returns:
        Capitalized text
    """
    if not text:
        return ""
    
    return " ".join(word.capitalize() for word in text.split())


def format_list(
    items: list,
    separator: str = ", ",
    last_separator: str = " и "
) -> str:
    """
    Format a list as a human-readable string.
    
    Args:
        items: List of items to format
        separator: Separator between items
        last_separator: Separator before last item
        
    Returns:
        Formatted string
    """
    if not items:
        return ""
    
    items = [str(item) for item in items if item]
    
    if len(items) == 1:
        return items[0]
    
    if len(items) == 2:
        return f"{items[0]}{last_separator}{items[1]}"
    
    return f"{separator.join(items[:-1])}{last_separator}{items[-1]}"
