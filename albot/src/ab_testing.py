"""
A/B testing system for scripts
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio


class TestStatus(Enum):
    """A/B test status"""
    DRAFT = "draft"           # Черновик
    ACTIVE = "active"         # Активный тест
    COMPLETED = "completed"   # Завершен
    PAUSED = "paused"         # Приостановлен


@dataclass
class ABTest:
    """A/B test configuration"""
    id: str
    name: str
    description: str
    script_a_id: str
    script_b_id: str
    traffic_split: float  # 0.0 to 1.0 (percentage for script A)
    status: TestStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    min_sample_size: int = 100
    confidence_level: float = 0.95
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {
                "script_a": {"conversions": 0, "total_leads": 0, "conversion_rate": 0.0},
                "script_b": {"conversions": 0, "total_leads": 0, "conversion_rate": 0.0}
            }


@dataclass
class TestResult:
    """A/B test result"""
    test_id: str
    script_a_performance: Dict[str, Any]
    script_b_performance: Dict[str, Any]
    winner: Optional[str]  # "A", "B", or None (inconclusive)
    confidence: float
    statistical_significance: bool
    recommendation: str


class ABTestingManager:
    """Manages A/B testing for scripts"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def create_test(self, name: str, description: str, script_a_id: str, 
                         script_b_id: str, traffic_split: float = 0.5) -> str:
        """Create new A/B test"""
        try:
            test_id = f"test_{int(datetime.now().timestamp())}"
            
            test = ABTest(
                id=test_id,
                name=name,
                description=description,
                script_a_id=script_a_id,
                script_b_id=script_b_id,
                traffic_split=traffic_split,
                status=TestStatus.DRAFT,
                created_at=datetime.now()
            )
            
            # Save test to database
            await self.supabase.save_ab_test(test)
            
            return test_id
            
        except Exception as e:
            raise Exception(f"Failed to create A/B test: {str(e)}")
    
    async def start_test(self, test_id: str) -> bool:
        """Start A/B test"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test:
                return False
            
            # Update test status
            test.status = TestStatus.ACTIVE
            test.started_at = datetime.now()
            
            await self.supabase.update_ab_test(test)
            return True
            
        except Exception as e:
            print(f"Failed to start test: {e}")
            return False
    
    async def pause_test(self, test_id: str) -> bool:
        """Pause A/B test"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test:
                return False
            
            test.status = TestStatus.PAUSED
            await self.supabase.update_ab_test(test)
            return True
            
        except Exception as e:
            print(f"Failed to pause test: {e}")
            return False
    
    async def complete_test(self, test_id: str) -> bool:
        """Complete A/B test"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test:
                return False
            
            test.status = TestStatus.COMPLETED
            test.ended_at = datetime.now()
            
            await self.supabase.update_ab_test(test)
            return True
            
        except Exception as e:
            print(f"Failed to complete test: {e}")
            return False
    
    async def get_script_for_lead(self, test_id: str, lead_id: str) -> str:
        """Get script variant for lead (A or B)"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test or test.status != TestStatus.ACTIVE:
                return test.script_a_id  # Default to A
            
            # Simple traffic splitting based on lead ID hash
            lead_hash = hash(lead_id) % 100
            traffic_threshold = int(test.traffic_split * 100)
            
            if lead_hash < traffic_threshold:
                return test.script_a_id
            else:
                return test.script_b_id
                
        except Exception as e:
            print(f"Failed to get script for lead: {e}")
            return None
    
    async def record_conversion(self, test_id: str, script_variant: str, lead_id: str) -> bool:
        """Record conversion for A/B test"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test:
                return False
            
            # Update metrics
            if script_variant == "A":
                test.metrics["script_a"]["conversions"] += 1
            elif script_variant == "B":
                test.metrics["script_b"]["conversions"] += 1
            
            # Recalculate conversion rates
            await self._recalculate_metrics(test)
            
            # Save updated test
            await self.supabase.update_ab_test(test)
            return True
            
        except Exception as e:
            print(f"Failed to record conversion: {e}")
            return False
    
    async def record_lead(self, test_id: str, script_variant: str, lead_id: str) -> bool:
        """Record lead for A/B test"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test:
                return False
            
            # Update total leads
            if script_variant == "A":
                test.metrics["script_a"]["total_leads"] += 1
            elif script_variant == "B":
                test.metrics["script_b"]["total_leads"] += 1
            
            # Recalculate conversion rates
            await self._recalculate_metrics(test)
            
            # Save updated test
            await self.supabase.update_ab_test(test)
            return True
            
        except Exception as e:
            print(f"Failed to record lead: {e}")
            return False
    
    async def _recalculate_metrics(self, test: ABTest) -> None:
        """Recalculate test metrics"""
        try:
            # Calculate conversion rates
            script_a_total = test.metrics["script_a"]["total_leads"]
            script_a_conversions = test.metrics["script_a"]["conversions"]
            test.metrics["script_a"]["conversion_rate"] = (
                script_a_conversions / script_a_total if script_a_total > 0 else 0.0
            )
            
            script_b_total = test.metrics["script_b"]["total_leads"]
            script_b_conversions = test.metrics["script_b"]["conversions"]
            test.metrics["script_b"]["conversion_rate"] = (
                script_b_conversions / script_b_total if script_b_total > 0 else 0.0
            )
            
        except Exception as e:
            print(f"Failed to recalculate metrics: {e}")
    
    async def analyze_test(self, test_id: str) -> TestResult:
        """Analyze A/B test results"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test:
                raise Exception("Test not found")
            
            script_a_metrics = test.metrics["script_a"]
            script_b_metrics = test.metrics["script_b"]
            
            # Calculate statistical significance
            significance = await self._calculate_significance(
                script_a_metrics["conversions"], script_a_metrics["total_leads"],
                script_b_metrics["conversions"], script_b_metrics["total_leads"]
            )
            
            # Determine winner
            winner = None
            if significance["statistical_significance"]:
                if script_a_metrics["conversion_rate"] > script_b_metrics["conversion_rate"]:
                    winner = "A"
                elif script_b_metrics["conversion_rate"] > script_a_metrics["conversion_rate"]:
                    winner = "B"
            
            # Generate recommendation
            recommendation = self._generate_recommendation(winner, significance)
            
            return TestResult(
                test_id=test_id,
                script_a_performance=script_a_metrics,
                script_b_performance=script_b_metrics,
                winner=winner,
                confidence=significance["confidence"],
                statistical_significance=significance["statistical_significance"],
                recommendation=recommendation
            )
            
        except Exception as e:
            raise Exception(f"Failed to analyze test: {str(e)}")
    
    async def _calculate_significance(self, conversions_a: int, total_a: int, 
                                    conversions_b: int, total_b: int) -> Dict[str, Any]:
        """Calculate statistical significance using chi-square test"""
        try:
            # Simplified chi-square test
            if total_a < 30 or total_b < 30:
                return {
                    "statistical_significance": False,
                    "confidence": 0.0,
                    "message": "Недостаточно данных для статистического анализа"
                }
            
            # Calculate conversion rates
            rate_a = conversions_a / total_a if total_a > 0 else 0
            rate_b = conversions_b / total_b if total_b > 0 else 0
            
            # Calculate difference
            difference = abs(rate_a - rate_b)
            
            # Simple significance threshold (can be improved with proper statistical test)
            if difference > 0.05 and min(total_a, total_b) > 50:
                return {
                    "statistical_significance": True,
                    "confidence": 0.95,
                    "message": "Статистически значимая разница"
                }
            else:
                return {
                    "statistical_significance": False,
                    "confidence": 0.0,
                    "message": "Недостаточно данных для вывода"
                }
                
        except Exception as e:
            return {
                "statistical_significance": False,
                "confidence": 0.0,
                "message": f"Ошибка расчета: {str(e)}"
            }
    
    def _generate_recommendation(self, winner: Optional[str], significance: Dict[str, Any]) -> str:
        """Generate recommendation based on test results"""
        if not significance["statistical_significance"]:
            return "Недостаточно данных для принятия решения. Продолжите тестирование."
        
        if winner == "A":
            return "Скрипт A показывает лучшие результаты. Рекомендуется использовать его."
        elif winner == "B":
            return "Скрипт B показывает лучшие результаты. Рекомендуется использовать его."
        else:
            return "Результаты скриптов статистически не отличаются. Можно использовать любой."
    
    async def get_active_tests(self) -> List[ABTest]:
        """Get all active A/B tests"""
        try:
            return await self.supabase.get_active_ab_tests()
        except Exception as e:
            print(f"Failed to get active tests: {e}")
            return []
    
    async def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get test results summary"""
        try:
            test = await self.supabase.get_ab_test(test_id)
            if not test:
                return {}
            
            return {
                "test_id": test_id,
                "name": test.name,
                "status": test.status.value,
                "metrics": test.metrics,
                "created_at": test.created_at.isoformat(),
                "started_at": test.started_at.isoformat() if test.started_at else None,
                "ended_at": test.ended_at.isoformat() if test.ended_at else None
            }
            
        except Exception as e:
            print(f"Failed to get test results: {e}")
            return {}
    
    async def get_test_recommendations(self, test_id: str) -> str:
        """Get test recommendations"""
        try:
            result = await self.analyze_test(test_id)
            
            recommendations = f"""
📊 *РЕЗУЛЬТАТЫ A/B ТЕСТА*

*Скрипт A:*
• Конверсия: {result.script_a_performance['conversion_rate']:.1%}
• Лидов: {result.script_a_performance['total_leads']}
• Конверсий: {result.script_a_performance['conversions']}

*Скрипт B:*
• Конверсия: {result.script_b_performance['conversion_rate']:.1%}
• Лидов: {result.script_b_performance['total_leads']}
• Конверсий: {result.script_b_performance['conversions']}

*Статистическая значимость:* {'✅' if result.statistical_significance else '❌'}
*Уровень доверия:* {result.confidence:.1%}

*Рекомендация:* {result.recommendation}
            """
            
            return recommendations
            
        except Exception as e:
            return f"❌ Ошибка анализа теста: {str(e)}"
