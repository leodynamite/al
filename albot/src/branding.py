"""
Branding and customization management
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel

from .billing import UserSubscription, SubscriptionTier, SubscriptionStatus


class BotBranding(BaseModel):
    """Bot branding configuration"""
    bot_name: str = "AL Bot"
    logo_url: Optional[str] = None
    welcome_message: Optional[str] = None
    custom_colors: Optional[Dict[str, str]] = None


class BrandingManager:
    """Manages bot branding and customization"""
    
    def __init__(self):
        pass
    
    def get_bot_branding(self, subscription: Optional[UserSubscription]) -> BotBranding:
        """Get bot branding based on subscription"""
        if not subscription or subscription.status == SubscriptionStatus.TRIAL or subscription.is_read_only:
            # Trial and read-only: fixed branding
            return BotBranding(
                bot_name="AL Bot",
                logo_url=None,
                welcome_message="Привет! Я AL-бот: на базе ваших данных создам скрипт диалога и рекомендации.",
                custom_colors=None
            )
        else:
            # Paid subscriptions: allow customization
            return BotBranding(
                bot_name=subscription.custom_bot_name or "AL Bot",
                logo_url=subscription.custom_logo_url,
                welcome_message=self._get_custom_welcome_message(subscription),
                custom_colors=self._get_custom_colors(subscription)
            )
    
    def _get_custom_welcome_message(self, subscription: UserSubscription) -> Optional[str]:
        """Get custom welcome message for paid users"""
        if subscription.tier == SubscriptionTier.PRO or subscription.tier == SubscriptionTier.ENTERPRISE:
            # Pro and Enterprise can customize welcome message
            return None  # TODO: Get from database
        return None
    
    def _get_custom_colors(self, subscription: UserSubscription) -> Optional[Dict[str, str]]:
        """Get custom colors for Enterprise users"""
        if subscription.tier == SubscriptionTier.ENTERPRISE:
            # Only Enterprise can customize colors
            return None  # TODO: Get from database
        return None
    
    def can_customize_branding(self, subscription: UserSubscription) -> bool:
        """Check if user can customize branding"""
        if subscription.status == SubscriptionStatus.TRIAL or subscription.is_read_only:
            return False
        
        return subscription.tier in [SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]
    
    def can_customize_name(self, subscription: UserSubscription) -> bool:
        """Check if user can customize bot name"""
        return self.can_customize_branding(subscription)
    
    def can_customize_logo(self, subscription: UserSubscription) -> bool:
        """Check if user can customize logo"""
        return self.can_customize_branding(subscription)
    
    def can_customize_colors(self, subscription: UserSubscription) -> bool:
        """Check if user can customize colors (Enterprise only)"""
        if subscription.status == SubscriptionStatus.TRIAL or subscription.is_read_only:
            return False
        
        return subscription.tier == SubscriptionTier.ENTERPRISE
    
    def get_branding_restrictions(self, subscription: UserSubscription) -> str:
        """Get branding restrictions message"""
        if subscription.status == SubscriptionStatus.TRIAL:
            return "Trial: персонализация недоступна. Оформите подписку Pro или Enterprise."
        elif subscription.is_read_only:
            return "Read-only: персонализация недоступна. Оформите подписку для продолжения."
        elif subscription.tier == SubscriptionTier.BASIC:
            return "Basic: персонализация недоступна. Обновите до Pro или Enterprise."
        else:
            return "Персонализация доступна"

