import os

print("TARGET_USERNAME:", os.environ.get("TARGET_USERNAME"))
print("TARGET_PASSWORD:", os.environ.get("TARGET_PASSWORD"))
print("All ENV starting with TARGET:")
for k, v in os.environ.items():
    if k.startswith("TARGET_"):
        print(f"  {k}: {v}")
