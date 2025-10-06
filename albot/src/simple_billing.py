"""
Simplified billing system - manual subscription activation
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

from .integrations import SupabaseClient


class SubscriptionTier(str, Enum):
    """Subscription tiers"""
    TRIAL = "trial"
    BASIC = "basic"      # 9,900 ₽ - 50-100 диалогов
    PRO = "pro"          # 19,900 ₽ - до 300 диалогов
    ENTERPRISE = "enterprise"  # 39,900 ₽ - 500+ диалогов


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"  # Ожидает активации


class UserSubscription(BaseModel):
    """User subscription model"""
    user_id: int
    tier: SubscriptionTier
    status: SubscriptionStatus
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    dialogs_used: int = 0
    dialogs_limit: int = 50  # trial limit
    created_at: datetime
    expires_at: Optional[datetime] = None
    # Branding restrictions
    custom_bot_name: Optional[str] = None
    custom_logo_url: Optional[str] = None
    # Read-only mode
    is_read_only: bool = False


class SimpleBillingManager:
    """Simplified billing manager - manual subscription activation"""
    
    def __init__(self, supabase_client, notification_manager=None):
        self.supabase = supabase_client
        self.notification_manager = notification_manager
        
        # Subscription limits
        self.tier_limits = {
            SubscriptionTier.TRIAL: 50,
            SubscriptionTier.BASIC: 100,
            SubscriptionTier.PRO: 300,
            SubscriptionTier.ENTERPRISE: 1000
        }
        
        # Subscription prices
        self.tier_prices = {
            SubscriptionTier.BASIC: 9900,
            SubscriptionTier.PRO: 19900,
            SubscriptionTier.ENTERPRISE: 39900
        }
    
    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Get user subscription"""
        try:
            subscription_data = await self.supabase.get_user_subscription(user_id)
            if not subscription_data:
                return None
            
            return UserSubscription(
                user_id=user_id,
                tier=SubscriptionTier(subscription_data['tier']),
                status=SubscriptionStatus(subscription_data['status']),
                trial_start=subscription_data.get('trial_start'),
                trial_end=subscription_data.get('trial_end'),
                dialogs_used=subscription_data.get('dialogs_used', 0),
                dialogs_limit=subscription_data.get('dialogs_limit', 50),
                created_at=subscription_data['created_at'],
                expires_at=subscription_data.get('expires_at'),
                custom_bot_name=subscription_data.get('custom_bot_name'),
                custom_logo_url=subscription_data.get('custom_logo_url'),
                is_read_only=subscription_data.get('is_read_only', False)
            )
        except Exception as e:
            print(f"Failed to get subscription: {e}")
            return None
    
    async def create_trial_subscription(self, user_id: int) -> UserSubscription:
        """Create trial subscription for new user"""
        try:
            now = datetime.now()
            trial_end = now + timedelta(days=14)
            
            subscription = UserSubscription(
                user_id=user_id,
                tier=SubscriptionTier.TRIAL,
                status=SubscriptionStatus.TRIAL,
                trial_start=now,
                trial_end=trial_end,
                dialogs_used=0,
                dialogs_limit=50,
                created_at=now,
                expires_at=trial_end,
                is_read_only=False
            )
            
            await self.supabase.save_user_subscription(subscription)
            return subscription
            
        except Exception as e:
            raise Exception(f"Failed to create trial subscription: {str(e)}")
    
    async def request_subscription(self, user_id: int, tier: SubscriptionTier, 
                                 user_data: Dict[str, Any]) -> bool:
        """Request subscription (manual activation)"""
        try:
            # Create pending subscription
            subscription = UserSubscription(
                user_id=user_id,
                tier=tier,
                status=SubscriptionStatus.PENDING,
                dialogs_used=0,
                dialogs_limit=self.tier_limits[tier],
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=30),
                is_read_only=False
            )
            
            await self.supabase.save_user_subscription(subscription)
            
            # Send notification to admin
            if self.notification_manager:
                await self.notification_manager.notify_subscription(user_data, tier.value)
            
            return True
            
        except Exception as e:
            print(f"Failed to request subscription: {e}")
            return False
    
    async def activate_subscription(self, user_id: int, tier: SubscriptionTier) -> bool:
        """Activate subscription (manual)"""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return False
            
            # Update subscription
            subscription.tier = tier
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.dialogs_limit = self.tier_limits[tier]
            subscription.expires_at = datetime.now() + timedelta(days=30)
            subscription.is_read_only = False
            
            await self.supabase.update_user_subscription(subscription)
            return True
            
        except Exception as e:
            print(f"Failed to activate subscription: {e}")
            return False
    
    async def check_dialog_limit(self, user_id: int) -> bool:
        """Check if user has reached dialog limit"""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return True  # No subscription = limit reached
            
            return subscription.dialogs_used >= subscription.dialogs_limit
            
        except Exception as e:
            print(f"Failed to check dialog limit: {e}")
            return True
    
    async def increment_dialog_count(self, user_id: int) -> bool:
        """Increment dialog count for user"""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return False
            
            subscription.dialogs_used += 1
            await self.supabase.update_user_subscription(subscription)
            return True
            
        except Exception as e:
            print(f"Failed to increment dialog count: {e}")
            return False
    
    async def get_subscription_info(self, subscription: UserSubscription) -> str:
        """Get subscription info text"""
        try:
            if subscription.status == SubscriptionStatus.TRIAL:
                days_left = (subscription.trial_end - datetime.now()).days if subscription.trial_end else 0
                return f"Trial: {days_left} дней, {subscription.dialogs_used}/{subscription.dialogs_limit} диалогов"
            elif subscription.status == SubscriptionStatus.ACTIVE:
                return f"{subscription.tier.value.upper()}: {subscription.dialogs_used}/{subscription.dialogs_limit} диалогов"
            elif subscription.status == SubscriptionStatus.PENDING:
                return f"Ожидает активации: {subscription.tier.value.upper()}"
            else:
                return "Подписка неактивна"
                
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    async def get_billing_info(self, user_id: int) -> str:
        """Get billing information for user"""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return "Подписка не найдена"
            
            info = f"""
💳 *ИНФОРМАЦИЯ О ПОДПИСКЕ*

*Текущий тариф:* {subscription.tier.value.upper()}
*Статус:* {subscription.status.value.upper()}
*Использовано диалогов:* {subscription.dialogs_used}/{subscription.dialogs_limit}

*Доступные тарифы:*
• BASIC: 9,900 ₽/мес (до 100 диалогов)
• PRO: 19,900 ₽/мес (до 300 диалогов)
• ENTERPRISE: 39,900 ₽/мес (до 1000 диалогов)

*Для активации подписки:*
1. Выберите тариф
2. Получите реквизиты для оплаты
3. Ожидайте активации (до 24 часов)
            """
            
            return info
            
        except Exception as e:
            return f"❌ Ошибка получения информации: {str(e)}"
    
    async def get_payment_info(self, tier: SubscriptionTier) -> str:
        """Get payment information for tier"""
        try:
            price = self.tier_prices.get(tier, 0)
            
            payment_info = f"""
💳 *ОПЛАТА ПОДПИСКИ*

*Тариф:* {tier.value.upper()}
*Стоимость:* {price:,} ₽/мес
*Лимит диалогов:* {self.tier_limits[tier]}

*Реквизиты для оплаты:*
• Сбербанк: 4081 7812 3456 7890
• Тинькофф: 4081 7812 3456 7891
• Яндекс.Деньги: 4100 1234 5678 9012

*В комментарии к переводу укажите:*
"AL Bot {tier.value.upper()}"

*После оплаты:*
1. Отправьте скриншот перевода
2. Ожидайте активации (до 24 часов)
3. Получите уведомление об активации

*Поддержка:* @albot_support
            """
            
            return payment_info
            
        except Exception as e:
            return f"❌ Ошибка получения реквизитов: {str(e)}"
    
    async def check_trial_expired(self, user_id: int) -> bool:
        """Check if trial has expired"""
        try:
            subscription = await self.get_user_subscription(user_id)
            if not subscription or subscription.status != SubscriptionStatus.TRIAL:
                return False
            
            if subscription.trial_end and datetime.now() > subscription.trial_end:
                # Mark as expired and read-only
                subscription.status = SubscriptionStatus.EXPIRED
                subscription.is_read_only = True
                await self.supabase.update_user_subscription(subscription)
                return True
            
            return False
            
        except Exception as e:
            print(f"Failed to check trial expiration: {e}")
            return False
