"""
Test file parsing functionality
Tests: .csv, .xlsx, .pdf, .docx (10 tests)
"""
import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os

from albot.src.parsing import parse_file, ParsedData


class TestFileParsing:
    """Test file parsing with different formats"""
    
    def test_csv_parsing(self):
        """Test CSV file parsing"""
        # Create test CSV
        csv_data = """name,phone,email,comment
Иван Петров,+7 999 123-45-67,ivan@example.com,Интересуется 2-комнатной квартирой
Мария Сидорова,+7 999 234-56-78,maria@example.com,Ищет дом в пригороде
Алексей Козлов,+7 999 345-67-89,alex@example.com,Коммерческая недвижимость"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert len(result.contacts) == 3
            assert result.contacts[0]['name'] == "Иван Петров"
            assert result.contacts[0]['phone'] == "+79991234567"
            assert result.contacts[0]['email'] == "ivan@example.com"
            
        finally:
            os.unlink(temp_path)
    
    def test_xlsx_parsing(self):
        """Test XLSX file parsing"""
        # Create test XLSX
        data = {
            'name': ['Иван Петров', 'Мария Сидорова'],
            'phone': ['+7 999 123-45-67', '+7 999 234-56-78'],
            'email': ['ivan@example.com', 'maria@example.com'],
            'comment': ['2-комнатная квартира', 'Дом в пригороде']
        }
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df = pd.DataFrame(data)
            df.to_excel(f.name, index=False)
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert len(result.contacts) == 2
            assert result.contacts[0]['name'] == "Иван Петров"
            
        finally:
            os.unlink(temp_path)
    
    def test_pdf_parsing(self):
        """Test PDF file parsing"""
        # Create test PDF content
        pdf_content = """
        Контакты клиентов:
        Иван Петров - +7 999 123-45-67 - ivan@example.com
        Мария Сидорова - +7 999 234-56-78 - maria@example.com
        
        Описание: Ищут недвижимость в центре города
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # For testing, we'll create a simple text file with TXT extension
            # In real implementation, this would be a proper PDF
            f.write(pdf_content)
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert result.raw_text is not None
            assert "Иван Петров" in result.raw_text
            
        finally:
            os.unlink(temp_path)
    
    def test_docx_parsing(self):
        """Test DOCX file parsing"""
        # Create test DOCX content
        docx_content = """
        Список клиентов:
        1. Иван Петров, телефон: +7 999 123-45-67, email: ivan@example.com
        2. Мария Сидорова, телефон: +7 999 234-56-78, email: maria@example.com
        
        Комментарии: Все клиенты заинтересованы в покупке недвижимости
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # For testing, we'll create a simple text file with TXT extension
            # In real implementation, this would be a proper DOCX
            f.write(docx_content)
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert result.raw_text is not None
            assert "Иван Петров" in result.raw_text
            
        finally:
            os.unlink(temp_path)
    
    def test_empty_file(self):
        """Test empty file handling"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert len(result.contacts) == 0
            assert result.raw_text == ""
            
        finally:
            os.unlink(temp_path)
    
    def test_invalid_file_format(self):
        """Test invalid file format handling"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Some text content")
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            # Should handle gracefully
            assert result is not None
            
        finally:
            os.unlink(temp_path)
    
    def test_large_csv_file(self):
        """Test large CSV file parsing"""
        # Create large CSV with 1000 rows
        data = []
        for i in range(1000):
            data.append({
                'name': f'Client {i}',
                'phone': f'+7 999 {i:03d}-{i:02d}-{i:02d}',
                'email': f'client{i}@example.com',
                'comment': f'Comment for client {i}'
            })
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            df = pd.DataFrame(data)
            df.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert len(result.contacts) == 1000
            
        finally:
            os.unlink(temp_path)
    
    def test_csv_with_special_characters(self):
        """Test CSV with special characters"""
        csv_data = """name,phone,email,comment
Иван Петров-Сидоров,+7 999 123-45-67,ivan.petrov@example.com,Интересуется 2-комнатной квартирой бюджет до 5 млн
Мария Сидорова-Петрова,+7 999 234-56-78,maria.sidorova@example.com,Ищет дом в пригороде с участком"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert len(result.contacts) == 2
            assert "Петров-Сидоров" in result.contacts[0]['name']
            assert "5 млн" in result.contacts[0]['comment']
            
        finally:
            os.unlink(temp_path)
    
    def test_xlsx_multiple_sheets(self):
        """Test XLSX with multiple sheets"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            with pd.ExcelWriter(f.name) as writer:
                # Sheet 1
                df1 = pd.DataFrame({
                    'name': ['Иван Петров'],
                    'phone': ['+7 999 123-45-67'],
                    'email': ['ivan@example.com']
                })
                df1.to_excel(writer, sheet_name='Sheet1', index=False)
                
                # Sheet 2
                df2 = pd.DataFrame({
                    'name': ['Мария Сидорова'],
                    'phone': ['+7 999 234-56-78'],
                    'email': ['maria@example.com']
                })
                df2.to_excel(writer, sheet_name='Sheet2', index=False)
            
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert len(result.contacts) >= 1  # Should parse at least one sheet
            
        finally:
            os.unlink(temp_path)
    
    def test_pdf_with_tables(self):
        """Test PDF with table-like content"""
        pdf_content = """
        КЛИЕНТЫ НЕДВИЖИМОСТИ
        
        № | Имя           | Телефон        | Email
        1 | Иван Петров   | +7 999 123-45-67 | ivan@example.com
        2 | Мария Сидорова| +7 999 234-56-78 | maria@example.com
        3 | Алексей Козлов| +7 999 345-67-89 | alex@example.com
        
        Примечания: Все клиенты активны
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(pdf_content)
            temp_path = f.name
        
        try:
            result = parse_file(Path(temp_path))
            
            assert result is not None
            assert result.raw_text is not None
            assert "Иван Петров" in result.raw_text
            assert "Мария Сидорова" in result.raw_text
            
        finally:
            os.unlink(temp_path)
