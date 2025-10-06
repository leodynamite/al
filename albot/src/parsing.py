"""
File parsing functionality for various document formats.
"""
import pandas as pd
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import io
import os

try:
    import openpyxl
    import xlrd
    from pdfminer.high_level import extract_text
    from docx import Document
except ImportError:
    # These will be handled gracefully in the parsing functions
    pass

from .utils import normalize_phone_to_ru


@dataclass
class ParsedData:
    """Parsed file data structure."""
    raw_text: Optional[str] = None
    contacts: List[Dict[str, str]] = None
    sample_ad: Optional[str] = None
    avg_price: Optional[float] = None
    address: Optional[str] = None

    def __post_init__(self):
        if self.contacts is None:
            self.contacts = []


def parse_file(file_path: str) -> ParsedData:
    """
    Parse various file formats and extract relevant data.
    
    Args:
        file_path: Path to the file to parse
        
    Returns:
        ParsedData object with extracted information
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    
    if suffix == '.csv':
        return _parse_csv(file_path)
    elif suffix in ['.xlsx', '.xls']:
        return _parse_excel(file_path)
    elif suffix == '.pdf':
        return _parse_pdf(file_path)
    elif suffix == '.docx':
        return _parse_docx(file_path)
    elif suffix == '.txt':
        return _parse_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def _parse_csv(file_path: Path) -> ParsedData:
    """Parse CSV file."""
    try:
        df = pd.read_csv(file_path)
        contacts = []
        
        # Look for contact columns
        for _, row in df.iterrows():
            contact = {}
            for col in df.columns:
                value = str(row[col]).strip()
                if value and value != 'nan':
                    col_lower = col.lower()
                    # Check column name first
                    if 'phone' in col_lower or 'телефон' in col_lower:
                        contact['phone'] = normalize_phone_to_ru(value)
                    elif 'email' in col_lower or 'почта' in col_lower or '@' in value:
                        contact['email'] = value
                    elif 'name' in col_lower or 'имя' in col_lower or 'фио' in col_lower:
                        contact['name'] = value
                    elif 'comment' in col_lower or 'комментарий' in col_lower or 'описание' in col_lower:
                        contact['comment'] = value
                    else:
                        # Fallback to content-based detection
                        if any(char.isdigit() for char in value) and len(value) > 5 and ('+' in value or value.count(' ') >= 2):
                            contact['phone'] = normalize_phone_to_ru(value)
                        elif '@' in value:
                            contact['email'] = value
                        elif len(value) > 2 and not any(char.isdigit() for char in value):
                            contact['name'] = value
                        else:
                            contact['other'] = value
            
            if contact:
                contacts.append(contact)
        
        return ParsedData(contacts=contacts)
    except Exception as e:
        return ParsedData(raw_text=f"Error parsing CSV: {str(e)}")


def _parse_excel(file_path: Path) -> ParsedData:
    """Parse Excel file."""
    try:
        df = pd.read_excel(file_path)
        contacts = []
        
        # Similar logic to CSV parsing
        for _, row in df.iterrows():
            contact = {}
            for col in df.columns:
                value = str(row[col]).strip()
                if value and value != 'nan':
                    if any(char.isdigit() for char in value) and len(value) > 5:
                        contact['phone'] = normalize_phone_to_ru(value)
                    elif '@' in value:
                        contact['email'] = value
                    elif len(value) > 2 and not any(char.isdigit() for char in value):
                        contact['name'] = value
                    else:
                        contact['other'] = value
            
            if contact:
                contacts.append(contact)
        
        return ParsedData(contacts=contacts)
    except Exception as e:
        return ParsedData(raw_text=f"Error parsing Excel: {str(e)}")


def _parse_pdf(file_path: Path) -> ParsedData:
    """Parse PDF file."""
    try:
        text = extract_text(str(file_path))
        return ParsedData(raw_text=text)
    except Exception as e:
        return ParsedData(raw_text=f"Error parsing PDF: {str(e)}")


def _parse_docx(file_path: Path) -> ParsedData:
    """Parse DOCX file."""
    try:
        doc = Document(str(file_path))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return ParsedData(raw_text=text)
    except Exception as e:
        return ParsedData(raw_text=f"Error parsing DOCX: {str(e)}")


def _parse_text(file_path: Path) -> ParsedData:
    """Parse text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return ParsedData(raw_text=text)
    except Exception as e:
        return ParsedData(raw_text=f"Error parsing text file: {str(e)}")
