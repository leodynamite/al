"""
Billing and subscription management
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import httpx
from pydantic import BaseModel

from .config import AppConfig
from .integrations import SupabaseClient


class SubscriptionTier(str, Enum):
    """Subscription tiers"""
    TRIAL = "trial"
    BASIC = "basic"  # 9,900 ₽ - 50-100 диалогов
    PRO = "pro"  # 19,900 ₽ - до 300 диалогов
    ENTERPRISE = "enterprise"  # 39,900 ₽ - 500+ диалогов


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


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


class BillingManager:
    """Handles billing and subscription logic"""
    
    def __init__(self, config: AppConfig, supabase: SupabaseClient):
        self.config = config
        self.supabase = supabase
        self.yo_money_shop_id = config.yo_money_shop_id
        self.yo_money_secret = config.yo_money_secret
    
    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Get user subscription from database"""
        try:
            result = await self.supabase.get_user_subscription(user_id)
            if result:
                return UserSubscription(**result)
            return None
        except Exception as e:
            print(f"Error getting subscription for user {user_id}: {e}")
            return None
    
    async def create_trial_subscription(self, user_id: int) -> UserSubscription:
        """Create trial subscription for new user"""
        now = datetime.utcnow()
        trial_end = now + timedelta(days=self.config.trial_days)
        
        subscription = UserSubscription(
            user_id=user_id,
            tier=SubscriptionTier.TRIAL,
            status=SubscriptionStatus.TRIAL,
            trial_start=now,
            trial_end=trial_end,
            dialogs_used=0,
            dialogs_limit=self.config.trial_dialogs,
            created_at=now
        )
        
        await self.supabase.save_subscription(subscription.dict())
        return subscription
    
    async def check_trial_expired(self, subscription: UserSubscription) -> bool:
        """Check if trial has expired and enable read-only mode"""
        if subscription.status != SubscriptionStatus.TRIAL:
            return False
        
        if subscription.trial_end and datetime.utcnow() > subscription.trial_end:
            # Mark as expired and enable read-only mode
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.is_read_only = True
            await self.supabase.update_subscription(subscription.user_id, {
                "status": SubscriptionStatus.EXPIRED.value,
                "is_read_only": True
            })
            return True
        
        return False
    
    async def check_dialog_limit(self, subscription: UserSubscription) -> bool:
        """Check if user has exceeded dialog limit"""
        if subscription.is_read_only:
            return True  # Read-only mode blocks new dialogs
        
        if subscription.status == SubscriptionStatus.TRIAL:
            return subscription.dialogs_used >= subscription.dialogs_limit
        
        # For paid subscriptions, check if limit exceeded
        if subscription.dialogs_limit > 0:
            return subscription.dialogs_used >= subscription.dialogs_limit
        
        return False
    
    async def increment_dialog_count(self, user_id: int) -> bool:
        """Increment dialog count for user"""
        try:
            await self.supabase.increment_dialog_count(user_id)
            return True
        except Exception as e:
            print(f"Error incrementing dialog count: {e}")
            return False
    
    async def create_payment_link(self, user_id: int, tier: SubscriptionTier, provider: str = "yoomoney") -> Optional[str]:
        """Create payment link for subscription"""
        if tier == SubscriptionTier.TRIAL:
            return None
        
        prices = {
            SubscriptionTier.BASIC: 9900,
            SubscriptionTier.PRO: 19900,
            SubscriptionTier.ENTERPRISE: 39900
        }
        
        amount = prices.get(tier, 9900)
        
        if provider == "yoomoney":
            return await self._create_yoomoney_payment(user_id, tier, amount)
        elif provider == "tinkoff":
            return await self._create_tinkoff_payment(user_id, tier, amount)
        elif provider == "cloudpayments":
            return await self._create_cloudpayments_payment(user_id, tier, amount)
        
        return None
    
    async def _create_yoomoney_payment(self, user_id: int, tier: SubscriptionTier, amount: int) -> Optional[str]:
        """Create YooMoney payment link"""
        if not self.yo_money_shop_id or not self.yo_money_secret:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://yoomoney.ru/api/request-payment",
                    data={
                        "pattern_id": "p2p",
                        "to": self.yo_money_shop_id,
                        "amount": amount,
                        "comment": f"AL Bot subscription - {tier.value}",
                        "label": f"user_{user_id}_tier_{tier.value}"
                    },
                    auth=(self.yo_money_shop_id, self.yo_money_secret)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("payment_url")
                
        except Exception as e:
            print(f"Error creating YooMoney payment: {e}")
        
        return None
    
    async def _create_tinkoff_payment(self, user_id: int, tier: SubscriptionTier, amount: int) -> Optional[str]:
        """Create Tinkoff payment link"""
        # TODO: Implement Tinkoff payment integration
        return None
    
    async def _create_cloudpayments_payment(self, user_id: int, tier: SubscriptionTier, amount: int) -> Optional[str]:
        """Create CloudPayments payment link"""
        # TODO: Implement CloudPayments integration
        return None
    
    async def activate_subscription(self, user_id: int, tier: SubscriptionTier) -> bool:
        """Activate paid subscription"""
        try:
            now = datetime.utcnow()
            expires_at = now + timedelta(days=30)  # Monthly subscription
            
            # Set dialog limits based on tier
            dialog_limits = {
                SubscriptionTier.BASIC: 100,  # 50-100 диалогов
                SubscriptionTier.PRO: 300,   # до 300 диалогов
                SubscriptionTier.ENTERPRISE: 500  # 500+ диалогов
            }
            
            subscription_data = {
                "user_id": user_id,
                "tier": tier.value,
                "status": SubscriptionStatus.ACTIVE.value,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "dialogs_used": 0,
                "dialogs_limit": dialog_limits.get(tier, 100),
                "is_read_only": False
            }
            
            await self.supabase.save_subscription(subscription_data)
            return True
            
        except Exception as e:
            print(f"Error activating subscription: {e}")
            return False
    
    async def cancel_subscription(self, user_id: int) -> bool:
        """Cancel user subscription"""
        try:
            await self.supabase.update_subscription(user_id, {
                "status": SubscriptionStatus.CANCELLED.value
            })
            return True
        except Exception as e:
            print(f"Error cancelling subscription: {e}")
            return False
    
    def get_trial_info(self, subscription: UserSubscription) -> str:
        """Get trial information for user"""
        if subscription.status != SubscriptionStatus.TRIAL:
            return "Trial не активен"
        
        days_left = (subscription.trial_end - datetime.utcnow()).days
        dialogs_left = subscription.dialogs_limit - subscription.dialogs_used
        
        return f"Trial: {days_left} дней, {dialogs_left} диалогов"
    
    def get_subscription_info(self, subscription: UserSubscription) -> str:
        """Get subscription information"""
        if subscription.is_read_only:
            return "🔒 Read-only режим. Доступна только история. Оформите подписку для продолжения работы."
        elif subscription.status == SubscriptionStatus.TRIAL:
            return self.get_trial_info(subscription)
        elif subscription.status == SubscriptionStatus.ACTIVE:
            return f"Подписка {subscription.tier.value} активна"
        elif subscription.status == SubscriptionStatus.EXPIRED:
            return "Подписка истекла. Обновите для продолжения работы"
        else:
            return "Подписка не активна"
    
    def get_bot_name(self, subscription: UserSubscription) -> str:
        """Get bot name based on subscription"""
        if subscription.status == SubscriptionStatus.TRIAL or subscription.is_read_only:
            return "AL Bot"  # Fixed name for trial/read-only
        else:
            return subscription.custom_bot_name or "AL Bot"
    
    def get_bot_logo(self, subscription: UserSubscription) -> Optional[str]:
        """Get bot logo based on subscription"""
        if subscription.status == SubscriptionStatus.TRIAL or subscription.is_read_only:
            return None  # No custom logo for trial/read-only
        else:
            return subscription.custom_logo_url
