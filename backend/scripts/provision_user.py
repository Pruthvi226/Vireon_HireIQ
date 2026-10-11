"""Provision trusted staff locally, without placing passwords in shell history."""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auth.auth_service import init_auth_db, register_user
from schemas.auth_schema import RegisterRequest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=["ADMIN", "RECRUITER"], required=True)
    parser.add_argument("--company")
    args = parser.parse_args()
    password = getpass.getpass("Password (8+ characters, at most 72 UTF-8 bytes): ")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")
    payload = RegisterRequest(name=args.name, email=args.email, role=args.role,
                              company_name=args.company, password=password)
    init_auth_db()
    user = register_user(payload)
    print(f"Created {user['role']} account {user['email']}")
