# 개발 도구 (Development Tools)

## 📋 프로젝트 정보

- **카테고리**: Development Support
- **설명**: 코드 분석 및 개선 도구
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
python run_dev_tools.py

# 또는 루트에서 직접 실행
cd ../..
python analyze_architecture.py
```

## 📁 프로젝트 구조

```
dev-tools/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 이 파일
├── requirements.txt     # 의존성
└── run_dev_tools.py  # 실행 스크립트
```

## 📦 주요 파일

1. `analyze_architecture.py`
2. `analyze_all_shinsegye_projects.py`
3. `code_quality_improver.py`
4. `code_quality_master.py`
5. `comprehensive_file_analyzer.py`
6. `comprehensive_project_analyzer.py`
7. `detailed_technical_report.py`
8. `fix_docstring_quotes.py`
9. `fix_duplicate_orders.py`
10. `intelligent_code_refactor.py`
... 외 8개 파일

## 🔗 관련 문서

- [CODE_QUALITY_FINAL_SUMMARY.md](../../CODE_QUALITY_FINAL_SUMMARY.md)
- [CODE_REVIEW_REPORT.md](../../CODE_REVIEW_REPORT.md)

## 🐳 Docker

```bash
# Docker로 실행
docker build -f ../../dockerfiles/Dockerfile.dev-tools -t dev-tools ../..
docker run -p None:None dev-tools
```

## 📝 참고사항

- 실제 소스 파일은 루트 디렉토리에 위치하며, src/ 폴더에는 심볼릭 링크로 연결됩니다.
- 이 프로젝트는 신세계(Shinsegye) 통합 시스템의 일부입니다.
- 전체 시스템 문서는 [루트 README](../../README.md)를 참고하세요.

---

**생성일**: 2025년 12월 05일  
**버전**: 1.0.0
