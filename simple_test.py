print("Test running")
import sys
print(sys.path)
try:
    from src.policy_extractor import extract_policy
    print("Import successful")
except Exception as e:
    print(f"Import error: {e}")
print("Done")