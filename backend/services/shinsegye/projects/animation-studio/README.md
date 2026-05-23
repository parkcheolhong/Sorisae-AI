# 애니메이션 스튜디오 (Animation Studio)

## 📋 프로젝트 정보

- **카테고리**: Creative Tools
- **설명**: AI 기반 애니메이션 제작
- **포트**: 5062

## 🚀 빠른 시작

### 설치
```bash
# 루트 디렉토리에서
pip install -r requirements.txt
```

### 실행
```bash
# 이 프로젝트 실행
python run_animation_studio.py

# 또는 루트에서 직접 실행
cd ../..
python animation_studio_demo.py
```

## 📁 프로젝트 구조

```
animation-studio/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 이 파일
├── requirements.txt     # 의존성
└── run_animation_studio.py  # 실행 스크립트
```

## 📦 주요 파일

1. `animation_studio_demo.py`
2. `demo_animation_voice_integration.py`
3. `sorisae_animation_studio_ultra.py`
4. `test_animation_voice_integration.py`

## 🔗 관련 문서


## 🐳 Docker

```bash
# Docker로 실행
docker build -f ../../dockerfiles/Dockerfile.animation-studio -t animation-studio ../..
docker run -p 5062:5062 animation-studio
```

## 📝 참고사항

- 실제 소스 파일은 루트 디렉토리에 위치하며, src/ 폴더에는 심볼릭 링크로 연결됩니다.
- 이 프로젝트는 신세계(Shinsegye) 통합 시스템의 일부입니다.
- 전체 시스템 문서는 [루트 README](../../README.md)를 참고하세요.

---

**생성일**: 2025년 12월 05일  
**버전**: 1.0.0
