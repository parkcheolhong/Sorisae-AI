# 테스트/검증 (Testing & Validation)

## 📋 프로젝트 정보

- **카테고리**: Development Support
- **설명**: 테스트 및 검증 도구
- **포트**: None

## 🚀 빠른 시작

### 설치
```bash
# 루트 디렉토리에서
pip install -r requirements.txt
```

### 실행
```bash
# 이 프로젝트 실행
python run_testing.py

# 또는 루트에서 직접 실행
cd ../..
python advanced_syntax_fixer.py
```

## 📁 프로젝트 구조

```
testing/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 이 파일
├── requirements.txt     # 의존성
└── run_testing.py  # 실행 스크립트
```

## 📦 주요 파일

1. `advanced_syntax_fixer.py`
2. `auto_syntax_validator.py`
3. `check_missing_programs.py`
4. `commissioning_test.py`
5. `completion_checker.py`
6. `project_syntax_checker.py`
7. `quick_validate.py`
8. `run_full_system_test.py`
9. `syno_check.py`
10. `syntax_checker.py`
... 외 6개 파일

## 🔗 관련 문서

- [COMPREHENSIVE_TEST_REPORT.md](../../COMPREHENSIVE_TEST_REPORT.md)
- [TEST_RESULTS_REPORT.md](../../TEST_RESULTS_REPORT.md)

## 🐳 Docker

```bash
# Docker로 실행
docker build -f ../../dockerfiles/Dockerfile.testing -t testing ../..
docker run -p None:None testing
```

## 📝 참고사항

- 실제 소스 파일은 루트 디렉토리에 위치하며, src/ 폴더에는 심볼릭 링크로 연결됩니다.
- 이 프로젝트는 신세계(Shinsegye) 통합 시스템의 일부입니다.
- 전체 시스템 문서는 [루트 README](../../README.md)를 참고하세요.

---

**생성일**: 2025년 12월 05일  
**버전**: 1.0.0
