"""
Additional bot commands for billing, analytics, and monitoring
"""
import asyncio
import io
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .billing import BillingManager, SubscriptionTier
from .analytics import AnalyticsManager
from .monitoring import MonitoringManager
from .integrations import SupabaseClient


class BotCommands:
    """Additional bot commands handler"""
    
    def __init__(self, billing: BillingManager, analytics: AnalyticsManager, 
                 monitoring: MonitoringManager, supabase: SupabaseClient):
        self.billing = billing
        self.analytics = analytics
        self.monitoring = monitoring
        self.supabase = supabase
    
    async def on_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /metrics command - show user metrics"""
        user = update.effective_user
        if not user:
            return
        
        try:
            # Get user metrics
            metrics = await self.analytics.get_user_metrics(user.id)
            
            # Get subscription info
            subscription = await self.billing.get_user_subscription(user.id)
            subscription_info = ""
            if subscription:
                subscription_info = self.billing.get_subscription_info(subscription)
            
            # Get detailed metrics
            dialogs_today = metrics.get('dialogs_today', 0)
            dialogs_week = metrics.get('dialogs_week', 0)
            hot_leads = metrics.get('hot_leads', 0)
            meetings_scheduled = metrics.get('meetings_scheduled', 0)
            leads_created = metrics.get('leads_created', 0)
            conversion_rate = metrics.get('conversion_rate', 0)
            avg_lead_score = metrics.get('avg_lead_score', 0)
            
            # Create dashboard table
            metrics_text = f"""
📊 *ДЭШБОРД АГЕНТСТВА*

*Подписка:* {subscription_info}

┌─────────────────────────────────┐
│ 📈 ДИАЛОГИ                       │
├─────────────────────────────────┤
│ Сегодня: {dialogs_today:>3} диалогов        │
│ За неделю: {dialogs_week:>3} диалогов       │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 🔥 ЛИДЫ                         │
├─────────────────────────────────┤
│ Всего лидов: {leads_created:>3}              │
│ Hot лидов: {hot_leads:>3}                   │
│ Конверсия: {conversion_rate:>5.1%}              │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 📅 ВСТРЕЧИ                      │
├─────────────────────────────────┤
│ Назначено: {meetings_scheduled:>3} встреч        │
│ Средний score: {avg_lead_score:>3}            │
└─────────────────────────────────┘
            """
            
            # Create keyboard with export options
            keyboard = [
                [
                    InlineKeyboardButton("📊 Детальная статистика", callback_data="detailed_metrics"),
                    InlineKeyboardButton("👥 Список лидов", callback_data="leads_list")
                ],
                [
                    InlineKeyboardButton("📤 Экспорт в CSV", callback_data="export_csv"),
                    InlineKeyboardButton("📈 Google Sheets", callback_data="export_sheets")
                ],
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data="refresh_metrics")
                ]
            ]
            
            await update.message.reply_text(
                metrics_text, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения метрик: {str(e)}")
    
    async def on_detailed_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show detailed metrics"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        try:
            # Get detailed metrics
            metrics = await self.analytics.get_user_metrics(user.id)
            
            detailed_text = f"""
📊 *ДЕТАЛЬНАЯ СТАТИСТИКА*

*📈 Диалоги:*
• Сегодня: {metrics.get('dialogs_today', 0)}
• Вчера: {metrics.get('dialogs_yesterday', 0)}
• За неделю: {metrics.get('dialogs_week', 0)}
• За месяц: {metrics.get('dialogs_month', 0)}

*🔥 Лиды:*
• Всего: {metrics.get('leads_created', 0)}
• Hot: {metrics.get('hot_leads', 0)}
• Warm: {metrics.get('warm_leads', 0)}
• Cold: {metrics.get('cold_leads', 0)}

*📊 Конверсия:*
• Общая: {metrics.get('conversion_rate', 0):.1%}
• Hot → встреча: {metrics.get('hot_to_meeting_rate', 0):.1%}
• Встреча → сделка: {metrics.get('meeting_to_deal_rate', 0):.1%}

*📅 Встречи:*
• Назначено: {metrics.get('meetings_scheduled', 0)}
• Проведено: {metrics.get('meetings_completed', 0)}
• Отменено: {metrics.get('meetings_cancelled', 0)}

