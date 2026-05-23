"""소리새 engines120 전체 슬롯 능력 분석 스캐너"""
from pathlib import Path

engines_dir = Path('/app/backend/services/shinsegye/engines120')
slots = sorted(engines_dir.glob('slot*.py'))
print(f'총 슬롯 파일: {len(slots)}개\n')

for s in slots:
    try:
        txt = s.read_text(encoding='utf-8', errors='ignore')
        lines = txt.splitlines()
        classes = [
            l.replace('class ', '').split('(')[0].strip()
            for l in lines if l.strip().startswith('class ')
        ][:4]
        # 첫 번째 의미있는 주석/docstring
        desc = ''
        for l in lines[:15]:
            stripped = l.strip().strip('"""').strip("'''").strip('#').strip()
            if stripped and not stripped.startswith('import') and not stripped.startswith('from') and len(stripped) > 5:
                desc = stripped[:80]
                break
        print(f'{s.name[:52]:52s} classes={classes}')
        if desc:
            print(f'  desc: {desc}')
    except Exception as e:
        print(f'{s.name}: ERROR {e}')
