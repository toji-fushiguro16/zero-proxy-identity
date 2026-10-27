from werkzeug.security import generate_password_hash

from auth import ADMIN_PASSWORD, db_execute, init_db

if not ADMIN_PASSWORD:
    raise SystemExit("Set ADMIN_PASSWORD in backend/.env first")

init_db()
db_execute(
    "UPDATE users SET password_hash = ?, role = 'admin' WHERE username = 'admin'",
    (generate_password_hash(ADMIN_PASSWORD),),
)
print("Admin password updated from .env")