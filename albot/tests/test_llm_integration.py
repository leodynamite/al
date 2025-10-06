"""
Test LLM integration functionality
Tests: 10 different files should always generate script + 3 recommendations
"""
import pytest
import asyncio
from pathlib import Path
import tempfile
import os

from albot.src.llm import LLMClient
from albot.src.config import LLMConfig


class TestLLMIntegration:
    """Test LLM integration with different file types"""
    
    @pytest.fixture
    def llm_client(self):
        """Create LLM client for testing"""
        config = LLMConfig(
            api_key="test_key",
            base_url="https://api.deepseek.com",
            model="deepseek-chat"
        )
        client = LLMClient(config)
        
        # Mock the _chat_json method to return test data
        async def mock_chat_json(messages):
            return {
                "profile": {
                    "type": "residential",
                    "avg_check": "5-10 млн",
                    "target_audience": "Молодые семьи",
                    "main_channel": "Авито",
                    "weaknesses": ["Низкая конверсия", "Долгий цикл продаж"]
                },
                "script": [
                    {
                        "order": 1,
                        "text": "Какой тип недвижимости вас интересует?",
                        "type": "choice",
                        "choices": ["Квартира", "Дом", "Коммерческая"],
                        "mandatory": True,
                        "purpose": "Определить тип недвижимости"
                    },
                    {
                        "order": 2,
                        "text": "Какой у вас бюджет?",
                        "type": "text",
                        "mandatory": True,
                        "purpose": "Понять финансовые возможности"
                    },
                    {
                        "order": 3,
                        "text": "В каком районе предпочитаете?",
                        "type": "text",
                        "mandatory": False,
                        "purpose": "Уточнить локацию"
                    },
                    {
                        "order": 4,
                        "text": "Когда планируете покупку?",
                        "type": "choice",
                        "choices": ["В течение месяца", "В течение 3 месяцев", "В течение года"],
                        "mandatory": True,
                        "purpose": "Определить срочность"
                    }
                ],
                "recommendations": [
                    "Используйте эмоциональные триггеры в описаниях",
                    "Предлагайте несколько вариантов для сравнения",
                    "Собирайте обратную связь после каждого показа"
                ]
            }
        
        client._chat_json = mock_chat_json
        return client
    
    @pytest.mark.asyncio
    async def test_csv_analysis(self, llm_client):
        """Test LLM analysis of CSV file"""
        csv_content = """
        name,phone,email,comment
        Иван Петров,+7 999 123-45-67,ivan@example.com,Интересуется 2-комнатной квартирой
        Мария Сидорова,+7 999 234-56-78,maria@example.com,Ищет дом в пригороде
        """
        
        result = await llm_client.analyze_agency(csv_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
        assert len(result["recommendations"]) == 3
        assert len(result["script"]) >= 4  # At least 4 questions
    
    @pytest.mark.asyncio
    async def test_xlsx_analysis(self, llm_client):
        """Test LLM analysis of XLSX file"""
        xlsx_content = """
        Клиенты недвижимости:
        - Иван Петров: +7 999 123-45-67, ищет 2-комнатную квартиру
        - Мария Сидорова: +7 999 234-56-78, интересуется домом
        - Алексей Козлов: +7 999 345-67-89, коммерческая недвижимость
        """
        
        result = await llm_client.analyze_agency(xlsx_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
        assert len(result["recommendations"]) == 3
    
    @pytest.mark.asyncio
    async def test_pdf_analysis(self, llm_client):
        """Test LLM analysis of PDF file"""
        pdf_content = """
        АГЕНТСТВО НЕДВИЖИМОСТИ "ДОМ ПЛЮС"
        
        База клиентов:
        1. Иван Петров - +7 999 123-45-67 - ivan@example.com
           Интересуется 2-комнатной квартирой в центре, бюджет до 5 млн
        
        2. Мария Сидорова - +7 999 234-56-78 - maria@example.com
           Ищет дом в пригороде с участком, бюджет до 8 млн
        
        3. Алексей Козлов - +7 999 345-67-89 - alex@example.com
           Коммерческая недвижимость, офисы в центре
        
        Средний чек: 6 млн рублей
        Основной канал: Авито, Циан
        """
        
        result = await llm_client.analyze_agency(pdf_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
        assert len(result["recommendations"]) == 3
    
    @pytest.mark.asyncio
    async def test_docx_analysis(self, llm_client):
        """Test LLM analysis of DOCX file"""
        docx_content = """
        СПИСОК КЛИЕНТОВ АГЕНТСТВА
        
        Клиент 1: Иван Петров
        Телефон: +7 999 123-45-67
        Email: ivan@example.com
        Интересы: 2-комнатная квартира в центре города
        Бюджет: до 5 млн рублей
        
        Клиент 2: Мария Сидорова
        Телефон: +7 999 234-56-78
        Email: maria@example.com
        Интересы: Дом в пригороде с участком
        Бюджет: до 8 млн рублей
        
        Клиент 3: Алексей Козлов
        Телефон: +7 999 345-67-89
        Email: alex@example.com
        Интересы: Коммерческая недвижимость
        Бюджет: до 15 млн рублей
        """
        
        result = await llm_client.analyze_agency(docx_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
        assert len(result["recommendations"]) == 3
    
    @pytest.mark.asyncio
    async def test_empty_file_analysis(self, llm_client):
        """Test LLM analysis of empty file"""
        result = await llm_client.analyze_agency("")
        
        # Should handle empty content gracefully
        assert result is not None
        # Should return fallback or default response
    
    @pytest.mark.asyncio
    async def test_large_file_analysis(self, llm_client):
        """Test LLM analysis of large file"""
        large_content = "Клиенты недвижимости: " + "Иван Петров, +7 999 123-45-67, ivan@example.com; " * 100
        
        result = await llm_client.analyze_agency(large_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_special_characters_analysis(self, llm_client):
        """Test LLM analysis with special characters"""
        special_content = """
        Клиенты с особыми требованиями:
        - Иван Петров-Сидоров: +7 999 123-45-67, ищет "2-комнатную квартиру"
        - Мария Сидорова-Петрова: +7 999 234-56-78, интересуется домом с участком
        - Алексей Козлов-Волков: +7 999 345-67-89, коммерческая недвижимость
        """
        
        result = await llm_client.analyze_agency(special_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_mixed_language_analysis(self, llm_client):
        """Test LLM analysis with mixed languages"""
        mixed_content = """
        Real Estate Agency Clients:
        - Иван Петров: +7 999 123-45-67, ищет apartment в центре
        - Maria Sidorova: +7 999 234-56-78, интересуется house в пригороде
        - Alexey Kozlov: +7 999 345-67-89, commercial real estate
        """
        
        result = await llm_client.analyze_agency(mixed_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_structured_data_analysis(self, llm_client):
        """Test LLM analysis of structured data"""
        structured_content = """
        {
            "agency": "Дом Плюс",
            "clients": [
                {"name": "Иван Петров", "phone": "+7 999 123-45-67", "interest": "2-комнатная квартира"},
                {"name": "Мария Сидорова", "phone": "+7 999 234-56-78", "interest": "дом в пригороде"}
            ],
            "average_price": 6000000,
            "main_channel": "Авито"
        }
        """
        
        result = await llm_client.analyze_agency(structured_content)
        
        assert result is not None
        assert "profile" in result
        assert "script" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_script_generation_consistency(self, llm_client):
        """Test that LLM always generates consistent script format"""
        test_contents = [
            "Клиенты: Иван Петров, +7 999 123-45-67",
            "Агентство недвижимости с клиентами",
            "Список контактов для недвижимости",
            "База данных клиентов агентства",
            "Клиенты, интересующиеся недвижимостью"
        ]
        
        for content in test_contents:
            result = await llm_client.analyze_agency(content)
            
            assert result is not None
            assert "profile" in result
            assert "script" in result
            assert "recommendations" in result
            assert len(result["recommendations"]) == 3
            assert len(result["script"]) >= 4  # At least 4 questions
            
            # Check script structure
            for question in result["script"]:
                assert "order" in question
                assert "text" in question
                assert "type" in question
                assert "mandatory" in question
                assert "purpose" in question
