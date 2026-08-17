import json
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import traceback

BASE = 'http://127.0.0.1:3005'
USER = 'ui.admin.round@devanalysis.local'
PWD = 'RoundUi!20260426'

def req(method, url, data=None, headers=None, timeout=25):
    headers = headers or {}
    body = None
    if data is not None:
        body = data.encode('utf-8') if isinstance(data, str) else data
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')
    except Exception:
        return -1, ''

def get_token():
    payload = urllib.parse.urlencode({'username': USER, 'password': PWD})
    code, text = req('POST', BASE + '/api/proxy', data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if code != 200:
        return None
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    token = parsed.get('access_token')
    return token if isinstance(token, str) and token.strip() else None

def get_status(path, token):
    code, _ = req('GET', BASE + path, headers={'Authorization': 'Bearer ' + token})
    return code

try:
    overall_pass = True
    for cycle in range(1, 3):
        print(f'=== CYCLE {cycle} : backend restart ===')
        r = subprocess.run(['docker', 'compose', 'restart', 'backend'], capture_output=True, text=True)
        if r.stdout:
            print(r.stdout.rstrip())
        if r.stderr:
            print(r.stderr.rstrip())

        cycle_recovered = False
        for round_no in range(1, 9):
            token = get_token()
            if not token:
                print(f'CYCLE {cycle} ROUND {round_no} LOGIN=FAIL')
                continue

            cap_summary = get_status('/api/admin/orchestrator/capabilities/summary', token)
            sec_guard = get_status('/api/admin/orchestrator/capabilities/security-guard', token)
            self_run = get_status('/api/admin/workspace-self-run-record?latest=true', token)
            sys_set = get_status('/api/admin/system-settings', token)

            round_pass = (cap_summary == 200 and sec_guard == 200 and self_run == 204 and sys_set == 200)
            if round_pass:
                cycle_recovered = True

            print(
                f'CYCLE {cycle} ROUND {round_no} '
                f'capability_summary={cap_summary} '
                f'security_guard={sec_guard} '
                f'self_run_latest={self_run} '
                f'system_settings={sys_set} '
                f'round_pass={round_pass}'
            )

        print(f'CYCLE {cycle} RECOVERED={cycle_recovered}')
        if not cycle_recovered:
            overall_pass = False

    print(f'FINAL OVERALL_PASS={overall_pass}')
except Exception:
    traceback.print_exc()
    print('FINAL OVERALL_PASS=False (script_exception)')
