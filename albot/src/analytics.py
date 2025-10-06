"""
Analytics and metrics tracking
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel

from .config import AppConfig
from .integrations import SupabaseClient


class EventType(str, Enum):
    """Analytics event types"""
    USER_ONBOARDED = "user_onboarded"
    FILE_UPLOADED = "file_uploaded"
    SCRIPT_GENERATED = "script_generated"
    SCRIPT_APPLIED = "script_applied"
    DIALOG_STARTED = "dialog_started"
    DIALOG_COMPLETED = "dialog_completed"
    LEAD_CREATED = "lead_created"
    LEAD_SCORED = "lead_scored"
    LEAD_BOOKED = "lead_booked"
    LEAD_HOT_PUSH = "lead_hot_push"
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"


class AnalyticsEvent(BaseModel):
    """Analytics event model"""
    event_type: EventType
    user_id: int
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    session_id: Optional[str] = None


class AnalyticsManager:
    """Handles analytics and metrics tracking"""
    
    def __init__(self, config: AppConfig, supabase: SupabaseClient):
        self.config = config
        self.supabase = supabase
        self._event_queue: List[AnalyticsEvent] = []
    
    async def track_event(
        self, 
        event_type: EventType, 
        user_id: int, 
        metadata: Dict[str, Any] = None,
        session_id: str = None
    ) -> None:
        """Track analytics event"""
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            session_id=session_id
        )
        
        # Add to queue for batch processing
        self._event_queue.append(event)
        
        # Process queue if it gets too large
        if len(self._event_queue) >= 10:
            await self._flush_events()
    
    async def _flush_events(self) -> None:
        """Flush queued events to database"""
        if not self._event_queue:
            return
        
        try:
            events_data = [event.dict() for event in self._event_queue]
            await self.supabase.save_analytics_events(events_data)
            self._event_queue.clear()
        except Exception as e:
            print(f"Error flushing analytics events: {e}")
    
    async def get_user_metrics(self, user_id: int) -> Dict[str, Any]:
        """Get user-specific metrics"""
        try:
            metrics = await self.supabase.get_user_metrics(user_id)
            return metrics or {}
        except Exception as e:
            print(f"Error getting user metrics: {e}")
            return {}
    
    async def get_global_metrics(self) -> Dict[str, Any]:
        """Get global system metrics"""
        try:
            metrics = await self.supabase.get_global_metrics()
            return metrics or {}
        except Exception as e:
            print(f"Error getting global metrics: {e}")
            return {}
    
    async def get_conversion_funnel(self, user_id: int) -> Dict[str, Any]:
        """Get conversion funnel for user"""
        try:
            funnel = await self.supabase.get_conversion_funnel(user_id)
            return funnel or {}
        except Exception as e:
            print(f"Error getting conversion funnel: {e}")
            return {}
    
    async def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        try:
            if format == "json":
                return await self.supabase.export_metrics_json()
            elif format == "csv":
                return await self.supabase.export_metrics_csv()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Error exporting metrics: {e}")
            return "Export failed"
    
    # Convenience methods for common events
    async def track_user_onboarded(self, user_id: int, method: str) -> None:
        """Track user onboarding"""
        await self.track_event(
            EventType.USER_ONBOARDED,
            user_id,
            {"method": method}
        )
    
    async def track_file_uploaded(self, user_id: int, file_type: str, file_size: int) -> None:
        """Track file upload"""
        await self.track_event(
            EventType.FILE_UPLOADED,
            user_id,
            {"file_type": file_type, "file_size": file_size}
        )
    
    async def track_script_generated(self, user_id: int, script_id: str, method: str) -> None:
        """Track script generation"""
        await self.track_event(
            EventType.SCRIPT_GENERATED,
            user_id,
            {"script_id": script_id, "method": method}
        )
    
    async def track_script_applied(self, user_id: int, script_id: str) -> None:
        """Track script application"""
        await self.track_event(
            EventType.SCRIPT_APPLIED,
            user_id,
            {"script_id": script_id}
        )
    
    async def track_dialog_started(self, user_id: int, lead_id: str) -> None:
        """Track dialog start"""
        await self.track_event(
            EventType.DIALOG_STARTED,
            user_id,
            {"lead_id": lead_id}
        )
    
    async def track_dialog_completed(self, user_id: int, lead_id: str, duration: int) -> None:
        """Track dialog completion"""
        await self.track_event(
            EventType.DIALOG_COMPLETED,
            user_id,
            {"lead_id": lead_id, "duration_seconds": duration}
        )
    
    async def track_lead_created(self, user_id: int, lead_id: str, source: str) -> None:
        """Track lead creation"""
        await self.track_event(
            EventType.LEAD_CREATED,
            user_id,
            {"lead_id": lead_id, "source": source}
        )
    
    async def track_lead_scored(self, user_id: int, lead_id: str, score: int, status: str) -> None:
        """Track lead scoring"""
        await self.track_event(
            EventType.LEAD_SCORED,
            user_id,
            {"lead_id": lead_id, "score": score, "status": status}
        )
    
    async def track_lead_booked(self, user_id: int, lead_id: str, calendar_event_id: str) -> None:
        """Track lead booking"""
        await self.track_event(
            EventType.LEAD_BOOKED,
            user_id,
            {"lead_id": lead_id, "calendar_event_id": calendar_event_id}
        )
    
    async def track_subscription_started(self, user_id: int, tier: str) -> None:
        """Track subscription start"""
        await self.track_event(
            EventType.SUBSCRIPTION_STARTED,
            user_id,
            {"tier": tier}
        )
    
    async def track_subscription_cancelled(self, user_id: int, tier: str) -> None:
        """Track subscription cancellation"""
        await self.track_event(
            EventType.SUBSCRIPTION_CANCELLED,
            user_id,
            {"tier": tier}
        )
    
    async def track_lead_hot_push(self, user_id: int, lead_id: str, channel_id: str) -> None:
        """Track hot lead push to channel"""
        await self.track_event(
            EventType.LEAD_HOT_PUSH,
            user_id,
            {"lead_id": lead_id, "channel_id": channel_id}
        )
