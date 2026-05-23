#!/usr/bin/env python3
"""
신세계 프로젝트 폴더 분리 및 구조화 스크립트
Shinsegye Projects Folder Organization Script

각 프로젝트를 독립적인 폴더로 분리하여 관리하기 쉽게 구조화합니다.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ProjectOrganizer:
    """프로젝트 구조화 관리자"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.projects_root = self.base_path / "projects_separated"
        self.projects = self._define_projects()

    def _define_projects(self) -> Dict[str, Dict]:
        """18개 프로젝트 정의 및 파일 매핑"""
        return {
            "sorisae-core": {
                "name_ko": "소리새 핵심",
                "name_en": "Sorisae Core System",
                "category": "Core Systems",
                "description": "Two-Cycle Brain AI 핵심 시스템",
                "port": 5050,
                "files": [
                    "run_all_shinsegye.py",
                    "sorisae_ai_decision_engine.py",
                    "sorisae_dashboard_web.py",
                    "sorisae_divine_intelligence_105.py",
                    "sorisae_dual_brain_comparison.py",
                    "sorisae_dual_brain_stock_system.py",
                    "sorisae_enhanced_consciousness.py",
                    "sorisae_enhanced_features.py",
                    "sorisae_ethical_consciousness_engine.py",
                    "sorisae_ethical_consciousness_simple.py",
                    "sorisae_integrated_dashboard.py",
                    "sorisae_integrated_hybrid_system.py",
                    "sorisae_master_hybrid_system.py",
                    "sorisae_master_system.py",
                    "sorisae_maximum_upgrade_system.py",
                    "sorisae_multi_ego_core.py",
                    "sorisae_nextgen_features.py",
                    "sorisae_temporal_integration.py",
                    "sorisae_transcendent_102.py",
                    "sorisae_ultimate_integrated_system.py",
                    "sorisae_unified_launcher.py",
                    "launch_dashboard.py",
                    "launch_integrated_system.py",
                    "run_complete_sorisae_system.py",
                    "run_hybrid_system.py"
                ],
                "modules": ["modules/sorisae", "modules/ai_code_manager"],
                "templates": ["templates/dashboard.html"],
                "docs": ["TWO_CYCLE_ARCHITECTURE.md", "TWO_CYCLE_DESIGN.md"]
            },
            "interpreter": {
                "name_ko": "나도 통역사",
                "name_en": "Multi-Language Interpreter",
                "category": "Language Processing",
                "description": "실시간 13개 언어 통역 시스템",
                "port": 5051,
                "files": [
                    "hybrid_conversation_translator.py",
                    "hybrid_interpreter_system.py",
                    "multilingual_system.py",
                    "sorisae_interpreter.py",
                    "sorisae_multilingual_support.py",
                    "sorisae_southeast_asia_translator.py"
                ],
                "data": ["hybrid_interpreter_data"],
                "docs": ["INTERPRETER_GUIDE.md", "SORISAE_LANGUAGE_GUIDE.md"]
            },
            "cyber-detective": {
                "name_ko": "사이버 탐정",
                "name_en": "Cyber Detective",
                "category": "Security & Analysis",
                "description": "AI 기반 사이버 수사 시스템",
                "port": 5052,
                "files": [
                    "cyber_detective_ai.py",
                    "cyber_detective_dashboard.py",
                    "cyber_detective_detailed_analysis.py",
                    "cyber_detective_future_tech.py",
                    "cyber_detective_global_network.py",
                    "cyber_detective_global_server_analysis.py",
                    "cyber_detective_gps_radius.py",
                    "cyber_detective_methodology.py",
                    "cyber_detective_visual_monitoring.py",
                    "cyber_investigation_report.py",
                    "cyber_realtime_monitor.py",
                    "sorisae_cyber_investigator.py"
                ],
                "docs": []
            },
            "movie-studio": {
                "name_ko": "4D 영화 제작",
                "name_en": "4D Movie Studio",
                "category": "Creative Tools",
                "description": "음성 기반 4D 영화 제작 시스템",
                "port": 5000,
                "files": [
                    "sorisae_4d_movie_demo.py",
                    "sorisae_movie_installer.py",
                    "sorisae_movie_web_server.py",
                    "sorisae_voice_movie_server.py"
                ],
                "data": ["rendered_scenes"],
                "docs": ["소리새_4D영화제작_README.md", "영화제작_소리새_연동_상태_보고서.md"]
            },
            "iot-smarthome": {
                "name_ko": "IoT 스마트홈",
                "name_en": "IoT Smart Home",
                "category": "IoT",
                "description": "스마트홈 디바이스 제어 시스템",
                "port": 5053,
                "files": [
                    "hybrid_iot_controller.py",
                    "sorisae_iot_integration.py",
                    "sorisae_iot_smarthome.py",
                    "sorisae_iot_voice_control.py",
                    "spatiotemporal_learning_system.py",
                    "spatiotemporal_learning_system_new.py"
                ],
                "docs": []
            },
            "investment-advisor": {
                "name_ko": "투자 어드바이저",
                "name_en": "Investment Advisor",
                "category": "Finance",
                "description": "듀얼브레인 AI 투자 조언 (200% 수익률)",
                "port": 5058,
                "files": [
                    "sorisae_investment_advisor_200.py",
                    "stock_prediction_200_percent.py"
                ],
                "docs": []
            },
            "music-composer": {
                "name_ko": "작사/작곡",
                "name_en": "Music Composer",
                "category": "Creative Tools",
                "description": "AI 기반 음악 작곡 및 작사 시스템",
                "port": 5061,
                "files": [
                    "animation_studio_theme_song_demo.py",
                    "emotion_based_music_generator.py",
                    "music_chat_friend_system.py",
                    "start_music_chat_server.py"
                ],
                "docs": ["MUSIC_CHAT_COMPLETION_REPORT.md"]
            },
            "animation-studio": {
                "name_ko": "애니메이션 스튜디오",
                "name_en": "Animation Studio",
                "category": "Creative Tools",
                "description": "AI 기반 애니메이션 제작",
                "port": 5062,
                "files": [
                    "animation_studio_demo.py",
                    "demo_animation_voice_integration.py",
                    "sorisae_animation_studio_ultra.py",
                    "test_animation_voice_integration.py"
                ],
                "docs": []
            },
            "civil-bidding": {
                "name_ko": "토목 입찰 시스템",
                "name_en": "Civil Engineering Bidding",
                "category": "Business",
                "description": "AI 기반 건설 프로젝트 입찰 분석",
                "port": 5055,
                "files": [
                    "civil_engineering_bidding_demo.py",
                    "sorisae_civil_engineering_bidding.py"
                ],
                "docs": []
            },
            "game-economy": {
                "name_ko": "게임 경제 시스템",
                "name_en": "Game Economy System",
                "category": "Gaming",
                "description": "세계 최초 '게임으로 먹고살기' 플랫폼",
                "port": 5056,
                "files": [
                    "game_earning_analysis.py",
                    "sorisae_earning_game.py",
                    "sorisae_game_concept_design.py",
                    "sorisae_game_economy_system.py"
                ],
                "docs": []
            },
            "shopping-mall": {
                "name_ko": "쇼핑몰 시스템",
                "name_en": "Shopping Mall System",
                "category": "Business",
                "description": "7개 AI 에이전트 자율 쇼핑몰 (소피움 에이아이)",
                "port": 5057,
                "files": [
                    "autonomous_shopping_demo.py",
                    "integrated_shopping_tutor_designer.py",
                    "shopping_mall_dashboard.py"
                ],
                "templates": ["shopping_mall_visual.html"],
                "docs": []
            },
            "gps-police": {
                "name_ko": "GPS & 경찰 시스템",
                "name_en": "GPS & Police System",
                "category": "Security & Analysis",
                "description": "윤리적 GPS 추적 및 경찰 시스템",
                "port": 5063,
                "files": [
                    "current_police_system_status.py",
                    "ethical_gps_system.py",
                    "ethical_gps_system_simple.py",
                    "regional_ai_police_coverage.py",
                    "sorisae_gps_ethics_completion_report.py"
                ],
                "docs": []
            },
            "security": {
                "name_ko": "보안 시스템",
                "name_en": "Security System",
                "category": "Security & Analysis",
                "description": "다층 보안 시스템",
                "port": 5064,
                "files": [
                    "advanced_security_system.py",
                    "biometric_security_system.py",
                    "hybrid_cyber_security_system.py",
                    "security_demo.py",
                    "security_key_manager.py"
                ],
                "docs": ["SECURITY.md", "ACCESS_KEYS.md"]
            },
            "satellite": {
                "name_ko": "위성 시스템",
                "name_en": "Satellite System",
                "category": "Infrastructure",
                "description": "차세대 인공위성 WiFi 시스템",
                "port": 5059,
                "files": [
                    "mountain_emergency_satellite.py",
                    "practical_satellite_manager.py",
                    "sorisae_satellite_demo.py",
                    "sorisae_satellite_wifi_system.py"
                ],
                "data": ["satellite_data"],
                "docs": []
            },
            "vr-games": {
                "name_ko": "VR/게임",
                "name_en": "VR & Games",
                "category": "Gaming",
                "description": "VR 및 게임 생성 시스템",
                "port": 5065,
                "files": [
                    "sorisae_fantasy_vr_infinite_universe_game.py",
                    "sorisae_vr_launcher.py",
                    "trend_idea_generator.py"
                ],
                "docs": []
            },
            "dev-tools": {
                "name_ko": "개발 도구",
                "name_en": "Development Tools",
                "category": "Development Support",
                "description": "코드 분석 및 개선 도구",
                "port": None,
                "files": [
                    "analyze_architecture.py",
                    "analyze_all_shinsegye_projects.py",
                    "code_quality_improver.py",
                    "code_quality_master.py",
                    "comprehensive_file_analyzer.py",
                    "comprehensive_project_analyzer.py",
                    "detailed_technical_report.py",
                    "fix_docstring_quotes.py",
                    "fix_duplicate_orders.py",
                    "intelligent_code_refactor.py",
                    "project_review_verification.py",
                    "ai_performance_optimizer.py",
                    "ai_performance_tuner.py",
                    "creative_workflow_engine.py",
                    "intelligent_cache_system.py",
                    "next_gen_caching_system.py",
                    "next_gen_optimization_system.py",
                    "async_performance_system.py"
                ],
                "docs": ["CODE_QUALITY_FINAL_SUMMARY.md", "CODE_REVIEW_REPORT.md"]
            },
            "testing": {
                "name_ko": "테스트/검증",
                "name_en": "Testing & Validation",
                "category": "Development Support",
                "description": "테스트 및 검증 도구",
                "port": None,
                "files": [
                    "advanced_syntax_fixer.py",
                    "auto_syntax_validator.py",
                    "check_missing_programs.py",
                    "commissioning_test.py",
                    "completion_checker.py",
                    "project_syntax_checker.py",
                    "quick_validate.py",
                    "run_full_system_test.py",
                    "syno_check.py",
                    "syntax_checker.py",
                    "syntax_error_fixer.py",
                    "test_web_apps.py",
                    "validate_data.py",
                    "validate_python_files.py",
                    "verify_install.py",
                    "verify_sorisae_features.py"
                ],
                "tests": ["tests"],
                "docs": ["COMPREHENSIVE_TEST_REPORT.md", "TEST_RESULTS_REPORT.md"]
            },
            "voice-processing": {
                "name_ko": "음성 처리",
                "name_en": "Voice Processing",
                "category": "Core Systems",
                "description": "음성 인식 및 처리 시스템",
                "port": None,
                "files": [
                    "sorisae_voice_processor.py",
                    "sorisae_voice_reactive.py",
                    "voice_calling_system.py",
                    "voice_command_processor.py",
                    "voice_tuner.py",
                    "enhanced_voice_exit.py",
                    "hybrid_voice_processor.py"
                ],
                "docs": []
            }
        }

    def create_project_folder(self, project_id: str, project_info: Dict) -> Path:
        """프로젝트 폴더 생성"""
        project_path = self.projects_root / project_id
        project_path.mkdir(parents=True, exist_ok=True)

        # 서브디렉토리 생성
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "docs").mkdir(exist_ok=True)
        (project_path / "data").mkdir(exist_ok=True)
        (project_path / "config").mkdir(exist_ok=True)

        return project_path

    def create_readme(self, project_path: Path, project_id: str, project_info: Dict):
        """프로젝트별 README.md 생성"""
        readme_content = f"""# {project_info['name_ko']} ({project_info['name_en']})

## 📋 프로젝트 정보

- **카테고리**: {project_info['category']}
- **설명**: {project_info['description']}
- **포트**: {project_info.get('port', 'N/A')}

## 🚀 빠른 시작

### 설치
```bash
# 루트 디렉토리에서
pip install -r requirements.txt
```

### 실행
```bash
# 이 프로젝트 실행
python run_{project_id.replace('-', '_')}.py

# 또는 루트에서 직접 실행
cd ../..
python {project_info['files'][0] if project_info.get('files') else 'run_all_shinsegye.py'}
```

## 📁 프로젝트 구조

```
{project_id}/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 이 파일
├── requirements.txt     # 의존성
└── run_{project_id.replace('-', '_')}.py  # 실행 스크립트
```

## 📦 주요 파일

"""
        # 파일 목록 추가
        for i, file_name in enumerate(project_info.get('files', [])[:10], 1):
            readme_content += f"{i}. `{file_name}`\n"

        if len(project_info.get('files', [])) > 10:
            readme_content += f"... 외 {len(project_info['files']) - 10}개 파일\n"

        readme_content += f"""
## 🔗 관련 문서

"""
        # 문서 링크 추가
        for doc in project_info.get('docs', []):
            readme_content += f"- [{doc}](../../{doc})\n"

        readme_content += f"""
## 🐳 Docker

```bash
# Docker로 실행
docker build -f ../../dockerfiles/Dockerfile.{project_id} -t {project_id} ../..
docker run -p {project_info.get('port', '5000')}:{project_info.get('port', '5000')} {project_id}
```

## 📝 참고사항

- 실제 소스 파일은 루트 디렉토리에 위치하며, src/ 폴더에는 심볼릭 링크로 연결됩니다.
- 이 프로젝트는 신세계(Shinsegye) 통합 시스템의 일부입니다.
- 전체 시스템 문서는 [루트 README](../../README.md)를 참고하세요.

---

**생성일**: {datetime.now().strftime('%Y년 %m월 %d일')}  
**버전**: 1.0.0
"""

        with open(project_path / "README.md", 'w', encoding='utf-8') as f:
            f.write(readme_content)

    def create_requirements(self, project_path: Path, project_id: str, project_info: Dict):
        """프로젝트별 requirements.txt 생성"""
        # 기본 의존성
        requirements = [
            "# 프로젝트별 의존성",
            "# 전체 의존성은 루트의 requirements.txt 참고",
            "",
            "# 공통 의존성",
            "Flask>=2.0.0",
            "flask-cors>=3.0.10",
            "flask-socketio>=5.0.0",
            "python-socketio>=5.0.0",
        ]

        # 프로젝트별 특수 의존성
        if project_id == "interpreter":
            requirements.extend([
                "",
                "# 통역 관련",
                "googletrans==4.0.0-rc1",
                "langdetect>=1.0.9"
            ])
        elif project_id == "movie-studio":
            requirements.extend([
                "",
                "# 영화 제작 관련",
                "opencv-python>=4.5.0",
                "manim>=0.15.0"
            ])
        elif project_id == "voice-processing":
            requirements.extend([
                "",
                "# 음성 처리 관련",
                "pyttsx3>=2.90",
                "SpeechRecognition>=3.8.1",
                "pyaudio>=0.2.11"
            ])
        elif project_id in ["cyber-detective", "security", "gps-police"]:
            requirements.extend([
                "",
                "# 보안/분석 관련",
                "scapy>=2.4.5",
                "cryptography>=3.4.8"
            ])
        elif project_id == "iot-smarthome":
            requirements.extend([
                "",
                "# IoT 관련",
                "paho-mqtt>=1.6.0"
            ])

        requirements.append("")

        with open(project_path / "requirements.txt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(requirements))

    def create_run_script(self, project_path: Path, project_id: str, project_info: Dict):
        """프로젝트 실행 스크립트 생성"""
        main_file = project_info.get('files', ['run_all_shinsegye.py'])[0]
        name_ko = project_info['name_ko']
        description = project_info['description']

        script_content = f'''#!/usr/bin/env python3
"""
{name_ko} 실행 스크립트
{project_info['name_en']} Launch Script

이 스크립트는 프로젝트를 독립적으로 실행합니다.
"""

import sys
import os
from pathlib import Path

# 루트 디렉토리를 Python 경로에 추가
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print(f"🚀 {name_ko} 시작")
    print(f"   {description}")
    print("=" * 80)
    print()

    # 작업 디렉토리를 루트로 변경
    os.chdir(root_dir)

    # 메인 파일 실행
    main_file = root_dir / "{main_file}"

    if not main_file.exists():
        print(f"❌ 오류: {{main_file}} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"📂 실행 파일: {{main_file}}")
    print()

    # 파일 실행
    with open(main_file, 'r', encoding='utf-8') as f:
        code = compile(f.read(), main_file, 'exec')
        exec(code, {{'__name__': '__main__', '__file__': str(main_file)}})


if __name__ == "__main__":
    main()
'''

        script_path = project_path / f"run_{project_id.replace('-', '_')}.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # 실행 권한 부여
        os.chmod(script_path, 0o755)

    def create_symlinks(self, project_path: Path, project_id: str, project_info: Dict):
        """소스 파일 심볼릭 링크 생성"""
        src_dir = project_path / "src"

        for file_name in project_info.get('files', []):
            source = self.base_path / file_name
            if source.exists():
                target = src_dir / file_name
                try:
                    # 이미 존재하면 제거
                    if target.exists() or target.is_symlink():
                        target.unlink()
                    # 심볼릭 링크 생성 (상대 경로 사용)
                    relative_source = os.path.relpath(source, src_dir)
                    target.symlink_to(relative_source)
                    print(f"  ✓ 링크 생성: {file_name}")
                except Exception as e:
                    print(f"  ⚠️  링크 생성 실패 ({file_name}): {e}")

    def organize_project(self, project_id: str, project_info: Dict):
        """개별 프로젝트 구조화"""
        print(f"\n{'='*80}")
        print(f"📦 프로젝트 구조화: {project_info['name_ko']} ({project_id})")
        print(f"{'='*80}")

        # 1. 폴더 생성
        print("📁 폴더 생성 중...")
        project_path = self.create_project_folder(project_id, project_info)
        print(f"  ✓ {project_path}")

        # 2. README 생성
        print("📝 README.md 생성 중...")
        self.create_readme(project_path, project_id, project_info)
        print(f"  ✓ README.md")

        # 3. requirements.txt 생성
        print("📦 requirements.txt 생성 중...")
        self.create_requirements(project_path, project_id, project_info)
        print(f"  ✓ requirements.txt")

        # 4. 실행 스크립트 생성
        print("🚀 실행 스크립트 생성 중...")
        self.create_run_script(project_path, project_id, project_info)
        print(f"  ✓ run_{project_id.replace('-', '_')}.py")

        # 5. 심볼릭 링크 생성
        print("🔗 소스 파일 링크 생성 중...")
        self.create_symlinks(project_path, project_id, project_info)

        print(f"✅ {project_info['name_ko']} 구조화 완료!")

    def create_master_index(self):
        """전체 프로젝트 인덱스 생성"""
        index_content = f"""# 신세계 프로젝트 분리 폴더 구조
# Shinsegye Projects Separated Structure

> **생성일**: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}  
> **총 프로젝트 수**: {len(self.projects)}

---

## 📋 프로젝트 목록

"""

        # 카테고리별로 분류
        by_category = {}
        for project_id, info in self.projects.items():
            cat = info['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((project_id, info))

        # 카테고리별 출력
        for category in sorted(by_category.keys()):
            index_content += f"\n### {category}\n\n"
            for project_id, info in by_category[category]:
                port_info = f"Port: {info['port']}" if info.get('port') else "No Web UI"
                index_content += f"- **[{info['name_ko']}]({project_id}/README.md)** ({info['name_en']})\n"
                index_content += f"  - {info['description']}\n"
                index_content += f"  - {port_info}\n"
                index_content += f"  - 파일 수: {len(info.get('files', []))}\n"

        index_content += """
---

## 🚀 사용 방법

### 1. 전체 시스템 실행
```bash
# 루트 디렉토리에서
python run_all_shinsegye.py
```

### 2. 개별 프로젝트 실행
```bash
# 프로젝트 폴더에서
cd projects_separated/[프로젝트명]
python run_[프로젝트명].py

# 예시
cd projects_separated/sorisae-core
python run_sorisae_core.py
```

### 3. Docker로 실행
```bash
# 개별 프로젝트
docker-compose -f dockerfiles/docker-compose.all-projects.yml up [서비스명]

# 전체 시스템
docker-compose -f dockerfiles/docker-compose.all-projects.yml up
```

---

## 📁 폴더 구조

각 프로젝트 폴더는 다음과 같은 구조를 가집니다:

```
project-name/
├── src/                 # 소스 파일 (심볼릭 링크)
├── docs/                # 문서
├── data/                # 데이터 파일
├── config/              # 설정 파일
├── README.md            # 프로젝트 설명
├── requirements.txt     # 의존성
└── run_project_name.py  # 실행 스크립트
```

---

## 🔗 관련 문서

- [전체 시스템 README](../README.md)
- [설치 가이드](../INSTALL.md)
- [빠른 시작](../QUICKSTART.md)
- [Docker 가이드](../dockerfiles/README.md)
- [프로그램 분류](../programs_by_category/README.md)

---

## 📝 참고사항

1. **심볼릭 링크**: 실제 소스 파일은 루트 디렉토리에 위치하며, 각 프로젝트의 `src/` 폴더에는 심볼릭 링크로 연결됩니다.
2. **의존성**: 각 프로젝트의 `requirements.txt`는 해당 프로젝트에 필요한 최소 의존성만 포함합니다. 전체 의존성은 루트의 `requirements.txt`를 참고하세요.
3. **독립 실행**: 각 프로젝트는 독립적으로 실행 가능하도록 설계되었지만, 일부 프로젝트는 다른 모듈에 대한 의존성이 있을 수 있습니다.

---

**버전**: 1.0.0  
**상태**: ✅ 프로덕션 준비 완료
"""

        with open(self.projects_root / "README.md", 'w', encoding='utf-8') as f:
            f.write(index_content)

        print(f"\n✅ 마스터 인덱스 생성 완료: {self.projects_root / 'README.md'}")

    def create_summary_json(self):
        """프로젝트 요약 JSON 생성"""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_projects": len(self.projects),
            "projects": {}
        }

        for project_id, info in self.projects.items():
            summary["projects"][project_id] = {
                "name_ko": info['name_ko'],
                "name_en": info['name_en'],
                "category": info['category'],
                "description": info['description'],
                "port": info.get('port'),
                "file_count": len(info.get('files', [])),
                "has_docs": len(info.get('docs', [])) > 0,
                "has_data": 'data' in info or 'modules' in info,
                "path": f"projects_separated/{project_id}"
            }

        json_path = self.projects_root / "projects_summary.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"✅ 프로젝트 요약 JSON 생성 완료: {json_path}")

    def run(self):
        """전체 구조화 실행"""
        print("🚀 신세계 프로젝트 폴더 분리 시작")
        print(f"대상: {len(self.projects)}개 프로젝트")
        print(f"출력 디렉토리: {self.projects_root}")
        print()

        # 프로젝트 루트 디렉토리 생성
        self.projects_root.mkdir(parents=True, exist_ok=True)

        # 각 프로젝트 구조화
        for project_id, project_info in self.projects.items():
            self.organize_project(project_id, project_info)

        # 마스터 인덱스 생성
        print(f"\n{'='*80}")
        print("📚 마스터 인덱스 생성 중...")
        print(f"{'='*80}")
        self.create_master_index()

        # 요약 JSON 생성
        self.create_summary_json()

        print(f"\n{'='*80}")
        print("✅ 전체 프로젝트 폴더 분리 완료!")
        print(f"{'='*80}")
        print(f"\n📂 결과 위치: {self.projects_root.absolute()}")
        print(f"📄 인덱스: {(self.projects_root / 'README.md').absolute()}")
        print()


def main():
    """메인 함수"""
    print("=" * 80)
    print("🧠 신세계 프로젝트 폴더 분리 시스템")
    print("=" * 80)
    print()

    organizer = ProjectOrganizer()
    organizer.run()

    print("🎉 작업이 완료되었습니다!")
    print()


if __name__ == "__main__":
    main()
