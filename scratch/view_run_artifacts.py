import os
import json

execution_id = "dd76e3a0-753d-4684-b1f5-4ae7374a006f"
artifact_dir = os.path.join("backend", "playwrightt", "public", "artifacts", execution_id)

if not os.path.exists(artifact_dir):
    print(f"Directory {artifact_dir} does not exist.")
else:
    print(f"Contents of {artifact_dir}:", os.listdir(artifact_dir))
    
    metadata_path = os.path.join(artifact_dir, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            print("Metadata content:")
            print(json.dumps(json.load(f), indent=2))
            
    log_path = os.path.join(artifact_dir, "execution.log")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            print("Logs:")
            print(f.read())
