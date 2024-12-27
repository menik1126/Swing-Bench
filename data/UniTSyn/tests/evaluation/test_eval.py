"""tests for  get_coverage module in evaluation/execution.py"""
import os
from evaluation.execution import get_coverage
import unittest
import logging
from unitsyncer.common import UNITSYNCER_HOME


class TestEvaluationCoverage(unittest.TestCase):
    """tests for evaluation/execution.py"""

    def test_python(self):
        focal = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    """ Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    """\n    for idx, elem in enumerate(numbers):\n        for idx2, elem2 in enumerate(numbers):\n            if idx != idx2:\n                distance = abs(elem - elem2)\n                if distance < threshold:\n                    return True\n\n    return False\n'
        test = "\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(has_close_elements):\n    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True\n    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False\n    assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True\n    assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False\n    assert has_close_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True\n    assert has_close_elements([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) == True\n    assert has_close_elements([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False\n\ncheck(has_close_elements)"
        self.assertEqual(get_coverage(focal, test, "python"), (None, 100, 100))

    def test_cpp(self):
        focal = "/*\nCheck if in given vector of numbers, are any two numbers closer to each other than\ngiven threshold.\n>>> has_close_elements({1.0, 2.0, 3.0}, 0.5)\nfalse\n>>> has_close_elements({1.0, 2.8, 3.0, 4.0, 5.0, 2.0}, 0.3)\ntrue\n*/\n#include<stdio.h>\n#include<vector>\n#include<math.h>\nusing namespace std;\nbool has_close_elements(vector<float> numbers, float threshold){\n    int i,j;\n    \n    for (i=0;i<numbers.size();i++)\n    for (j=i+1;j<numbers.size();j++)\n    if (abs(numbers[i]-numbers[j])<threshold)\n    return true;\n\n    return false;\n}\n\n"
        test = "#undef NDEBUG\n#include<assert.h>\nint main(){\n    vector<float> a={1.0, 2.0, 3.9, 4.0, 5.0, 2.2};\n    assert (has_close_elements(a, 0.3)==true);\n    assert (has_close_elements(a, 0.05) == false);\n\n    assert (has_close_elements({1.0, 2.0, 5.9, 4.0, 5.0}, 0.95) == true);\n    assert (has_close_elements({1.0, 2.0, 5.9, 4.0, 5.0}, 0.8) ==false);\n    assert (has_close_elements({1.0, 2.0, 3.0, 4.0, 5.0}, 2.0) == true);\n    assert (has_close_elements({1.1, 2.2, 3.1, 4.1, 5.1}, 1.0) == true);\n    assert (has_close_elements({1.1, 2.2, 3.1, 4.1, 5.1}, 0.5) == false);\n    \n}\n"

        self.assertEqual(get_coverage(focal, test, "cpp"), (None, 100, 100))

    def test_java(self):
        java_lib_path = os.path.join(UNITSYNCER_HOME, "evaluation", "lib")

        focal = "import java.util.*;\nimport java.lang.*;\n\nclass Solution {\n    /**\n    Check if in given list of numbers, are any two numbers closer to each other than given threshold.\n    >>> hasCloseElements(Arrays.asList(1.0, 2.0, 3.0), 0.5)\n    false\n    >>> hasCloseElements(Arrays.asList(1.0, 2.8, 3.0, 4.0, 5.0, 2.0), 0.3)\n    true\n     */\n    public boolean hasCloseElements(List<Double> numbers, double threshold) {\n        for (int i = 0; i < numbers.size(); i++) {\n            for (int j = i + 1; j < numbers.size(); j++) {\n                double distance = Math.abs(numbers.get(i) - numbers.get(j));\n                if (distance < threshold) return true;\n            }\n        }\n        return false;\n    }\n}"
        test = "public class Main {\n    public static void main(String[] args) {\n        Solution s = new Solution();\n        List<Boolean> correct = Arrays.asList(\n                s.hasCloseElements(new ArrayList<>(Arrays.asList(11.0, 2.0, 3.9, 4.0, 5.0, 2.2)), 0.3),\n                !s.hasCloseElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 3.9, 4.0, 5.0, 2.2)), 0.05),\n                s.hasCloseElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 5.9, 4.0, 5.0)), 0.95),\n                !s.hasCloseElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 5.9, 4.0, 5.0)), 0.8),\n                s.hasCloseElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 3.0, 4.0, 5.0, 2.0)), 0.1),\n                s.hasCloseElements(new ArrayList<>(Arrays.asList(1.1, 2.2, 3.1, 4.1, 5.1)), 1.0),\n                !s.hasCloseElements(new ArrayList<>(Arrays.asList(1.1, 2.2, 3.1, 4.1, 5.1)), 0.5)\n        );\n        if (correct.contains(false)) {\n            throw new AssertionError();\n        }\n    }\n}"
        self.assertEqual(
            get_coverage(focal, test, "java", java_lib_path=java_lib_path),
            (None, 100, 100),
        )

    def test_js(self):
        focal = "/* Check if in given list of numbers, are any two numbers closer to each other than\n  given threshold.\n  >>> hasCloseElements([1.0, 2.0, 3.0], 0.5)\n  false\n  >>> hasCloseElements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n  true\n  */\nconst hasCloseElements = (numbers, threshold) => {\n  for (let i = 0; i < numbers.length; i++) {\n    for (let j = 0; j < numbers.length; j++) {\n      if (i != j) {\n        let distance = Math.abs(numbers[i] - numbers[j]);\n        if (distance < threshold) {\n          return true;\n        }\n      }\n    }\n  }\n  return false;\n}\n\n"
        test = "const testHasCloseElements = () => {\n  console.assert(hasCloseElements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) === true)\n  console.assert(\n    hasCloseElements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) === false\n  )\n  console.assert(hasCloseElements([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) === true)\n  console.assert(hasCloseElements([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) === false)\n  console.assert(hasCloseElements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) === true)\n  console.assert(hasCloseElements([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) === true)\n  console.assert(hasCloseElements([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) === false)\n}\n\ntestHasCloseElements()\n"
        self.assertEqual(get_coverage(focal, test, "js"), (100, 100, 100))

    def test_go(self):
        focal = 'import (\n    "math"\n)\n\n// Check if in given list of numbers, are any two numbers closer to each other than given threshold.\n// >>> HasCloseElements([]float64{1.0, 2.0, 3.0}, 0.5)\n// false\n// >>> HasCloseElements([]float64{1.0, 2.8, 3.0, 4.0, 5.0, 2.0}, 0.3)\n// true\nfunc HasCloseElements(numbers []float64, threshold float64) bool {\n    for i := 0; i < len(numbers); i++ {\n        for j := i + 1; j < len(numbers); j++ {\n            var distance float64 = math.Abs(numbers[i] - numbers[j])\n            if distance < threshold {\n                return true\n            }\n        }\n    }\n    return false\n}\n\n'
        test = "func TestHasCloseElements(t *testing.T) {\n    assert := assert.New(t)\n    assert.Equal(true, HasCloseElements([]float64{11.0, 2.0, 3.9, 4.0, 5.0, 2.2}, 0.3))\n    assert.Equal(false, HasCloseElements([]float64{1.0, 2.0, 3.9, 4.0, 5.0, 2.2}, 0.05))\n    assert.Equal(true, HasCloseElements([]float64{1.0, 2.0, 5.9, 4.0, 5.0}, 0.95))\n    assert.Equal(false, HasCloseElements([]float64{1.0, 2.0, 5.9, 4.0, 5.0}, 0.8))\n    assert.Equal(true, HasCloseElements([]float64{1.0, 2.0, 3.0, 4.0, 5.0, 2.0}, 0.1))\n    assert.Equal(true, HasCloseElements([]float64{1.1, 2.2, 3.1, 4.1, 5.1}, 1.0))\n    assert.Equal(false, HasCloseElements([]float64{1.1, 2.2, 3.1, 4.1, 5.1}, 0.5))\n}\n"
        self.assertEqual(get_coverage(focal, test, "go"), (100, None, None))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
