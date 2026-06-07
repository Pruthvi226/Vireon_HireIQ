import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth.auth_service import init_auth_db, seed_demo_users


if __name__ == "__main__":
    init_auth_db()
    result = seed_demo_users()
    print(result["message"])
    for email in result["users"]:
        print(email)
