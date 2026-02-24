import unittest

def load_file_content(file_path, repo_structure, decoding="utf-8"):
    path_parts = file_path.split("/")
    if len(path_parts) == 1:
        path_parts.insert(0, "")
    file_content = repo_structure
    for part in path_parts:
        if part in file_content:
            file_content = file_content[part]
        else:
            return ""
    if isinstance(file_content, dict) and "text" in file_content:
        text_lines = [
            line.encode("ISO-8859-1").decode(decoding) for line in file_content["text"]
        ]
        return "\n".join(text_lines)
    return ""

class TestLoadFileContent(unittest.TestCase):
    def setUp(self):
        self.repo_structure = {
            "": {
                "README.md": {
                    "text": ["# Project", "This is a sample project."]
                },
                "LICENSE": {
                    "text": ["MIT License", "Copyright (c) 2025"]
                }
            },
            "src": {
                "main.py": {
                    "text": ["def main():", "    print('Hello World')", "", "if __name__ == '__main__':", "    main()"]
                }
            },
            "src/utils": {
                "helpers.py": {
                    "text": ["def helper_function():", "    return 'Helper'"]
                },
                "config.py": {
                    "text": ["CONFIG = {", "    'debug': True", "}"]
                }
            },
            "tests": {
                "test_main.py": {
                    "text": ["import unittest", "", "class TestMain(unittest.TestCase):", "    def test_main(self):", "        self.assertTrue(True)"]
                }
            }
        }
        
        self.special_chars_repo = {
            "": {
                "utf8_file.txt": {
                    "text": ["こんにちは", "你好", "Привет"]
                }
            }
        }
        
        self.empty_repo = {}
    
    def test_load_root_file(self):
        content = load_file_content("README.md", self.repo_structure)
        expected = "# Project\nThis is a sample project."
        self.assertEqual(content, expected)
    
    def test_load_nested_file(self):
        content = load_file_content("src/main.py", self.repo_structure)
        expected = "def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()"
        self.assertEqual(content, expected)
    
    def test_nonexistent_file(self):
        content = load_file_content("src/nonexistent.py", self.repo_structure)
        self.assertEqual(content, "")
    
    def test_nonexistent_directory(self):
        content = load_file_content("nonexistent_dir/file.py", self.repo_structure)
        self.assertEqual(content, "")
    
    def test_directory_as_file(self):
        content = load_file_content("src", self.repo_structure)
        self.assertEqual(content, "")
    
    def test_empty_repo(self):
        content = load_file_content("file.txt", self.empty_repo)
        self.assertEqual(content, "")
    
    def test_latin1_encoding(self):
        latin1_repo = {
            "": {
                "latin1_file.txt": {
                    "text": ["café", "résumé", "naïve"]
                }
            }
        }
        content = load_file_content("latin1_file.txt", latin1_repo, decoding="latin-1")
        expected = "café\nrésumé\nnaïve"
        self.assertEqual(content, expected)

if __name__ == "__main__":
    unittest.main()