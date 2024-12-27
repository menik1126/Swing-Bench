from tree_sitter import Language
import tree_sitter_rust as tsrust
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjavascript
import tree_sitter_go as tsgo
import tree_sitter_python as python
import tree_sitter_cpp as tscpp

JAVA_LANGUAGE = Language(tsjava.language(), "java")
JAVASCRIPT_LANGUAGE = Language(tsjavascript.language(), "javascript")
RUST_LANGUAGE = Language(tsrust.language(), "rust")
GO_LANGUAGE = Language(tsgo.language(), "go")
CPP_LANGUAGE = Language(tscpp.language(), "cpp")
PYTHON_LANGUAGE = Language(python.language(), "python")