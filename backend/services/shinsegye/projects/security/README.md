# 보안 시스템 (Security System)

## 📋 프로젝트 정보

- **카테고리**: Security & Analysis
- **설명**: 다층 보안 시스템
- **포트**: 5064

## 🚀 빠른 시작

### 설치
```bash
# 루트 디렉토리에서
pip install -r requirements.txt
```

### 실행
```bash
# 이 프로젝트 실행
python run_security.py

# 또는 루트에서 직접 실행
cd ../..
python advanced_security_system.py
```

## 📁 프로젝트 구조

```
security/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 이 파일
├── requirements.txt     # 의존성
└── run_security.py  # 실행 스크립트
```

## 📦 주요 파일

1. `advanced_security_system.py`
2. `biometric_security_system.py`
3. `hybrid_cyber_security_system.py`
4. `security_demo.py`
5. `security_key_manager.py`

## 🔗 관련 문서

- [SECURITY.md](../../SECURITY.md)
- [ACCESS_KEYS.md](../../ACCESS_KEYS.md)

## 🐳 Docker

```bash
# Docker로 실행
docker build -f ../../dockerfiles/Dockerfile.security -t security ../..
docker run -p 5064:5064 security
```

## 📝 참고사항

- 실제 소스 파일은 루트 디렉토리에 위치하며, src/ 폴더에는 심볼릭 링크로 연결됩니다.
- 이 프로젝트는 신세계(Shinsegye) 통합 시스템의 일부입니다.
- 전체 시스템 문서는 [루트 README](../../README.md)를 참고하세요.

---

**생성일**: 2025년 12월 05일  
**버전**: 1.0.0
