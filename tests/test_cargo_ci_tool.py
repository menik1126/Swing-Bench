import os
import tempfile
import shutil
import subprocess
import json
from swingarena.harness.router import CargoCITool

def create_test_rust_project():
    temp_dir = tempfile.mkdtemp()
    project_name = "test_cargo_project"
    project_dir = os.path.join(temp_dir, project_name)
    
    
    subprocess.run(["cargo", "new", "--lib", project_name], cwd=temp_dir, check=True)
    
    
    lib_rs_content = """
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

pub fn multiply(a: i32, b: i32) -> i32 {
    a * b
}

pub fn is_even(n: i32) -> bool {
    n % 2 == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 2), 4);
    }

    #[test]
    fn test_multiply() {
        assert_eq!(multiply(2, 3), 6);
    }

    #[test]
    fn test_is_even() {
        assert!(is_even(2));
        assert!(!is_even(3));
    }

    #[test]
    fn test_will_fail() {
        assert_eq!(add(2, 2), 5, "fail!");
    }
}
"""
    
    with open(os.path.join(project_dir, "src", "lib.rs"), "w") as f:
        f.write(lib_rs_content)
    
    return temp_dir, project_dir, project_name

def test_cargo_ci_tool():
    work_dir, project_dir, project_name = create_test_rust_project()
    try:
        output_dir = os.path.join(work_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        config = {
            "workdir": work_dir,
            "repo": f"local/{project_name}",  
            "merge_commit": "HEAD",  
            "patch": "",  
            "output_dir": output_dir
        }
        
        global RUST_BASE_ENV
        RUST_BASE_ENV = {f"local/{project_name}": []}
        
        class TestCargoCITool(CargoCITool):
            def _build_repo_base_env(self):
                return ["#!/bin/bash"]
            
            def _build_eval_script(self):
                return ["#!/bin/bash"]
        
        cargo_tool = TestCargoCITool(config)
        cargo_tool.task.target_dir = project_dir
        
        log_file = os.path.join(output_dir, "cargo_test.log")
        result = cargo_tool.run_ci(log_file)
        
        print("Cargo Test Results:")
        print(f"Return code: {result['returncode']}")
        print("\nPassed tests:")
        for test in result['test_results']['passed']:
            print(f"✓ {test}")
        
        print("\nFailed tests:")
        for test in result['test_results']['failed']:
            print(f"✗ {test}")
            # if test in result['test_results']['failure_details']:
            #     print(f"  Details: {result['test_results']['failure_details'][test]}")
        
        print("\nIgnored tests:")
        for test in result['test_results']['ignored']:
            print(f"- {test}")
        
        with open(os.path.join(output_dir, "results.json"), "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\nDetailed results saved to {os.path.join(output_dir, 'results.json')}")
        
        return result
    
    finally:
        shutil.rmtree(work_dir)
        pass

if __name__ == "__main__":
    test_cargo_ci_tool()