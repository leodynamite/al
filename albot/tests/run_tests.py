#!/usr/bin/env python3
"""
Test runner for AL Bot acceptance tests
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_file_parsing import TestFileParsing
from tests.test_llm_integration import TestLLMIntegration
from tests.test_ux_flow import TestUXFlow
from tests.test_trial_gating import TestTrialGating
from tests.test_load_performance import TestLoadPerformance


class TestRunner:
    """Run all acceptance tests"""
    
    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    async def run_file_parsing_tests(self):
        """Run file parsing tests (10 tests)"""
        print("🧪 Running file parsing tests...")
        
        test_class = TestFileParsing()
        tests = [
            test_class.test_csv_parsing,
            test_class.test_xlsx_parsing,
            test_class.test_pdf_parsing,
            test_class.test_docx_parsing,
            test_class.test_empty_file,
            test_class.test_invalid_file_format,
            test_class.test_large_csv_file,
            test_class.test_csv_with_special_characters,
            test_class.test_xlsx_multiple_sheets,
            test_class.test_pdf_with_tables
        ]
        
        for test in tests:
            try:
                await test()
                self.passed_tests += 1
                print(f"  ✅ {test.__name__}")
            except Exception as e:
                self.failed_tests += 1
                print(f"  ❌ {test.__name__}: {e}")
            
            self.total_tests += 1
        
        self.results["file_parsing"] = {
            "total": 10,
            "passed": self.passed_tests,
            "failed": self.failed_tests
        }
    
    async def run_llm_integration_tests(self):
        """Run LLM integration tests (10 tests)"""
        print("🤖 Running LLM integration tests...")
        
        test_class = TestLLMIntegration()
        tests = [
            test_class.test_csv_analysis,
            test_class.test_xlsx_analysis,
            test_class.test_pdf_analysis,
            test_class.test_docx_analysis,
            test_class.test_empty_file_analysis,
            test_class.test_large_file_analysis,
            test_class.test_special_characters_analysis,
            test_class.test_mixed_language_analysis,
            test_class.test_structured_data_analysis,
            test_class.test_script_generation_consistency
        ]
        
        for test in tests:
            try:
                await test()
                self.passed_tests += 1
                print(f"  ✅ {test.__name__}")
            except Exception as e:
                self.failed_tests += 1
                print(f"  ❌ {test.__name__}: {e}")
            
            self.total_tests += 1
        
        self.results["llm_integration"] = {
            "total": 10,
            "passed": self.passed_tests - sum(r["passed"] for r in self.results.values()),
            "failed": self.failed_tests - sum(r["failed"] for r in self.results.values())
        }
    
    async def run_ux_flow_tests(self):
        """Run UX flow tests (5 agents)"""
        print("👥 Running UX flow tests (5 agents)...")
        
        test_class = TestUXFlow()
        tests = [
            test_class.test_agent_1_complete_flow,
            test_class.test_agent_2_xlsx_upload,
            test_class.test_agent_3_pdf_upload,
            test_class.test_agent_4_docx_upload,
            test_class.test_agent_5_error_handling
        ]
        
        for test in tests:
            try:
                await test()
                self.passed_tests += 1
                print(f"  ✅ {test.__name__}")
            except Exception as e:
                self.failed_tests += 1
                print(f"  ❌ {test.__name__}: {e}")
            
            self.total_tests += 1
        
        self.results["ux_flow"] = {
            "total": 5,
            "passed": self.passed_tests - sum(r["passed"] for r in self.results.values()),
            "failed": self.failed_tests - sum(r["failed"] for r in self.results.values())
        }
    
    async def run_trial_gating_tests(self):
        """Run trial gating tests"""
        print("🔒 Running trial gating tests...")
        
        test_class = TestTrialGating()
        tests = [
            test_class.test_trial_user_under_limit,
            test_class.test_trial_user_at_limit,
            test_class.test_trial_user_over_limit,
            test_class.test_trial_expired,
            test_class.test_read_only_mode,
            test_class.test_dialog_count_increment,
            test_class.test_paid_user_no_limits,
            test_class.test_paid_user_at_limit,
            test_class.test_pro_user_higher_limit,
            test_class.test_enterprise_unlimited
        ]
        
        for test in tests:
            try:
                await test()
                self.passed_tests += 1
                print(f"  ✅ {test.__name__}")
            except Exception as e:
                self.failed_tests += 1
                print(f"  ❌ {test.__name__}: {e}")
            
            self.total_tests += 1
        
        self.results["trial_gating"] = {
            "total": 10,
            "passed": self.passed_tests - sum(r["passed"] for r in self.results.values()),
            "failed": self.failed_tests - sum(r["failed"] for r in self.results.values())
        }
    
    async def run_load_performance_tests(self):
        """Run load performance tests"""
        print("⚡ Running load performance tests...")
        
        test_class = TestLoadPerformance()
        tests = [
            test_class.test_concurrent_start_commands,
            test_class.test_concurrent_file_uploads,
            test_class.test_mixed_operations_load,
            test_class.test_database_performance,
            test_class.test_memory_usage,
            test_class.test_error_handling_under_load
        ]
        
        for test in tests:
            try:
                await test()
                self.passed_tests += 1
                print(f"  ✅ {test.__name__}")
            except Exception as e:
                self.failed_tests += 1
                print(f"  ❌ {test.__name__}: {e}")
            
            self.total_tests += 1
        
        self.results["load_performance"] = {
            "total": 6,
            "passed": self.passed_tests - sum(r["passed"] for r in self.results.values()),
            "failed": self.failed_tests - sum(r["failed"] for r in self.results.values())
        }
    
    async def run_all_tests(self):
        """Run all acceptance tests"""
        print("🚀 Starting AL Bot Acceptance Tests")
        print("=" * 50)
        
        # Run all test suites
        await self.run_file_parsing_tests()
        await self.run_llm_integration_tests()
        await self.run_ux_flow_tests()
        await self.run_trial_gating_tests()
        await self.run_load_performance_tests()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        for suite_name, results in self.results.items():
            print(f"{suite_name}: {results['passed']}/{results['total']} passed")
        
        print(f"\nTotal: {self.passed_tests}/{self.total_tests} tests passed")
        
        if self.failed_tests == 0:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"❌ {self.failed_tests} tests failed")
            return False


async def main():
    """Main test runner"""
    runner = TestRunner()
    success = await runner.run_all_tests()
    
    if success:
        print("\n✅ Acceptance tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some acceptance tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

