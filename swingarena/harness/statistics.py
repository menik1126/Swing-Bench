import json
import os
import argparse
from collections import defaultdict
from typing import Dict, List, Set, Tuple

def compare_test_results(before: str, after: str) -> Dict:
    """
    Compare test results before and after applying a patch.
    
    Args:
        before: Path to the file containing test results before the patch
        after: Path to the file containing test results after the patch
        
    Returns:
        Dictionary with statistics about test changes
    """
    if not os.path.exists(before) or not os.path.exists(after):
        return {"error": "One or both files do not exist"}
    
    if before.endswith('.jsonl'):
        before_data = []
        with open(before, 'r') as f:
            for line in f:
                data = json.loads(line)
                before_data.append(data)
    else:
        with open(before, 'r') as f:
            before_data = json.load(f)

    if after.endswith('.jsonl'):
        after_data = []
        with open(after, 'r') as f:
            for line in f:
                data = json.loads(line)
                after_data.append(data)
    else:
        with open(after, 'r') as f:
            after_data = json.load(f)

    # Group instances by their ID
    before_instances = {}
    after_instances = {}
    
    if isinstance(before_data, list):
        for instance in before_data:
            if "instance_id" in instance:
                before_instances[instance["instance_id"]] = instance
    else:
        if "instance_id" in before_data:
            before_instances[before_data["instance_id"]] = before_data
    
    if isinstance(after_data, list):
        for instance in after_data:
            if "instance_id" in instance:
                after_instances[instance["instance_id"]] = instance
    else:
        if "instance_id" in after_data:
            after_instances[after_data["instance_id"]] = after_data
    
    # Compare results for each instance
    results = {}
    
    # Transition counters
    total_f2p = 0  # Failed to Passed
    total_f2f = 0  # Failed to Failed (remained failed)
    total_p2p = 0  # Passed to Passed (remained passed)
    total_p2f = 0  # Passed to Failed
    instances_with_f2p = set()  # Instances that have at least one F2P transition
    
    for instance_id in set(before_instances.keys()) | set(after_instances.keys()):
        before = before_instances.get(instance_id)
        after = after_instances.get(instance_id)
        
        if before is None or after is None:
            continue
        
        before_passed = set(before.get("test_results", {}).get("passed", []))
        before_failed = set(before.get("test_results", {}).get("failed", []))
        
        after_passed = set(after.get("test_results", {}).get("passed", []))
        after_failed = set(after.get("test_results", {}).get("failed", []))
        
        # Find tests that changed status
        newly_passed = after_passed - before_passed  # F2P (from failed to passed)
        newly_failed = after_failed - before_failed  # P2F (from passed to failed)
        fixed_tests = before_failed - after_failed   # Another way to count F2P
        
        # Count transitions
        f2p_count = len(before_failed & after_passed)
        f2f_count = len(before_failed & after_failed)
        p2p_count = len(before_passed & after_passed)
        p2f_count = len(before_passed & after_failed)
        
        # Update totals
        total_f2p += f2p_count
        total_f2f += f2f_count
        total_p2p += p2p_count
        total_p2f += p2f_count
        
        # Track instances with F2P transitions
        if f2p_count > 0:
            instances_with_f2p.add(instance_id)
        
        results[instance_id] = {
            "repo": before.get("repo"),
            "before_passed_count": len(before_passed),
            "before_failed_count": len(before_failed),
            "after_passed_count": len(after_passed),
            "after_failed_count": len(after_failed),
            "newly_passed": list(newly_passed),
            "newly_failed": list(newly_failed),
            "fixed_tests": list(fixed_tests),
            "f2p_count": f2p_count,
            "f2f_count": f2f_count,
            "p2p_count": p2p_count,
            "p2f_count": p2f_count
        }
    
    # Add transition statistics to the results
    results["_statistics"] = {
        "total_f2p": total_f2p,
        "total_f2f": total_f2f,
        "total_p2p": total_p2p,
        "total_p2f": total_p2f,
        "instances_with_f2p_count": len(instances_with_f2p),
        "instances_with_f2p": list(instances_with_f2p)
    }
    
    return results

def main():
    """
    Command-line interface for comparing test results.
    """
    parser = argparse.ArgumentParser(description='Compare test results before and after applying a patch.')
    parser.add_argument('--before', help='Path to the file containing test results before the patch')
    parser.add_argument('--after', help='Path to the file containing test results after the patch')
    parser.add_argument('--output', '-o', help='Path to save the comparison results (JSON format)')
    parser.add_argument('--summary', '-s', action='store_true', help='Print a summary of the comparison')
    
    args = parser.parse_args()
    
    results = compare_test_results(args.before, args.after)
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return 1
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")
    
    if args.summary or not args.output:
        stats = results.pop("_statistics", {})
        total_instances = len(results)
        total_before_passed = sum(instance["before_passed_count"] for instance in results.values())
        total_before_failed = sum(instance["before_failed_count"] for instance in results.values())
        total_after_passed = sum(instance["after_passed_count"] for instance in results.values())
        total_after_failed = sum(instance["after_failed_count"] for instance in results.values())
        total_newly_passed = sum(len(instance["newly_passed"]) for instance in results.values())
        total_newly_failed = sum(len(instance["newly_failed"]) for instance in results.values())
        total_fixed = sum(len(instance["fixed_tests"]) for instance in results.values())
        
        print("\nTest Comparison Summary:")
        print(f"Total instances: {total_instances}")
        print(f"Before: {total_before_passed} passed, {total_before_failed} failed")
        print(f"After:  {total_after_passed} passed, {total_after_failed} failed")
        print(f"Newly passed tests: {total_newly_passed}")
        print(f"Newly failed tests: {total_newly_failed}")
        print(f"Fixed tests: {total_fixed}")
        
        # Print transition statistics
        print("\nTest Transition Statistics:")
        print(f"Failed to Passed (F2P): {stats.get('total_f2p', 0)}")
        print(f"Failed to Failed (F2F): {stats.get('total_f2f', 0)}")
        print(f"Passed to Passed (P2P): {stats.get('total_p2p', 0)}")
        print(f"Passed to Failed (P2F): {stats.get('total_p2f', 0)}")
        print(f"Instances with F2P transitions: {stats.get('instances_with_f2p_count', 0)}")
        
        # Show some examples of changed tests if available
        for instance_id, data in results.items():
            if data["newly_passed"] or data["newly_failed"] or data["fixed_tests"]:
                print(f"\nChanges in instance {instance_id} ({data['repo']}):")
                if data["newly_passed"]:
                    print(f"  Newly passed: {', '.join(data['newly_passed'][:3])}" + 
                          (f" and {len(data['newly_passed']) - 3} more" if len(data['newly_passed']) > 3 else ""))
                if data["newly_failed"]:
                    print(f"  Newly failed: {', '.join(data['newly_failed'][:3])}" + 
                          (f" and {len(data['newly_failed']) - 3} more" if len(data['newly_failed']) > 3 else ""))
                if data["fixed_tests"]:
                    print(f"  Fixed tests: {', '.join(data['fixed_tests'][:3])}" + 
                          (f" and {len(data['fixed_tests']) - 3} more" if len(data['fixed_tests']) > 3 else ""))
                break  # Just show one example
    
    return 0

if __name__ == "__main__":
    exit(main())

# python -m swebench.harness.statistics \
#     --before report/20250325_100532/evaluation.jsonl \
#     --after report/20250326_001405/evaluation.jsonl \
#     --output output.json \
#     --summary