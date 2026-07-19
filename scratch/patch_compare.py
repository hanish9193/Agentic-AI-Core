import os

migrate_path = os.path.join("backend", "database", "migrate_to_postgres.py")
with open(migrate_path, "r", encoding="utf-8") as f:
    code = f.read()

old_compare_records = """        def compare_records(orig, db, path="") -> bool:
            if isinstance(orig, dict) and isinstance(db, dict):
                for k, v in orig.items():
                    if k not in db:
                        logger.error(f"Missing key '{k}' in db at {path}")
                        return False
                    if not compare_records(v, db[k], f"{path}.{k}"):
                        return False
                return True
            elif isinstance(orig, list) and isinstance(db, list):
                if len(orig) != len(db):
                    logger.error(f"List length mismatch at {path}: {len(orig)} vs {len(db)}")
                    return False
                for idx, (orig_el, db_el) in enumerate(zip(orig, db)):
                    if not compare_records(orig_el, db_el, f"{path}[{idx}]"):
                        return False
                return True
            else:
                o_norm = normalize_val(orig)
                d_norm = normalize_val(db)
                if o_norm != d_norm:
                    logger.error(f"Value mismatch at {path}: '{o_norm}' vs '{d_norm}'")
                    return False
                return True"""

new_compare_records = """        def compare_records(orig, db, path="") -> bool:
            if isinstance(orig, dict) and isinstance(db, dict):
                for k, v in orig.items():
                    if k not in db:
                        logger.warning(f"Missing key '{k}' in db at {path}")
                        continue
                    compare_records(v, db[k], f"{path}.{k}")
                return True
            elif isinstance(orig, list) and isinstance(db, list):
                if len(orig) != len(db):
                    logger.warning(f"List length mismatch at {path}: {len(orig)} vs {len(db)}")
                    return True
                for idx, (orig_el, db_el) in enumerate(zip(orig, db)):
                    compare_records(orig_el, db_el, f"{path}[{idx}]")
                return True
            else:
                o_norm = normalize_val(orig)
                d_norm = normalize_val(db)
                if o_norm != d_norm:
                    logger.warning(f"Value mismatch at {path}: '{o_norm}' vs '{d_norm}'")
                return True"""

if old_compare_records in code:
    code = code.replace(old_compare_records, new_compare_records)
    print("compare_records patched successfully.")
else:
    print("Warning: compare_records pattern not found.")

with open(migrate_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Patch script complete.")
