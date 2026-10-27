from werkzeug.security import check_password_hash

from auth import ADMIN_PASSWORD, db_query

print("ADMIN_PASSWORD loaded:", bool(ADMIN_PASSWORD), "| length:", len(ADMIN_PASSWORD or ""))
row = db_query("SELECT password_hash, role FROM users WHERE username = 'admin'", one=True)
print("admin row found:", bool(row), "| role:", row["role"] if row else None)
if row and ADMIN_PASSWORD:
    print("DB password matches .env:", check_password_hash(row["password_hash"], ADMIN_PASSWORD))