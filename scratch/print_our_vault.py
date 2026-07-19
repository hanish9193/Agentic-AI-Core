import sys
import os
sys.path.append(os.getcwd())

from backend.services.vault_service import VaultService

project_id = "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"
u, p = VaultService().get_credentials(project_id)

print(f"Decrypted credentials for project {project_id}:")
print(f"  Username: {u}")
print(f"  Password: {p}")