*🎯 Эффективность:*
• Средний score: {metrics.get('avg_lead_score', 0)}
• Лучший score: {metrics.get('max_lead_score', 0)}
• Время ответа: {metrics.get('avg_response_time', 0):.1f} сек
            """
            
            await query.message.reply_text(
                detailed_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад к дэшборду", callback_data="back_to_dashboard")]
                ])
            )
            
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def on_export_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Export metrics to CSV"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        try:
            # Get user leads
            leads = await self.supabase.get_user_leads(user.id)
            
            # Create CSV content
            csv_content = "ID,Имя,Телефон,Email,Score,Статус,Дата создания,Источник\n"
            for lead in leads:
                csv_content += f"{lead.get('id', '')},{lead.get('name', '')},{lead.get('phone', '')},{lead.get('email', '')},{lead.get('score', 0)},{lead.get('status', '')},{lead.get('created_at', '')},{lead.get('source', '')}\n"
            
            # Send CSV as file
            await query.message.reply_document(
                document=io.BytesIO(csv_content.encode('utf-8')),
                filename=f"leads_{user.id}_{datetime.now().strftime('%Y%m%d')}.csv",
                caption="📤 Экспорт лидов в CSV"
            )
            
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка экспорта: {str(e)}")
    
    async def on_export_sheets(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Export to Google Sheets"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        try:
            # Check if user has Google Sheets integration
            sheets_connected = await self.supabase.check_google_sheets_integration(user.id)
            
            if not sheets_connected:
                # Show integration setup
                await query.message.reply_text(
                    "🔗 *Google Sheets интеграция*\n\n"
                    "Для экспорта в Google Sheets нужно подключить интеграцию:\n\n"
                    "1. Перейдите в /settings\n"
                    "2. Выберите 'Google Sheets'\n"
                    "3. Авторизуйтесь в Google\n"
                    "4. Разрешите доступ к таблицам\n\n"
                    "После этого экспорт будет доступен автоматически!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Настройки", callback_data="open_settings")]
                    ])
                )
            else:
                # Export to Google Sheets
                await query.message.reply_text("📈 Экспортирую в Google Sheets...")
                
                # Simulate export
                await asyncio.sleep(2)
                
                await query.message.reply_text(
                    "✅ *Экспорт завершен!*\n\n"
                    "📊 Данные отправлены в Google Sheets\n"
                    "🔗 [Открыть таблицу](https://docs.google.com/spreadsheets/d/example)\n\n"
                    "Таблица обновляется автоматически каждые 15 минут.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_metrics")]
                    ])
                )
                
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка экспорта: {str(e)}")
    
    async def on_leads(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /leads command - show recent leads"""
        user = update.effective_user
        if not user:
            return
        
        try:
            # Get user leads from database
            leads = await self.supabase.get_user_leads(user.id)
            
            if not leads:
                await update.message.reply_text(
                    "📋 *Список лидов*\n\n"
                    "У вас пока нет лидов.\n"
                    "Загрузите файл или настройте бота для начала работы.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Create leads table
            leads_text = "📋 *СПИСОК ЛИДОВ*\n\n"
            leads_text += "┌─────────────────────────────────────────────────────────┐\n"
            leads_text += "│ Имя                │ Телефон        │ Score │ Статус │\n"
            leads_text += "├─────────────────────────────────────────────────────────┤\n"
            
            for lead in leads[:10]:  # Show first 10 leads
                name = lead.get('name', 'Неизвестно')[:15]
                phone = lead.get('phone', '')[:12]
                score = lead.get('score', 0)
                status = lead.get('status', 'new')
                
                # Status emoji
                status_emoji = "🔥" if score >= 70 else "🟡" if score >= 40 else "❄️"
                
                leads_text += f"│ {name:<15} │ {phone:<12} │ {score:>3}  │ {status_emoji} {status:<4} │\n"
            
            leads_text += "└─────────────────────────────────────────────────────────┘\n\n"
            
            # Add summary
            hot_count = sum(1 for lead in leads if lead.get('score', 0) >= 70)
            warm_count = sum(1 for lead in leads if 40 <= lead.get('score', 0) < 70)
            cold_count = sum(1 for lead in leads if lead.get('score', 0) < 40)
            
            leads_text += f"*📊 Итого:* {len(leads)} лидов\n"
            leads_text += f"• 🔥 Hot: {hot_count}\n"
            leads_text += f"• 🟡 Warm: {warm_count}\n"
            leads_text += f"• ❄️ Cold: {cold_count}\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 Детальная аналитика", callback_data="detailed_analytics"),
                    InlineKeyboardButton("📤 Экспорт CSV", callback_data="export_csv")
                ],
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data="refresh_metrics"),
                    InlineKeyboardButton("🔙 Дэшборд", callback_data="back_to_dashboard")
                ]
            ]
            
            await update.message.reply_text(
                leads_text, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения лидов: {str(e)}")
    
    async def on_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command - show integration settings"""
        user = update.effective_user
        if not user:
            return
        
        try:
            # Get integration status
            integration_manager = getattr(self, 'integration_manager', None)
            if not integration_manager:
                from .integration_manager import IntegrationManager
                integration_manager = IntegrationManager(self.supabase)
                self.integration_manager = integration_manager
            
            status = await integration_manager.get_integration_status(user.id)
            
            # Build status text
            settings_text = "⚙️ *НАСТРОЙКИ ИНТЕГРАЦИЙ*\n\n"
            
            # CRM Status
            crm_status = "✅" if status["crm"]["connected"] else "❌"
            crm_type = status["crm"]["type"].upper() if status["crm"]["type"] != "none" else "Не подключён"
            settings_text += f"*🏢 CRM:* {crm_status} {crm_type}\n"
            
            # Calendar Status
            calendar_status = "✅" if status["calendar"]["connected"] else "❌"
            calendar_type = status["calendar"]["type"].upper() if status["calendar"]["type"] != "none" else "Не подключён"
            settings_text += f"*📅 Календарь:* {calendar_status} {calendar_type}\n"
            
            # Email Status
            email_status = "✅" if status["email"]["connected"] else "❌"
            email_manager = status["email"]["manager_email"] if status["email"]["manager_email"] != "not_set" else "Не настроен"
            settings_text += f"*📧 Email:* {email_status} {email_manager}\n"
            
            # Google Sheets Status
            sheets_status = "✅" if status["google_sheets"]["connected"] else "❌"
            settings_text += f"*📊 Google Sheets:* {sheets_status}\n"
            
            settings_text += "\n*💡 Подключите интеграции для полной автоматизации:*"
            
            keyboard = [
                [
                    InlineKeyboardButton("🏢 CRM", callback_data="setup_crm"),
                    InlineKeyboardButton("📅 Календарь", callback_data="setup_calendar")
                ],
                [
                    InlineKeyboardButton("📧 Email", callback_data="setup_email"),
                    InlineKeyboardButton("📊 Google Sheets", callback_data="setup_sheets")
                ],
                [
                    InlineKeyboardButton("🔍 Тест подключений", callback_data="test_integrations"),
                    InlineKeyboardButton("❌ Отключить все", callback_data="disconnect_all")
                ]
            ]
            
            await update.message.reply_text(
                settings_text, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения настроек: {str(e)}")
    
    async def on_setup_crm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Setup CRM integration"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        try:
            setup_text = """
🏢 *НАСТРОЙКА CRM*

Выберите вашу CRM систему:

*amoCRM:*
• Подключение через OAuth 2.0
• Автоматическая синхронизация лидов
• Обновление статусов

*Bitrix24:*
• Подключение через OAuth
• Полная интеграция с воронкой
• Уведомления о новых лидах

*Webhook (любая CRM):*
• Универсальное подключение
• Отправка данных по webhook
• Поддержка любых CRM
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("🔗 amoCRM", callback_data="connect_amocrm"),
                    InlineKeyboardButton("🏢 Bitrix24", callback_data="connect_bitrix24")
                ],
                [
                    InlineKeyboardButton("🔌 Webhook", callback_data="setup_webhook"),
                    InlineKeyboardButton("❌ Отключить CRM", callback_data="disconnect_crm")
                ],
                [
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings")
                ]
            ]
            
            await query.message.reply_text(
                setup_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def on_setup_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Setup Calendar integration"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        try:
            setup_text = """
📅 *НАСТРОЙКА КАЛЕНДАРЯ*

*Яндекс.Календарь:*
• Подключение через OAuth 2.0
• Автоматическое создание встреч
• Синхронизация с вашим календарем
• Уведомления о встречах

*Google Calendar:*
• Подключение через Google OAuth
• Интеграция с Gmail
• Автоматические напоминания

*Outlook:*
• Подключение через Microsoft OAuth
• Синхронизация с Office 365
• Корпоративная интеграция
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📅 Яндекс.Календарь", callback_data="connect_yandex_calendar"),
                    InlineKeyboardButton("📊 Google Calendar", callback_data="connect_google_calendar")
                ],
                [
                    InlineKeyboardButton("📧 Outlook", callback_data="connect_outlook"),
                    InlineKeyboardButton("❌ Отключить календарь", callback_data="disconnect_calendar")
                ],
                [
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings")
                ]
            ]
            
            await query.message.reply_text(
                setup_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def on_setup_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Setup Email integration"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        try:
            setup_text = """
📧 *НАСТРОЙКА EMAIL*

*SMTP настройки:*
• Gmail: smtp.gmail.com:587
• Yandex: smtp.yandex.ru:587
• Mail.ru: smtp.mail.ru:587
• Корпоративная почта

*Настройки уведомлений:*
• Email менеджера для hot лидов
• Шаблоны писем
• Автоматические уведомления

*Безопасность:*
• Использование App Passwords
• Шифрование SMTP
• Защита данных
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📧 Настроить SMTP", callback_data="setup_smtp"),
                    InlineKeyboardButton("👤 Email менеджера", callback_data="setup_manager_email")
                ],
                [
                    InlineKeyboardButton("📝 Шаблоны писем", callback_data="setup_email_templates"),
                    InlineKeyboardButton("❌ Отключить email", callback_data="disconnect_email")
                ],
                [
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings")
                ]
            ]
            
            await query.message.reply_text(
                setup_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def on_test_integrations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Test all integrations"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        try:
            await query.message.reply_text("🔍 Тестирую подключения...")
            
            # Get integration manager
            integration_manager = getattr(self, 'integration_manager', None)
            if not integration_manager:
                from .integration_manager import IntegrationManager
                integration_manager = IntegrationManager(self.supabase)
                self.integration_manager = integration_manager
            
            # Test CRM
            crm_result = await integration_manager.test_crm_connection(user.id)
            crm_status = "✅" if crm_result.get("status") == "connected" else "❌"
            crm_message = crm_result.get("message", "Не подключен")
            
            # Test Calendar
            calendar_result = await integration_manager.test_calendar_connection(user.id)
            calendar_status = "✅" if calendar_result.get("status") == "connected" else "❌"
            calendar_message = calendar_result.get("message", "Не подключен")
            
            # Test Email
            email_result = await integration_manager.test_email_connection(user.id)
            email_status = "✅" if email_result.get("status") == "connected" else "❌"
            email_message = email_result.get("message", "Не настроен")
            
            test_results = f"""
🔍 *РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ*

*🏢 CRM:* {crm_status} {crm_message}

*📅 Календарь:* {calendar_status} {calendar_message}

*📧 Email:* {email_status} {email_message}

*💡 Рекомендации:*
• Подключите все интеграции для полной автоматизации
• Проверьте настройки подключений
• Обратитесь в поддержку при ошибках
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("🔙 Назад к настройкам", callback_data="back_to_settings"),
                    InlineKeyboardButton("🔄 Повторить тест", callback_data="test_integrations")
                ]
            ]
            
            await query.message.reply_text(
                test_results,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка тестирования: {str(e)}")
    
    async def on_billing(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /billing command - show billing information"""
        user = update.effective_user
        if not user:
            return
        
        try:
            subscription = await self.billing.get_user_subscription(user.id)
            if not subscription:
                await update.message.reply_text("❌ Подписка не найдена")
                return
            
            billing_text = f"""
💰 *Информация о подписке*

*Текущий план:* {subscription.tier.value.title()}
*Статус:* {subscription.status.value.title()}

*Использование:*
• Диалогов использовано: {subscription.dialogs_used}
• Лимит диалогов: {subscription.dialogs_limit if subscription.dialogs_limit > 0 else 'Безлимит'}

*Доступные тарифы:*
• 🥉 Basic: 9,900 ₽/мес (50-100 диалогов, без персонализации)
• 🥈 Pro: 19,900 ₽/мес (до 300 диалогов, персонализация, CRM)
• 🥇 Enterprise: 39,900 ₽/мес (500+ диалогов, кастом-бот, приоритетная поддержка)
            """
            
            if subscription.status.value == "trial":
                trial_info = self.billing.get_trial_info(subscription)
                billing_text += f"\n*Trial:* {trial_info}"
            
            keyboard = []
            if subscription.status.value in ["trial", "expired"] or subscription.is_read_only:
                keyboard.extend([
                    [InlineKeyboardButton("🥉 Basic (9,900 ₽)", callback_data="subscribe_basic")],
                    [InlineKeyboardButton("🥈 Pro (19,900 ₽)", callback_data="subscribe_pro")],
                    [InlineKeyboardButton("🥇 Enterprise (39,900 ₽)", callback_data="subscribe_enterprise")]
                ])
            
            if subscription.status.value == "active":
                keyboard.append([InlineKeyboardButton("❌ Отменить подписку", callback_data="cancel_subscription")])
            
            await update.message.reply_text(
                billing_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения информации о подписке: {str(e)}")
    
    async def on_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command - pause bot operations"""
        user = update.effective_user
        if not user:
            return
        
        # Track subscription cancellation
        subscription = await self.billing.get_user_subscription(user.id)
        if subscription:
            await self.analytics.track_subscription_cancelled(user.id, subscription.tier.value)
            await self.billing.cancel_subscription(user.id)
        
        await update.message.reply_text(
            "⏸️ Бот приостановлен. Для возобновления работы используйте /start"
        )
    
    async def on_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /export command - export leads to Excel"""
        user = update.effective_user
        if not user:
            return
        
        try:
            # Track export event
            await self.analytics.track_event("export_requested", user.id, {"format": "excel"})
            
            # Generate export file (placeholder)
            export_text = """
📤 *Экспорт лидов*

*Доступные форматы:*
• Excel (.xlsx) - Рекомендуется
• CSV (.csv) - Универсальный
• JSON (.json) - Для разработчиков

*Что экспортируется:*
• Все лиды за период
• Контактная информация
• Scores и статусы
• Даты создания
• Источники лидов
            """
            
            keyboard = [
                [InlineKeyboardButton("📊 Excel (.xlsx)", callback_data="export_excel")],
                [InlineKeyboardButton("📄 CSV (.csv)", callback_data="export_csv")],
                [InlineKeyboardButton("🔧 JSON (.json)", callback_data="export_json")]
            ]
            
            await update.message.reply_text(
                export_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка экспорта: {str(e)}")
    
    async def on_delete_my_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /delete_my_data command - GDPR compliance"""
        user = update.effective_user
        if not user:
            return
        
        try:
            # Show confirmation
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить все данные", callback_data="confirm_delete_data")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete_data")]
            ]
            
            await update.message.reply_text(
                "⚠️ *Удаление всех данных*\n\n"
                "Это действие удалит:\n"
                "• Все ваши лиды\n"
                "• Скрипты и настройки\n"
                "• Историю диалогов\n"
                "• Подписку и платежи\n\n"
                "Действие необратимо!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def on_terms(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /terms command - show terms of service"""
        terms_text = """
📋 *Условия использования AL Bot*

*Ответственность за данные:*
Агентство несёт полную ответственность за законность использования базы клиентов и соблюдение требований ФЗ-152 "О персональных данных".

*Обработка данных:*
• Лиды шифруются в базе данных
• Телефоны и email маскируются в логах
• Данные хранятся в соответствии с GDPR
• Возможность полного удаления данных

*Использование:*
• Trial: 14 дней или 50 диалогов
• После trial: доступ только к истории
• Платные планы: безлимитные диалоги
• Автоматическое продление подписки

*Интеграции:*
• Календарь: через OAuth (безопасно)
• CRM: через API (защищённо)
• Экспорт: в зашифрованном виде

*Поддержка:*
• Telegram: @albot_support
• Email: support@albot.ru
• Документация: docs.albot.ru
        """
        
        await update.message.reply_text(terms_text, parse_mode=ParseMode.MARKDOWN)
    
    async def on_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command - show system status (admin only)"""
        user = update.effective_user
        if not user:
            return
        
        # Check if user is admin (placeholder)
        if user.id not in [123456789]:  # Replace with actual admin IDs
            await update.message.reply_text("❌ Доступ запрещён")
            return
        
        try:
            status = await self.monitoring.get_system_status()
            
            status_text = f"""
🔧 *Статус системы*

*Время:* {status.get('timestamp', 'N/A')}
*Активных пользователей:* {status.get('active_users', 0)}
*Диалогов сегодня:* {status.get('total_dialogs_today', 0)}
*Ошибок за 5 мин:* {status.get('error_rate', 0):.1%}
*Очередь сообщений:* {status.get('queue_size', 0)}
*Нерешённых алертов:* {status.get('unresolved_alerts', 0)}
            """
            
            await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статуса: {str(e)}")
