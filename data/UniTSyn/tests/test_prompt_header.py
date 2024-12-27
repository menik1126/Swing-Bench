"""tests for get_def_header module in evaluation/extract_def.py"""
import os
from unitsyncer.extract_def import get_def_header
import unittest
import logging
from unitsyncer.common import UNITSYNCER_HOME


class TestGetDefHeader(unittest.TestCase):
    def test_py(self):
        test = "\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(has_close_elements):\n    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True\n    assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False\n    assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True\n    assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False\n    assert has_close_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True\n    assert has_close_elements([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) == True\n    assert has_close_elements([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False\n\ncheck(has_close_elements)"

        self.assertEqual(
            get_def_header(test, "python"), "def check(has_close_elements):\n"
        )

    def test_go(self):
        test = "func TestHasCloseElements(t *testing.T) {\n    assert := assert.New(t)\n    assert.Equal(true, HasCloseElements([]float64{11.0, 2.0, 3.9, 4.0, 5.0, 2.2}, 0.3))\n    assert.Equal(false, HasCloseElements([]float64{1.0, 2.0, 3.9, 4.0, 5.0, 2.2}, 0.05))\n    assert.Equal(true, HasCloseElements([]float64{1.0, 2.0, 5.9, 4.0, 5.0}, 0.95))\n    assert.Equal(false, HasCloseElements([]float64{1.0, 2.0, 5.9, 4.0, 5.0}, 0.8))\n    assert.Equal(true, HasCloseElements([]float64{1.0, 2.0, 3.0, 4.0, 5.0, 2.0}, 0.1))\n    assert.Equal(true, HasCloseElements([]float64{1.1, 2.2, 3.1, 4.1, 5.1}, 1.0))\n    assert.Equal(false, HasCloseElements([]float64{1.1, 2.2, 3.1, 4.1, 5.1}, 0.5))\n}\n"
        self.assertEqual(
            get_def_header(test, "go"),
            "func TestHasCloseElements(t *testing.T) {\n",
        )

    def test_js(self):
        test = "const testHasCloseElements = () => {\n  console.assert(hasCloseElements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) === true)\n  console.assert(\n    hasCloseElements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) === false\n  )\n  console.assert(hasCloseElements([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) === true)\n  console.assert(hasCloseElements([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) === false)\n  console.assert(hasCloseElements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) === true)\n  console.assert(hasCloseElements([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) === true)\n  console.assert(hasCloseElements([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) === false)\n}\n\ntestHasCloseElements()\n"

        self.assertEqual(
            get_def_header(test, "js"),
            "const testHasCloseElements = () => {\n",
        )

    def test_cpp(self):
        test = """
TEST(AsmWriterTest, DebugPrintDetachedArgument) {
  LLVMContext Ctx;
  auto Ty = Type::getInt32Ty(Ctx);
  auto Arg = new Argument(Ty);

  std::string S;
  raw_string_ostream OS(S);
  Arg->print(OS);
  EXPECT_EQ(S, "i32 <badref>");
  delete Arg;
}"""
        self.assertEqual(
            get_def_header(test, "cpp"),
            "TEST(AsmWriterTest, DebugPrintDetachedArgument) {\n",
        )

        code = """
TEST(BFSTest, InstantiateGraphFromEdges)
{
    Graph<int> g({ {1, 2}, {1, 3}, {2, 3} });

    std::vector<int> bfs = g.BFS(1);
    std::vector<int> expected{ 1, 2, 3 };

    ASSERT_EQ(bfs, expected);
}
"""
        self.assertEqual(
            get_def_header(code, "cpp"),
            "TEST(BFSTest, InstantiateGraphFromEdges) {\n",
        )

    def test_java(self):
        code = """@Test
void catalogLoads() {
	@SuppressWarnings("rawtypes")
	ResponseEntity<Map> entity = new TestRestTemplate()
			.getForEntity("http://localhost:" + this.port + "/context/eureka/apps", Map.class);
	assertThat(entity.getStatusCode()).isEqualTo(HttpStatus.OK);
	String computedPath = entity.getHeaders().getFirst("X-Version-Filter-Computed-Path");
	assertThat(computedPath).isEqualTo("/context/eureka/v2/apps");
}"""

        self.assertEqual(get_def_header(code, "java"), "@Test\nvoid catalogLoads() {\n")

        code = """@Test
void testAdd() {
    assertThat(add(1, 2)).isEqualTo(3);    
}"""
        self.assertEqual(get_def_header(code, "java"), "@Test\nvoid testAdd() {\n")

        code = """@Test
public void testInputParts(ServiceTransformationEngine transformationEngine, @All ServiceManager serviceManager) throws Exception {

    //check and import services
    checkAndImportServices(transformationEngine, serviceManager);

    URI op = findServiceURI(serviceManager, "serv1323166560");
    String[] expected = {"con241744282", "con1849951292", "con1653328292"};
    if (op != null) {
        Set<URI> ops = serviceManager.listOperations(op);
        Set<URI> inputs = serviceManager.listInputs(ops.iterator().next());
        Set<URI> parts = new HashSet<URI>(serviceManager.listMandatoryParts(inputs.iterator().next()));
        assertTrue(parts.size() == 3);
        for (URI part : parts) {
            boolean valid = false;
            for (String expectedInput : expected) {
                if (part.toASCIIString().contains(expectedInput)) {
                    valid = true;
                    break;
                }
            }
            assertTrue(valid);
        }
    } else {
        fail();
    }

    serviceManager.shutdown();
}"""

        self.assertEqual(
            get_def_header(code, "java"),
            "@Test\npublic void testInputParts(ServiceTransformationEngine transformationEngine, @All ServiceManager serviceManager) throws Exception {\n",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
