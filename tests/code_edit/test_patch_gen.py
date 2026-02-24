import unittest
import os
import tempfile
import subprocess

def generate_git_diff(file_path, old_content, new_content):
    """
    Creates a temporary git repository and returns the diff between two versions of a file.
    
    Args:
        file_path: Path to the file within the repository
        old_content: Initial content of the file
        new_content: Modified content of the file
    
    Returns:
        String containing the git diff output
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run("git init -b main -q", shell=True, cwd=tmp_dir)
        subprocess.run("git config user.name 'test'", shell=True, cwd=tmp_dir)
        subprocess.run("git config user.email 'test@example.com'", shell=True, cwd=tmp_dir)        
        file_dir = os.path.dirname(file_path)
        if file_dir:
            os.makedirs(os.path.join(tmp_dir, file_dir), exist_ok=True)

        with open(os.path.join(tmp_dir, file_path), "w") as f:
            f.write(old_content)
        subprocess.run(
            f"git add {file_path} && git commit -m 'initial commit'",
            shell=True,
            cwd=tmp_dir
        )
        
        with open(os.path.join(tmp_dir, file_path), "w") as f:
            f.write(new_content)
        result = subprocess.run(
            f"git diff {file_path}", 
            shell=True, 
            capture_output=True,
            cwd=tmp_dir
        )
        diff_output = result.stdout.decode("utf-8")

        return diff_output
    
class TestGenerateGitDiff(unittest.TestCase):
    def test_basic_modification(self):
        """Test basic code modification."""
        old_content = """fn factorial(n: u32) -> u32 {
    if n <= 1 { return 1; }
    n + factorial(n - 1)  // bug: using + instead of *
}"""
        new_content = """fn factorial(n: u32) -> u32 {
    if n <= 1 { return 1; }
    n * factorial(n - 1)  // fixed: using * instead of +
}"""
        file_path = "src/lib.rs"
        
        diff = generate_git_diff(file_path, old_content, new_content)
        
        self.assertIn("diff --git", diff)
        self.assertIn("--- a/src/lib.rs", diff)
        self.assertIn("+++ b/src/lib.rs", diff)
        self.assertIn("-    n + factorial(n - 1)", diff)
        self.assertIn("+    n * factorial(n - 1)", diff)

    def test_multiline_changes(self):
        """Test multiple line modifications."""
        old_content = """fn add_numbers(a: i32, b: i32) -> i32 {
    // Old implementation
    let result = a;
    result + b
}"""
        new_content = """fn add_numbers(a: i32, b: i32) -> i32 {
    // New implementation with proper return
    let result = a + b;
    result
}"""
        file_path = "src/math.rs"
        
        diff = generate_git_diff(file_path, old_content, new_content)
        print("diff: ", diff)
        self.assertIn("diff --git", diff)
        self.assertIn("--- a/src/math.rs", diff)
        self.assertIn("+++ b/src/math.rs", diff)
        self.assertIn("-    // Old implementation", diff)
        self.assertIn("+    // New implementation with proper return", diff)
        self.assertIn("-    let result = a;", diff)
        self.assertIn("+    let result = a + b;", diff)

    def test_nested_directory(self):
        """Test file in nested directory structure."""
        old_content = "println!(\"Hello\");"
        new_content = "println!(\"Hello, World!\");"
        file_path = "src/utils/logging/printer.rs"
        
        diff = generate_git_diff(file_path, old_content, new_content)
        
        self.assertIn("diff --git", diff)
        self.assertIn("--- a/src/utils/logging/printer.rs", diff)
        self.assertIn("+++ b/src/utils/logging/printer.rs", diff)
        self.assertIn('-println!("Hello");', diff)
        self.assertIn('+println!("Hello, World!");', diff)

    def test_whitespace_changes(self):
        """Test handling of whitespace changes."""
        old_content = """fn test() {
    let x = 1;
    let y = 2;
}"""
        new_content = """fn test() {
    let x = 1;
    
    let y = 2;
}"""
        file_path = "src/test.rs"
        
        diff = generate_git_diff(file_path, old_content, new_content)
        print("diff: ", diff)
        self.assertIn("diff --git", diff)
        self.assertIn("@@ ", diff)
        self.assertIn("+", diff)  

    def test_empty_file(self):
        """Test handling empty file content."""
        old_content = ""
        new_content = "// New file content"
        file_path = "src/empty.rs"
        
        diff = generate_git_diff(file_path, old_content, new_content)
        print("diff: ", diff)
        self.assertIn("diff --git", diff)
        self.assertIn("+// New file content", diff)

    def test_no_changes(self):
        """Test when content hasn't changed."""
        content = """fn test() {
    println!("test");
}"""
        file_path = "src/same.rs"
        
        diff = generate_git_diff(file_path, content, content)
        
        self.assertEqual(diff.strip(), "")

if __name__ == '__main__':
    unittest.main()