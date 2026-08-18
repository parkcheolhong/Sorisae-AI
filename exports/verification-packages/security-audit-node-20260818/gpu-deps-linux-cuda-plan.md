# GPU 의존성 분리 설치 플랜 (Linux/CUDA)

## 목표
- auto-gptq, autoawq, xformers, bitsandbytes를 CUDA 가능한 Linux 환경에서 설치/검증

## 권장 베이스라인
- OS: Ubuntu 22.04+
- Python: 3.11 (권장)
- CUDA: 12.1+ (드라이버/런타임 일치)
- PyTorch: CUDA 빌드

## 절차
1. `python3.11 -m venv .venv-gpu && source .venv-gpu/bin/activate`
2. `pip install -U pip setuptools wheel`
3. `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`
4. `pip install --no-cache-dir bitsandbytes==0.50.1 xformers==0.0.35`
5. `pip install --no-cache-dir autoawq==0.2.9`
6. `pip install --no-cache-dir auto-gptq==0.7.1`
7. `python -c "import torch,auto_gptq,awq,bitsandbytes,xformers; print('ok')"`

## 통과 기준
- import 검증 통과
- `pip check` 통과
