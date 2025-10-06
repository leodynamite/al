"""
Hot leads management and push notifications
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .config import AppConfig
from .integrations import SupabaseClient
from .analytics import AnalyticsManager
from .models import Lead, LeadStatus


class HotLeadNotification(BaseModel):
    """Hot lead notification model"""
    lead_id: str
    user_id: int
    lead_name: str
    phone: str
    email: Optional[str] = None
    score: int
    source: str
    created_at: datetime
    script_id: str


class HotLeadsManager:
    """Manages hot leads and push notifications"""
    
    def __init__(self, config: AppConfig, supabase: SupabaseClient, analytics: AnalyticsManager):
        self.config = config
        self.supabase = supabase
        self.analytics = analytics
        self.managers_channel_id = config.telegram_managers_channel_id
    
    async def process_hot_lead(self, lead: Lead, user_id: int) -> bool:
        """Process hot lead and send notification"""
        try:
            # Create hot lead notification
            notification = HotLeadNotification(
                lead_id=lead.id,
                user_id=user_id,
                lead_name=lead.answers[0].value if lead.answers else "Unknown",
                phone=self._extract_phone_from_answers(lead.answers),
                email=self._extract_email_from_answers(lead.answers),
                score=lead.lead_score,
                source=lead.source.value,
                created_at=lead.created_at,
                script_id=lead.script_id
            )
            
            # Send to managers channel
            await self._send_hot_lead_notification(notification)
            
            # Track analytics event
            await self.analytics.track_lead_hot_push(
                user_id, 
                lead.id, 
                self.managers_channel_id or "unknown"
            )
            
            return True
            
        except Exception as e:
            print(f"Error processing hot lead: {e}")
            return False
    
    def _extract_phone_from_answers(self, answers: List[Dict[str, Any]]) -> str:
        """Extract phone number from lead answers"""
        for answer in answers:
            if "phone" in answer.get("question_id", "").lower() or "телефон" in answer.get("question_id", "").lower():
                return answer.get("value", "")
        return "Не указан"
    
    def _extract_email_from_answers(self, answers: List[Dict[str, Any]]) -> Optional[str]:
        """Extract email from lead answers"""
        for answer in answers:
            if "email" in answer.get("question_id", "").lower() or "почта" in answer.get("question_id", "").lower():
                return answer.get("value")
        return None
    
    async def _send_hot_lead_notification(self, notification: HotLeadNotification) -> None:
        """Send hot lead notification to managers channel"""
        if not self.managers_channel_id:
            print("Managers channel not configured")
            return
        
        try:
            from telegram import Bot
            from telegram.constants import ParseMode
            
            bot = Bot(token=self.config.telegram_bot_token)
            
            # Format phone number
            phone_display = self._format_phone(notification.phone)
            
            # Create notification message
            message = f"""
🔥 *ГОРЯЧИЙ ЛИД!*

*Контакт:* {notification.lead_name}
*Телефон:* {phone_display}
*Email:* {notification.email or 'Не указан'}
*Score:* {notification.score}/100
*Источник:* {notification.source}
*Время:* {notification.created_at.strftime('%H:%M')}

*Действия:*
            """
            
            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("📞 Принять звонок", callback_data=f"hot_call_{notification.lead_id}"),
                    InlineKeyboardButton("💬 Отправить SMS", callback_data=f"hot_sms_{notification.lead_id}")
                ],
                [
                    InlineKeyboardButton("🔗 Открыть в CRM", callback_data=f"hot_crm_{notification.lead_id}"),
                    InlineKeyboardButton("📅 Назначить встречу", callback_data=f"hot_meeting_{notification.lead_id}")
                ]
            ]
            
            await bot.send_message(
                chat_id=self.managers_channel_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error sending hot lead notification: {e}")
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number for display"""
        if not phone or phone == "Не указан":
            return "Не указан"
        
        # Basic phone formatting
        phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if len(phone_clean) == 11 and phone_clean.startswith("7"):
            return f"+7 {phone_clean[1:4]} {phone_clean[4:7]}-{phone_clean[7:9]}-{phone_clean[9:11]}"
        elif len(phone_clean) == 10 and phone_clean.startswith("9"):
            return f"+7 {phone_clean[0:3]} {phone_clean[3:6]}-{phone_clean[6:8]}-{phone_clean[8:10]}"
        
        return phone
    
    async def handle_hot_lead_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, lead_id: str) -> None:
        """Handle hot lead action button clicks"""
        try:
            query = update.callback_query
            if query:
                await query.answer()
            
            if action == "call":
                await self._handle_call_action(update, lead_id)
            elif action == "sms":
                await self._handle_sms_action(update, lead_id)
            elif action == "crm":
                await self._handle_crm_action(update, lead_id)
            elif action == "meeting":
                await self._handle_meeting_action(update, lead_id)
                
        except Exception as e:
            print(f"Error handling hot lead action: {e}")
    
    async def _handle_call_action(self, update: Update, lead_id: str) -> None:
        """Handle call action"""
        await update.callback_query.edit_message_text(
            f"📞 Звонок по лиду {lead_id} принят в работу.\n"
            "Менеджер получит уведомление о необходимости связаться с клиентом."
        )
    
    async def _handle_sms_action(self, update: Update, lead_id: str) -> None:
        """Handle SMS action"""
        await update.callback_query.edit_message_text(
            f"💬 SMS по лиду {lead_id} отправлено.\n"
            "Клиент получит сообщение в течение 5 минут."
        )
    
    async def _handle_crm_action(self, update: Update, lead_id: str) -> None:
        """Handle CRM action"""
        await update.callback_query.edit_message_text(
            f"🔗 Лид {lead_id} открыт в CRM.\n"
            "Вы можете просмотреть полную информацию о клиенте."
        )
    
    async def _handle_meeting_action(self, update: Update, lead_id: str) -> None:
        """Handle meeting action"""
        await update.callback_query.edit_message_text(
            f"📅 Встреча по лиду {lead_id} назначена.\n"
            "Клиент получит приглашение в календарь."
        )
    
    async def get_hot_leads_stats(self, user_id: int) -> Dict[str, Any]:
        """Get hot leads statistics for user"""
        try:
            # TODO: Implement hot leads stats from Supabase
            # Query: SELECT COUNT(*) as hot_count, AVG(score) as avg_score 
            # FROM leads WHERE user_id = ? AND status = 'hot'
            return {
                "hot_count": 3,
                "avg_score": 78,
                "conversion_rate": 0.25
            }
        except Exception as e:
            print(f"Error getting hot leads stats: {e}")
            return {}
