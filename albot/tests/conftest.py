"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from albot.src.config import AppConfig
from albot.src.integrations import SupabaseClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Create test configuration"""
    return AppConfig(
        telegram_bot_token="test_token",
        deepseek_api_key="test_key",
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
        data_dir=Path("./test_data")
    )


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client"""
    supabase = Mock(spec=SupabaseClient)
    supabase.get_user_subscription = AsyncMock(return_value=None)
    supabase.save_subscription = AsyncMock(return_value=True)
    supabase.update_subscription = AsyncMock(return_value=True)
    supabase.increment_dialog_count = AsyncMock(return_value=True)
    supabase.save_analytics_events = AsyncMock(return_value=True)
    supabase.get_error_rate = AsyncMock(return_value=0.0)
    supabase.get_crm_error_rate = AsyncMock(return_value=0.0)
    supabase.get_message_queue_size = AsyncMock(return_value=0)
    supabase.get_llm_token_usage = AsyncMock(return_value={})
    return supabase


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_csv_file(temp_dir):
    """Create sample CSV file for testing"""
    csv_path = temp_dir / "test_clients.csv"
    csv_content = """name,phone,email,comment
Иван Петров,+7 999 123-45-67,ivan@example.com,Интересуется 2-комнатной квартирой
Мария Сидорова,+7 999 234-56-78,maria@example.com,Ищет дом в пригороде
Алексей Козлов,+7 999 345-67-89,alex@example.com,Коммерческая недвижимость"""
    
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    return csv_path


@pytest.fixture
def sample_xlsx_file(temp_dir):
    """Create sample XLSX file for testing"""
    import pandas as pd
    
    xlsx_path = temp_dir / "test_clients.xlsx"
    data = {
        'name': ['Иван Петров', 'Мария Сидорова', 'Алексей Козлов'],
        'phone': ['+7 999 123-45-67', '+7 999 234-56-78', '+7 999 345-67-89'],
        'email': ['ivan@example.com', 'maria@example.com', 'alex@example.com'],
        'comment': ['2-комнатная квартира', 'Дом в пригороде', 'Коммерческая недвижимость']
    }
    
    df = pd.DataFrame(data)
    df.to_excel(xlsx_path, index=False)
    
    return xlsx_path


@pytest.fixture
def sample_pdf_file(temp_dir):
    """Create sample PDF file for testing"""
    pdf_path = temp_dir / "test_clients.pdf"
    pdf_content = """
    Контакты клиентов:
    Иван Петров - +7 999 123-45-67 - ivan@example.com
    Мария Сидорова - +7 999 234-56-78 - maria@example.com
    Алексей Козлов - +7 999 345-67-89 - alex@example.com
    
    Описание: Ищут недвижимость в центре города
    """
    
    with open(pdf_path, 'w', encoding='utf-8') as f:
        f.write(pdf_content)
    
    return pdf_path


@pytest.fixture
def sample_docx_file(temp_dir):
    """Create sample DOCX file for testing"""
    docx_path = temp_dir / "test_clients.docx"
    docx_content = """
    Список клиентов:
    1. Иван Петров, телефон: +7 999 123-45-67, email: ivan@example.com
    2. Мария Сидорова, телефон: +7 999 234-56-78, email: maria@example.com
    3. Алексей Козлов, телефон: +7 999 345-67-89, email: alex@example.com
    
    Комментарии: Все клиенты заинтересованы в покупке недвижимости
    """
    
    with open(docx_path, 'w', encoding='utf-8') as f:
        f.write(docx_content)
    
    return docx_path


@pytest.fixture
def mock_telegram_update():
    """Create mock Telegram update"""
    user = Mock()
    user.id = 1001
    user.first_name = "TestUser"
    user.phone = "+7 999 123-45-67"
    
    update = Mock()
    update.effective_user = user
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    update.message.edit_text = AsyncMock()
    update.callback_query = None
    
    return update


@pytest.fixture
def mock_telegram_context():
    """Create mock Telegram context"""
    context = Mock()
    context.user_data = {}
    context.bot = Mock()
    context.bot.get_file = AsyncMock()
    
    return context


@pytest.fixture
def mock_llm_response():
    """Create mock LLM response"""
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


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "load: marks tests as load tests"
    )

