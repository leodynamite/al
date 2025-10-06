"""
UX texts and messaging for AL Bot
"""
from typing import Dict, Any
from .branding import BrandingManager
from .billing import BillingManager, SubscriptionTier


class UXTexts:
    """UX texts and messaging system"""
    
    def __init__(self, branding_manager: BrandingManager, billing_manager: BillingManager):
        self._branding = branding_manager
        self._billing = billing_manager
    
    async def get_welcome_message(self, user_id: int) -> str:
        """Get personalized welcome message"""
        subscription = await self._billing.get_user_subscription(user_id)
        branding = self._branding.get_bot_branding(subscription)
        
        if subscription and subscription.tier == SubscriptionTier.TRIAL:
            return f"""Привет! Я {branding.bot_name} — ваш AI-ассистент по лидогенерации.

В бесплатной версии я работаю под своим брендом.
В платной — клиенты будут видеть именно ваше агентство.

Выберите действие:"""
        else:
            return f"""Привет! Я {branding.bot_name} — ваш AI-ассистент по лидогенерации.

Готов помочь с генерацией и квалификацией лидов.
Выберите действие:"""
    
    def get_file_upload_status(self) -> str:
        """File upload status message"""
        return "Файл принят, анализирую…"
    
    def get_analysis_progress(self, eta_seconds: int = 20) -> str:
        """Analysis progress message"""
        return f"Анализирую данные… ETA: ~{eta_seconds} сек"
    
    def get_script_ready_message(self) -> str:
        """Script generation complete message"""
        return """Скрипт готов! 

Хотите:
• Применить — активировать скрипт
• Редактировать — настроить вопросы
• Протестировать — проверить на демо-лидах"""
    
    def get_hot_lead_notification(self, lead_data: Dict[str, Any]) -> str:
        """Hot lead push notification"""
        name = lead_data.get('name', 'Клиент')
        city = lead_data.get('city', 'Город')
        budget = lead_data.get('budget', 'Бюджет')
        
        return f"""🔥 HOT лид: {name}, {city}, бюджет {budget}

Срочно обработать!"""
    
    def get_trial_expired_message(self) -> str:
        """Trial expired message"""
        return """❌ Пробный период закончился

Для продолжения работы подключите подписку:
• Basic: 9 900 ₽/мес (до 100 диалогов)
• Pro: 19 900 ₽/мес (до 300 диалогов) 
• Enterprise: 39 900 ₽/мес (безлимит)

Окупается с одной сделки! 💰"""
    
    def get_read_only_mode_message(self) -> str:
        """Read-only mode message"""
        return """📖 Режим просмотра

История доступна, но новые лиды не принимаются.
Подключите подписку для продолжения работы."""
    
    def get_subscription_benefits(self, tier: SubscriptionTier) -> str:
        """Subscription benefits message"""
        benefits = {
            SubscriptionTier.BASIC: """✅ Basic (9 900 ₽/мес):
• До 100 диалогов в месяц
• Базовый брендинг
• Email поддержка""",
            
            SubscriptionTier.PRO: """✅ Pro (19 900 ₽/мес):
• До 300 диалогов в месяц
• Полный брендинг агентства
• CRM интеграция
• Приоритетная поддержка""",
            
            SubscriptionTier.ENTERPRISE: """✅ Enterprise (39 900 ₽/мес):
• Безлимитные диалоги
• Кастомный бот
• Персональный менеджер
• API доступ"""
        }
        
        return benefits.get(tier, "Информация о подписке недоступна")
    
    def get_commercial_offer(self) -> str:
        """Commercial offer message"""
        return """💼 Коммерческое предложение

🎯 AL Bot = ваш виртуальный менеджер, который работает 24/7

✨ Преимущества:
• Автоматическая квалификация лидов
• Работает круглосуточно
• Не устает и не болеет
• Масштабируется без ограничений

💰 Окупается с одной сделки → от 9 900 ₽/мес

🚀 Бесплатный тест 14 дней — но только в подписке клиенты видят именно ваше агентство."""
    
    def get_branding_explanation(self) -> str:
        """Branding explanation message"""
        return """🎨 Брендинг агентства

В бесплатной версии:
• Клиенты видят "AL Bot"
• Стандартный дизайн
• Ограниченная персонализация

В платной версии:
• Клиенты видят ваше агентство
• Ваш логотип и цвета
• Полная персонализация
• Психологический эффект доверия"""
    
    def get_success_metrics(self, metrics: Dict[str, Any]) -> str:
        """Success metrics message"""
        dialogs_today = metrics.get('dialogs_today', 0)
        hot_leads = metrics.get('hot_leads', 0)
        meetings_scheduled = metrics.get('meetings_scheduled', 0)
        conversion_rate = metrics.get('conversion_rate', 0)
        
        return f"""📊 Ваша статистика:

• Диалогов сегодня: {dialogs_today}
• Горячих лидов: {hot_leads}
• Встреч назначено: {meetings_scheduled}
• Конверсия: {conversion_rate:.1f}%

Отличная работа! 🚀"""
    
    def get_error_message(self, error_type: str) -> str:
        """Error message"""
        error_messages = {
            'file_format': "❌ Неподдерживаемый формат файла. Поддерживаются: .csv, .xlsx, .pdf, .docx, .txt",
            'file_empty': "❌ Файл пустой. Загрузите файл с данными клиентов.",
            'file_too_large': "❌ Файл слишком большой. Максимальный размер: 10 МБ",
            'llm_error': "❌ Ошибка анализа. Попробуйте еще раз или обратитесь в поддержку.",
            'subscription_error': "❌ Ошибка подписки. Обратитесь в поддержку.",
            'network_error': "❌ Ошибка сети. Проверьте подключение к интернету."
        }
        
        return error_messages.get(error_type, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    def get_help_message(self) -> str:
        """Help message"""
        return """🆘 Помощь

📋 Доступные команды:
• /start — главное меню
• /metrics — статистика
• /leads — просмотр лидов
• /settings — настройки
• /billing — подписка
• /help — эта справка

💬 Поддержка: @albot_support
📧 Email: support@albot.ru"""
    
    def get_onboarding_question(self, question_num: int, total: int) -> str:
        """Onboarding question message"""
        questions = [
            "1️⃣ Какой тип недвижимости?",
            "2️⃣ Средний чек ваших сделок?",
            "3️⃣ Основной канал привлечения?",
            "4️⃣ Цель скрипта?",
            "5️⃣ Срочность клиентов?",
            "6️⃣ Регион работы?",
            "7️⃣ Количество агентов?",
            "8️⃣ Исходящие диалоги?"
        ]
        
        if question_num <= len(questions):
            return f"{questions[question_num-1]} ({question_num}/{total})"
        return f"Вопрос {question_num} из {total}"
    
    def get_legal_notice(self) -> str:
        """Legal notice for outbound bot"""
        return """⚠️ Правовое уведомление

Исходящие диалоги могут регулироваться законом о рекламе и защите персональных данных.

✅ Я согласен с условиями использования
❌ Отказаться от исходящих диалогов

Агентство несет ответственность за соблюдение законодательства."""

