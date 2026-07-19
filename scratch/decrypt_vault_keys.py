import sys
import os

# Add project root to sys.path so we can import backend packages
sys.path.append(os.getcwd())

from backend.services.vault_service import VaultService

vs = VaultService()
vault_data = vs._read_vault()
print(f"Total projects in vault: {len(vault_data)}")

for pid in vault_data.keys():
    try:
        username, password = vs.get_credentials(pid)
        if username or password:
            print(f"Project ID: {pid} | Username: {username} | Password: {password}")
    except Exception as e:
        print(f"Project ID: {pid} | Decrypt error: {e}")
