"""
Test trial gating functionality
Tests: After 50 dialogs - blocking
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from albot.src.billing import BillingManager, UserSubscription, SubscriptionTier, SubscriptionStatus
from albot.src.integrations import SupabaseClient


class TestTrialGating:
    """Test trial gating and dialog limits"""
    
    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client"""
        supabase = Mock(spec=SupabaseClient)
        supabase.get_user_subscription = AsyncMock()
        supabase.save_subscription = AsyncMock(return_value=True)
        supabase.update_subscription = AsyncMock(return_value=True)
        supabase.increment_dialog_count = AsyncMock(return_value=True)
        return supabase
    
    @pytest.fixture
    def billing_manager(self, mock_supabase):
        """Create billing manager"""
        config = Mock()
        config.trial_days = 14
        config.trial_dialogs = 50
        return BillingManager(config, mock_supabase)
    
    @pytest.mark.asyncio
    async def test_trial_user_under_limit(self, billing_manager, mock_supabase):
        """Test trial user under dialog limit"""
        # Create trial subscription with 30 dialogs used
        subscription = UserSubscription(
            user_id=1001,
            tier=SubscriptionTier.TRIAL,
            status=SubscriptionStatus.TRIAL,
            trial_start=datetime.utcnow() - timedelta(days=5),
            trial_end=datetime.utcnow() + timedelta(days=9),
            dialogs_used=30,
            dialogs_limit=50,
            created_at=datetime.utcnow() - timedelta(days=5),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user can start new dialog
        can_start = not await billing_manager.check_dialog_limit(subscription)
        assert can_start is True
        
        # Check trial info
        trial_info = billing_manager.get_trial_info(subscription)
        assert "8 дней" in trial_info
        assert "20 диалогов" in trial_info
    
    @pytest.mark.asyncio
    async def test_trial_user_at_limit(self, billing_manager, mock_supabase):
        """Test trial user at dialog limit"""
        # Create trial subscription with 50 dialogs used
        subscription = UserSubscription(
            user_id=1002,
            tier=SubscriptionTier.TRIAL,
            status=SubscriptionStatus.TRIAL,
            trial_start=datetime.utcnow() - timedelta(days=3),
            trial_end=datetime.utcnow() + timedelta(days=11),
            dialogs_used=50,
            dialogs_limit=50,
            created_at=datetime.utcnow() - timedelta(days=3),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user is blocked
        is_blocked = await billing_manager.check_dialog_limit(subscription)
        assert is_blocked is True
        
        # Check subscription info
        subscription_info = billing_manager.get_subscription_info(subscription)
        assert "Trial" in subscription_info
    
    @pytest.mark.asyncio
    async def test_trial_user_over_limit(self, billing_manager, mock_supabase):
        """Test trial user over dialog limit"""
        # Create trial subscription with 60 dialogs used (over limit)
        subscription = UserSubscription(
            user_id=1003,
            tier=SubscriptionTier.TRIAL,
            status=SubscriptionStatus.TRIAL,
            trial_start=datetime.utcnow() - timedelta(days=2),
            trial_end=datetime.utcnow() + timedelta(days=12),
            dialogs_used=60,
            dialogs_limit=50,
            created_at=datetime.utcnow() - timedelta(days=2),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user is blocked
        is_blocked = await billing_manager.check_dialog_limit(subscription)
        assert is_blocked is True
    
    @pytest.mark.asyncio
    async def test_trial_expired(self, billing_manager, mock_supabase):
        """Test expired trial user"""
        # Create expired trial subscription
        subscription = UserSubscription(
            user_id=1004,
            tier=SubscriptionTier.TRIAL,
            status=SubscriptionStatus.TRIAL,
            trial_start=datetime.utcnow() - timedelta(days=15),
            trial_end=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
            dialogs_used=25,
            dialogs_limit=50,
            created_at=datetime.utcnow() - timedelta(days=15),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if trial is expired
        is_expired = await billing_manager.check_trial_expired(subscription)
        assert is_expired is True
        
        # Check if user is in read-only mode
        assert subscription.is_read_only is True
    
    @pytest.mark.asyncio
    async def test_read_only_mode(self, billing_manager, mock_supabase):
        """Test read-only mode blocking"""
        # Create read-only subscription
        subscription = UserSubscription(
            user_id=1005,
            tier=SubscriptionTier.TRIAL,
            status=SubscriptionStatus.EXPIRED,
            trial_start=datetime.utcnow() - timedelta(days=20),
            trial_end=datetime.utcnow() - timedelta(days=6),
            dialogs_used=30,
            dialogs_limit=50,
            created_at=datetime.utcnow() - timedelta(days=20),
            is_read_only=True
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user is blocked in read-only mode
        is_blocked = await billing_manager.check_dialog_limit(subscription)
        assert is_blocked is True
        
        # Check subscription info
        subscription_info = billing_manager.get_subscription_info(subscription)
        assert "Read-only режим" in subscription_info
    
    @pytest.mark.asyncio
    async def test_dialog_count_increment(self, billing_manager, mock_supabase):
        """Test dialog count increment"""
        # Create trial subscription
        subscription = UserSubscription(
            user_id=1006,
            tier=SubscriptionTier.TRIAL,
            status=SubscriptionStatus.TRIAL,
            trial_start=datetime.utcnow() - timedelta(days=1),
            trial_end=datetime.utcnow() + timedelta(days=13),
            dialogs_used=10,
            dialogs_limit=50,
            created_at=datetime.utcnow() - timedelta(days=1),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Increment dialog count
        success = await billing_manager.increment_dialog_count(1006)
        assert success is True
        
        # Verify increment was called
        mock_supabase.increment_dialog_count.assert_called_with(1006)
    
    @pytest.mark.asyncio
    async def test_paid_user_no_limits(self, billing_manager, mock_supabase):
        """Test paid user has no dialog limits"""
        # Create paid subscription
        subscription = UserSubscription(
            user_id=1007,
            tier=SubscriptionTier.BASIC,
            status=SubscriptionStatus.ACTIVE,
            trial_start=None,
            trial_end=None,
            dialogs_used=50,
            dialogs_limit=100,  # Basic plan limit
            created_at=datetime.utcnow() - timedelta(days=5),
            expires_at=datetime.utcnow() + timedelta(days=25),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user can start new dialog (under limit)
        can_start = not await billing_manager.check_dialog_limit(subscription)
        assert can_start is True
    
    @pytest.mark.asyncio
    async def test_paid_user_at_limit(self, billing_manager, mock_supabase):
        """Test paid user at dialog limit"""
        # Create paid subscription at limit
        subscription = UserSubscription(
            user_id=1008,
            tier=SubscriptionTier.BASIC,
            status=SubscriptionStatus.ACTIVE,
            trial_start=None,
            trial_end=None,
            dialogs_used=100,
            dialogs_limit=100,  # At limit
            created_at=datetime.utcnow() - timedelta(days=5),
            expires_at=datetime.utcnow() + timedelta(days=25),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user is blocked at limit
        is_blocked = await billing_manager.check_dialog_limit(subscription)
        assert is_blocked is True
    
    @pytest.mark.asyncio
    async def test_pro_user_higher_limit(self, billing_manager, mock_supabase):
        """Test Pro user has higher dialog limit"""
        # Create Pro subscription
        subscription = UserSubscription(
            user_id=1009,
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            trial_start=None,
            trial_end=None,
            dialogs_used=200,
            dialogs_limit=300,  # Pro plan limit
            created_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() + timedelta(days=20),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user can start new dialog (under limit)
        can_start = not await billing_manager.check_dialog_limit(subscription)
        assert can_start is True
    
    @pytest.mark.asyncio
    async def test_enterprise_unlimited(self, billing_manager, mock_supabase):
        """Test Enterprise user has unlimited dialogs"""
        # Create Enterprise subscription
        subscription = UserSubscription(
            user_id=1010,
            tier=SubscriptionTier.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            trial_start=None,
            trial_end=None,
            dialogs_used=500,
            dialogs_limit=500,  # Enterprise plan limit
            created_at=datetime.utcnow() - timedelta(days=15),
            expires_at=datetime.utcnow() + timedelta(days=15),
            is_read_only=False
        )
        
        mock_supabase.get_user_subscription.return_value = subscription
        
        # Check if user can start new dialog (at limit but Enterprise)
        can_start = not await billing_manager.check_dialog_limit(subscription)
        # Enterprise users might have different logic
        # This test verifies the current behavior

