"""
Monitoring and alerting system
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import httpx
from pydantic import BaseModel

from .config import AppConfig
from .integrations import SupabaseClient


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert(BaseModel):
    """Alert model"""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    resolved: bool = False


class MonitoringManager:
    """Handles monitoring and alerting"""
    
    def __init__(self, config: AppConfig, supabase: SupabaseClient):
        self.config = config
        self.supabase = supabase
        self.errors_channel_id = config.errors_channel_id
        self.sentry_dsn = config.sentry_dsn
        self._alert_queue: List[Alert] = []
        
        # Setup logging
        self.logger = logging.getLogger("albot.monitoring")
        self._setup_sentry()
    
    def _setup_sentry(self) -> None:
        """Setup Sentry for error tracking"""
        if self.sentry_dsn:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.logging import LoggingIntegration
                
                sentry_logging = LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                )
                
                sentry_sdk.init(
                    dsn=self.sentry_dsn,
                    integrations=[sentry_logging],
                    traces_sample_rate=0.1
                )
            except ImportError:
                self.logger.warning("Sentry not installed, skipping setup")
    
    async def send_telegram_alert(self, alert: Alert) -> None:
        """Send alert to Telegram errors channel"""
        if not self.errors_channel_id:
            return
        
        try:
            from telegram import Bot
            from telegram.constants import ParseMode
            
            bot = Bot(token=self.config.telegram_bot_token)
            
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }
            
            emoji = emoji_map.get(alert.level, "📢")
            
            message = f"""
{emoji} *{alert.title}*

{alert.message}

