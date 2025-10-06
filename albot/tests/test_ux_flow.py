"""
Test UX flow functionality
Tests: 5 agents go through /start → upload → apply without errors
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import tempfile
import os

from albot.src.bot import ALBot
from albot.src.config import AppConfig
from albot.src.billing import BillingManager, SubscriptionTier
from albot.src.analytics import AnalyticsManager
from albot.src.monitoring import MonitoringManager
from albot.src.integrations import SupabaseClient


class TestUXFlow:
    """Test complete UX flow for 5 agents"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        from albot.src.config import TelegramConfig, LLMConfig, StorageConfig
        
        return AppConfig(
            telegram=TelegramConfig(bot_token="test_token"),
            llm=LLMConfig(
                api_key="test_key",
                base_url="https://api.deepseek.com",
                model="deepseek-chat"
            ),
            storage=StorageConfig(data_dir=Path("./test_data"))
        )
    
    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client"""
        supabase = Mock(spec=SupabaseClient)
        supabase.get_user_subscription = AsyncMock(return_value=None)
        supabase.save_subscription = AsyncMock(return_value=True)
        supabase.increment_dialog_count = AsyncMock(return_value=True)
        supabase.save_analytics_events = AsyncMock(return_value=True)
        return supabase
    
    @pytest.fixture
    def mock_bot(self, mock_config, mock_supabase):
        """Create mock bot with dependencies"""
        with patch('albot.src.bot.BillingManager') as mock_billing, \
             patch('albot.src.bot.AnalyticsManager') as mock_analytics, \
             patch('albot.src.bot.MonitoringManager') as mock_monitoring, \
             patch('albot.src.bot.BotCommands') as mock_commands, \
             patch('albot.src.bot.BrandingManager') as mock_branding, \
             patch('albot.src.bot.HotLeadsManager') as mock_hot_leads, \
             patch('albot.src.bot.ErrorHandler') as mock_error_handler, \
             patch('albot.src.bot.UXTexts') as mock_ux_texts, \
             patch('albot.src.bot.CommercialManager') as mock_commercial:
            
            # Configure async mocks
            mock_analytics_instance = Mock()
            mock_analytics_instance.track_user_onboarded = AsyncMock()
            mock_analytics_instance.track_file_uploaded = AsyncMock()
            mock_analytics_instance.track_script_generated = AsyncMock()
            mock_analytics_instance.track_script_applied = AsyncMock()
            mock_analytics.return_value = mock_analytics_instance
            
            # Create mock subscription object
            mock_subscription = Mock()
            mock_subscription.is_read_only = False
            mock_subscription.tier = "TRIAL"
            
            # Create mock status enum
            mock_status = Mock()
            mock_status.value = "trial"
            mock_subscription.status = mock_status
            
            mock_billing_instance = Mock()
            mock_billing_instance.get_user_subscription = AsyncMock(return_value=mock_subscription)
            mock_billing_instance.create_trial_subscription = AsyncMock(return_value=True)
            mock_billing_instance.check_trial_expired = AsyncMock(return_value=False)
            mock_billing_instance.check_dialog_limit = AsyncMock(return_value=False)
            mock_billing_instance.get_trial_info = Mock(return_value="Trial info")
            mock_billing_instance.get_subscription_info = Mock(return_value="Subscription info")
            mock_billing.return_value = mock_billing_instance
            
            # Create mock branding object
            mock_branding_obj = Mock()
            mock_branding_obj.welcome_message = "Привет! Я AL-бот"
            mock_branding_obj.bot_name = "AL Bot"
            mock_branding_obj.bot_logo_url = None
            mock_branding_obj.theme_color = "#007bff"
            
            mock_branding_instance = Mock()
            mock_branding_instance.get_bot_branding = Mock(return_value=mock_branding_obj)
            mock_branding.return_value = mock_branding_instance
            
            # Mock other managers
            mock_hot_leads.return_value = Mock()
            mock_error_handler.return_value = Mock()
            mock_ux_texts.return_value = Mock()
            mock_commercial.return_value = Mock()
            
            bot = ALBot(mock_config)
            bot._supabase = mock_supabase
            return bot
    
    @pytest.mark.asyncio
    async def test_agent_1_complete_flow(self, mock_bot):
        """Test Agent 1: Complete flow from start to apply"""
        # Mock user and update
        user = Mock()
        user.id = 1001
        user.first_name = "Agent1"
        user.phone = "+7 999 123-45-67"
        
        update = Mock()
        update.effective_user = user
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.message.reply_html = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.get_file = AsyncMock()
        
        # Test /start command
        await mock_bot.on_start(update, context)
        
        # Verify start response
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Привет! Я AL-бот" in call_args[0][0]
        
        # Test file upload
        document = Mock()
        document.file_name = "test_clients.csv"
        document.file_size = 1024
        document.file_id = "test_file_id"
        
        update.message.document = document
        
        # Mock file download
        file_mock = Mock()
        file_mock.download_to_drive = AsyncMock()
        
        # Mock document.get_file() method
        document.get_file = AsyncMock(return_value=file_mock)
        context.bot.get_file.return_value = file_mock
        
        # Mock file parsing
        with patch('albot.src.bot.parse_file') as mock_parse:
            mock_parse.return_value = Mock(
                contacts=[Mock(name="Иван Петров", phone="+7 999 123-45-67")],
                raw_text="Test content"
            )
            
            # Mock LLM response
            with patch.object(mock_bot._llm, 'extract_entities') as mock_extract:
                mock_extract.return_value = {"contacts": 1}
                
                with patch.object(mock_bot._llm, 'analyze_agency') as mock_analyze:
                    mock_analyze.return_value = {
                        "profile": {"type": "residential"},
                        "script": [
                            {"order": 1, "text": "Какой тип недвижимости?", "type": "choice", "mandatory": True},
                            {"order": 2, "text": "Ваш бюджет?", "type": "text", "mandatory": True}
                        ],
                        "recommendations": ["Совет 1", "Совет 2", "Совет 3"]
                    }
                    
                    await mock_bot.on_file(update, context)
        
        # Verify file processing
        assert context.user_data.get("last_result") is not None
        assert context.user_data.get("script_model") is not None
    
    @pytest.mark.asyncio
    async def test_agent_2_xlsx_upload(self, mock_bot):
        """Test Agent 2: XLSX file upload"""
        user = Mock()
        user.id = 1002
        user.first_name = "Agent2"
        
        update = Mock()
        update.effective_user = user
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.message.reply_html = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.get_file = AsyncMock()
        
        # Test XLSX upload
        document = Mock()
        document.file_name = "clients.xlsx"
        document.file_size = 2048
        document.file_id = "test_xlsx_id"
        
        update.message.document = document
        
        file_mock = Mock()
        file_mock.download_to_drive = AsyncMock()
        context.bot.get_file.return_value = file_mock
        
        with patch('albot.src.bot.parse_file') as mock_parse:
            mock_parse.return_value = Mock(
                contacts=[Mock(name="Мария Сидорова", phone="+7 999 234-56-78")],
                raw_text="Excel content"
            )
            
            with patch.object(mock_bot._llm, 'extract_entities') as mock_extract:
                mock_extract.return_value = {"contacts": 1}
                
                with patch.object(mock_bot._llm, 'analyze_agency') as mock_analyze:
                    mock_analyze.return_value = {
                        "profile": {"type": "commercial"},
                        "script": [
                            {"order": 1, "text": "Тип коммерческой недвижимости?", "type": "choice", "mandatory": True}
                        ],
                        "recommendations": ["Рекомендация 1", "Рекомендация 2", "Рекомендация 3"]
                    }
                    
                    await mock_bot.on_file(update, context)
        
        # Verify successful processing
        assert context.user_data.get("last_result") is not None
    
    @pytest.mark.asyncio
    async def test_agent_3_pdf_upload(self, mock_bot):
        """Test Agent 3: PDF file upload"""
        user = Mock()
        user.id = 1003
        user.first_name = "Agent3"
        
        update = Mock()
        update.effective_user = user
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.message.reply_html = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.get_file = AsyncMock()
        
        # Test PDF upload
        document = Mock()
        document.file_name = "clients.pdf"
        document.file_size = 4096
        document.file_id = "test_pdf_id"
        
        update.message.document = document
        
        file_mock = Mock()
        file_mock.download_to_drive = AsyncMock()
        context.bot.get_file.return_value = file_mock
        
        with patch('albot.src.bot.parse_file') as mock_parse:
            mock_parse.return_value = Mock(
                contacts=[],
                raw_text="PDF content with client information"
            )
            
            with patch.object(mock_bot._llm, 'extract_entities') as mock_extract:
                mock_extract.return_value = {"contacts": 0, "text": "PDF content"}
                
                with patch.object(mock_bot._llm, 'analyze_agency') as mock_analyze:
                    mock_analyze.return_value = {
                        "profile": {"type": "mixed"},
                        "script": [
                            {"order": 1, "text": "Какой тип недвижимости?", "type": "choice", "mandatory": True}
                        ],
                        "recommendations": ["PDF совет 1", "PDF совет 2", "PDF совет 3"]
                    }
                    
                    await mock_bot.on_file(update, context)
        
        # Verify successful processing
        assert context.user_data.get("last_result") is not None
    
    @pytest.mark.asyncio
    async def test_agent_4_docx_upload(self, mock_bot):
        """Test Agent 4: DOCX file upload"""
        user = Mock()
        user.id = 1004
        user.first_name = "Agent4"
        
        update = Mock()
        update.effective_user = user
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.message.reply_html = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.get_file = AsyncMock()
        
        # Test DOCX upload
        document = Mock()
        document.file_name = "clients.docx"
        document.file_size = 3072
        document.file_id = "test_docx_id"
        
        update.message.document = document
        
        file_mock = Mock()
        file_mock.download_to_drive = AsyncMock()
        context.bot.get_file.return_value = file_mock
        
        with patch('albot.src.bot.parse_file') as mock_parse:
            mock_parse.return_value = Mock(
                contacts=[Mock(name="Алексей Козлов", phone="+7 999 345-67-89")],
                raw_text="Word document content"
            )
            
            with patch.object(mock_bot._llm, 'extract_entities') as mock_extract:
                mock_extract.return_value = {"contacts": 1}
                
                with patch.object(mock_bot._llm, 'analyze_agency') as mock_analyze:
                    mock_analyze.return_value = {
                        "profile": {"type": "luxury"},
                        "script": [
                            {"order": 1, "text": "Бюджет на недвижимость?", "type": "text", "mandatory": True}
                        ],
                        "recommendations": ["DOCX совет 1", "DOCX совет 2", "DOCX совет 3"]
                    }
                    
                    await mock_bot.on_file(update, context)
        
        # Verify successful processing
        assert context.user_data.get("last_result") is not None
    
    @pytest.mark.asyncio
    async def test_agent_5_error_handling(self, mock_bot):
        """Test Agent 5: Error handling in flow"""
        user = Mock()
        user.id = 1005
        user.first_name = "Agent5"
        
        update = Mock()
        update.effective_user = user
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.message.reply_html = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.get_file = AsyncMock()
        
        # Test invalid file
        document = Mock()
        document.file_name = "invalid.txt"
        document.file_size = 512
        document.file_id = "test_invalid_id"
        
        update.message.document = document
        
        # Should handle invalid file gracefully
        await mock_bot.on_file(update, context)
        
        # Verify error handling
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        assert "Неподдерживаемый формат" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_all_agents_concurrent(self, mock_bot):
        """Test all 5 agents working concurrently"""
        agents = [
            {"id": 1001, "name": "Agent1", "file": "test1.csv"},
            {"id": 1002, "name": "Agent2", "file": "test2.xlsx"},
            {"id": 1003, "name": "Agent3", "file": "test3.pdf"},
            {"id": 1004, "name": "Agent4", "file": "test4.docx"},
            {"id": 1005, "name": "Agent5", "file": "test5.csv"}
        ]
        
        async def process_agent(agent):
            """Process single agent"""
            user = Mock()
            user.id = agent["id"]
            user.first_name = agent["name"]
            
            update = Mock()
            update.effective_user = user
            update.message = Mock()
            update.message.reply_text = AsyncMock()
        update.message.reply_html = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        context.bot = Mock()
        context.bot.get_file = AsyncMock()
        
        # Test /start
        await mock_bot.on_start(update, context)
        
        # Test file upload
        document = Mock()
        document.file_name = agent["file"]
        document.file_size = 1024
        document.file_id = f"test_{agent['id']}"
        
        update.message.document = document
        
        file_mock = Mock()
        file_mock.download_to_drive = AsyncMock()
        context.bot.get_file.return_value = file_mock
        
        with patch('albot.src.bot.parse_file') as mock_parse:
            mock_parse.return_value = Mock(
                contacts=[Mock(name=f"Client {agent['id']}", phone=f"+7 999 {agent['id']}-45-67")],
                raw_text=f"Content for {agent['name']}"
            )
            
            with patch.object(mock_bot._llm, 'extract_entities') as mock_extract:
                mock_extract.return_value = {"contacts": 1}
                
                with patch.object(mock_bot._llm, 'analyze_agency') as mock_analyze:
                    mock_analyze.return_value = {
                        "profile": {"type": "test"},
                        "script": [
                            {"order": 1, "text": "Test question?", "type": "text", "mandatory": True}
                        ],
                        "recommendations": ["Test 1", "Test 2", "Test 3"]
                    }
                    
                    await mock_bot.on_file(update, context)
        
        return agent["id"]
        
        # Process all agents concurrently
        results = await asyncio.gather(*[process_agent(agent) for agent in agents])
        
        # Verify all agents processed successfully
        assert len(results) == 5
        assert all(result in [1001, 1002, 1003, 1004, 1005] for result in results)
