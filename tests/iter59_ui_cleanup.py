import os

import pymongo
import requests
from dotenv import load_dotenv


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def run_cleanup():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"},
        timeout=30,
    )
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    role_names = {"UI QA Role Iter59", "UI QA Role Iter59-B"}
    role_ids = []
    roles = requests.get(f"{API}/admin/access/roles", headers=headers, timeout=30)
    roles.raise_for_status()
    for role in roles.json():
        if role.get("name") in role_names:
            role_ids.append(role["id"])

    users = requests.get(f"{API}/admin/admin-users", headers=headers, timeout=30)
    users.raise_for_status()
    for user in users.json():
        if user.get("email") == "iter59-ui-admin@example.com":
            requests.delete(f"{API}/admin/admin-users/{user['id']}", headers=headers, timeout=30)

    for rid in role_ids:
        requests.delete(f"{API}/admin/access/roles/{rid}", headers=headers, timeout=30)

    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    db.users.delete_many({"email": "iter59-ui-admin@example.com"})
    db.admin_roles.delete_many({"name": {"$in": list(role_names)}})
    print("iter59 ui cleanup done")


if __name__ == "__main__":
    run_cleanup()