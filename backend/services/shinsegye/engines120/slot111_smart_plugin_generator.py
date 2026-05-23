"""
스마트 플러그인 생성기 (Smart Plugin Generator)
사용자 요구를 분석하여 자동으로 맞춤형 플러그인 생성
"""
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class SmartPluginGenerator:
    def __init__(self, plugins_dir="modules/plugins"):
        self.plugins_dir = plugins_dir
        self.plugin_templates = {
            "utility": self._get_utility_template(),
            "entertainment": self._get_entertainment_template(),
            "productivity": self._get_productivity_template(),
            "learning": self._get_learning_template(),
            "creative": self._get_creative_template()
        }

        # 요구사항 분석 키워드
        self.requirement_patterns = {
            "file_management": ["파일", "폴더", "디렉토리", "저장", "삭제", "정리"],
            "data_processing": ["데이터", "분석", "처리", "변환", "파싱"],
            "automation": ["자동", "반복", "스케줄", "작업", "태스크"],
            "communication": ["메시지", "알림", "이메일", "채팅", "소통"],
            "entertainment": ["게임", "음악", "재미", "엔터테인먼트", "놀이"],
            "learning": ["학습", "공부", "교육", "배우기", "연습"],
            "creative": ["창조", "아이디어", "예술", "디자인", "창작"]
        }

        self.generated_plugins = []

    def analyze_user_request(self, request: str) -> Dict[str, Any]:
        """사용자 요청 분석"""
        analysis = {
            "primary_category": None,
            "secondary_categories": [],
            "extracted_features": [],
            "complexity_level": "simple",
            "suggested_name": None,
            "confidence_score": 0
        }

        request_lower = request.lower()

        # 카테고리 분석
        category_scores = {}
        for category, keywords in self.requirement_patterns.items():
            score = sum(1 for keyword in keywords if keyword in request_lower)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            # 가장 높은 점수의 카테고리
            primary = max(category_scores.items(), key=lambda x: x[1])
            analysis["primary_category"] = primary[0]
            analysis["confidence_score"] = min(primary[1] * 20, 100)

            # 나머지 관련 카테고리들
            analysis["secondary_categories"] = [
                cat for cat, score in category_scores.items()
                if cat != primary[0] and score > 0
            ]

        # 기능 추출
        analysis["extracted_features"] = self._extract_features(request)

        # 복잡도 추정
        analysis["complexity_level"] = self._estimate_complexity(request)

        # 플러그인 이름 제안
        analysis["suggested_name"] = self._suggest_plugin_name(request, analysis["primary_category"])

        return analysis

    def generate_plugin(self, request: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """플러그인 자동 생성"""
        analysis = self.analyze_user_request(request)

        # 플러그인 정보 구성
        plugin_info = {
            "name": custom_name or analysis["suggested_name"],
            "category": analysis["primary_category"],
            "description": f"사용자 요청에 따라 생성된 플러그인: {request[:50]}...",
            "features": analysis["extracted_features"],
            "complexity": analysis["complexity_level"],
            "created_at": datetime.now().isoformat(),
            "file_path": None
        }

        # 템플릿 선택 및 코드 생성
        template_category = self._map_to_template_category(analysis["primary_category"])
        template = self.plugin_templates.get(template_category, self.plugin_templates["utility"])

        # 플러그인 코드 생성
        plugin_code = self._customize_template(template, plugin_info, request)

        # 파일 저장
        plugin_file_path = self._save_plugin(plugin_info["name"], plugin_code)
        plugin_info["file_path"] = plugin_file_path

        # 생성 기록
        self.generated_plugins.append(plugin_info)

        return {
            "success": True,
            "plugin_info": plugin_info,
            "code_preview": plugin_code[:300] + "..." if len(plugin_code) > 300 else plugin_code,
            "installation_guide": self._generate_installation_guide(plugin_info)
        }

    def _extract_features(self, request: str) -> List[str]:
        """요청에서 기능 추출"""
        features = []

        # 동작 키워드 추출
        action_patterns = {
            r"(생성|만들|create)": "생성 기능",
            r"(삭제|제거|delete)": "삭제 기능",
            r"(검색|찾기|search)": "검색 기능",
            r"(분석|analyze)": "분석 기능",
            r"(변환|convert)": "변환 기능",
            r"(저장|save)": "저장 기능",
            r"(자동화|automation)": "자동화 기능",
            r"(알림|notification)": "알림 기능"
        }

        for pattern, feature in action_patterns.items():
            if re.search(pattern, request, re.IGNORECASE):
                features.append(feature)

        # 객체 키워드 추출
        if "파일" in request:
            features.append("파일 처리")
        if "데이터" in request:
            features.append("데이터 처리")
        if "웹" in request:
            features.append("웹 연동")

        return features or ["기본 기능"]

    def _estimate_complexity(self, request: str) -> str:
        """요청의 복잡도 추정"""
        complexity_indicators = {
            "simple": ["간단", "쉬운", "기본"],
            "medium": ["중간", "적당", "보통"],
            "complex": ["복잡", "고급", "어려운", "전문"]
        }

        request_lower = request.lower()

        # 복잡성 지표들
        if any(word in request_lower for word in ["ai", "머신러닝", "딥러닝", "알고리즘"]):
            return "complex"
        elif any(word in request_lower for word in ["api", "데이터베이스", "네트워크"]):
            return "medium"
        elif len(request.split()) > 20:
            return "medium"
        else:
            return "simple"

    def _suggest_plugin_name(self, request: str, category: str) -> str:
        """플러그인 이름 제안"""
        # 카테고리별 접두사
        category_prefixes = {
            "file_management": "FileWizard",
            "data_processing": "DataMaster",
            "automation": "AutoMagic",
            "communication": "ConnectPro",
            "entertainment": "FunTime",
            "learning": "StudyBuddy",
            "creative": "ArtGenius"
        }

        prefix = category_prefixes.get(category, "SmartPlugin")

        # 요청에서 핵심 단어 추출
        words = request.split()
        key_words = [word for word in words if len(word) > 3 and word.isalpha()]

        if key_words:
            suffix = key_words[0].capitalize()
        else:
            suffix = "Helper"

        return f"{prefix}_{suffix}"

    def _map_to_template_category(self, category: str) -> str:
        """분석된 카테고리를 템플릿 카테고리로 매핑"""
        mapping = {
            "file_management": "utility",
            "data_processing": "utility",
            "automation": "productivity",
            "communication": "productivity",
            "entertainment": "entertainment",
            "learning": "learning",
            "creative": "creative"
        }

        return mapping.get(category, "utility")

    def _customize_template(self, template: str, plugin_info: Dict, original_request: str) -> str:
        """템플릿을 요청에 맞게 커스터마이징"""
        customized = template

        # 기본 정보 치환
        customized = customized.replace("{PLUGIN_NAME}", plugin_info["name"])
        customized = customized.replace("{PLUGIN_DESCRIPTION}", plugin_info["description"])
        customized = customized.replace("{CREATION_DATE}", plugin_info["created_at"])

        # 기능별 커스터마이징
        features_code = self._generate_features_code(plugin_info["features"], original_request)
        customized = customized.replace("{CUSTOM_FEATURES}", features_code)

        return customized

    def _generate_features_code(self, features: List[str], request: str) -> str:
        """기능 목록을 기반으로 코드 생성"""
        code_blocks = []

        for feature in features:
            if "생성" in feature:
                code_blocks.append("""

    def create_item(self, name: str, content: Any = None):
        \"\"\"아이템 생성\"\"\"
        # 생성 로직 구현
        return f"{name} 생성 완료"
                """)
            elif "검색" in feature:
                code_blocks.append("""

    def search_items(self, query: str):
        \"\"\"아이템 검색\"\"\"
        # 검색 로직 구현
        return f"{query} 검색 결과"
                """)
            elif "분석" in feature:
                code_blocks.append("""

    def analyze_data(self, data: Any):
        \"\"\"데이터 분석\"\"\"
        # 분석 로직 구현
        return "분석 완료"
                """)

        return "\n".join(code_blocks) if code_blocks else """

    def custom_function(self, input_data: Any):
        \"\"\"커스텀 기능\"\"\"
        # 사용자 요청에 맞는 로직 구현
        return "작업 완료"
        """

    def _save_plugin(self, plugin_name: str, plugin_code: str) -> str:
        """플러그인 파일 저장"""
        # 안전한 파일명 생성
        safe_name = re.sub(r'[^\w\-_]', '_', plugin_name.lower())
        file_path = os.path.join(self.plugins_dir, f"{safe_name}.py")

        # 디렉토리 생성
        os.makedirs(self.plugins_dir, exist_ok=True)

        # 파일 저장
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(plugin_code)
            return file_path
        except Exception as e:
            return f"저장 실패: {e}"

    def _generate_installation_guide(self, plugin_info: Dict) -> str:
        """설치 가이드 생성"""
        return f"""
📦 **플러그인 설치 가이드**

**플러그인명**: {plugin_info['name']}
**카테고리**: {plugin_info['category']}
**파일 위치**: {plugin_info['file_path']}

**설치 방법**:
1. 플러그인 파일이 자동으로 생성되었습니다
2. 플러그인 매니저에서 활성화하세요:
   ```python
   plugin_manager.load_plugin('{plugin_info['name']}')
   ```

**주요 기능**:
{chr(10).join([f'• {feature}' for feature in plugin_info['features']])}

**사용 예시**:
```python
plugin = get_plugin('{plugin_info['name']}')
result = plugin.execute("your_command")
print(result)
```
        """.strip()

    def list_generated_plugins(self) -> str:
        """생성된 플러그인 목록"""
        if not self.generated_plugins:
            return "아직 생성된 플러그인이 없습니다."

        plugin_list = []
        for i, plugin in enumerate(self.generated_plugins, 1):
            plugin_list.append(f"{i}. {plugin['name']} ({plugin['category']}) - {plugin['created_at'][:10]}")

        return "🧩 **생성된 플러그인 목록**:\n" + "\n".join(plugin_list)

    # 템플릿 메서드들

    def _get_utility_template(self) -> str:
        return '''"""
{PLUGIN_NAME}
{PLUGIN_DESCRIPTION}
생성일: {CREATION_DATE}
"""

from modules.plugins.base_plugin import BasePlugin
from typing import Any, Dict, List


class {PLUGIN_NAME}(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "{PLUGIN_NAME}"
        self.version = "1.0.0"
        self.description = "{PLUGIN_DESCRIPTION}"

    def execute(self, command: str, *args, **kwargs) -> Any:
        """메인 실행 메서드"""
        if command == "help":
            return self.get_help()
        elif command == "status":
            return self.get_status()
        else:
            return self.handle_custom_command(command, *args, **kwargs)

    def handle_custom_command(self, command: str, *args, **kwargs) -> Any:
        """커스텀 명령 처리"""
        # 기본 응답
        return f"{self.name}에서 '{command}' 명령을 처리했습니다."
{CUSTOM_FEATURES}

    def get_help(self) -> str:
        """도움말 반환"""
        return f"""
🛠️ {self.name} 도움말
설명: {self.description}
버전: {self.version}

사용 가능한 명령:
• help - 이 도움말 표시
• status - 플러그인 상태 확인
        """

    def get_status(self) -> Dict:
        """플러그인 상태 반환"""
        return {
            "name": self.name,
            "version": self.version,
            "active": True,
            "last_used": "방금 전"
        }
'''

    def _get_entertainment_template(self) -> str:
        return '''"""
{PLUGIN_NAME} - 엔터테인먼트 플러그인
{PLUGIN_DESCRIPTION}
생성일: {CREATION_DATE}
"""

from modules.plugins.base_plugin import BasePlugin
import random
from typing import Any, Dict, List


class {PLUGIN_NAME}(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "{PLUGIN_NAME}"
        self.version = "1.0.0"
        self.description = "{PLUGIN_DESCRIPTION}"
        self.fun_responses = [
            "와! 재미있네요! 🎉",
            "또 해볼까요? 😄",
            "신나는데요! 🎊"
        ]

    def execute(self, command: str, *args, **kwargs) -> Any:
        """메인 실행 메서드"""
        if command == "play":
            return self.start_entertainment()
        elif command == "joke":
            return self.tell_joke()
        elif command == "random":
            return self.random_fun()
        else:
            return f"{random.choice(self.fun_responses)} '{command}' 명령이 실행되었어요!"

    def start_entertainment(self) -> str:
        """엔터테인먼트 시작"""
        return "🎮 재미있는 시간을 시작해볼까요? 무엇을 하고 싶으세요?"

    def tell_joke(self) -> str:
        """농담 들려주기"""
        jokes = [
            "프로그래머가 바에 가서 맥주 2병을 주문했어요. 바텐더가 '2병 맞나요?'라고 물으니 '네, 하지만 null check 먼저 해주세요'라고 답했답니다! 😂",
            "왜 프로그래머는 어둠을 무서워할까요? 버그가 숨어있을 수 있거든요! 🐛",
            "AI가 커피를 주문하면 뭐라고 할까요? '딥러닝 한 잔 주세요!' ☕"
        ]
        return random.choice(jokes)
{CUSTOM_FEATURES}

    def random_fun(self) -> str:
        """랜덤 재미 요소"""
        fun_activities = [
            "🎲 주사위 던지기: " + str(random.randint(1, 6)),
            "🔮 오늘의 운세: 코딩이 잘 될 예정입니다!",
            "🎨 색깔 추천: " + random.choice(["빨강", "파랑", "노랑", "초록", "보라"])
        ]
        return random.choice(fun_activities)
'''

    def _get_productivity_template(self) -> str:
        return '''"""
{PLUGIN_NAME} - 생산성 플러그인
{PLUGIN_DESCRIPTION}
생성일: {CREATION_DATE}
"""

from modules.plugins.base_plugin import BasePlugin
from datetime import datetime
from typing import Any, Dict, List


class {PLUGIN_NAME}(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "{PLUGIN_NAME}"
        self.version = "1.0.0"
        self.description = "{PLUGIN_DESCRIPTION}"
        self.tasks = []

    def execute(self, command: str, *args, **kwargs) -> Any:
        """메인 실행 메서드"""
        if command == "add_task":
            return self.add_task(*args, **kwargs)
        elif command == "list_tasks":
            return self.list_tasks()
        elif command == "complete_task":
            return self.complete_task(*args, **kwargs)
        elif command == "productivity_tip":
            return self.get_productivity_tip()
        else:
            return self.handle_productivity_command(command, *args, **kwargs)

    def add_task(self, task_name: str, priority: str = "medium") -> str:
        """작업 추가"""
        task = {
            "name": task_name,
            "priority": priority,
            "created": datetime.now().isoformat(),
            "completed": False
        }
        self.tasks.append(task)
        return f"✅ 작업 '{task_name}' 이 추가되었습니다 (우선순위: {priority})"

    def list_tasks(self) -> str:
        """작업 목록"""
        if not self.tasks:
            return "📝 등록된 작업이 없습니다."

        task_list = ["📋 **작업 목록**:"]
        for i, task in enumerate(self.tasks, 1):
            status = "✅" if task["completed"] else "⏳"
            task_list.append(f"{i}. {status} {task['name']} ({task['priority']})")

        return "\\n".join(task_list)
{CUSTOM_FEATURES}

    def complete_task(self, task_index: int) -> str:
        """작업 완료"""
        try:
            task = self.tasks[task_index - 1]
            task["completed"] = True
            return f"🎉 작업 '{task['name']}' 이 완료되었습니다!"
        except IndexError:
            return "❌ 해당 작업을 찾을 수 없습니다."

    def get_productivity_tip(self) -> str:
        """생산성 팁"""
        tips = [
            "🧠 25분 집중 + 5분 휴식의 포모도로 기법을 써보세요!",
            "📱 방해 요소를 제거하고 집중 환경을 만드세요!",
            "🎯 하루에 3가지 중요한 일만 정해서 실행하세요!",
            "⏰ 가장 중요한 일을 아침에 먼저 하세요!"
        ]
        return f"💡 **오늘의 생산성 팁**: {tips[datetime.now().day % len(tips)]}"
'''

    def _get_learning_template(self) -> str:
        return '''"""
{PLUGIN_NAME} - 학습 플러그인
{PLUGIN_DESCRIPTION}
생성일: {CREATION_DATE}
"""

from modules.plugins.base_plugin import BasePlugin
import random
from typing import Any, Dict, List


class {PLUGIN_NAME}(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "{PLUGIN_NAME}"
        self.version = "1.0.0"
        self.description = "{PLUGIN_DESCRIPTION}"
        self.learning_progress = {}

    def execute(self, command: str, *args, **kwargs) -> Any:
        """메인 실행 메서드"""
        if command == "learn":
            return self.start_learning(*args, **kwargs)
        elif command == "quiz":
            return self.generate_quiz()
        elif command == "progress":
            return self.show_progress()
        elif command == "tip":
            return self.learning_tip()
        else:
            return self.handle_learning_command(command, *args, **kwargs)

    def start_learning(self, topic: str = "general") -> str:
        """학습 시작"""
        if topic not in self.learning_progress:
            self.learning_progress[topic] = {"sessions": 0, "score": 0}

        self.learning_progress[topic]["sessions"] += 1

        return f"""
📚 **{topic} 학습을 시작합니다!**

학습 세션: {self.learning_progress[topic]["sessions"]}번째
현재 레벨: 초급자

오늘의 학습 목표를 설정해보세요! 🎯
        """

    def generate_quiz(self) -> str:
        """퀴즈 생성"""
        quiz_questions = [
            "Q: 파이썬에서 리스트와 튜플의 차이점은?",
            "Q: 함수형 프로그래밍의 핵심 원칙 3가지는?",
            "Q: API와 SDK의 차이점을 설명하세요.",
            "Q: 객체지향 프로그래밍의 4가지 특징은?"
        ]

        return f"""
🧠 **오늘의 퀴즈**
{random.choice(quiz_questions)}

💡 답변을 생각해보시고, 'answer' 명령으로 답해보세요!
        """
{CUSTOM_FEATURES}

    def show_progress(self) -> str:
        """학습 진행도"""
        if not self.learning_progress:
            return "📊 아직 학습 기록이 없습니다. 'learn' 명령으로 시작해보세요!"

        progress_report = ["📈 **학습 진행도**:"]
        for topic, data in self.learning_progress.items():
            progress_report.append(f"• {topic}: {data['sessions']}회 학습")

        return "\\n".join(progress_report)

    def learning_tip(self) -> str:
        """학습 팁"""
        tips = [
            "🔄 반복 학습이 기억에 가장 효과적입니다!",
            "✍️ 배운 내용을 직접 써보며 실습하세요!",
            "🤝 다른 사람에게 설명해보면 이해도가 높아집니다!",
            "🎯 작은 목표부터 달성하며 성취감을 쌓으세요!"
        ]
        return f"💡 **학습 팁**: {random.choice(tips)}"
'''

    def _get_creative_template(self) -> str:
        return '''"""
{PLUGIN_NAME} - 창조적 플러그인
{PLUGIN_DESCRIPTION}
생성일: {CREATION_DATE}
"""

from modules.plugins.base_plugin import BasePlugin
import random
from typing import Any, Dict, List


class {PLUGIN_NAME}(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "{PLUGIN_NAME}"
        self.version = "1.0.0"
        self.description = "{PLUGIN_DESCRIPTION}"
        self.creative_ideas = []

    def execute(self, command: str, *args, **kwargs) -> Any:
        """메인 실행 메서드"""
        if command == "inspire":
            return self.get_inspiration()
        elif command == "create":
            return self.creative_generator(*args, **kwargs)
        elif command == "brainstorm":
            return self.brainstorm_session(*args, **kwargs)
        elif command == "art":
            return self.artistic_suggestion()
        else:
            return self.spark_creativity(command, *args, **kwargs)

    def get_inspiration(self) -> str:
        """영감 제공"""
        inspirations = [
            "🌟 '창조성은 지식을 연결하는 것이다' - 스티브 잡스",
            "🎨 '모든 아이는 예술가다. 문제는 어른이 되어서도 예술가로 남는 것이다' - 피카소",
            "💡 '상상력은 지식보다 중요하다' - 아인슈타인",
            "🚀 '불가능해 보이는 것을 가능하게 만드는 것이 혁신이다' - 월트 디즈니"
        ]

        return f"""
✨ **오늘의 영감**
{random.choice(inspirations)}

🎯 이 영감으로 무엇을 만들어볼까요?
        """

    def creative_generator(self, theme: str = "random") -> str:
        """창의적 아이디어 생성"""
        if theme == "random":
            themes = ["미래", "자연", "음악", "색깔", "우주", "꿈"]
            theme = random.choice(themes)

        creative_elements = {
            "미래": ["홀로그램", "AI 동반자", "시간 여행", "무중력"],
            "자연": ["나무의 속삭임", "바람의 춤", "물의 흐름", "새의 노래"],
            "음악": ["리듬", "하모니", "멜로디", "침묵의 아름다움"],
            "색깔": ["무지개", "그라데이션", "빛의 스펙트럼", "색의 온도"]
        }

        elements = creative_elements.get(theme, ["신비", "마법", "경이", "아름다움"])

        idea = f"{theme}을 테마로 한 {random.choice(elements)}와 함께하는 창조적 프로젝트"
        self.creative_ideas.append(idea)

        return f"""
🎨 **창의적 아이디어**
테마: {theme}
아이디어: {idea}

💭 이 아이디어를 어떻게 발전시켜볼까요?
        """
{CUSTOM_FEATURES}

    def brainstorm_session(self, topic: str = "혁신") -> str:
        """브레인스토밍 세션"""
        session_prompts = [
            f"{topic}에 대해 10가지 다른 관점에서 생각해보세요",
            f"만약 {topic}을 색깔로 표현한다면?",
            f"{topic}의 반대는 무엇일까요? 그것에서 배울 점은?",
            f"{topic}을 아이가 본다면 어떻게 해석할까요?"
        ]

        return f"""
🧠 **브레인스토밍 세션 시작!**
주제: {topic}

💭 질문: {random.choice(session_prompts)}

✍️ 5분 동안 자유롭게 아이디어를 적어보세요!
        """

    def artistic_suggestion(self) -> str:
        """예술적 제안"""
        art_forms = ["디지털 아트", "시 쓰기", "음악 작곡", "스토리텔링", "조각", "사진"]
        colors = ["파스텔톤", "비비드", "모노크롬", "네온", "자연색"]
        moods = ["몽환적", "역동적", "고요한", "신비로운", "따뜻한"]

        art_form = random.choice(art_forms)
        color = random.choice(colors)
        mood = random.choice(moods)

        return f"""
🎨 **오늘의 예술적 제안**

형태: {art_form}
색감: {color}
분위기: {mood}

🌟 이 조합으로 무언가 창조해보세요!
어떤 작품이 탄생할지 기대됩니다! ✨
        """

    def spark_creativity(self, input_text: str, *args, **kwargs) -> str:
        """창의성 자극"""
        return f"""
💫 **창의적 해석**
입력: {input_text}

🎭 이것을 다른 관점에서 보면:
• 예술가의 눈으로: 색과 형태의 조합
• 과학자의 눈으로: 패턴과 구조의 분석
• 아이의 눈으로: 순수한 호기심과 상상
• 철학자의 눈으로: 존재와 의미의 탐구

✨ 어떤 관점이 가장 흥미로우신가요?
        """
'''
