import json
import requests

backend = "http://127.0.0.1:8000"
base = "http://127.0.0.1:3005"

login = requests.post(
    f"{backend}/api/auth/login",
    data={"username": "119cash@naver.com", "password": "space0215@"},
    timeout=15,
)
login.raise_for_status()
token = login.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

print("=== system-settings x5 ===")
for i in range(1, 6):
    try:
        r = requests.get(f"{base}/api/admin/system-settings", headers=headers, timeout=30)
        body_preview = r.text[:180].replace("\n", " ")
        print(f"system-settings#{i} http={r.status_code} body={body_preview}")
    except Exception as exc:
        print(f"system-settings#{i} EXC {type(exc).__name__}: {exc}")

print("=== orchestrate chat x3 ===")
chat_headers = {**headers, "Content-Type": "application/json"}
payload = {"task": "health check", "message": "quick orchestration ping", "mode": "balanced"}
for i in range(1, 4):
    try:
        r = requests.post(
            f"{base}/api/llm/orchestrate/chat",
            headers=chat_headers,
            data=json.dumps(payload),
            timeout=70,
        )
        preview = r.text[:220].replace("\n", " ")
        print(f"chat#{i} http={r.status_code} body={preview}")
    except Exception as exc:
        print(f"chat#{i} EXC {type(exc).__name__}: {exc}")
