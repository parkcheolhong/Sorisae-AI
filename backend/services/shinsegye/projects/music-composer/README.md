# 작사/작곡 (Music Composer)

## 📋 프로젝트 정보

- **카테고리**: Creative Tools
- **설명**: AI 기반 음악 작곡 및 작사 시스템
- **포트**: 5061

## 🚀 빠른 시작

### 설치
```bash
# 루트 디렉토리에서
pip install -r requirements.txt
```

### 실행
```bash
# 이 프로젝트 실행
python run_music_composer.py

# 또는 루트에서 직접 실행
cd ../..
python animation_studio_theme_song_demo.py
```

## 📁 프로젝트 구조

```
music-composer/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 이 파일
├── requirements.txt     # 의존성
└── run_music_composer.py  # 실행 스크립트
```

## 📦 주요 파일

1. `animation_studio_theme_song_demo.py`
2. `emotion_based_music_generator.py`
3. `music_chat_friend_system.py`
4. `start_music_chat_server.py`

## 🔗 관련 문서

- [MUSIC_CHAT_COMPLETION_REPORT.md](../../MUSIC_CHAT_COMPLETION_REPORT.md)

## 🐳 Docker

```bash
# Docker로 실행
docker build -f ../../dockerfiles/Dockerfile.music-composer -t music-composer ../..
docker run -p 5061:5061 music-composer
```

## 📝 참고사항

- 실제 소스 파일은 루트 디렉토리에 위치하며, src/ 폴더에는 심볼릭 링크로 연결됩니다.
- 이 프로젝트는 신세계(Shinsegye) 통합 시스템의 일부입니다.
- 전체 시스템 문서는 [루트 README](../../README.md)를 참고하세요.

---

**생성일**: 2025년 12월 05일  
**버전**: 1.0.0
