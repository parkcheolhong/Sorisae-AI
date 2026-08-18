# 의존성 설치/보안 최종 판정 체크리스트 (2026-08-18)

상태: 실패

목적:
- Node 보안 우선 패치 적용 후 재검증
- GPU 의존성 분리 설치 계획 실행 및 설치 성공/실패 확정
- 설치/보안 정합성 근거를 고정 문서로 남김

범위:
- Node 프로젝트 6개
- Python 메인 venv + GPU 고난도 패키지(auto-gptq/autoawq/xformers/bitsandbytes)

## 1) Node 보안 우선 패치 적용

- [x] 각 Node 프로젝트에 `npm audit fix --omit=dev` 실행
- 근거: frontend__frontend__audit-fix.log
- 근거: mobile-nadotongryoksa__audit-fix.log
- 근거: apps__mobile-nadotongryoksa__audit-fix.log
- 근거: apps__mobile-stock-ai__audit-fix.log
- 근거: addons__node_service__audit-fix.log
- 근거: addons__nextjs_react__audit-fix.log

## 2) Node 보안 재검증 결과

- [x] 프로젝트별 잔여 취약점 집계 완료
- 근거: frontend__frontend__audit.json
- 근거: mobile-nadotongryoksa__audit.json
- 근거: apps__mobile-nadotongryoksa__audit.json
- 근거: apps__mobile-stock-ai__audit.json
- 근거: addons__node_service__audit.json
- 근거: addons__nextjs_react__audit.json

### 비브레이킹 순차 패치 Wave 1 적용

- [x] addons__node_service `express` 4.21.1 -> 4.22.2 상향
- [x] addons__nextjs_react `next` 16.2.6 -> 16.3.1 상향
- [x] apps__mobile-stock-ai `brace-expansion` override 1.1.18 적용
- 근거: post-nonbreaking-wave1/addons__node_service__audit.json
- 근거: post-nonbreaking-wave1/addons__nextjs_react__audit.json
- 근거: post-nonbreaking-wave1/apps__mobile-stock-ai__audit.json
- 근거: post-nonbreaking-wave1/mobile-nadotongryoksa__audit.json
- 근거: post-nonbreaking-wave1/apps__mobile-nadotongryoksa__audit.json

### 잔여 취약점 요약 (post-fix)

| Project | Critical | High | Moderate | Low | Total |
|---|---:|---:|---:|---:|---:|
| frontend__frontend | 0 | 0 | 0 | 0 | 0 |
| mobile-nadotongryoksa | 0 | 10 | 0 | 0 | 10 |
| apps__mobile-nadotongryoksa | 0 | 10 | 0 | 0 | 10 |
| apps__mobile-stock-ai | 0 | 10 | 0 | 0 | 10 |
| addons__node_service | 0 | 0 | 0 | 0 | 0 |
| addons__nextjs_react | 0 | 0 | 0 | 0 | 0 |

- [ ] High/Moderate 취약점 0건 달성
- 근거: 총 잔여 취약점 30건(High 30, Moderate 0)

## 3) Python 설치 정합성

- [x] 메인 venv 의존성 무결성 점검 통과
- 근거: `python -m pip check` => `No broken requirements found.`

## 4) GPU 의존성 완전설치(분리 플랜)

- [x] 분리 설치 플랜 문서 생성 완료
- 근거: gpu-deps-linux-cuda-plan.md
- 근거: gpu-deps-python311-venv-plan.md

- [x] 현재 Windows/Python3.13 환경 설치 시도 기록 완료
- 근거: gpu-deps-windows-attempt.log

- [x] Python 3.11 분리 venv 실행 완료
- 근거: gpu-py311-split-install.log

### GPU 패키지 설치 상태 (현재 메인 venv, Python 3.13)

- [x] 성공: torch==2.13.0
- [ ] 실패: auto-gptq==0.7.1
- [ ] 실패: autoawq==0.2.9
- [ ] 실패: xformers==0.0.35
- [ ] 실패: bitsandbytes==0.50.1

실패 근거:
- auto-gptq: metadata/build 실패
- autoawq: `triton` 패키지 해석 실패(플랫폼/조합 제약)
- 결과적으로 GPU 고난도 의존성은 Linux/CUDA 또는 Python 3.11 분리 venv에서 처리 필요

### GPU 패키지 설치 상태 (분리 venv, Python 3.11)

- [x] 성공: torch==2.13.0
- [x] 성공: bitsandbytes==0.50.1
- [x] 성공: xformers==0.0.35
- [x] 성공: auto-gptq==0.7.1
- [ ] 실패: autoawq==0.2.9 (패키지 미발견)
- [x] pip check 통과

근거:
- gpu-py311-split-install.log

## 5) 최종 판정

- [ ] 완료됨
- 근거: Node 잔여 High/Moderate 취약점 존재 + autoawq 미설치

최종 판정:
- 실패
