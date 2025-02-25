"""Utility functions for the Comparateur_PDF project."""

import re
from datetime import datetime
from typing import Optional, Tuple

def parse_date(date_str: str) -> Tuple[Optional[datetime.date], Optional[str]]:
    """Parse a date string into a date object.

    Args:
        date_str: The date string to parse.

    Returns:
        Parsed date and error message if any.
    """
    formats = [
        '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y%m%d',
        '%d %b %Y', '%d %B %Y'
    ]
    clean_date = re.sub(r'[^\d:/ -]', '', str(date_str)).strip()
    clean_date = re.sub(r'/', '-', clean_date)
    date_part = clean_date.split(' ')[0] if ' ' in clean_date else clean_date
    for fmt in formats:
        try:
            return datetime.strptime(date_part, fmt).date(), None
        except ValueError:
            continue
    return None, f"Unrecognized format: {clean_date}"

def normalize_serial(serial: str) -> str:
    """Normalize a serial number by removing non-alphanumeric characters and converting to uppercase.

    Args:
        serial: The serial number to normalize.

    Returns:
        Normalized serial number.
    """
    return re.sub(r'[^A-Z0-9]', '', str(serial).upper())
