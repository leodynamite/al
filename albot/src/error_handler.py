"""
Error handling and monitoring for AL Bot
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from telegram import Update
from telegram.ext import ContextTypes

from .monitoring import MonitoringManager, AlertLevel
from .integrations import SupabaseClient


class ErrorType(str, Enum):
    """Error types for monitoring"""
    BOT_500 = "bot_500"
    BOT_TIMEOUT = "bot_timeout"
    CRM_ERROR = "crm_error"
    LLM_ERROR = "llm_error"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"


class ErrorHandler:
    """Handles errors and sends alerts to monitoring system"""
    
    def __init__(self, monitoring: MonitoringManager, supabase: SupabaseClient):
        self.monitoring = monitoring
        self.supabase = supabase
        self.logger = logging.getLogger("albot.error_handler")
        
        # Error counters for rate limiting
        self._error_counts: Dict[str, int] = {}
        self._last_reset = datetime.utcnow()
    
    async def handle_bot_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
        """Handle bot errors (500, timeouts)"""
        try:
            error_type = self._classify_error(error)
            user_id = update.effective_user.id if update.effective_user else 0
            
            # Track error in database
            await self._track_error(error_type, user_id, str(error), {
                "update_id": update.update_id if update else None,
                "error_class": error.__class__.__name__,
                "traceback": str(error)
            })
            
            # Send alert for critical errors
            if error_type in [ErrorType.BOT_500, ErrorType.BOT_TIMEOUT]:
                await self.monitoring.create_alert(
                    AlertLevel.CRITICAL,
                    "Bot Critical Error",
                    f"Bot error: {error_type.value} - {str(error)[:100]}",
                    {
                        "error_type": error_type.value,
                        "user_id": user_id,
                        "error_class": error.__class__.__name__
                    }
                )
            
            # Log error
            self.logger.error(f"Bot error {error_type.value}: {error}", exc_info=True)
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
    
    async def handle_crm_error(self, crm_type: str, error: Exception, user_id: int) -> None:
        """Handle CRM API errors"""
        try:
            # Track CRM error
            await self._track_error(ErrorType.CRM_ERROR, user_id, str(error), {
                "crm_type": crm_type,
                "error_class": error.__class__.__name__
            })
            
            # Check for consecutive CRM errors
            consecutive_errors = await self.supabase.get_consecutive_crm_errors()
            
            if consecutive_errors > 5:
                await self.monitoring.create_alert(
                    AlertLevel.CRITICAL,
                    "CRM Consecutive Errors",
                    f"CRM {crm_type} has {consecutive_errors} consecutive errors",
                    {
                        "crm_type": crm_type,
                        "consecutive_errors": consecutive_errors
                    }
                )
            
            self.logger.error(f"CRM error ({crm_type}): {error}")
            
        except Exception as e:
            self.logger.error(f"Error handling CRM error: {e}")
    
    async def handle_llm_error(self, error: Exception, user_id: int, tokens_used: int = 0) -> None:
        """Handle LLM API errors"""
        try:
            # Track LLM error
            await self._track_error(ErrorType.LLM_ERROR, user_id, str(error), {
                "tokens_used": tokens_used,
                "error_class": error.__class__.__name__
            })
            
            # Check if user is abusing LLM
            if tokens_used > 100000:  # 100k tokens
                await self.monitoring.create_alert(
                    AlertLevel.WARNING,
                    "High LLM Usage",
                    f"User {user_id} used {tokens_used} tokens with error",
                    {
                        "user_id": user_id,
                        "tokens_used": tokens_used
                    }
                )
            
            self.logger.error(f"LLM error for user {user_id}: {error}")
            
        except Exception as e:
            self.logger.error(f"Error handling LLM error: {e}")
    
    async def handle_database_error(self, error: Exception, operation: str) -> None:
        """Handle database errors"""
        try:
            # Track database error
            await self._track_error(ErrorType.DATABASE_ERROR, 0, str(error), {
                "operation": operation,
                "error_class": error.__class__.__name__
            })
            
            # Send critical alert for database errors
            await self.monitoring.create_alert(
                AlertLevel.CRITICAL,
                "Database Error",
                f"Database error in {operation}: {str(error)[:100]}",
                {
                    "operation": operation,
                    "error_class": error.__class__.__name__
                }
            )
            
            self.logger.error(f"Database error in {operation}: {error}")
            
        except Exception as e:
            self.logger.error(f"Error handling database error: {e}")
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type"""
        error_str = str(error).lower()
        
        if "500" in error_str or "internal server error" in error_str:
            return ErrorType.BOT_500
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorType.BOT_TIMEOUT
        elif "network" in error_str or "connection" in error_str:
            return ErrorType.NETWORK_ERROR
        else:
            return ErrorType.BOT_500  # Default to 500 error
    
    async def _track_error(self, error_type: ErrorType, user_id: int, message: str, metadata: Dict[str, Any]) -> None:
        """Track error in database"""
        try:
            # TODO: Implement error tracking in Supabase
            # INSERT INTO error_logs (error_type, user_id, message, metadata, created_at)
            # VALUES (error_type.value, user_id, message, metadata, NOW())
            pass
        except Exception as e:
            self.logger.error(f"Error tracking error: {e}")
    
    async def get_error_rate(self, minutes: int = 5) -> float:
        """Get error rate for specified minutes"""
        try:
            # TODO: Implement error rate calculation from database
            # SELECT COUNT(*) FROM error_logs 
            # WHERE created_at >= NOW() - INTERVAL '{minutes} minutes'
            return 0.0
        except Exception as e:
            self.logger.error(f"Error getting error rate: {e}")
            return 0.0
    
    async def get_critical_errors_count(self, minutes: int = 5) -> int:
        """Get count of critical errors"""
        try:
            # TODO: Implement critical errors counting
            # SELECT COUNT(*) FROM error_logs 
            # WHERE error_type IN ('bot_500', 'bot_timeout')
            # AND created_at >= NOW() - INTERVAL '{minutes} minutes'
            return 0
        except Exception as e:
            self.logger.error(f"Error getting critical errors count: {e}")
            return 0

