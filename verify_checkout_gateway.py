import requests
import uuid
import sys

BASE = "http://127.0.0.1:8000/api/marketplace"
AUTH_BASE = "http://127.0.0.1:8000/api/auth"

def make_user():
    uid = uuid.uuid4().hex[:8]
    email = f"gw_v_{uid}@example.com"
    pw = "Passw0rd!123"
    requests.post(f"{AUTH_BASE}/signup", json={"email": email, "username": f"gw_{uid}", "password": pw, "full_name": "GW"})
    r = requests.post(f"{AUTH_BASE}/login", data={"username": email, "password": pw})
    r.raise_for_status()
    return r.json()["access_token"]

all_pass = True
for i in range(1, 3):
    try:
        token = make_user()
        catalog = requests.get(f"{BASE}/v1/subscription/catalog", headers={"Authorization": f"Bearer {token}"}).json()
        first = next((c for c in catalog if c.get("active_plan")), None)
        if not first:
            print(f"PASS{i} FAIL: no catalog item with active_plan")
            all_pass = False
            continue
        pc = first["product_code"]
        plc = first["active_plan"]["plan_code"]
        r = requests.post(
            f"{BASE}/v1/billing/checkout/sessions",
            json={
                "provider": "stripe",
                "product_code": pc,
                "plan_code": plc,
                "success_url": "http://127.0.0.1:3000/marketplace/subscription?checkout=success",
                "cancel_url":  "http://127.0.0.1:3000/marketplace/subscription?checkout=cancel",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        j = r.json()
        sid = j.get("session_id", "")
        sim = j.get("verification_simulated")
        mode = j.get("verification_mode", "")
        url_ok = bool(j.get("checkout_url", ""))
        status_ok = r.status_code == 200
        ok = status_ok and bool(sid) and url_ok
        flag = "PASS" if ok else "FAIL"
        print(f"{flag}{i} http={r.status_code} product={pc} plan={plc}")
        print(f"  session_id={sid[:30]}... simulated={sim} mode={mode} checkout_url_ok={url_ok}")
        if not ok:
            all_pass = False
            print(f"  raw={j}")
    except Exception as e:
        print(f"PASS{i} EXCEPTION: {e}")
        all_pass = False

print("ALL_PASS=", all_pass)
sys.exit(0 if all_pass else 1)
