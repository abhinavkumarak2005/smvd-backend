import subprocess

result = subprocess.run(
    ["pytest", "tests/integration/test_admin_workflow.py"], 
    capture_output=True, 
    text=True
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