*Level:* {alert.level.value}
*Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
            
            if alert.metadata:
                metadata_str = "\n".join([f"• {k}: {v}" for k, v in alert.metadata.items()])
                message += f"\n*Details:*\n{metadata_str}"
            
            await bot.send_message(
                chat_id=self.errors_channel_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
    
    async def create_alert(
        self, 
        level: AlertLevel, 
        title: str, 
        message: str, 
        metadata: Dict[str, Any] = None
    ) -> Alert:
        """Create and process alert"""
        alert = Alert(
            level=level,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Add to queue
        self._alert_queue.append(alert)
        
        # Send to Telegram if critical/warning
        if level in [AlertLevel.CRITICAL, AlertLevel.ERROR, AlertLevel.WARNING]:
            await self.send_telegram_alert(alert)
        
        # Log the alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }.get(level, logging.INFO)
        
        self.logger.log(log_level, f"{title}: {message}")
        
        return alert
    
    async def check_backend_errors(self) -> None:
        """Check for backend errors and create alerts"""
        try:
            # Get error rate from last 5 minutes
            error_rate = await self.supabase.get_error_rate(minutes=5)
            
            # Check for 500 errors and timeouts
            critical_errors = await self.supabase.get_critical_errors(minutes=5)
            
            if critical_errors > 0:
                await self.create_alert(
                    AlertLevel.CRITICAL,
                    "Critical Bot Errors",
                    f"Detected {critical_errors} critical errors (500/timeouts) in the last 5 minutes",
                    {"critical_errors": critical_errors, "error_rate": error_rate}
                )
            
            if error_rate > 0.1:  # 10% error rate
                await self.create_alert(
                    AlertLevel.WARNING,
                    "High Error Rate",
                    f"Backend error rate is {error_rate:.1%} in the last 5 minutes",
                    {"error_rate": error_rate}
                )
            
            if error_rate > 0.2:  # 20% error rate
                await self.create_alert(
                    AlertLevel.CRITICAL,
                    "Critical Error Rate",
                    f"Backend error rate is {error_rate:.1%} in the last 5 minutes",
                    {"error_rate": error_rate}
                )
                
        except Exception as e:
            self.logger.error(f"Error checking backend errors: {e}")
    
    async def check_crm_api_errors(self) -> None:
        """Check CRM API error rate"""
        try:
            crm_error_rate = await self.supabase.get_crm_error_rate(minutes=5)
            
            # Check for consecutive CRM errors
            consecutive_crm_errors = await self.supabase.get_consecutive_crm_errors()
            
            if consecutive_crm_errors > 5:  # More than 5 consecutive errors
                await self.create_alert(
                    AlertLevel.CRITICAL,
                    "CRM Consecutive Errors",
                    f"CRM API has {consecutive_crm_errors} consecutive errors. Possible service outage.",
                    {"consecutive_errors": consecutive_crm_errors, "error_rate": crm_error_rate}
                )
            
            if crm_error_rate > 0.1:  # 10% CRM API errors
                await self.create_alert(
                    AlertLevel.WARNING,
                    "CRM API Issues",
                    f"CRM API error rate is {crm_error_rate:.1%} in the last 5 minutes",
                    {"crm_error_rate": crm_error_rate}
                )
                
        except Exception as e:
            self.logger.error(f"Error checking CRM API errors: {e}")
    
    async def check_message_queue(self) -> None:
        """Check message queue size"""
        try:
            queue_size = await self.supabase.get_message_queue_size()
            queue_rate = await self.supabase.get_message_queue_rate(minutes=5)
            
            # Check for queue buildup over 5 minutes
            if queue_rate > 1000:  # More than 1000 messages in 5 minutes
                await self.create_alert(
                    AlertLevel.WARNING,
                    "Message Queue Overload",
                    f"Message queue processing {queue_rate} messages in 5 minutes. Current queue: {queue_size}",
                    {"queue_size": queue_size, "queue_rate": queue_rate}
                )
            
            if queue_size > 1000:
                await self.create_alert(
                    AlertLevel.WARNING,
                    "Message Queue Overload",
                    f"Message queue has {queue_size} pending messages",
                    {"queue_size": queue_size}
                )
            
            if queue_size > 5000:
                await self.create_alert(
                    AlertLevel.CRITICAL,
                    "Message Queue Critical",
                    f"Message queue has {queue_size} pending messages - system may be overloaded",
                    {"queue_size": queue_size}
                )
                
        except Exception as e:
            self.logger.error(f"Error checking message queue: {e}")
    
    async def check_llm_token_usage(self) -> None:
        """Check LLM token usage for abuse prevention"""
        try:
            # Get token usage for last hour
            token_usage = await self.supabase.get_llm_token_usage(hours=1)
            
            # Alert if any user exceeds reasonable limits
            for user_id, tokens in token_usage.items():
                # Check subscription limits
                subscription = await self.supabase.get_user_subscription(user_id)
                if subscription:
                    # Different limits based on subscription tier
                    if subscription.tier == "trial" and tokens > 10000:  # 10k tokens for trial
                        await self.create_alert(
                            AlertLevel.WARNING,
                            "Trial User High LLM Usage",
                            f"Trial user {user_id} used {tokens} tokens in the last hour (limit: 10k)",
                            {"user_id": user_id, "tokens": tokens, "tier": "trial"}
                        )
                    elif subscription.tier == "basic" and tokens > 50000:  # 50k tokens for basic
                        await self.create_alert(
                            AlertLevel.WARNING,
                            "Basic User High LLM Usage",
                            f"Basic user {user_id} used {tokens} tokens in the last hour (limit: 50k)",
                            {"user_id": user_id, "tokens": tokens, "tier": "basic"}
                        )
                    elif subscription.tier == "pro" and tokens > 200000:  # 200k tokens for pro
                        await self.create_alert(
                            AlertLevel.WARNING,
                            "Pro User High LLM Usage",
                            f"Pro user {user_id} used {tokens} tokens in the last hour (limit: 200k)",
                            {"user_id": user_id, "tokens": tokens, "tier": "pro"}
                        )
                
                # Critical alerts for excessive usage regardless of tier
                if tokens > 100000:  # 100k tokens per hour
                    await self.create_alert(
                        AlertLevel.WARNING,
                        "High LLM Usage",
                        f"User {user_id} used {tokens} tokens in the last hour",
                        {"user_id": user_id, "tokens": tokens}
                    )
                
                if tokens > 500000:  # 500k tokens per hour
                    await self.create_alert(
                        AlertLevel.CRITICAL,
                        "Excessive LLM Usage",
                        f"User {user_id} used {tokens} tokens in the last hour - possible abuse",
                        {"user_id": user_id, "tokens": tokens}
                    )
                    
        except Exception as e:
            self.logger.error(f"Error checking LLM token usage: {e}")
    
    async def run_health_checks(self) -> None:
        """Run all health checks"""
        await asyncio.gather(
            self.check_backend_errors(),
            self.check_crm_api_errors(),
            self.check_message_queue(),
            self.check_llm_token_usage(),
            return_exceptions=True
        )
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            status = {
                "timestamp": datetime.utcnow().isoformat(),
                "alerts": len(self._alert_queue),
                "unresolved_alerts": len([a for a in self._alert_queue if not a.resolved]),
                "error_rate": await self.supabase.get_error_rate(minutes=5),
                "queue_size": await self.supabase.get_message_queue_size(),
                "active_users": await self.supabase.get_active_users_count(),
                "total_dialogs_today": await self.supabase.get_dialogs_count_today()
            }
            return status
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved"""
        try:
            await self.supabase.resolve_alert(alert_id)
            return True
        except Exception as e:
            self.logger.error(f"Error resolving alert: {e}")
            return False
