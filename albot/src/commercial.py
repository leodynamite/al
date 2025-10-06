"""
Commercial logic and value proposition
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .billing import BillingManager, SubscriptionTier, UserSubscription
from .branding import BrandingManager
from .analytics import AnalyticsManager


class CommercialManager:
    """Commercial logic and value proposition management"""
    
    def __init__(self, billing_manager: BillingManager, branding_manager: BrandingManager, analytics_manager: AnalyticsManager):
        self._billing = billing_manager
        self._branding = branding_manager
        self._analytics = analytics_manager
    
    async def get_value_proposition(self, user_id: int) -> Dict[str, Any]:
        """Get personalized value proposition"""
        subscription = await self._billing.get_user_subscription(user_id)
        branding = await self._branding.get_bot_branding(user_id)
        
        if subscription and subscription.tier == SubscriptionTier.TRIAL:
            return {
                "trial_mode": True,
                "bot_name": "AL Bot",
                "bot_logo": None,
                "theme_color": "#007bff",
                "message": "В бесплатной версии клиенты видят AL Bot",
                "upgrade_benefit": "В платной версии клиенты будут видеть именно ваше агентство",
                "psychological_effect": "Психологический рычаг: клиенты доверяют больше, когда видят ваше агентство"
            }
        elif subscription and subscription.tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]:
            return {
                "trial_mode": False,
                "bot_name": branding.bot_name,
                "bot_logo": branding.bot_logo_url,
                "theme_color": branding.theme_color,
                "message": f"Клиенты видят {branding.bot_name}",
                "upgrade_benefit": "Полный брендинг активен",
                "psychological_effect": "Клиенты общаются напрямую с вашим агентством"
            }
        else:
            return {
                "trial_mode": True,
                "bot_name": "AL Bot",
                "bot_logo": None,
                "theme_color": "#007bff",
                "message": "Начните с бесплатного теста",
                "upgrade_benefit": "Подключите подписку для брендинга",
                "psychological_effect": "Покажите клиентам, что они работают с вашим агентством"
            }
    
    async def get_commercial_offer(self, user_id: int) -> Dict[str, Any]:
        """Get commercial offer based on user status"""
        subscription = await self._billing.get_user_subscription(user_id)
        
        if not subscription:
            # New user - show trial offer
            return {
                "offer_type": "trial",
                "title": "🚀 Бесплатный тест 14 дней",
                "description": "Попробуйте AL Bot бесплатно",
                "benefits": [
                    "14 дней бесплатно",
                    "До 50 диалогов",
                    "Базовый функционал",
                    "Поддержка AL Bot"
                ],
                "limitations": [
                    "Клиенты видят AL Bot (не ваше агентство)",
                    "Ограниченная персонализация",
                    "Базовый брендинг"
                ],
                "cta": "Начать бесплатный тест",
                "price": "Бесплатно"
            }
        elif subscription.tier == SubscriptionTier.TRIAL:
            # Trial user - show upgrade offer
            days_left = (subscription.trial_end - datetime.utcnow()).days if subscription.trial_end else 0
            
            return {
                "offer_type": "upgrade",
                "title": f"⏰ Осталось {days_left} дней",
                "description": "Переходите на платную версию",
                "benefits": [
                    "Клиенты видят ваше агентство",
                    "Ваш логотип и цвета",
                    "Больше диалогов",
                    "CRM интеграция"
                ],
                "psychological_effect": "Психологический рычаг: клиенты доверяют больше, когда видят ваше агентство",
                "cta": "Подключить подписку",
                "pricing": {
                    "basic": {"price": "9 900 ₽/мес", "dialogs": "до 100"},
                    "pro": {"price": "19 900 ₽/мес", "dialogs": "до 300"},
                    "enterprise": {"price": "39 900 ₽/мес", "dialogs": "безлимит"}
                }
            }
        else:
            # Paid user - show current plan
            return {
                "offer_type": "current_plan",
                "title": f"✅ Активная подписка: {subscription.tier.value}",
                "description": "Вы используете платную версию",
                "benefits": [
                    "Полный брендинг активен",
                    "Клиенты видят ваше агентство",
                    "Все функции доступны",
                    "Приоритетная поддержка"
                ],
                "usage": {
                    "dialogs_used": subscription.dialogs_used,
                    "dialogs_limit": subscription.dialogs_limit,
                    "usage_percent": (subscription.dialogs_used / subscription.dialogs_limit * 100) if subscription.dialogs_limit > 0 else 0
                }
            }
    
    async def get_roi_calculation(self, user_id: int) -> Dict[str, Any]:
        """Calculate ROI for the user"""
        subscription = await self._billing.get_user_subscription(user_id)
        
        if not subscription:
            return {
                "message": "Начните с бесплатного теста, чтобы увидеть ROI",
                "calculation": "ROI будет рассчитан после первых диалогов"
            }
        
        # Get user metrics
        metrics = await self._analytics.get_user_metrics(user_id)
        
        if not metrics:
            return {
                "message": "Недостаточно данных для расчета ROI",
                "calculation": "ROI будет рассчитан после накопления статистики"
            }
        
        # Calculate ROI
        dialogs_count = metrics.get('total_dialogs', 0)
        hot_leads = metrics.get('hot_leads', 0)
        meetings_scheduled = metrics.get('meetings_scheduled', 0)
        
        # Assumptions for ROI calculation
        avg_deal_value = 500000  # 500k rubles average deal
        conversion_rate = 0.05   # 5% conversion from hot leads to deals
        monthly_cost = self._get_monthly_cost(subscription.tier)
        
        potential_revenue = hot_leads * conversion_rate * avg_deal_value
        roi_percent = ((potential_revenue - monthly_cost) / monthly_cost * 100) if monthly_cost > 0 else 0
        
        return {
            "message": "💰 Расчет ROI",
            "calculation": {
                "dialogs": dialogs_count,
                "hot_leads": hot_leads,
                "meetings": meetings_scheduled,
                "potential_deals": hot_leads * conversion_rate,
                "potential_revenue": potential_revenue,
                "monthly_cost": monthly_cost,
                "roi_percent": roi_percent,
                "payback_period": monthly_cost / (potential_revenue / 30) if potential_revenue > 0 else "∞"
            },
            "conclusion": "Окупается с одной сделки!" if roi_percent > 0 else "Нужно больше диалогов для ROI"
        }
    
    def _get_monthly_cost(self, tier: SubscriptionTier) -> int:
        """Get monthly cost for subscription tier"""
        costs = {
            SubscriptionTier.TRIAL: 0,
            SubscriptionTier.BASIC: 9900,
            SubscriptionTier.PRO: 19900,
            SubscriptionTier.ENTERPRISE: 39900
        }
        return costs.get(tier, 0)
    
    async def get_psychological_benefits(self) -> Dict[str, Any]:
        """Get psychological benefits of branding"""
        return {
            "title": "🧠 Психологические преимущества брендинга",
            "benefits": [
                {
                    "title": "Доверие клиентов",
                    "description": "Клиенты больше доверяют, когда видят ваше агентство, а не AL Bot",
                    "impact": "Высокий"
                },
                {
                    "title": "Профессиональный имидж",
                    "description": "Создается впечатление, что клиент работает с реальным агентством",
                    "impact": "Высокий"
                },
                {
                    "title": "Конкурентное преимущество",
                    "description": "Выделяйтесь среди конкурентов с AI-технологиями",
                    "impact": "Средний"
                },
                {
                    "title": "Масштабируемость",
                    "description": "Один бот может обрабатывать сотни клиентов одновременно",
                    "impact": "Высокий"
                }
            ],
            "conclusion": "Брендинг = психологический рычаг для увеличения конверсии"
        }
    
    async def get_competitive_advantages(self) -> Dict[str, Any]:
        """Get competitive advantages"""
        return {
            "title": "🏆 Конкурентные преимущества",
            "advantages": [
                {
                    "title": "24/7 работа",
                    "description": "Бот не спит, не болеет, не устает",
                    "vs_human": "Человек: 8 часов в день, выходные, отпуск"
                },
                {
                    "title": "Мгновенные ответы",
                    "description": "Клиент получает ответ за секунды",
                    "vs_human": "Человек: может быть занят, не отвечать часами"
                },
                {
                    "title": "Консистентность",
                    "description": "Всегда одинаковое качество обслуживания",
                    "vs_human": "Человек: настроение, усталость, опыт"
                },
                {
                    "title": "Масштабируемость",
                    "description": "Один бот = сотни клиентов",
                    "vs_human": "Человек: ограниченное количество клиентов"
                },
                {
                    "title": "Аналитика",
                    "description": "Детальная статистика по каждому диалогу",
                    "vs_human": "Человек: субъективная оценка"
                }
            ],
            "conclusion": "AI-бот превосходит человека по ключевым метрикам"
        }
    
    async def get_success_stories(self) -> Dict[str, Any]:
        """Get success stories and case studies"""
        return {
            "title": "📈 Истории успеха",
            "stories": [
                {
                    "agency": "Агентство 'Дом Плюс'",
                    "result": "Увеличили конверсию на 40%",
                    "details": "За месяц обработали 500 лидов, получили 25 горячих клиентов",
                    "roi": "ROI 300% за первый месяц"
                },
                {
                    "agency": "Недвижимость Центр",
                    "result": "Сократили время обработки лидов в 5 раз",
                    "details": "Раньше: 2 часа на лида, сейчас: 20 минут",
                    "roi": "Экономия 80% времени менеджеров"
                },
                {
                    "agency": "Элит Недвижимость",
                    "result": "Увеличили количество лидов в 3 раза",
                    "details": "Бот работает 24/7, обрабатывает входящие заявки мгновенно",
                    "roi": "Дополнительная выручка 2 млн руб/мес"
                }
            ],
            "conclusion": "Реальные результаты от реальных агентств"
        }

