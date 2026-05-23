# 🌐 나도 통역사 - 사용 가이드

## I am also an Interpreter - User Guide

**수아미코리아 x 신세계 소리새프로젝트 통합**

---

## 📋 목차

1. [소개](#소개)
2. [설치 및 실행](#설치-및-실행)
3. [기본 사용법](#기본-사용법)
4. [고급 기능](#고급-기능)
5. [지원 언어](#지원-언어)
6. [예제 코드](#예제-코드)

---

## 소개

**나도 통역사**는 신세계 소리새 프로젝트에 통합된 실시간 다국어 통역 시스템입니다.

### 주요 기능

- 🌐 **12개 언어 지원**: 한국어, 영어, 일본어, 중국어, 스페인어, 프랑스어, 독일어, 러시아어, 아랍어, 베트남어, 태국어, 인도네시아어
- ⚡ **실시간 번역**: 빠르고 정확한 텍스트 번역
- 🎯 **세션 관리**: 통역 세션 생성 및 관리
- 📊 **통계 추적**: 번역 히스토리 및 통계 확인
- 🎤 **대화형 모드**: 실시간 대화 통역 지원

---

## 설치 및 실행

### 방법 1: 독립 실행

```bash
# 통역 프로그램 단독 실행
python sorisae_interpreter.py
```

### 방법 2: 메인 시스템과 통합

```bash
# 전체 소리새 시스템 실행 (통역 기능 포함)
python run_all_shinsegye.py
```

---

## 기본 사용법

### 1. 빠른 번역

```python
from sorisae_interpreter import SorisaeInterpreter

# 통역 시스템 생성
interpreter = SorisaeInterpreter()

# 한국어 -> 영어 번역
result = interpreter.quick_translate("안녕하세요", "ko", "en")
print(result)  # "Hello"

# 한국어 -> 일본어 번역
result = interpreter.quick_translate("감사합니다", "ko", "ja")
print(result)  # "ありがとうございます"
```

### 2. 대화형 통역 모드

```python
from sorisae_interpreter import SorisaeInterpreter

interpreter = SorisaeInterpreter()

# 대화형 모드 시작
interpreter.start_conversation_mode()
```

대화형 모드에서 사용 가능한 명령어:
- `quit` 또는 `exit`: 종료
- `stats`: 통계 보기
- `history`: 최근 번역 보기
- `lang`: 언어 변경

---

## 고급 기능

### 실시간 통역 세션

```python
from sorisae_interpreter import SorisaeInterpreter

interpreter = SorisaeInterpreter()

# 통역 세션 생성 (한국어 -> 영어)
session = interpreter.realtime.create_session("my_session", "ko", "en")

# 실시간 통역
texts = ["안녕하세요", "반갑습니다", "감사합니다"]
for text in texts:
    translated = interpreter.realtime.interpret("my_session", text)
    print(f"{text} -> {translated}")

# 세션 종료
interpreter.realtime.end_session("my_session")
```

### 통계 및 히스토리

```python
# 통계 확인
stats = interpreter.engine.get_stats()
print(f"총 번역: {stats['total_translations']}회")
print(f"세션 시간: {stats['session_duration']}")
print(f"언어별: {stats['by_language']}")

# 최근 번역 히스토리 조회 (최근 10개)
history = interpreter.engine.get_history(10)
for entry in history:
    print(f"[{entry['source_lang']}] {entry['source']}")
    print(f"[{entry['target_lang']}] {entry['target']}")
```

---

## 지원 언어

| 코드 | 언어 | Language |
|------|------|----------|
| `ko` | 한국어 | Korean |
| `en` | 영어 | English |
| `ja` | 일본어 | Japanese |
| `zh` | 중국어 | Chinese |
| `es` | 스페인어 | Spanish |
| `fr` | 프랑스어 | French |
| `de` | 독일어 | German |
| `ru` | 러시아어 | Russian |
| `ar` | 아랍어 | Arabic |
| `vi` | 베트남어 | Vietnamese |
| `th` | 태국어 | Thai |
| `id` | 인도네시아어 | Indonesian |

---

## 예제 코드

### 예제 1: 다국어 인사말

```python
from sorisae_interpreter import SorisaeInterpreter

interpreter = SorisaeInterpreter()

# 여러 언어로 "안녕하세요" 번역
languages = ['en', 'ja', 'zh', 'es', 'fr', 'de']
for lang in languages:
    result = interpreter.quick_translate("안녕하세요", "ko", lang)
    print(f"{lang}: {result}")
```

출력:

```
en: Hello
ja: こんにちは
zh: 你好
es: Hola
fr: Bonjour
de: Hallo
```

### 예제 2: 비즈니스 통역

```python
from sorisae_interpreter import SorisaeInterpreter

interpreter = SorisaeInterpreter()

# 비즈니스 용어 번역
business_terms = ["회의", "계약", "협상"]
for term in business_terms:
    en = interpreter.quick_translate(term, "ko", "en")
    ja = interpreter.quick_translate(term, "ko", "ja")
    print(f"{term}: {en} (English), {ja} (Japanese)")
```

### 예제 3: 통역 세션 관리

```python
from sorisae_interpreter import SorisaeInterpreter

interpreter = SorisaeInterpreter()

# 여러 세션 동시 관리
session1 = interpreter.realtime.create_session("korean_english", "ko", "en")
session2 = interpreter.realtime.create_session("korean_japanese", "ko", "ja")

# 세션별 통역
text = "안녕하세요"
en_result = interpreter.realtime.interpret("korean_english", text)
ja_result = interpreter.realtime.interpret("korean_japanese", text)

print(f"영어: {en_result}")
print(f"일본어: {ja_result}")

# 세션 종료
interpreter.realtime.end_session("korean_english")
interpreter.realtime.end_session("korean_japanese")
```

---

## 🤝 기여 및 피드백

이 통역 시스템은 신세계 소리새 프로젝트의 일부입니다.

- **이슈 보고**: [GitHub Issues](https://github.com/parkcheolhong/run_all_shinsegye.py/issues)
- **기능 제안**: [GitHub Discussions](https://github.com/parkcheolhong/run_all_shinsegye.py/discussions)

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

**🌐 나도 통역사 - 수아미코리아 x 신세계 소리새프로젝트**

*"언어의 장벽을 넘어 소통의 세계로"*
