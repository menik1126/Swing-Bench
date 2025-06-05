import logging
import json
import re

from swebench.harness.constants.swing_constants import SwingbenchInstance
from swebench.harness.agent.model import AgentProxy
from swebench.harness.agent.prompt import (
    TEST_AGENT_PROBLEM_AND_TEST,
    TEST_AGENT_TEST_ONLY, 
    TEST_AGENT_PROBLEM_TEST_AND_GOLDEN,
    TEST_AGENT_USER_PROBLEM_AND_TEST,
    TEST_AGENT_USER_TEST_ONLY,
    TEST_AGENT_USER_PROBLEM_TEST_AND_GOLDEN
)

class TestAgent:
    def __init__(self, 
                 model_name: str,
                 base_url: str = None,
                 api_key: str = None,
                 temperature: float = 0.0,
                 max_tokens: int = 2048,
                 top_p: float = 1.0
                 ):
        self.agent_proxy = AgentProxy(
            name=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("TestAgent")
    
    def verify_patch(self, 
                     patch: str, 
                     testcase: str, 
                     problem_statement: str = None,
                     golden_patch: str = None,
                     use_problem: bool = False,
                     use_test: bool = True,
                     use_golden: bool = False,
                     data: SwingbenchInstance = None) -> dict:
        if data and not problem_statement and use_problem:
            problem_statement = data.problem_statement
            if hasattr(data, 'hints_text') and data.hints_text:
                problem_statement += "\n" + data.hints_text
        
        assert not use_problem or (use_problem and problem_statement), "Problem statement is required when use_problem=True"
        assert not use_golden or (use_golden and golden_patch), "Golden patch is required when use_golden=True"
        assert use_test, "Test case is required (use_test cannot be False)"
        
        self.logger.info(f"Verifying patch with: use_problem={use_problem}, use_test={use_test}, use_golden={use_golden}")

        if use_problem and use_golden:
            result = self._verify_with_problem_test_and_golden(patch, testcase, problem_statement, golden_patch)
        elif use_problem:
            result = self._verify_with_problem_and_test(patch, testcase, problem_statement)
        else:
            result = self._verify_with_test_only(patch, testcase)
        
        return result
    
    def _verify_with_problem_and_test(self, patch: str, testcase: str, problem_statement: str) -> dict:
        system_prompt = TEST_AGENT_PROBLEM_AND_TEST
        user_prompt = TEST_AGENT_USER_PROBLEM_AND_TEST.format(
            problem_statement=problem_statement,
            testcase=testcase,
            patch=patch
        )
        
        return self._get_model_verification(system_prompt, user_prompt)
    
    def _verify_with_test_only(self, patch: str, testcase: str) -> dict:
        system_prompt = TEST_AGENT_TEST_ONLY
        user_prompt = TEST_AGENT_USER_TEST_ONLY.format(
            testcase=testcase,
            patch=patch
        )
        
        return self._get_model_verification(system_prompt, user_prompt)
    
    def _verify_with_problem_test_and_golden(self, patch: str, testcase: str, problem_statement: str, golden_patch: str) -> dict:
        system_prompt = TEST_AGENT_PROBLEM_TEST_AND_GOLDEN
        user_prompt = TEST_AGENT_USER_PROBLEM_TEST_AND_GOLDEN.format(
            problem_statement=problem_statement,
            testcase=testcase,
            golden_patch=golden_patch,
            patch=patch
        )
        
        return self._get_model_verification(system_prompt, user_prompt)
    
    def _verify_with_problem_test_and_golden(self, patch: str, testcase: str, 
                                            problem_statement: str, golden_patch: str) -> dict:
        system_prompt = TEST_AGENT_PROBLEM_TEST_AND_GOLDEN
        
        user_prompt = TEST_AGENT_USER_PROBLEM_TEST_AND_GOLDEN.format(
            problem_statement=problem_statement,
            testcase=testcase,
            golden_patch=golden_patch,
            patch=patch
        )
        
        return self._get_model_verification(system_prompt, user_prompt)
    
    def _get_model_verification(self, system_prompt: str, user_prompt: str) -> dict:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.agent_proxy.generate(messages)
            self.logger.info(f"Model response: {response}")
            
            try:
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                if json_match:
                    result_json = json.loads(json_match.group(1))
                else:
                    result_json = json.loads(response)
                
                success = result_json.get("success", False)
                reasoning = result_json.get("reasoning", "No reasoning provided")
                confidence = result_json.get("confidence", "MEDIUM")
                issues = result_json.get("issues", [])
                
                details = {
                    "confidence": confidence,
                    "issues": issues,
                    "reasoning": reasoning,
                    "full_response": response
                }
                
                return {
                    "success": success,
                    "details": details
                }
                
            except json.JSONDecodeError:
                # If the response is not JSON, try to determine success from text
                if "successfully" in response.lower() or "passes" in response.lower():
                    return {
                        "success": True,
                        "details": {"confidence": "LOW", "full_response": response}
                    }
                else:
                    return {
                        "success": False,
                        "details": {"confidence": "VERY_LOW", "full_response": response}
                    }
        
        except Exception as e:
            self.logger.error(f"Error during model verification: {str(e)}")
            return {
                "success": False,
                "details": {"error": str(e), "confidence": "VERY_LOW"}
            }


if __name__ == "__main__":
    sample_testcase = """--- /dev/null
+++ b/test_add.py
@@ -0,0 +1,15 @@
+import unittest
+from calculator import add
+
+class TestAdd(unittest.TestCase):
+    def test_add_positive(self):
+        self.assertEqual(add(1, 2), 3)
+        self.assertEqual(add(5, 7), 12)
+    
+    def test_add_negative(self):
+        self.assertEqual(add(-1, -2), -3)
+        self.assertEqual(add(-5, 7), 2)
+    
+if __name__ == '__main__':
+    unittest.main()
+"""
    
    # Correct patch
    correct_patch = """--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b  # Bug: subtraction instead of addition
+    return a + b  # Fixed: now correctly performs addition
"""
    
    # Incorrect patch (doesn't fix the issue)
    incorrect_patch = """--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,3 @@
 def add(a, b):
-    return a - b  # Bug: subtraction instead of addition
+    # Still incorrect but with a comment change
+    return a - b
"""
    
    problem_statement = "Fix the bug in the calculator's add function. It's currently subtracting instead of adding."
    
    test_agent = TestAgent(
        model_name="qwen-max-latest",
        api_key="sk-826b874003eb4f309bd65c7a6f0f79b5",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1/"
    )
        
    print("==== Testing with problem statement and test case (correct patch) ====")
    result = test_agent.verify_patch(
        patch=correct_patch,
        testcase=sample_testcase,
        problem_statement=problem_statement,
        use_problem=True
    )
    print(f"Success: {result['success']}")
    print(f"Confidence: {result['details']['confidence']}")
    
    print("\n==== Testing with problem statement and test case (incorrect patch) ====")
    result = test_agent.verify_patch(
        patch=incorrect_patch,
        testcase=sample_testcase,
        problem_statement=problem_statement,
        use_problem=True
    )
    print(f"Success: {result['success']}")
    print(f"Confidence: {result['details']['confidence']}")
    
    print("\n==== Testing with test case only (correct patch) ====")
    result = test_agent.verify_patch(
        patch=correct_patch,
        testcase=sample_testcase
    )
    print(f"Success: {result['success']}")
    print(f"Confidence: {result['details']['confidence']}")
    
    print("\n==== Testing with problem, test, and golden patch ====")
    slightly_different_patch = """--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,3 @@
 def add(a, b):
-    return a - b  # Bug: subtraction instead of addition
+    # Fixed with a different comment
+    return a + b
"""
    result = test_agent.verify_patch(
        patch=slightly_different_patch,
        testcase=sample_testcase,
        problem_statement=problem_statement,
        golden_patch=correct_patch,
        use_problem=True,
        use_golden=True
    )
    print(f"Success: {result['success']}")
    print(f"Confidence: {result['details']['confidence']}")