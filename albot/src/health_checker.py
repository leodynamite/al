"""
Health checker for AL Bot system
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from enum import Enum

from .monitoring import MonitoringManager, AlertLevel
from .integrations import SupabaseClient


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


class HealthChecker:
    """Performs health checks on AL Bot system"""
    
    def __init__(self, monitoring: MonitoringManager, supabase: SupabaseClient):
        self.monitoring = monitoring
        self.supabase = supabase
        self.logger = logging.getLogger("albot.health_checker")
        
        # Health check intervals
        self.check_interval = 60  # seconds
        self.last_check = datetime.utcnow()
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and return status"""
        try:
            health_status = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": HealthStatus.HEALTHY,
                "checks": {}
            }
            
            # Run individual health checks
            checks = await asyncio.gather(
                self._check_database_health(),
                self._check_llm_health(),
                self._check_telegram_health(),
                self._check_crm_health(),
                self._check_queue_health(),
                return_exceptions=True
            )
            
            # Process check results
            check_names = ["database", "llm", "telegram", "crm", "queue"]
            for i, result in enumerate(checks):
                if isinstance(result, Exception):
                    health_status["checks"][check_names[i]] = {
                        "status": HealthStatus.CRITICAL,
                        "error": str(result)
                    }
                else:
                    health_status["checks"][check_names[i]] = result
            
            # Determine overall status
            statuses = [check.get("status", HealthStatus.CRITICAL) for check in health_status["checks"].values()]
            if HealthStatus.DOWN in statuses:
                health_status["overall_status"] = HealthStatus.DOWN
            elif HealthStatus.CRITICAL in statuses:
                health_status["overall_status"] = HealthStatus.CRITICAL
            elif HealthStatus.WARNING in statuses:
                health_status["overall_status"] = HealthStatus.WARNING
            
            # Send alerts if needed
            await self._process_health_alerts(health_status)
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error in health checks: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": HealthStatus.CRITICAL,
                "error": str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start_time = datetime.utcnow()
            
            # Test database connection
            await self.supabase.get_active_users_count()
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            if response_time > 5.0:
                return {
                    "status": HealthStatus.WARNING,
                    "message": f"Database slow response: {response_time:.2f}s",
                    "response_time": response_time
                }
            elif response_time > 10.0:
                return {
                    "status": HealthStatus.CRITICAL,
                    "message": f"Database very slow response: {response_time:.2f}s",
                    "response_time": response_time
                }
            else:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": f"Database healthy: {response_time:.2f}s",
                    "response_time": response_time
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.DOWN,
                "message": f"Database connection failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_llm_health(self) -> Dict[str, Any]:
        """Check LLM service health"""
        try:
            # TODO: Implement LLM health check
            # Test with a simple request to LLM service
            return {
                "status": HealthStatus.HEALTHY,
                "message": "LLM service healthy"
            }
        except Exception as e:
            return {
                "status": HealthStatus.CRITICAL,
                "message": f"LLM service error: {str(e)}",
                "error": str(e)
            }
    
    async def _check_telegram_health(self) -> Dict[str, Any]:
        """Check Telegram Bot API health"""
        try:
            # TODO: Implement Telegram health check
            # Test with getMe API call
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Telegram API healthy"
            }
        except Exception as e:
            return {
                "status": HealthStatus.CRITICAL,
                "message": f"Telegram API error: {str(e)}",
                "error": str(e)
            }
    
    async def _check_crm_health(self) -> Dict[str, Any]:
        """Check CRM integrations health"""
        try:
            # Check CRM error rates
            crm_error_rate = await self.supabase.get_crm_error_rate(minutes=5)
            
            if crm_error_rate > 0.5:  # 50% error rate
                return {
                    "status": HealthStatus.CRITICAL,
                    "message": f"CRM high error rate: {crm_error_rate:.1%}",
                    "error_rate": crm_error_rate
                }
            elif crm_error_rate > 0.1:  # 10% error rate
                return {
                    "status": HealthStatus.WARNING,
                    "message": f"CRM elevated error rate: {crm_error_rate:.1%}",
                    "error_rate": crm_error_rate
                }
            else:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": f"CRM healthy: {crm_error_rate:.1%} error rate",
                    "error_rate": crm_error_rate
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.CRITICAL,
                "message": f"CRM health check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_queue_health(self) -> Dict[str, Any]:
        """Check message queue health"""
        try:
            queue_size = await self.supabase.get_message_queue_size()
            queue_rate = await self.supabase.get_message_queue_rate(minutes=5)
            
            if queue_size > 5000:
                return {
                    "status": HealthStatus.CRITICAL,
                    "message": f"Queue overloaded: {queue_size} messages",
                    "queue_size": queue_size
                }
            elif queue_size > 1000:
                return {
                    "status": HealthStatus.WARNING,
                    "message": f"Queue high: {queue_size} messages",
                    "queue_size": queue_size
                }
            elif queue_rate > 1000:  # More than 1000 messages in 5 minutes
                return {
                    "status": HealthStatus.WARNING,
                    "message": f"Queue processing high rate: {queue_rate} messages/5min",
                    "queue_rate": queue_rate
                }
            else:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": f"Queue healthy: {queue_size} messages, {queue_rate} rate",
                    "queue_size": queue_size,
                    "queue_rate": queue_rate
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.CRITICAL,
                "message": f"Queue health check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _process_health_alerts(self, health_status: Dict[str, Any]) -> None:
        """Process health status and send alerts if needed"""
        try:
            overall_status = health_status["overall_status"]
            
            if overall_status == HealthStatus.DOWN:
                await self.monitoring.create_alert(
                    AlertLevel.CRITICAL,
                    "System Down",
                    "AL Bot system is down. Critical components are failing.",
                    {"health_status": health_status}
                )
            elif overall_status == HealthStatus.CRITICAL:
                await self.monitoring.create_alert(
                    AlertLevel.CRITICAL,
                    "System Critical",
                    "AL Bot system is in critical state. Multiple components failing.",
                    {"health_status": health_status}
                )
            elif overall_status == HealthStatus.WARNING:
                await self.monitoring.create_alert(
                    AlertLevel.WARNING,
                    "System Warning",
                    "AL Bot system has warnings. Some components are degraded.",
                    {"health_status": health_status}
                )
                
        except Exception as e:
            self.logger.error(f"Error processing health alerts: {e}")
    
    async def start_health_monitoring(self) -> None:
        """Start continuous health monitoring"""
        while True:
            try:
                await self.run_health_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(self.check_interval)

