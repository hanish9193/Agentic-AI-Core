import json
import os
from backend.services.vault_service import VaultService

vault_path = os.path.join("backend", "database", "vault.json")

if os.path.exists(vault_path):
    try:
        vs = VaultService()
        with open(vault_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("Vault content (raw and decrypted):")
        print("=" * 60)
        for pid, creds in data.items():
            u, p = vs.get_credentials(pid)
            print(f"Project ID: {pid}")
            print(f"  User (decrypted): {u}")
            print(f"  Pass (decrypted): {p}")
            print(f"  Raw: {creds}")
            print("-" * 40)
    except Exception as e:
        print(f"Failed to read vault: {e}")
else:
    print("vault.json does not exist.")
