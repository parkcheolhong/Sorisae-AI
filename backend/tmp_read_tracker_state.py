import json
import subprocess

from backend.tmp_hard_gate_paths import hard_gate_result_path

RESULT_PATH = hard_gate_result_path()


def main() -> None:
    payload = {'result_exists': RESULT_PATH.exists()}
    if RESULT_PATH.exists():
        data = json.loads(RESULT_PATH.read_text(encoding='utf-8'))
        payload['tracker_state'] = data.get('tracker_state')
        payload['updated_at'] = data.get('updated_at')
        checkpoints = data.get('checkpoints') or []
        payload['last_checkpoint'] = checkpoints[-1] if checkpoints else None
    ps = subprocess.check_output(['ps', '-ef'], text=True)
    payload['processes'] = [
        line for line in ps.splitlines()
        if 'backend.tmp_run_hard_gate_consistency' in line or 'backend.tmp_check_hard_gate_progress' in line
    ]
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == '__main__':
    main()
