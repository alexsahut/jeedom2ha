import subprocess
import sys
import os

def test_runtime_imports():
    print("Testing daemon startup with actual Jeedom command structure...")
    
    # Simulate: python3 resources/daemon/main.py --help
    # This checks if imports are valid without starting the full async loop
    cmd = [sys.executable, "resources/daemon/main.py", "--help"]
    
    # We run from project root, NO PYTHONPATH set (main.py must handle its own path)
    env = os.environ.copy()
    if "PYTHONPATH" in env:
        del env["PYTHONPATH"]
        
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        env=env,
        cwd=os.getcwd()
    )
    
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")
    
    if result.returncode == 0:
        print("SUCCESS: Daemon started and printed help. Imports are valid.")
    else:
        print(f"FAILURE: Daemon failed to start (exit code {result.returncode})")
        if "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr:
            print("Detected Import Error!")
        sys.exit(1)

if __name__ == "__main__":
    test_runtime_imports()
