import os
import pytest
from pathlib import Path
from swingarena.harness.agent import create_patch_from_diff, parse_testcase, PatchVerifier, TestVerifier
from swingarena.harness.router import CargoCITool
from swingarena.harness.constants.swing_constants import SwingbenchInstance

def test_create_patch_from_diff(tmp_path):
    """Test creating patch from two versions of code."""
    original_code = """fn add(a: i32, b: i32) -> i32 {
    a + b  // missing return
}"""
    
    fixed_code = """fn add(a: i32, b: i32) -> i32 {
    return a + b;
}"""
    
    file_path = "src/lib.rs"
    patch = create_patch_from_diff(original_code, fixed_code, file_path)
    
    print("Generated patch:", patch)
    
    # Verify patch format
    assert "diff --git" in patch
    assert "a/src/lib.rs" in patch
    assert "b/src/lib.rs" in patch
    assert "-    a + b" in patch
    assert "+    return a + b;" in patch

def test_parse_testcase():
    """Test creating patch for new test file."""
    test_code = """#[test]
fn test_add() {
    assert_eq!(add(2, 3), 5);
}"""
    
    file_path = "tests/test_lib.rs"
    patch = parse_testcase(test_code, file_path)
    
    # Verify patch format
    assert "diff --git" in patch
    assert "new file mode 100644" in patch
    assert "--- /dev/null" in patch
    assert "+++ b/tests/test_lib.rs" in patch
    assert "+#[test]" in patch
    assert "+fn test_add() {" in patch

def test_patch_verifier_extract_patch(tmp_path):
    """Test PatchVerifier's _extract_patch method."""
    # Setup
    src_dir = tmp_path
    lib_file = os.path.join(src_dir, "src", "lib.rs")
    os.makedirs(os.path.dirname(lib_file), exist_ok=True)
    
    original_code = """fn factorial(n: u32) -> u32 {
    if n <= 1 { return 1; }
    n + factorial(n - 1)  // bug: using + instead of *
}"""
    
    with open(lib_file, "w") as f:
        f.write(original_code)
    
    # Test input with markdown
    model_output = """```rust
fn factorial(n: u32) -> u32 {
    if n <= 1 { return 1; }
    n * factorial(n - 1)  // fixed: using * instead of +
}
```"""
    
    verifier = PatchVerifier(ci_tool_name="cargo", src_folder=str(src_dir))
    patch = verifier._extract_patch(model_output)
    
    print("Generated patch in verifier test:", patch)
    
    # Verify patch format
    assert "diff --git" in patch
    assert "a/src/lib.rs" in patch
    assert "b/src/lib.rs" in patch
    assert "-    n + factorial" in patch
    assert "+    n * factorial" in patch

def test_test_verifier_extract_patch(tmp_path):
    """Test TestVerifier's _extract_patch method."""
    # Create a test instance
    instance = SwingbenchInstance(
        instance_id="test_instance_1",
        repo="test/repo",
        problem_statement="Test problem",
        hints_text="Test hints",
        base_commit="HEAD",
        merge_commit_sha="HEAD",
        patch="""diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -1,5 +1,5 @@
 fn factorial(n: u32) -> u32 {
     if n <= 1 { return 1; }
-    n + factorial(n - 1)
+    n * factorial(n - 1)
 }""",
        test_patch=None
    )
    
    # Test input with markdown
    model_output = """```rust
#[test]
fn test_factorial() {
    assert_eq!(factorial(3), 6);
    assert_eq!(factorial(4), 24);
}
```"""
    
    # Create CargoCITool with required config
    ci_tool = CargoCITool({
        "instance_id": instance.instance_id,
        "repo": instance.repo,
        "base_commit": instance.base_commit,
        "merge_commit": instance.merge_commit_sha,
        "workdir": str(tmp_path),
        "output_dir": str(tmp_path / "logs"),
        "src_folder": str(tmp_path),
        "patch": instance.patch,
        "apply_patch": True,
        "ci_name_list": ["test"]
    })
    
    verifier = TestVerifier(ci_tool=ci_tool)
    patch = verifier._extract_patch(model_output)
    
    print("Generated test patch:", patch)
    
    # Verify patch format
    assert "diff --git" in patch
    assert "new file mode 100644" in patch
    assert "--- /dev/null" in patch
    assert "+++ b/tests/test_lib.rs" in patch
    assert "+#[test]" in patch
    assert "+fn test_factorial() {" in patch

if __name__ == "__main__":
    pytest.main([__file__])