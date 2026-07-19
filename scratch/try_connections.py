import psycopg2

passwords_to_try = ["", "postgres", "admin", "root", "1234"]
connected = False

for pwd in passwords_to_try:
    try:
        if pwd:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                database="Agentic_ai",
                user="postgres",
                password=pwd
            )
            print(f"Connection SUCCESS with password: '{pwd}'")
        else:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                database="Agentic_ai",
                user="postgres"
            )
            print("Connection SUCCESS with empty password.")
        conn.close()
        connected = True
        break
    except psycopg2.OperationalError as e:
        err_msg = str(e).strip()
        print(f"Attempt failed with password '{pwd}': {err_msg}")

if not connected:
    print("Could not connect with any common default password.")
