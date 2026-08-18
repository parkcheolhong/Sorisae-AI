# GPU 의존성 분리 설치 플랜 (Windows 유지 + Python 3.11 별도 venv)

## 목표
- 현재 기본 .venv(3.13)는 유지하고, GPU 전용 .venv-gpu311에서만 고난도 의존성 관리

## 절차
1. Python 3.11 설치 확인
2. `py -3.11 -m venv .venv-gpu311`
3. `.venv-gpu311\Scripts\python.exe -m pip install -U pip setuptools wheel`
4. `.venv-gpu311\Scripts\python.exe -m pip install torch==2.4.*`
5. `.venv-gpu311\Scripts\python.exe -m pip install bitsandbytes==0.50.1 xformers==0.0.35 autoawq==0.2.9 auto-gptq==0.7.1`
6. `.venv-gpu311\Scripts\python.exe -m pip check`
7. import smoke test 수행

## 통과 기준
- GPU 전용 venv에서 설치/검증 성공
- 메인 venv(3.13)와 독립성 유지
