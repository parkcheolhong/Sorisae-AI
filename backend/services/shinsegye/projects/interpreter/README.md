# 나도 통역사 (Multi-Language Interpreter)

## 📋 프로젝트 정보

- **카테고리**: Language Processing
- **설명**: 실시간 13개 언어 통역 시스템
- **포트**: 5051

## 🚀 빠른 시작

### 설치
```bash
# 루트 디렉토리에서
pip install -r requirements.txt
```

### 실행
```bash
# 이 프로젝트 실행
python run_interpreter.py

# 또는 루트에서 직접 실행
cd ../..
python hybrid_conversation_translator.py
```

## 📁 프로젝트 구조

```
interpreter/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 이 파일
├── requirements.txt     # 의존성
└── run_interpreter.py  # 실행 스크립트
```

## 📦 주요 파일

1. `hybrid_conversation_translator.py`
2. `hybrid_interpreter_system.py`
3. `multilingual_system.py`
4. `sorisae_interpreter.py`
5. `sorisae_multilingual_support.py`
6. `sorisae_southeast_asia_translator.py`

## 🔗 관련 문서

- [INTERPRETER_GUIDE.md](../../INTERPRETER_GUIDE.md)
- [SORISAE_LANGUAGE_GUIDE.md](../../SORISAE_LANGUAGE_GUIDE.md)

## 🐳 Docker

```bash
# Docker로 실행
docker build -f ../../dockerfiles/Dockerfile.interpreter -t interpreter ../..
docker run -p 5051:5051 interpreter
```

## 📝 참고사항

- 실제 소스 파일은 루트 디렉토리에 위치하며, src/ 폴더에는 심볼릭 링크로 연결됩니다.
- 이 프로젝트는 신세계(Shinsegye) 통합 시스템의 일부입니다.
- 전체 시스템 문서는 [루트 README](../../README.md)를 참고하세요.

---

**생성일**: 2025년 12월 05일  
**버전**: 1.0.0
