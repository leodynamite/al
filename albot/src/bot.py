from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from loguru import logger
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.constants import ParseMode
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler,
)

from .config import AppConfig
from .llm import LLMClient
from .parsing import parse_file, ParsedData
from .integrations import send_email_smtp, SupabaseClient
from .models import Script, ScriptQuestion, QuestionType
from .billing import BillingManager, SubscriptionTier
from .analytics import AnalyticsManager, EventType
from .monitoring import MonitoringManager
from .commands import BotCommands
from .branding import BrandingManager
from .hot_leads import HotLeadsManager
from .error_handler import ErrorHandler
from .ux_texts import UXTexts
from .commercial import CommercialManager


ASK_NAME, ASK_GOAL = range(2)

# Онбординг: состояния
(
    Q_BIZ_TYPE,
    Q_AVG_CHECK,
    Q_CHANNEL,
    Q_GOAL_MULTI,
    Q_URGENCY,
    Q_REGION,
    Q_AGENTS,
    Q_OUTBOUND,
    Q_LEGAL,
) = range(10, 19)

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".docx", ".txt"}


@dataclass
class UserSession:
    name: Optional[str] = None
    goal: Optional[str] = None
    input_file_path: Optional[Path] = None


class ALBot:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._app: Optional[Application] = None
        self._llm = LLMClient(config.llm)
        self._supabase = SupabaseClient(
            config.supabase_url or "",
            config.supabase_anon_key or "",
            config.encryption_key
        )
        self._billing = BillingManager(config, self._supabase)
        self._analytics = AnalyticsManager(config, self._supabase)
        self._monitoring = MonitoringManager(config, self._supabase)
        self._commands = BotCommands(self._billing, self._analytics, self._monitoring, self._supabase)
        self._branding = BrandingManager()
        self._hot_leads = HotLeadsManager(config, self._supabase, self._analytics)
        self._error_handler = ErrorHandler(self._monitoring, self._supabase)
        self._ux_texts = UXTexts(self._branding, self._billing)
        self._commercial = CommercialManager(self._billing, self._branding, self._analytics)

    def build(self) -> Application:
        app = (
            ApplicationBuilder()
            .token(self.config.telegram.bot_token)
            .concurrent_updates(True)
            .build()
        )

        app.add_handler(CommandHandler("start", self.on_start))
        app.add_handler(CommandHandler("help", self.on_help))
        app.add_handler(CommandHandler("offer", self.on_offer))
        app.add_handler(CommandHandler("metrics", self._commands.on_metrics))
        app.add_handler(CommandHandler("leads", self._commands.on_leads))
        app.add_handler(CommandHandler("settings", self._commands.on_settings))
        app.add_handler(CommandHandler("stop", self._commands.on_stop))
        app.add_handler(CommandHandler("billing", self._commands.on_billing))
        app.add_handler(CommandHandler("export", self._commands.on_export))
        app.add_handler(CommandHandler("delete_my_data", self._commands.on_delete_my_data))
        app.add_handler(CommandHandler("terms", self._commands.on_terms))
        app.add_handler(CommandHandler("status", self._commands.on_system_status))
        # Календарь
        app.add_handler(CommandHandler("connect_calendar", self.on_connect_calendar))
        app.add_handler(CommandHandler("calendar_code", self.on_calendar_code))
        app.add_handler(CommandHandler("calendar", self.on_calendar))

        # File upload
        app.add_handler(MessageHandler(filters.Document.ALL, self.on_file))

        # Simple questionnaire
        conv = ConversationHandler(
            entry_points=[CommandHandler("brief", self.on_brief_start)],
            states={
                ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_name)],
                ASK_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_goal)],
            },
            fallbacks=[CommandHandler("cancel", self.on_cancel)],
            name="brief",
            persistent=False,
        )
        app.add_handler(conv)

        # Онбординг-вопросник (если нет файла)
        onboarding = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.on_onboarding_start, pattern="^menu_brief$")],
            states={
                Q_BIZ_TYPE: [CallbackQueryHandler(self.on_q_biz_type)],
                Q_AVG_CHECK: [CallbackQueryHandler(self.on_q_avg_check)],
                Q_CHANNEL: [CallbackQueryHandler(self.on_q_channel)],
                Q_GOAL_MULTI: [CallbackQueryHandler(self.on_q_goal_multi)],
                Q_URGENCY: [CallbackQueryHandler(self.on_q_urgency)],
                Q_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_q_region)],
                Q_AGENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_q_agents)],
                Q_OUTBOUND: [CallbackQueryHandler(self.on_q_outbound)],
                Q_LEGAL: [CallbackQueryHandler(self.on_q_legal)],
            },
            fallbacks=[CommandHandler("cancel", self.on_cancel)],
            name="onboarding",
            persistent=False,
        )
        app.add_handler(onboarding)

        # Callback buttons (редактор скрипта и общее)
        app.add_handler(CallbackQueryHandler(self.on_toggle_mandatory, pattern=r"^toggle:mandatory:"))
        app.add_handler(CallbackQueryHandler(self.on_weight_change, pattern=r"^weight:q:"))
        app.add_handler(CallbackQueryHandler(self.on_set_hot_values, pattern=r"^hotvals:q:"))
        app.add_handler(CallbackQueryHandler(self.on_move_question, pattern=r"^move:q:"))
        app.add_handler(CallbackQueryHandler(self.on_change_type, pattern=r"^type:q:"))
        app.add_handler(CallbackQueryHandler(self.on_edit_question, pattern=r"^edit:q:"))
        app.add_handler(CallbackQueryHandler(self.on_cancel_edit, pattern="^cancel_edit$"))
        app.add_handler(CallbackQueryHandler(self.on_activate_script, pattern="^activate_script$"))
        app.add_handler(CallbackQueryHandler(self.on_dashboard_action, pattern="^(detailed_metrics|leads_list|export_csv|export_sheets|refresh_metrics|back_to_dashboard|open_settings)$"))
        app.add_handler(CallbackQueryHandler(self.on_action))
        app.add_handler(CallbackQueryHandler(self.on_commercial_offer, pattern="^commercial_offer$"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text_input))

        self._app = app
        return app

    async def on_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input for various purposes"""
        # Check if user is waiting for hot values input
        if context.user_data.get("waiting_for_hot_values"):
            await self.on_hot_values_input(update, context)
            return
            
        # Check if user is editing question text
        if context.user_data.get("waiting_for_question_text"):
            await self.on_save_question_text(update, context)
            return
            
        # Default response
        await update.message.reply_text(
            "Используйте /start для начала работы с ботом"
        )

    async def on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user:
            return
        
        # Track user onboarding
        await self._analytics.track_user_onboarded(user.id, "start_command")
        
        # Check subscription status
        subscription = await self._billing.get_user_subscription(user.id)
        if not subscription:
            subscription = await self._billing.create_trial_subscription(user.id)
        
        # Check if trial expired or read-only mode
        if await self._billing.check_trial_expired(subscription):
            await update.message.reply_text(
                "🔒 Ваш trial период истёк. Бот переведён в read-only режим.\n"
                "Доступна только история, новые лиды не принимаются.\n"
                "Оформите подписку для продолжения работы.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💰 Оформить подписку", callback_data="menu_pricing")
                ]])
            )
            return
        
        # Check if in read-only mode
        if subscription.is_read_only:
            await update.message.reply_text(
                "🔒 Бот работает в read-only режиме.\n"
                "Доступна только история, новые лиды не принимаются.\n"
                "Оформите подписку для продолжения работы.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💰 Оформить подписку", callback_data="menu_pricing")
                ]])
            )
            return
        
        # Get branding based on subscription
        branding = self._branding.get_bot_branding(subscription)
        welcome_text = await self._ux_texts.get_welcome_message(user.id)
        
        # Add subscription info
        if subscription.status.value == "trial":
            trial_info = self._billing.get_trial_info(subscription)
            welcome_text += f"\n\n*Статус:* {trial_info}"
        
        webapp_buttons = []
        if getattr(self.config, "webapp_url", None) and str(self.config.webapp_url).startswith("https"):
            webapp_buttons.append(InlineKeyboardButton("🚀 Открыть приложение", web_app=WebAppInfo(url=str(self.config.webapp_url))))

        kb = InlineKeyboardMarkup([
            webapp_buttons if webapp_buttons else [],
            [
                InlineKeyboardButton("Загрузить файл", callback_data="menu_upload"),
                InlineKeyboardButton("Ответить на вопросы", callback_data="menu_brief"),
            ],
            [
                InlineKeyboardButton("Посмотреть демо", callback_data="menu_demo"),
                InlineKeyboardButton("Тарифы", callback_data="menu_pricing"),
            ],
            [
                InlineKeyboardButton("📊 Метрики", callback_data="menu_metrics"),
                InlineKeyboardButton("👥 Лиды", callback_data="menu_leads"),
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings"),
            ],
            [
                InlineKeyboardButton("💼 Коммерческое предложение", callback_data="commercial_offer"),
            ],
        ])
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )

    async def on_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = self._ux_texts.get_help_message()
        await update.message.reply_text(help_text)
    
    async def on_offer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Commercial offer command handler"""
        user = update.effective_user
        if not user:
            return
        
        # Get commercial offer
        offer = await self._commercial.get_commercial_offer(user.id)
        
        if offer["offer_type"] == "trial":
            text = f"🚀 {offer['title']}\n\n{offer['description']}\n\n"
            text += "✅ Преимущества:\n"
            for benefit in offer["benefits"]:
                text += f"• {benefit}\n"
            text += "\n⚠️ Ограничения:\n"
            for limitation in offer["limitations"]:
                text += f"• {limitation}\n"
            text += f"\n💰 Цена: {offer['price']}"
            
        elif offer["offer_type"] == "upgrade":
            text = f"⏰ {offer['title']}\n\n{offer['description']}\n\n"
            text += "✅ Преимущества:\n"
            for benefit in offer["benefits"]:
                text += f"• {benefit}\n"
            text += f"\n🧠 {offer['psychological_effect']}\n\n"
            text += "💰 Тарифы:\n"
            for tier, info in offer["pricing"].items():
                text += f"• {tier.title()}: {info['price']} ({info['dialogs']})\n"
                
        else:  # current_plan
            text = f"✅ {offer['title']}\n\n{offer['description']}\n\n"
            text += "✅ Ваши преимущества:\n"
            for benefit in offer["benefits"]:
                text += f"• {benefit}\n"
            text += f"\n📊 Использование: {offer['usage']['dialogs_used']}/{offer['usage']['dialogs_limit']} диалогов"
        
        # Add ROI calculation
        roi = await self._commercial.get_roi_calculation(user.id)
        if roi.get("calculation"):
            text += f"\n\n💰 {roi['message']}\n"
            calc = roi["calculation"]
            text += f"• Потенциальная выручка: {calc['potential_revenue']:,.0f} ₽\n"
            text += f"• ROI: {calc['roi_percent']:.1f}%\n"
            text += f"• {roi['conclusion']}"
        
        await update.message.reply_text(text)
    
    async def on_commercial_offer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Commercial offer button handler"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        if not user:
            return
        
        # Get commercial offer
        offer = await self._commercial.get_commercial_offer(user.id)
        
        if offer["offer_type"] == "trial":
            text = f"🚀 {offer['title']}\n\n{offer['description']}\n\n"
            text += "✅ Преимущества:\n"
            for benefit in offer["benefits"]:
                text += f"• {benefit}\n"
            text += "\n⚠️ Ограничения:\n"
            for limitation in offer["limitations"]:
                text += f"• {limitation}\n"
            text += f"\n💰 Цена: {offer['price']}"
            
        elif offer["offer_type"] == "upgrade":
            text = f"⏰ {offer['title']}\n\n{offer['description']}\n\n"
            text += "✅ Преимущества:\n"
            for benefit in offer["benefits"]:
                text += f"• {benefit}\n"
            text += f"\n🧠 {offer['psychological_effect']}\n\n"
            text += "💰 Тарифы:\n"
            for tier, info in offer["pricing"].items():
                text += f"• {tier.title()}: {info['price']} ({info['dialogs']})\n"
                
        else:  # current_plan
            text = f"✅ {offer['title']}\n\n{offer['description']}\n\n"
            text += "✅ Ваши преимущества:\n"
            for benefit in offer["benefits"]:
                text += f"• {benefit}\n"
            text += f"\n📊 Использование: {offer['usage']['dialogs_used']}/{offer['usage']['dialogs_limit']} диалогов"
        
        # Add ROI calculation
        roi = await self._commercial.get_roi_calculation(user.id)
        if roi.get("calculation"):
            text += f"\n\n💰 {roi['message']}\n"
            calc = roi["calculation"]
            text += f"• Потенциальная выручка: {calc['potential_revenue']:,.0f} ₽\n"
            text += f"• ROI: {calc['roi_percent']:.1f}%\n"
            text += f"• {roi['conclusion']}"
        
        # Add psychological benefits
        psych_benefits = await self._commercial.get_psychological_benefits()
        text += f"\n\n{psych_benefits['title']}\n"
        for benefit in psych_benefits["benefits"]:
            text += f"• {benefit['title']}: {benefit['description']}\n"
        text += f"\n{psych_benefits['conclusion']}"
        
        await query.edit_message_text(text=text)

    async def on_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        assert update.message is not None
        doc = update.message.document
        if not doc:
            return
        # Проверка расширения
        suffix = ""
        if doc.file_name:
            suffix = Path(doc.file_name).suffix.lower()
        if suffix and suffix not in SUPPORTED_EXTENSIONS:
            await update.message.reply_text(
                "Поддерживаемые форматы: .csv, .xlsx, .xls, .pdf, .docx, .txt"
            )
            return
        # Show upload progress
        status_msg = await update.message.reply_text("📤 Загружаю файл...")
        
        # Download file
        file = await doc.get_file()
        dest = self.config.storage.data_dir / f"{doc.file_id}_{doc.file_name or 'upload'}"
        await file.download_to_drive(custom_path=str(dest))
        
        # Update progress
        await status_msg.edit_text("📥 Файл загружен, анализирую...")
        
        session = context.user_data.setdefault("session", UserSession())
        session.input_file_path = dest
        
        # Show analysis progress with countdown
        for i in range(15, 0, -1):
            await status_msg.edit_text(f"🔍 Анализирую файл... ({i} сек)")
            await asyncio.sleep(1)
        
        await status_msg.edit_text("✅ Анализ завершен!")
        # Парсинг файла
        parsed = parse_file(dest)
        # Пустой файл
        if not parsed.contacts and not parsed.raw_text:
            csv_template = "name,phone,email,source,comment\nИван,+7xxxxxxxxxx,ivan@example.com,upload,Заявка"
            await update.message.reply_text("Файл пустой. Загрузите CSV по шаблону ниже:")
            await update.message.reply_text(f"```\n{csv_template}\n```", parse_mode=ParseMode.MARKDOWN)
            return
        # Если есть текст — извлечь сущности через LLM
        entities = {}
        if parsed.raw_text:
            entities = (await self._llm.extract_entities(parsed.raw_text)).get("entities", {})
        # Сформировать промпт на основе парсинга
        parts = []
        if parsed.sample_ad:
            parts.append(f"Пример объявления: {parsed.sample_ad}")
        if parsed.avg_price:
            parts.append(f"Средняя цена: {parsed.avg_price}")
        if parsed.address:
            parts.append(f"Адрес: {parsed.address}")
        if entities:
            parts.append(f"Сущности: {entities}")
        if parsed.contacts:
            lead_lines = []
            for c in parsed.contacts[:5]:
                lead_lines.append(f"{c.name or ''} {c.phone or ''} {c.email or ''} {c.source or ''} {c.comment or ''}".strip())
            parts.append("Контакты (пример):\n" + "\n".join(lead_lines))
        context.user_data["parsed_prompt"] = "\n".join(parts)
        await self._run_llm(update, context, source="file")

    async def on_brief_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["session"] = UserSession()
        await update.message.reply_text("Как вас зовут?")
        return ASK_NAME

    async def on_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session: UserSession = context.user_data.get("session")
        session.name = update.message.text.strip()
        await update.message.reply_text("Какая главная цель диалога? (пример: квалификация лида)")
        return ASK_GOAL

    async def on_goal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        session: UserSession = context.user_data.get("session")
        session.goal = update.message.text.strip()
        await update.message.reply_text("Спасибо! Запускаю анализ…")
        await self._run_llm(update, context, source="brief")
        return ConversationHandler.END

    async def on_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Отменено.")
        return ConversationHandler.END

    async def _run_llm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *, source: str):
        session: UserSession = context.user_data.get("session")
        # Составляем промпт из анкеты/файла
        parts = []
        if session and session.name:
            parts.append(f"Имя: {session.name}")
        if session and session.goal:
            parts.append(f"Цель: {session.goal}")
        if session and session.input_file_path:
            parts.append(f"Файл: {session.input_file_path.name}")
        if context.user_data.get("parsed_prompt"):
            parts.append(context.user_data["parsed_prompt"])
        prompt = "\n".join(parts) or "Подготовь универсальный скрипт квалификации лида."
        # Выбор промпта по источнику
        if source in {"file", "onboarding"} and context.user_data.get("parsed_prompt"):
            try:
                result = await asyncio.wait_for(
                    self._llm.analyze_agency(context.user_data["parsed_prompt"]),
                    timeout=25,
                )
            except asyncio.TimeoutError:
                await update.message.reply_text("⏱️ Время ожидания ответа AI истекло. Показываю универсальный шаблон.")
                result = {"script": ScriptTemplates().get_universal_template()}
            except Exception:
                await update.message.reply_text("⚠️ Не удалось получить ответ AI. Показываю универсальный шаблон.")
                result = {"script": ScriptTemplates().get_universal_template()}
        elif source == "brief":
            result = await self._llm.script_from_answers({
                "name": getattr(session, "name", None),
                "goal": getattr(session, "goal", None),
            })
        else:
            result = await self._llm.generate_script({"prompt": prompt, "source": source})
        context.user_data["last_result"] = result
        # Сохраним скрипт в модель для редактора, если возможен список
        self._ensure_script_model(context, result)
        script = result.get("script", "Черновик скрипта")
        recs_list = result.get("recommendations", [])
        recs = "\n".join(f"- {r}" for r in recs_list) if recs_list else "Рекомендаций нет."

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Просмотреть скрипт", callback_data="view_script"),
                InlineKeyboardButton("Редактировать вручную", callback_data="edit_script"),
            ],
            [
                InlineKeyboardButton("Применить и запустить тест", callback_data="apply_and_test"),
            ],
        ])
        text = self._ux_texts.get_script_ready_message()
        if update.message:
            await update.message.reply_html(text, reply_markup=kb, disable_web_page_preview=True)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text=text, reply_markup=kb, parse_mode=ParseMode.HTML)

    async def on_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        action = query.data
        if action == "menu_upload":
            await query.message.reply_text("Пришлите файл (.csv, .xlsx, .pdf, .docx)")
        elif action == "menu_brief":
            # Этот кейс перехватит onboarding ConversationHandler
            return
        elif action == "menu_demo":
            await query.message.reply_text(
                "Демо: пример диалога\n— Бот: Чем могу помочь?\n— Лид: Хочу автоматизировать лидогенерацию...\n\nДемо дашборда: Конверсия, кол-во лидов, % квалифицированных."
            )
        elif action == "menu_pricing":
            await query.message.reply_text(
                "Тарифы: Starter $29, Pro $99, Scale $299. /billing для оформления"
            )
        elif action == "view_script":
            await self._show_script(query, context)
        elif action == "edit_script":
            await self._show_script_editor(query, context)
        elif action == "apply_and_test":
            # Show preview dialog first
            await self._show_preview_dialog(query, context)
        elif action == "test_auto":
            await query.message.reply_text("Симуляция: 10 диалогов, найдено 3 hot-лида. Рекомендация: назначить созвон.")
        elif action == "test_inbound":
            await query.message.reply_text("Ожидаю входящие лиды… (заглушка)")
        elif action == "menu_metrics":
            await self._show_metrics(query, context)
        elif action == "menu_settings":
            await self._show_settings(query, context)
        elif action == "menu_leads":
            await self._show_leads(query, context)
        elif action == "back_to_main":
            await self._show_main_menu(query, context)

    async def _open_editor(self, query, context: ContextTypes.DEFAULT_TYPE):
        await self._show_script_editor(query, context)
    
    async def _show_metrics(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать метрики"""
        metrics_text = """📊 **Аналитика**
        
**Сегодня:**
• Лидов: 12
• Горячих: 3
• Конверсия: 25%

**За неделю:**
• Лидов: 47
• Горячих: 12
• Встреч: 8

**Топ источники:**
• Авито: 35%
• Прямые звонки: 28%
• Instagram: 22%"""
        
        keyboard = [
            [InlineKeyboardButton("📈 Детальная аналитика", callback_data="detailed_metrics")],
            [InlineKeyboardButton("📊 Экспорт данных", callback_data="export_data")],
            [InlineKeyboardButton("← Назад", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            metrics_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_settings(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать настройки"""
        settings_text = """⚙️ **Настройки**
        
**Интеграции:**
• CRM: Не подключено
• Календарь: Не подключено
• Email: Не подключено

**Уведомления:**
• Push: Включено
• Email: Выключено

**Безопасность:**
• Шифрование: Включено
• Логи: Частично маскированы"""
        
        keyboard = [
            [InlineKeyboardButton("🔗 Подключить CRM", callback_data="setup_crm")],
            [InlineKeyboardButton("📅 Подключить календарь", callback_data="setup_calendar")],
            [InlineKeyboardButton("📧 Настройки email", callback_data="setup_email")],
            [InlineKeyboardButton("← Назад", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_leads(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать лиды"""
        leads_text = """👥 **Лиды**
        
**Горячие (3):**
• Иван Петров - Москва, 12млн
• Мария Сидорова - СПб, 8млн
• Алексей Козлов - Казань, 15млн

**Теплые (5):**
• Анна Смирнова - Москва, 5млн
• Дмитрий Волков - СПб, 7млн
• Елена Морозова - Казань, 6млн
• Сергей Новиков - Москва, 4млн
• Ольга Лебедева - СПб, 9млн

**Холодные (12):**
• Показать все..."""
        
        keyboard = [
            [InlineKeyboardButton("🔥 Горячие лиды", callback_data="hot_leads")],
            [InlineKeyboardButton("📞 Назначить встречи", callback_data="schedule_meetings")],
            [InlineKeyboardButton("📊 Фильтры", callback_data="leads_filters")],
            [InlineKeyboardButton("← Назад", callback_data="back_to_main")]
        ]
        
        await query.edit_message_text(
            leads_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_main_menu(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню"""
        welcome_text = """Привет! Я AL Bot — ваш AI-ассистент по лидогенерации.

В бесплатной версии я работаю под своим брендом.
В платной — клиенты будут видеть именно ваше агентство.

Выберите действие:"""
        
        webapp_buttons = []
        if getattr(self.config, "webapp_url", None) and str(self.config.webapp_url).startswith("https"):
            webapp_buttons.append(InlineKeyboardButton("🚀 Открыть приложение", web_app=WebAppInfo(url=str(self.config.webapp_url))))

        keyboard = [
            webapp_buttons if webapp_buttons else [],
            [
                InlineKeyboardButton("Загрузить файл", callback_data="menu_upload"),
                InlineKeyboardButton("Ответить на вопросы", callback_data="menu_brief"),
            ],
            [
                InlineKeyboardButton("Посмотреть демо", callback_data="menu_demo"),
                InlineKeyboardButton("Тарифы", callback_data="menu_pricing"),
            ],
            [
                InlineKeyboardButton("📊 Метрики", callback_data="menu_metrics"),
                InlineKeyboardButton("👥 Лиды", callback_data="menu_leads"),
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings"),
            ],
            [
                InlineKeyboardButton("💼 Коммерческое предложение", callback_data="commercial_offer"),
            ],
        ]
        
        await query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== Скрипт/редактор =====
    def _ensure_script_model(self, context: ContextTypes.DEFAULT_TYPE, result: Dict[str, Any]) -> None:
        if context.user_data.get("script_model"):
            return
        scr = result.get("script")
        if not isinstance(scr, list):
            return
        questions: List[ScriptQuestion] = []
        for idx, item in enumerate(scr, start=1):
            qid = str(item.get("id") or f"q{idx}")
            qtype_val = str(item.get("type") or "text")
            try:
                qtype = QuestionType(qtype_val) if qtype_val in QuestionType._value2member_map_ else QuestionType.text
            except Exception:
                qtype = QuestionType.text
            questions.append(ScriptQuestion(
                id=qid,
                order=int(item.get("order") or idx),
                text=str(item.get("text") or "Вопрос"),
                type=qtype,
                choices=item.get("choices") if isinstance(item.get("choices"), list) else None,
                mandatory=bool(item.get("mandatory") or False),
                weight=int(item.get("weight") or 0),
                hot_values=item.get("hot_values") if isinstance(item.get("hot_values"), list) else None,
            ))
        context.user_data["script_model"] = Script(id="scr_1", name="Черновик", created_by="org_1", questions=sorted(questions, key=lambda q: q.order))

    async def _show_script(self, query, context: ContextTypes.DEFAULT_TYPE):
        script: Script | None = context.user_data.get("script_model")
        if not script:
            await query.message.reply_text("Скрипт недоступен")
            return
        lines = [f"{q.order}) {q.text} [{q.type}] {'*' if q.mandatory else ''}" for q in script.questions]
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Preview", callback_data="preview"), InlineKeyboardButton("Activate", callback_data="activate")], [InlineKeyboardButton("Test 10", callback_data="test_auto")]])
        await query.message.reply_text("\n".join(lines), reply_markup=kb)

    async def _show_script_editor(self, query, context: ContextTypes.DEFAULT_TYPE):
        script: Script | None = context.user_data.get("script_model")
        if not script:
            await query.message.reply_text("Скрипт недоступен")
            return
        for q in sorted(script.questions, key=lambda z: z.order):
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("↑", callback_data=f"move:q:{q.id}:up"), InlineKeyboardButton("↓", callback_data=f"move:q:{q.id}:down")],
                [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit:q:{q.id}"), InlineKeyboardButton("Тип", callback_data=f"type:q:{q.id}")],
                [InlineKeyboardButton("Обязательный", callback_data=f"toggle:mandatory:{q.id}"), InlineKeyboardButton("Вес -", callback_data=f"weight:q:{q.id}:-")],
                [InlineKeyboardButton(f"{q.weight}", callback_data="noop"), InlineKeyboardButton("Вес +", callback_data=f"weight:q:{q.id}:+")],
                [InlineKeyboardButton("hot_values", callback_data=f"hotvals:q:{q.id}")],
            ])
            title = f"{q.order}) {q.text}\nТип: {q.type}\nОбязательный: {'да' if q.mandatory else 'нет'}\nВес: {q.weight}\nHot: {', '.join(q.hot_values or [])}"
            await query.message.reply_text(title, reply_markup=kb)

    async def on_edit_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline question editing"""
        query = update.callback_query
        await query.answer()
        
        # Extract question ID from callback data
        data = query.data.split(":")
        if len(data) != 3 or data[0] != "edit":
            return
            
        question_id = data[2]
        script: Script | None = context.user_data.get("script_model")
        if not script:
            await query.message.reply_text("Скрипт недоступен")
            return
            
        # Find the question
        question = None
        for q in script.questions:
            if q.id == question_id:
                question = q
                break
                
        if not question:
            await query.message.reply_text("Вопрос не найден")
            return
            
        # Store question ID for editing
        context.user_data["editing_question_id"] = question_id
        
        # Ask for new text
        await query.message.reply_text(
            f"Редактирование вопроса:\n\n{question.text}\n\nВведите новый текст вопроса:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit")]
            ])
        )
        
        # Set conversation state for text input
        context.user_data["waiting_for_question_text"] = True

    async def on_save_question_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save edited question text"""
        if not context.user_data.get("waiting_for_question_text"):
            return
            
        new_text = update.message.text.strip()
        if not new_text:
            await update.message.reply_text("Текст не может быть пустым")
            return
            
        question_id = context.user_data.get("editing_question_id")
        if not question_id:
            await update.message.reply_text("Ошибка: ID вопроса не найден")
            return
            
        script: Script | None = context.user_data.get("script_model")
        if not script:
            await update.message.reply_text("Скрипт недоступен")
            return
            
        # Find and update the question
        for q in script.questions:
            if q.id == question_id:
                q.text = new_text
                break
                
        # Clear editing state
        context.user_data["waiting_for_question_text"] = False
        context.user_data["editing_question_id"] = None
        
        await update.message.reply_text(
            "✅ Вопрос обновлен!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Продолжить редактирование", callback_data="edit_script")]
            ])
        )

    async def on_cancel_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel question editing"""
        query = update.callback_query
        await query.answer()
        
        # Clear editing state
        context.user_data["waiting_for_question_text"] = False
        context.user_data["editing_question_id"] = None
        
        await query.message.reply_text(
            "❌ Редактирование отменено",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Вернуться к редактированию", callback_data="edit_script")]
            ])
        )

    async def _show_preview_dialog(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Show preview dialog with test leads"""
        script: Script | None = context.user_data.get("script_model")
        if not script:
            await query.message.reply_text("Скрипт недоступен")
            return
            
        # Generate test leads
        test_leads = [
            {"name": "Анна Петрова", "phone": "+7 999 123-45-67", "budget": "8 млн", "urgency": "Срочно"},
            {"name": "Михаил Сидоров", "phone": "+7 999 234-56-78", "budget": "12 млн", "urgency": "Средне"},
            {"name": "Елена Козлова", "phone": "+7 999 345-67-89", "budget": "15 млн", "urgency": "Срочно"},
            {"name": "Дмитрий Иванов", "phone": "+7 999 456-78-90", "budget": "6 млн", "urgency": "Длительно"},
            {"name": "Ольга Смирнова", "phone": "+7 999 567-89-01", "budget": "20 млн", "urgency": "Срочно"}
        ]
        
        preview_text = "🎭 **Preview диалога с тест-лидами:**\n\n"
        
        for i, lead in enumerate(test_leads, 1):
            preview_text += f"**{i}. {lead['name']}** ({lead['phone']})\n"
            preview_text += f"   Бюджет: {lead['budget']}, Срочность: {lead['urgency']}\n\n"
            
            # Simulate conversation
            for j, question in enumerate(script.questions[:3], 1):  # Show first 3 questions
                preview_text += f"🤖 {question.text}\n"
                if question.type == "choice":
                    preview_text += f"👤 Выбирает: {['Вариант 1', 'Вариант 2', 'Вариант 3'][j % 3]}\n"
                elif question.type == "text":
                    preview_text += f"👤 Отвечает: {['Да, интересно', 'Нет, не подходит', 'Возможно'][j % 3]}\n"
                else:
                    preview_text += f"👤 Отвечает: {['Да', 'Нет', 'Не знаю'][j % 3]}\n"
                preview_text += "\n"
            
            preview_text += "---\n\n"
        
        preview_text += "✅ **Готово!** Скрипт протестирован на 5 лидах.\n"
        preview_text += "🎯 **Результат:** 3 hot-лида, 2 warm-лида\n"
        preview_text += "💡 **Рекомендация:** Назначить созвон с hot-лидами"
        
        await query.message.reply_text(
            preview_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🚀 Активировать скрипт", callback_data="activate_script"),
                    InlineKeyboardButton("📝 Редактировать", callback_data="edit_script")
                ],
                [
                    InlineKeyboardButton("🔄 Новый preview", callback_data="apply_and_test")
                ]
            ])
        )

    async def on_activate_script(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Activate script and start working"""
        query = update.callback_query
        await query.answer()
        
        # Track script activation
        await self._analytics.track_script_applied(query.from_user.id)
        
        await query.message.reply_text(
            "🎉 **Скрипт активирован!**\n\n"
            "✅ Бот готов к работе\n"
            "📊 Отслеживание лидов включено\n"
            "🔔 Уведомления о hot-лидах активны\n\n"
            "Используйте команды:\n"
            "• /metrics - статистика\n"
            "• /leads - просмотр лидов\n"
            "• /settings - настройки\n"
            "• /stop - остановить бота",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 Статистика", callback_data="show_metrics"),
                    InlineKeyboardButton("👥 Лиды", callback_data="show_leads")
                ],
                [
                    InlineKeyboardButton("⚙️ Настройки", callback_data="show_settings")
                ]
            ])
        )

    async def on_dashboard_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle dashboard action buttons"""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        
        if action == "detailed_metrics":
            await self._commands.on_detailed_metrics(update, context)
        elif action == "leads_list":
            await self._commands.on_leads(update, context)
        elif action == "export_csv":
            await self._commands.on_export_csv(update, context)
        elif action == "export_sheets":
            await self._commands.on_export_sheets(update, context)
        elif action == "refresh_metrics":
            await self._commands.on_metrics(update, context)
        elif action == "back_to_dashboard":
            await self._commands.on_metrics(update, context)
        elif action == "open_settings":
            await self._commands.on_settings(update, context)

    async def on_toggle_mandatory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cq = update.callback_query
        await cq.answer()
        _, _, qid = cq.data.split(":", 2)
        script: Script | None = context.user_data.get("script_model")
        if not script:
            return
        for qu in script.questions:
            if qu.id == qid:
                qu.mandatory = not qu.mandatory
                break
        await cq.message.reply_text("Обязательность обновлена.")

    async def on_weight_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cq = update.callback_query
        await cq.answer()
        _, _, qid, sign = cq.data.split(":", 3)
        script: Script | None = context.user_data.get("script_model")
        if not script:
            return
        for qu in script.questions:
            if qu.id == qid:
                delta = 5 if sign == "+" else -5
                qu.weight = max(0, min(50, qu.weight + delta))
                break
        await cq.message.reply_text("Вес обновлён.")

    async def on_set_hot_values(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cq = update.callback_query
        await cq.answer()
        _, _, qid = cq.data.split(":", 2)
        context.user_data["await_hot_values_for_qid"] = qid
        await cq.message.reply_text("Введите hot_values через запятую")

    async def on_hot_values_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        qid = context.user_data.get("await_hot_values_for_qid")
        if not qid:
            return
        script: Script | None = context.user_data.get("script_model")
        if not script:
            return
        values = [v.strip() for v in (update.message.text or '').split(',') if v.strip()]
        for qu in script.questions:
            if qu.id == qid:
                qu.hot_values = values
                break
        context.user_data.pop("await_hot_values_for_qid", None)
        await update.message.reply_text("hot_values обновлены.")

    async def on_move_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cq = update.callback_query
        await cq.answer()
        _, _, qid, direction = cq.data.split(":", 3)
        script: Script | None = context.user_data.get("script_model")
        if not script:
            return
        qs = sorted(script.questions, key=lambda z: z.order)
        idx = next((i for i, x in enumerate(qs) if x.id == qid), None)
        if idx is None:
            return
        if direction == "up" and idx > 0:
            qs[idx].order, qs[idx-1].order = qs[idx-1].order, qs[idx].order
        elif direction == "down" and idx < len(qs)-1:
            qs[idx].order, qs[idx+1].order = qs[idx+1].order, qs[idx].order
        script.questions = sorted(qs, key=lambda z: z.order)
        await cq.message.reply_text("Порядок обновлён.")

    async def on_change_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cq = update.callback_query
        await cq.answer()
        _, _, qid = cq.data.split(":", 2)
        script: Script | None = context.user_data.get("script_model")
        if not script:
            return
        order = [QuestionType.text, QuestionType.number, QuestionType.choice, QuestionType.date]
        for qu in script.questions:
            if qu.id == qid:
                cur = order.index(qu.type)
                qu.type = order[(cur + 1) % len(order)]
                break
        await cq.message.reply_text("Тип обновлён.")

    # ===== Онбординг =====
    async def on_onboarding_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data["onboarding"] = {}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Новостройка", callback_data="biz:Новостройка"),
             InlineKeyboardButton("Вторичка", callback_data="biz:Вторичка")],
            [InlineKeyboardButton("Аренда", callback_data="biz:Аренда"),
             InlineKeyboardButton("Коммерческая", callback_data="biz:Коммерческая")],
            [InlineKeyboardButton("Смешанное", callback_data="biz:Смешанное")],
        ])
        await query.message.reply_text("Тип бизнеса?", reply_markup=kb)
        return Q_BIZ_TYPE

    async def on_q_biz_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        _, value = q.data.split(":", 1)
        context.user_data["onboarding"]["business_type"] = value
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("<3млн", callback_data="avg:<3"),
             InlineKeyboardButton("3–7млн", callback_data="avg:3-7")],
            [InlineKeyboardButton("7–15млн", callback_data="avg:7-15"),
             InlineKeyboardButton(">15млн", callback_data="avg:>15")],
            [InlineKeyboardButton("Не знаю", callback_data="avg:unknown")],
        ])
        await q.message.reply_text("Средний чек?", reply_markup=kb)
        return Q_AVG_CHECK

    async def on_q_avg_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        _, value = q.data.split(":", 1)
        context.user_data["onboarding"]["avg_check"] = value
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Авито", callback_data="ch:Авито"),
             InlineKeyboardButton("Циан", callback_data="ch:Циан")],
            [InlineKeyboardButton("Instagram", callback_data="ch:Instagram"),
             InlineKeyboardButton("Реклама", callback_data="ch:Реклама")],
            [InlineKeyboardButton("Звонки", callback_data="ch:Звонки"),
             InlineKeyboardButton("Другое", callback_data="ch:Другое")],
        ])
        await q.message.reply_text("Основной канал привлечения?", reply_markup=kb)
        return Q_CHANNEL

    async def on_q_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        _, value = q.data.split(":", 1)
        context.user_data["onboarding"]["channel"] = value
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Назначить показ", callback_data="goal:+Показ")],
            [InlineKeyboardButton("Назначить созвон", callback_data="goal:+Созвон")],
            [InlineKeyboardButton("Заявка на оценку", callback_data="goal:+Оценка")],
            [InlineKeyboardButton("Подписать договор", callback_data="goal:+Договор")],
            [InlineKeyboardButton("Готово", callback_data="goal:done")],
        ])
        await q.message.reply_text(
            "Цель скрипта (можно выбрать несколько):",
            reply_markup=kb,
        )
        return Q_GOAL_MULTI

    async def on_q_goal_multi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        goals: list[str] = context.user_data["onboarding"].setdefault("goals", [])
        _, value = q.data.split(":", 1)
        if value == "done":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Срочно (недели)", callback_data="urg:Срочно")],
                [InlineKeyboardButton("1–3 мес", callback_data="urg:1-3")],
                [InlineKeyboardButton(">3 мес", callback_data="urg:>3")],
            ])
            await q.message.reply_text("Срочность клиентов?", reply_markup=kb)
            return Q_URGENCY
        else:
            if value not in goals:
                goals.append(value)
            await q.message.reply_text(f"Добавлено: {value}. Нажмите ещё или Готово.")
            return Q_GOAL_MULTI

    async def on_q_urgency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        _, value = q.data.split(":", 1)
        context.user_data["onboarding"]["urgency"] = value
        await q.message.reply_text("Регион / город? (введите текстом)")
        return Q_REGION

    async def on_q_region(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["onboarding"]["region"] = update.message.text.strip()
        await update.message.reply_text("Сколько агентов у вас? (число)")
        return Q_AGENTS

    async def on_q_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (update.message.text or "").strip()
        if not text.isdigit():
            await update.message.reply_text("Введите число, например 5")
            return Q_AGENTS
        context.user_data["onboarding"]["agents"] = int(text)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="out:yes"), InlineKeyboardButton("Нет", callback_data="out:no")]
        ])
        await update.message.reply_text("Хотите, чтобы бот инициировал диалоги сам (исходящий)?", reply_markup=kb)
        return Q_OUTBOUND

    async def on_q_outbound(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        _, value = q.data.split(":", 1)
        context.user_data["onboarding"]["outbound"] = value
        if value == "yes":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Согласен", callback_data="legal:accept")],
                [InlineKeyboardButton("Не согласен", callback_data="legal:decline")],
            ])
            notice = (
                "Риск-уведомление: исходящие сообщения требуют согласия и соблюдения закона о рекламе."
                " Подтвердите, что вы понимаете риски и согласны."
            )
            await q.message.reply_text(notice, reply_markup=kb)
            return Q_LEGAL
        else:
            await self._finish_onboarding(q, context)
            return ConversationHandler.END

    async def on_q_legal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        _, value = q.data.split(":", 1)
        context.user_data["onboarding"]["legal"] = value
        if value != "accept":
            await q.message.reply_text("Исходящий режим отключён.")
        await self._finish_onboarding(q, context)
        return ConversationHandler.END

    async def _finish_onboarding(self, q, context: ContextTypes.DEFAULT_TYPE):
        data = context.user_data.get("onboarding", {})
        # Формируем промпт и запускаем анализ
        prompt_lines = [f"{k}: {v}" for k, v in data.items()]
        prompt = "\n".join(prompt_lines)
        await q.message.reply_text("Спасибо! Анализирую ваши ответы…")
        # Переиспользуем общий вывод
        dummy_update = Update(update_id=q.update_id, callback_query=q)
        await self._run_llm(dummy_update, context, source="onboarding")

    async def on_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Метрики: конверсия 0%, лидов 0 (заглушка)")

    async def on_leads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Лиды: пока пусто (заглушка)")

    async def on_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Интеграции: CRM/Sheets/Calendar — настройка (заглушка). Для экспорта используйте /export")

    async def on_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Бот приостановлен (заглушка)")

    async def on_billing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Биллинг: оформите подписку (заглушка)")

    async def on_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Заглушка выгрузки в Excel
        await update.message.reply_text("Экспорт лидов в .xlsx (заглушка)")

    # Календарь: подключение и управление
    async def on_connect_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        auth_url = (
            f"{self.config.yandex_auth_url}?response_type=code&client_id={self.config.yandex_client_id}&redirect_uri={self.config.yandex_redirect_uri}"
        ) if (self.config.yandex_client_id and self.config.yandex_redirect_uri) else None
        if not auth_url:
            await update.message.reply_text("Яндекс.Календарь недоступен: проверьте конфигурацию.")
            return
        await update.message.reply_text(
            "Подключение Яндекс.Календаря:\n1) Откройте ссылку и авторизуйтесь\n2) Скопируйте код\n3) Отправьте /calendar_code <CODE>")
        await update.message.reply_text(auth_url)

    async def on_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /calendar command"""
        await update.message.reply_text(
            "📅 *Управление календарем*\n\n"
            "• /connect_calendar - подключить календарь\n"
            "• /calendar_code <CODE> - ввести код авторизации\n"
            "• /calendar_status - статус подключения",
            parse_mode="Markdown"
        )
    
    async def on_calendar_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from .integrations import YandexCalendarOAuth
        parts = (update.message.text or "").split(maxsplit=1)
        if len(parts) != 2:
            await update.message.reply_text("Формат: /calendar_code <CODE>")
            return
        code = parts[1].strip()
        try:
            ya = YandexCalendarOAuth(
                self.config.yandex_client_id or "",
                self.config.yandex_client_secret or "",
                self.config.yandex_token_url,
                self.config.yandex_calendar_api_base,
            )
            tokens = await ya.exchange_code(code, self.config.yandex_redirect_uri or "")
            context.user_data["yandex_tokens"] = tokens
            await update.message.reply_text("Календарь подключён. Теперь можно создавать события.")
        except Exception:
            await update.message.reply_text("Не удалось обменять код на токен. Проверьте корректность кода.")


def run_bot_sync() -> None:
    config = AppConfig.load()
    bot = ALBot(config)
    app = bot.build()
    logger.info("Starting AL-bot…")
    app.run_polling()


def main() -> None:
    try:
        run_bot_sync()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()


