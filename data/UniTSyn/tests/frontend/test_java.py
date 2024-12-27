import unittest
import os
import logging
from returns.maybe import Nothing, Some
from frontend.java.collect_focal import get_focal_call
from frontend.parser.ast_util import ASTUtil
from frontend.parser import JAVA_LANGUAGE


class TestJavaFrontend(unittest.TestCase):
    def __test_focal_helper(self, code: str):
        ast_util = ASTUtil(code)
        tree = ast_util.tree(JAVA_LANGUAGE)
        root_node = tree.root_node

        fn = ast_util.get_all_nodes_of_type(root_node, "method_declaration")[0]
        return get_focal_call(ast_util, fn)

    def test_focal(self):
        """
        For a regular @Test function, with function call in `assertThat`,
        that function call should be the focal
        """
        code = """
@Test
void catalogLoads() {
	@SuppressWarnings("rawtypes")
	ResponseEntity<Map> entity = new TestRestTemplate()
			.getForEntity("http://localhost:" + this.port + "/context/eureka/apps", Map.class);
	assertThat(entity.getStatusCode()).isEqualTo(HttpStatus.OK);
	String computedPath = entity.getHeaders().getFirst("X-Version-Filter-Computed-Path");
	assertThat(computedPath).isEqualTo("/context/eureka/v2/apps");
}"""

        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "getStatusCode")
        self.assertEqual(loc, (6, 19))

        code = """
@Test
void testAdd() {
    assertThat(add(1, 2)).isEqualTo(3);    
}"""
        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "add")
        self.assertEqual(loc, (3, 15))

        code = """
@Test
void testCompareTo() {
    assertTrue(0 == Status.INITIAL.compareTo(Status.INITIAL));
    assertTrue(0 > Status.INITIAL.compareTo(Status.TRANSLATED));
    assertTrue(0 > Status.INITIAL.compareTo(Status.VERIFIED));
    assertTrue(0 > Status.INITIAL.compareTo(Status.SPECIAL));

    assertTrue(0 < Status.TRANSLATED.compareTo(Status.INITIAL));
    assertTrue(0 == Status.TRANSLATED.compareTo(Status.TRANSLATED));
    assertTrue(0 > Status.TRANSLATED.compareTo(Status.VERIFIED));
    assertTrue(0 > Status.TRANSLATED.compareTo(Status.SPECIAL));

    assertTrue(0 < Status.VERIFIED.compareTo(Status.INITIAL));
    assertTrue(0 < Status.VERIFIED.compareTo(Status.TRANSLATED));
    assertTrue(0 == Status.VERIFIED.compareTo(Status.VERIFIED));
    assertTrue(0 > Status.VERIFIED.compareTo(Status.SPECIAL));

    assertTrue(0 < Status.SPECIAL.compareTo(Status.INITIAL));
    assertTrue(0 < Status.SPECIAL.compareTo(Status.TRANSLATED));
    assertTrue(0 < Status.SPECIAL.compareTo(Status.VERIFIED));
    assertTrue(0 == Status.SPECIAL.compareTo(Status.SPECIAL));
}"""
        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "compareTo")
        self.assertEqual(loc, (3, 35))

    def test_focal_not_in_assert(self):
        """
        if there is no function call in the first `assertThat`,
        the the last call before first `assertThat` is the focal
        """
        code = """
@Test
void catalogLoads() {
	@SuppressWarnings("rawtypes")
	ResponseEntity<Map> entity = new TestRestTemplate()
			.getForEntity("http://localhost:" + this.port + "/context/eureka/apps", Map.class);
	String computedPath = entity.getHeaders().getFirst("X-Version-Filter-Computed-Path");
	assertThat(computedPath).isEqualTo("/context/eureka/v2/apps");
}"""

        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "getFirst")
        self.assertEqual(loc, (6, 43))

        code = """
@Test
void testAdd() {
    int z = add(1, 2);
    assertThat(z).isEqualTo(3);    
}"""
        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "add")
        self.assertEqual(loc, (3, 12))

    def test_focal_not_assert(self):
        """If no assert in test function, then fail"""

        code = "@Test\nvoid testNothing() {\n}"
        self.assertEqual(self.__test_focal_helper(code), Nothing)

    def test_focal_in_branch(self):
        code = """
@Test
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
        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "size")
        self.assertEqual(loc, (13, 25))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
