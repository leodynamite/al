"""
Push notifications system for hot leads and system alerts
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode


class TelegramChannelManager:
    """Manages push notifications to Telegram channels"""
    
    def __init__(self, bot_token: str, hot_leads_channel_id: str, errors_channel_id: str):
        self.bot = Bot(token=bot_token)
        self.hot_leads_channel_id = hot_leads_channel_id
        self.errors_channel_id = errors_channel_id
    
    async def send_hot_lead_alert(self, lead_data: Dict[str, Any], agency_name: str = "Агентство") -> None:
        """Send hot lead alert to managers channel"""
        try:
            name = lead_data.get('name', 'Неизвестно')
            phone = lead_data.get('phone', 'Не указан')
            email = lead_data.get('email', 'Не указан')
            score = lead_data.get('score', 0)
            budget = lead_data.get('budget', 'Не указан')
            source = lead_data.get('source', 'Telegram')
            created_at = lead_data.get('created_at', datetime.now().strftime('%H:%M'))
            
            # Status emoji based on score
            status_emoji = "🔥" if score >= 70 else "🟡" if score >= 40 else "❄️"
            status_text = "HOT" if score >= 70 else "WARM" if score >= 40 else "COLD"
            
            message = f"""
{status_emoji} *{status_text} ЛИД - {agency_name}*

👤 *Клиент:* {name}
📞 *Телефон:* `{phone}`
📧 *Email:* {email}
💰 *Бюджет:* {budget}
🎯 *Score:* {score}/100
🌐 *Источник:* {source}
⏰ *Время:* {created_at}

*🚨 ТРЕБУЕТ НЕМЕДЛЕННОГО ВНИМАНИЯ!*
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📞 Позвонить", url=f"tel:{phone}"),
                    InlineKeyboardButton("📧 Написать", url=f"mailto:{email}")
                ],
                [
                    InlineKeyboardButton("💬 Telegram", url=f"https://t.me/{name.replace(' ', '_')}"),
                    InlineKeyboardButton("📋 В CRM", callback_data=f"open_crm_{lead_data.get('id', '')}")
                ],
                [
                    InlineKeyboardButton("✅ Обработан", callback_data=f"processed_{lead_data.get('id', '')}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{lead_data.get('id', '')}")
                ]
            ]
            
            await self.bot.send_message(
                chat_id=self.hot_leads_channel_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Failed to send hot lead alert: {e}")
    
    async def send_meeting_reminder(self, meeting_data: Dict[str, Any], agency_name: str = "Агентство") -> None:
        """Send meeting reminder to managers"""
        try:
            lead_name = meeting_data.get('lead_name', 'Неизвестно')
            meeting_time = meeting_data.get('meeting_time', 'Не указано')
            meeting_type = meeting_data.get('meeting_type', 'Встреча')
            lead_phone = meeting_data.get('lead_phone', 'Не указан')
            
            message = f"""
📅 *НАПОМИНАНИЕ О ВСТРЕЧЕ - {agency_name}*

👤 *Клиент:* {lead_name}
⏰ *Время:* {meeting_time}
📋 *Тип:* {meeting_type}
📞 *Телефон:* `{lead_phone}`

*💡 Не забудьте о предстоящей встрече!*
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📞 Позвонить", url=f"tel:{lead_phone}"),
                    InlineKeyboardButton("💬 Telegram", url=f"https://t.me/{lead_name.replace(' ', '_')}")
                ],
                [
                    InlineKeyboardButton("✅ Встреча проведена", callback_data=f"meeting_done_{meeting_data.get('id', '')}"),
                    InlineKeyboardButton("❌ Отменить встречу", callback_data=f"meeting_cancel_{meeting_data.get('id', '')}")
                ]
            ]
            
            await self.bot.send_message(
                chat_id=self.hot_leads_channel_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Failed to send meeting reminder: {e}")
    
    async def send_system_alert(self, alert_type: str, message: str, details: Dict[str, Any] = None) -> None:
        """Send system alert to errors channel"""
        try:
            alert_emoji = {
                "error": "🚨",
                "warning": "⚠️",
                "info": "ℹ️",
                "success": "✅"
            }.get(alert_type, "📢")
            
            alert_message = f"""
{alert_emoji} *СИСТЕМНЫЙ АЛЕРТ*

*Тип:* {alert_type.upper()}
*Время:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Сообщение:* {message}
            """
            
            if details:
                alert_message += f"\n*Детали:* {details}"
            
            await self.bot.send_message(
                chat_id=self.errors_channel_id,
                text=alert_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            print(f"Failed to send system alert: {e}")
    
    async def send_subscription_notification(self, user_data: Dict[str, Any], subscription_plan: str) -> None:
        """Send subscription notification to admin"""
        try:
            user_id = user_data.get('user_id')
            username = user_data.get('username', 'Неизвестно')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or username
            
            message = f"""
💳 *НОВАЯ ПОДПИСКА*

👤 *Пользователь:* {full_name}
🆔 *ID:* {user_id}
📱 *Username:* @{username}
📦 *Тариф:* {subscription_plan}
⏰ *Время:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*💡 Ожидает активации подписки*
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Активировать", callback_data=f"activate_sub_{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_sub_{user_id}")
                ],
                [
                    InlineKeyboardButton("👤 Профиль", callback_data=f"user_profile_{user_id}")
                ]
            ]
            
            await self.bot.send_message(
                chat_id=self.hot_leads_channel_id,  # Используем тот же канал
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Failed to send subscription notification: {e}")


class NotificationManager:
    """Main notification manager"""
    
    def __init__(self, bot_token: str, hot_leads_channel_id: str, errors_channel_id: str):
        self.channel_manager = TelegramChannelManager(bot_token, hot_leads_channel_id, errors_channel_id)
    
    async def notify_hot_lead(self, lead_data: Dict[str, Any], agency_name: str = "Агентство") -> None:
        """Notify about hot lead"""
        await self.channel_manager.send_hot_lead_alert(lead_data, agency_name)
    
    async def notify_meeting(self, meeting_data: Dict[str, Any], agency_name: str = "Агентство") -> None:
        """Notify about meeting"""
        await self.channel_manager.send_meeting_reminder(meeting_data, agency_name)
    
    async def notify_system_alert(self, alert_type: str, message: str, details: Dict[str, Any] = None) -> None:
        """Notify about system alert"""
        await self.channel_manager.send_system_alert(alert_type, message, details)
    
    async def notify_subscription(self, user_data: Dict[str, Any], subscription_plan: str) -> None:
        """Notify about new subscription"""
        await self.channel_manager.send_subscription_notification(user_data, subscription_plan)
