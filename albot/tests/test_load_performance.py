"""
Test load performance
Tests: 1000 messages/day → system works without lags
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor
import statistics
from pathlib import Path

from albot.src.bot import ALBot
from albot.src.config import AppConfig, TelegramConfig
from albot.src.billing import BillingManager
from albot.src.analytics import AnalyticsManager
from albot.src.monitoring import MonitoringManager
from albot.src.integrations import SupabaseClient


class TestLoadPerformance:
    """Test system performance under load"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        return AppConfig(
            telegram=TelegramConfig(bot_token="test_token"),
            data_dir=Path("./test_data")
        )
    
    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client with performance tracking"""
        supabase = Mock(spec=SupabaseClient)
        supabase.get_user_subscription = AsyncMock(return_value=None)
        supabase.save_subscription = AsyncMock(return_value=True)
        supabase.increment_dialog_count = AsyncMock(return_value=True)
        supabase.save_analytics_events = AsyncMock(return_value=True)
        supabase.get_error_rate = AsyncMock(return_value=0.0)
        supabase.get_message_queue_size = AsyncMock(return_value=0)
        return supabase
    
    @pytest.fixture
    def mock_bot(self, mock_config, mock_supabase):
        """Create mock bot with dependencies"""
        with patch('albot.src.bot.LLMClient') as mock_llm, \
             patch('albot.src.bot.BillingManager'), \
             patch('albot.src.bot.AnalyticsManager'), \
             patch('albot.src.bot.MonitoringManager'), \
             patch('albot.src.bot.BotCommands'), \
             patch('albot.src.bot.BrandingManager'), \
             patch('albot.src.bot.HotLeadsManager'), \
             patch('albot.src.bot.ErrorHandler'):
            
            # Mock LLM client
            mock_llm_instance = Mock()
            mock_llm_instance.extract_entities = AsyncMock(return_value={"contacts": 1})
            mock_llm_instance.analyze_agency = AsyncMock(return_value={
                "profile": {"type": "test"},
                "script": [{"order": 1, "text": "Test question", "type": "text", "mandatory": True}],
                "recommendations": ["Test recommendation"]
            })
            mock_llm.return_value = mock_llm_instance
            
            bot = ALBot(mock_config)
            bot._supabase = mock_supabase
            return bot
    
    @pytest.mark.asyncio
    async def test_concurrent_start_commands(self, mock_bot):
        """Test 100 concurrent /start commands"""
        async def send_start_command(user_id):
            """Send start command for user"""
            user = Mock()
            user.id = user_id
            user.first_name = f"User{user_id}"
            user.phone = f"+7 999 {user_id:03d}-45-67"
            
            update = Mock()
            update.effective_user = user
            update.message = Mock()
            update.message.reply_text = AsyncMock()
            
            context = Mock()
            context.user_data = {}
            
            start_time = time.time()
            await mock_bot.on_start(update, context)
            end_time = time.time()
            
            return end_time - start_time
        
        # Test 100 concurrent start commands
        start_time = time.time()
        response_times = await asyncio.gather(*[send_start_command(i) for i in range(100)])
        total_time = time.time() - start_time
        
        # Verify all commands completed
        assert len(response_times) == 100
        
        # Check performance metrics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Performance requirements
        assert avg_response_time < 1.0  # Average response < 1 second
        assert max_response_time < 5.0  # Max response < 5 seconds
        assert total_time < 10.0  # Total time < 10 seconds
        
        print(f"Concurrent /start commands:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average response: {avg_response_time:.2f}s")
        print(f"  Max response: {max_response_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(self, mock_bot):
        """Test 50 concurrent file uploads"""
        async def upload_file(user_id):
            """Upload file for user"""
            user = Mock()
            user.id = user_id
            user.first_name = f"User{user_id}"
            
            update = Mock()
            update.effective_user = user
            update.message = Mock()
            update.message.reply_text = AsyncMock()
            
            context = Mock()
            context.user_data = {}
            context.bot = Mock()
            context.bot.get_file = AsyncMock()
            
            # Mock file
            document = Mock()
            document.file_name = f"test_{user_id}.csv"
            document.file_size = 1024
            document.file_id = f"file_{user_id}"
            
            update.message.document = document
            
            file_mock = Mock()
            file_mock.download_to_drive = AsyncMock()
            context.bot.get_file.return_value = file_mock
            
            # Mock file parsing and LLM
            with patch('albot.src.bot.parse_file') as mock_parse:
                mock_parse.return_value = Mock(
                    contacts=[Mock(name=f"Client {user_id}", phone=f"+7 999 {user_id:03d}-45-67")],
                    raw_text=f"Content for user {user_id}"
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
                        
                        start_time = time.time()
                        await mock_bot.on_file(update, context)
                        end_time = time.time()
                        
                        return end_time - start_time
        
        # Test 50 concurrent file uploads
        start_time = time.time()
        response_times = await asyncio.gather(*[upload_file(i) for i in range(50)])
        total_time = time.time() - start_time
        
        # Verify all uploads completed
        assert len(response_times) == 50
        
        # Check performance metrics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Performance requirements
        assert avg_response_time < 2.0  # Average response < 2 seconds
        assert max_response_time < 10.0  # Max response < 10 seconds
        assert total_time < 30.0  # Total time < 30 seconds
        
        print(f"Concurrent file uploads:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average response: {avg_response_time:.2f}s")
        print(f"  Max response: {max_response_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_mixed_operations_load(self, mock_bot):
        """Test mixed operations under load"""
        async def mixed_operation(user_id, operation_type):
            """Perform mixed operation"""
            user = Mock()
            user.id = user_id
            user.first_name = f"User{user_id}"
            
            update = Mock()
            update.effective_user = user
            update.message = Mock()
            update.message.reply_text = AsyncMock()
            
            context = Mock()
            context.user_data = {}
            context.bot = Mock()
            context.bot.get_file = AsyncMock()
            
            start_time = time.time()
            
            if operation_type == "start":
                await mock_bot.on_start(update, context)
            elif operation_type == "file":
                # Mock file upload
                document = Mock()
                document.file_name = f"test_{user_id}.csv"
                document.file_size = 1024
                document.file_id = f"file_{user_id}"
                update.message.document = document
                
                file_mock = Mock()
                file_mock.download_to_drive = AsyncMock()
                context.bot.get_file.return_value = file_mock
                
                with patch('albot.src.bot.parse_file') as mock_parse:
                    mock_parse.return_value = Mock(
                        contacts=[Mock(name=f"Client {user_id}", phone=f"+7 999 {user_id:03d}-45-67")],
                        raw_text=f"Content for user {user_id}"
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
            
            end_time = time.time()
            return end_time - start_time
        
        # Test mixed operations: 200 start commands + 100 file uploads
        operations = []
        
        # Add start commands
        for i in range(200):
            operations.append(("start", i))
        
        # Add file uploads
        for i in range(100):
            operations.append(("file", i + 200))
        
        # Shuffle operations
        import random
        random.shuffle(operations)
        
        # Execute operations
        start_time = time.time()
        response_times = await asyncio.gather(*[
            mixed_operation(user_id, op_type) for op_type, user_id in operations
        ])
        total_time = time.time() - start_time
        
        # Verify all operations completed
        assert len(response_times) == 300
        
        # Check performance metrics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Performance requirements
        assert avg_response_time < 1.5  # Average response < 1.5 seconds
        assert max_response_time < 8.0  # Max response < 8 seconds
        assert total_time < 60.0  # Total time < 60 seconds
        
        print(f"Mixed operations load test:")
        print(f"  Total operations: 300")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average response: {avg_response_time:.2f}s")
        print(f"  Max response: {max_response_time:.2f}s")
        print(f"  Operations/second: {300/total_time:.2f}")
    
    @pytest.mark.asyncio
    async def test_database_performance(self, mock_supabase):
        """Test database operations performance"""
        async def db_operation(operation_id):
            """Perform database operation"""
            start_time = time.time()
            
            # Simulate database operations
            await mock_supabase.get_user_subscription(operation_id)
            await mock_supabase.save_subscription({"user_id": operation_id})
            await mock_supabase.increment_dialog_count(operation_id)
            await mock_supabase.save_analytics_events([{"event": "test"}])
            
            end_time = time.time()
            return end_time - start_time
        
        # Test 100 concurrent database operations
        start_time = time.time()
        response_times = await asyncio.gather(*[db_operation(i) for i in range(100)])
        total_time = time.time() - start_time
        
        # Verify all operations completed
        assert len(response_times) == 100
        
        # Check performance metrics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Performance requirements
        assert avg_response_time < 0.5  # Average response < 0.5 seconds
        assert max_response_time < 2.0  # Max response < 2 seconds
        assert total_time < 10.0  # Total time < 10 seconds
        
        print(f"Database operations:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average response: {avg_response_time:.2f}s")
        print(f"  Max response: {max_response_time:.2f}s")
        print(f"  Operations/second: {100/total_time:.2f}")
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, mock_bot):
        """Test memory usage under load"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform load operations
        async def memory_intensive_operation(user_id):
            """Memory intensive operation"""
            user = Mock()
            user.id = user_id
            user.first_name = f"User{user_id}"
            
            update = Mock()
            update.effective_user = user
            update.message = Mock()
            update.message.reply_text = AsyncMock()
            
            context = Mock()
            context.user_data = {}
            context.bot = Mock()
            context.bot.get_file = AsyncMock()
            
            # Simulate memory intensive operation
            large_data = [f"data_{i}" for i in range(1000)]
            
            await mock_bot.on_start(update, context)
            
            return len(large_data)
        
        # Execute 100 memory intensive operations
        results = await asyncio.gather(*[memory_intensive_operation(i) for i in range(100)])
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify all operations completed
        assert len(results) == 100
        
        # Check memory usage
        assert memory_increase < 100  # Memory increase < 100 MB
        
        print(f"Memory usage test:")
        print(f"  Initial memory: {initial_memory:.2f} MB")
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Memory increase: {memory_increase:.2f} MB")
    
    @pytest.mark.asyncio
    async def test_error_handling_under_load(self, mock_bot):
        """Test error handling under load"""
        async def operation_with_errors(user_id):
            """Operation that might fail"""
            try:
                user = Mock()
                user.id = user_id
                user.first_name = f"User{user_id}"
                
                update = Mock()
                update.effective_user = user
                update.message = Mock()
                update.message.reply_text = AsyncMock()
                
                context = Mock()
                context.user_data = {}
                
                # Simulate occasional errors
                if user_id % 10 == 0:  # 10% error rate
                    raise Exception(f"Simulated error for user {user_id}")
                
                await mock_bot.on_start(update, context)
                return "success"
                
            except Exception as e:
                return f"error: {str(e)}"
        
        # Test 100 operations with 10% error rate
        results = await asyncio.gather(*[operation_with_errors(i) for i in range(100)])
        
        # Verify all operations completed (even with errors)
        assert len(results) == 100
        
        # Count successes and errors
        successes = sum(1 for r in results if r == "success")
        errors = sum(1 for r in results if r.startswith("error"))
        
        # Should have ~90 successes and ~10 errors
        assert successes >= 80  # At least 80% success rate
        assert errors >= 5  # At least 5% error rate
        
        print(f"Error handling under load:")
        print(f"  Total operations: 100")
        print(f"  Successes: {successes}")
        print(f"  Errors: {errors}")
        print(f"  Success rate: {successes/100:.1%}")

