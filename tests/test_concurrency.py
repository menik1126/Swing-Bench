import unittest
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

class TestPortAllocation(unittest.TestCase):
    def setUp(self):
        global mutex, available_group, port_start, ports_per_instance, used_ports
        mutex = Lock()
        available_group = [0, 1, 2, 3]  # Available group indexes
        port_start = 8000
        ports_per_instance = 2
        used_ports = set()
        
    def test_port_allocation_issue(self):
        """Test that demonstrates the issue with port allocation in the original code."""
        def get_ports():
            with mutex:
                if not available_group:
                    raise RuntimeError("No available port group")
                group_index = available_group.pop(0)
                start_port = port_start + group_index * ports_per_instance
                ports = list(range(start_port, start_port + ports_per_instance))
                used_ports.update(ports)        
                return ports
                
        def release_ports(ports):
            with mutex:
                for port in ports:
                    if port in used_ports:
                        used_ports.remove(port)
                if ports[0] >= port_start and (ports[0] - port_start) % ports_per_instance == 0:
                    group_index = (ports[0] - port_start) // ports_per_instance
                    if ports == list(range(ports[0], ports[0] + ports_per_instance)):
                        available_group.append(group_index)
                    else:
                        raise ValueError("The group is not consequent")
                else:
                    raise ValueError("Invalid port group")
        
        # Mock task objects that record port allocation
        class Task:
            def __init__(self, id):
                self.id = id
                
            def run_ci(self, port_pool):
                # Simulate work with a small delay to ensure overlapping execution
                time.sleep(0.01)
                # Record which ports were used for this task
                task_ports[self.id] = port_pool.ports.copy()  # Create a copy to avoid reference issues
                return [True, None]  # Mock result
        
        class PortPool:
            def __init__(self, ports):
                self.ports = ports
        
        # Create a collection to track which ports were used by each task
        task_ports = {}
        tasks = [Task(i) for i in range(3)]
        
        # Mock progress bar
        pbar = MagicMock()
        
        # Lists to track results
        succeeded = []
        failed = []
        
        concurrency = 3
        
        # -------------------------------
        # DEMONSTRATE THE ISSUE
        # -------------------------------
        # In the problematic implementation, we get one set of ports
        # and use it for all tasks
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            ports = get_ports()  # Single port allocation for all tasks
            original_ports = ports.copy()  # Keep a copy of the original ports
            
            # Submit all tasks with the same ports
            futures = {executor.submit(task.run_ci, PortPool(ports)): task for task in tasks}
            
            # Wait for completion and process results
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    succeeded.append(task)
                except Exception as e:
                    failed.append(task)
                finally:
                    pbar.update(1)
                    # We need to check if these are still the original ports before releasing
                    if ports == original_ports:
                        release_ports(ports)
        
        # Verify all tasks used the same ports
        unique_port_sets = set(tuple(ports) for ports in task_ports.values())
        self.assertEqual(len(unique_port_sets), 1, 
                         "All tasks should have used the same ports in the problematic implementation")
        
        # Verify the first set of ports was released (group returned to available)
        self.assertIn(0, available_group, 
                      "The port group should have been released back to available_group")
        
        # -------------------------------
        # DEMONSTRATE THE CORRECT APPROACH
        # -------------------------------
        # Reset for testing the correct implementation
        self.setUp()
        task_ports = {}
        succeeded = []
        failed = []
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures_with_ports = {}
            
            # Allocate different ports for each task
            for task in tasks:
                task_specific_ports = get_ports()
                futures_with_ports[executor.submit(task.run_ci, PortPool(task_specific_ports))] = (task, task_specific_ports)
            
            # Process results and release the correct ports for each task
            for future in as_completed(futures_with_ports):
                task, task_specific_ports = futures_with_ports[future]
                try:
                    result = future.result()
                    succeeded.append(task)
                except Exception as e:
                    failed.append(task)
                finally:
                    pbar.update(1)
                    release_ports(task_specific_ports)
        
        # Verify each task used different ports
        unique_port_sets = set(tuple(ports) for ports in task_ports.values()) 
        self.assertEqual(len(unique_port_sets), len(tasks), 
                         "Each task should have used different ports in the correct implementation")
        
        # Verify all port groups were released
        self.assertEqual(len(available_group), 4, 
                         "All port groups should have been released back to available_group")

if __name__ == "__main__":
    unittest.main()