"""
Reset a forgotten password from the machine running the app.

The web form can only *change* a password (it asks for the current one), because
there is no email service to prove ownership. Whoever can run commands on this
machine already controls the data, so a local reset is the safe recovery path.

    python -m backend.services.reset_password_cli you@example.com
"""

from __future__ import annotations

import getpass
import sys

from backend.database import get_collection
from backend.routes.auth import _create_password_hash, _find_user_by_email


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python -m backend.services.reset_password_cli <email>")
        return 2
    email = argv[0].strip().lower()

    users = get_collection("users")
    if users is None:
        print("MongoDB isn't reachable. Start it, then try again.")
        return 1
    user = _find_user_by_email(users, email)
    if not user:
        print(f"No account found for {email}.")
        return 1

    new = getpass.getpass("New password (8+ characters): ")
    if len(new) < 8:
        print("Password must be at least 8 characters.")
        return 1
    if getpass.getpass("Repeat new password: ") != new:
        print("Passwords don't match.")
        return 1

    users.update_one({"_id": user["_id"]}, {"$set": {"hashed_password": _create_password_hash(new)}})
    print(f"Password reset for {email}. Sign in with the new password.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
