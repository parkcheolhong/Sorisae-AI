#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🏢 소리새 프로젝트 아키텍처 분석 & 컨트롤 타워 검증

전체 시스템이 중앙 집중식으로 잘 구성되어 있는지 분석합니다.
"""

from pathlib import Path


class ProjectArchitectureAnalyzer:
    """프로젝트 아키텍처 분석기"""

    def __init__(self, project_root="c:/Projects/Shinsegye_Main"):
        self.project_root = Path(project_root)
        self.analysis_results = {}

    def analyze_control_tower_structure(self):
        """컨트롤 타워 구조 분석"""
        print("🏢 소리새 프로젝트 아키텍처 분석")
        print("=" * 60)

        # 1. 핵심 컨트롤 타워 파일 위치 확인
        control_tower_files = {
            "SorisaeCore": "modules/ai_code_manager/sorisae_core_controller.py",
            "Dashboard": "modules/sorisae_dashboard_web.py",
            "MainEntry": "run_all_shinsegye.py",
            "AppEntry": "app_Sorisae.py"
        }

        print("📋 1. 핵심 컨트롤 타워 구성 요소")
        print("-" * 40)

        for name, path in control_tower_files.items():
            full_path = self.project_root / path
            exists = full_path.exists()
            size = full_path.stat().st_size if exists else 0
            status = "✅ 존재" if exists else "❌ 누락"

            print(f"   {name:15}: {status} ({size:,} bytes)")
            if exists:
                print(f"   {'':15}  📁 {path}")

        return control_tower_files

    def analyze_module_integration(self):
        """모듈 통합 구조 분석"""
        print("\n📦 2. 모듈 통합 구조 분석")
        print("-" * 40)

        # AI 코드 매니저 모듈들
        ai_modules_dir = self.project_root / "modules" / "ai_code_manager"
        if ai_modules_dir.exists():
            ai_modules = list(ai_modules_dir.glob("*.py"))
            print(f"   🤖 AI 코드 매니저: {len(ai_modules)}개 모듈")

            key_modules = [
                "sorisae_core_controller.py",  # 핵심 컨트롤러
                "nlp_processor.py",           # 자연어 처리
                "ai_music_composer.py",       # 음악 작곡
                "music_chat_system.py",       # 채팅 시스템
                "creative_sorisae_engine.py",  # 창조 엔진
                "persona_system.py",          # 페르소나 시스템
                "memory_palace.py",           # 기억 궁전
                "self_learning_engine.py"     # 자가 학습
            ]

            for module in key_modules:
                module_path = ai_modules_dir / module
                exists = module_path.exists()
                status = "✅" if exists else "❌"
                print(f"      {status} {module}")

        # 플러그인 시스템
        plugins_dir = self.project_root / "modules" / "plugins"
        if plugins_dir.exists():
            plugins = list(plugins_dir.glob("*.py"))
            print(f"   🔌 플러그인 시스템: {len(plugins)}개 플러그인")

        # 테스트 시스템
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            tests = list(tests_dir.glob("*.py"))
            print(f"   🧪 테스트 시스템: {len(tests)}개 테스트")

    def analyze_configuration_management(self):
        """설정 관리 구조 분석"""
        print("\n⚙️ 3. 설정 관리 구조 분석")
        print("-" * 40)

        config_files = [
            "config/settings.json",
            "config/nlp_patterns.json",
            "config/security_config.json",
            "config/voice_settings.json",
            "modules/ai_code_manager/settings.json",
            "requirements.txt"
        ]

        for config_file in config_files:
            config_path = self.project_root / config_file
            exists = config_path.exists()
            status = "✅" if exists else "❌"
            print(f"   {status} {config_file}")

    def analyze_command_flow(self):
        """명령 처리 흐름 분석"""
        print("\n🔄 4. 명령 처리 흐름 분석")
        print("-" * 40)

        try:
            # SorisaeCore 파일 분석
            core_path = self.project_root / "modules/ai_code_manager/sorisae_core_controller.py"
            if core_path.exists():
                with open(core_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 주요 메서드들 확인
                methods = {
                    "listen()": "음성 인식",
                    "speak()": "음성 출력",
                    "handle_creative_commands()": "창의적 명령 처리",
                    "process_voice_command()": "음성 명령 처리",
                    "run()": "메인 실행 루프"
                }

                print("   📝 핵심 처리 메서드:")
                for method, description in methods.items():
                    exists = f"def {method.split('(')[0]}" in content
                    status = "✅" if exists else "❌"
                    print(f"      {status} {method:25} - {description}")

        except Exception as e:
            print(f"   ❌ 분석 오류: {e}")

    def analyze_integration_quality(self):
        """통합 품질 분석"""
        print("\n🎯 5. 통합 품질 분석")
        print("-" * 40)

        integration_aspects = {
            "중앙집중식 제어": "SorisaeCore가 모든 모듈을 관리",
            "모듈간 통신": "표준화된 인터페이스 사용",
            "설정 통합": "중앙집중식 설정 관리",
            "로깅 통합": "통합 로깅 시스템",
            "플러그인 아키텍처": "확장 가능한 플러그인 시스템",
            "웹 대시보드": "실시간 모니터링 및 제어",
            "API 통합": "RESTful API 제공",
            "테스트 커버리지": "종합적인 테스트 시스템"
        }

        scores = {}
        total_score = 0

        for aspect, description in integration_aspects.items():
            # 간단한 휴리스틱으로 점수 계산
            score = self._evaluate_aspect(aspect)
            scores[aspect] = score
            total_score += score

            status = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
            print(f"   {status} {aspect:20}: {score}/10 - {description}")

        avg_score = total_score / len(integration_aspects)
        overall_status = "🟢 우수" if avg_score >= 8 else "🟡 양호" if avg_score >= 6 else "🔴 개선필요"

        print(f"\n   📊 전체 통합 점수: {avg_score:.1f}/10 {overall_status}")

        return scores, avg_score

    def _evaluate_aspect(self, aspect):
        """특정 측면의 점수 평가"""
        # 파일 존재 여부와 구조를 기반으로 간단한 점수 계산
        if aspect == "중앙집중식 제어":
            core_exists = (self.project_root / "modules/ai_code_manager/sorisae_core_controller.py").exists()
            return 9 if core_exists else 3

        elif aspect == "모듈간 통신":
            # 주요 모듈들이 존재하는지 확인
            key_modules = ["nlp_processor.py", "creative_sorisae_engine.py", "persona_system.py"]
            existing_count = sum(1 for m in key_modules if (self.project_root / "modules/ai_code_manager" / m).exists())
            return min(10, existing_count * 3 + 1)

        elif aspect == "설정 통합":
            config_exists = (self.project_root / "modules/ai_code_manager/settings.json").exists()
            return 8 if config_exists else 4

        elif aspect == "웹 대시보드":
            dashboard_exists = (self.project_root / "modules/sorisae_dashboard_web.py").exists()
            return 9 if dashboard_exists else 2

        elif aspect == "플러그인 아키텍처":
            plugins_dir = self.project_root / "modules/plugins"
            plugin_count = len(list(plugins_dir.glob("*.py"))) if plugins_dir.exists() else 0
            return min(10, plugin_count + 2)

        elif aspect == "테스트 커버리지":
            tests_dir = self.project_root / "tests"
            test_count = len(list(tests_dir.glob("*.py"))) if tests_dir.exists() else 0
            return min(10, test_count)

        else:
            return 7  # 기본 점수

    def generate_recommendations(self, scores, avg_score):
        """개선 권장사항 생성"""
        print("\n💡 6. 개선 권장사항")
        print("-" * 40)

        if avg_score >= 8:
            print("   🎉 전반적으로 우수한 아키텍처입니다!")
            print("   ✨ 소리새가 효과적인 컨트롤 타워 역할을 하고 있습니다.")

        elif avg_score >= 6:
            print("   👍 양호한 구조이지만 몇 가지 개선점이 있습니다:")

        else:
            print("   ⚠️ 개선이 필요한 영역들이 있습니다:")

        # 낮은 점수 영역에 대한 구체적 권장사항
        low_score_aspects = {k: v for k, v in scores.items() if v < 7}

        recommendations = {
            "중앙집중식 제어": "SorisaeCore 클래스를 더 체계적으로 구조화하세요",
            "모듈간 통신": "표준화된 인터페이스와 이벤트 시스템을 도입하세요",
            "설정 통합": "모든 설정을 중앙 설정 파일로 통합하세요",
            "로깅 통합": "통합 로깅 시스템을 구축하세요",
            "API 통합": "RESTful API를 더 체계적으로 설계하세요",
            "테스트 커버리지": "단위 테스트와 통합 테스트를 확충하세요"
        }

        for aspect in low_score_aspects:
            if aspect in recommendations:
                print(f"   📌 {aspect}: {recommendations[aspect]}")

    def run_full_analysis(self):
        """전체 분석 실행"""
        self.analyze_control_tower_structure()
        self.analyze_module_integration()
        self.analyze_configuration_management()
        self.analyze_command_flow()
        scores, avg_score = self.analyze_integration_quality()
        self.generate_recommendations(scores, avg_score)

        print("\n" + "=" * 60)
        print("📊 분석 완료!")

        # 최종 판정
        if avg_score >= 8:
            print("🏆 결론: 소리새는 훌륭한 컨트롤 타워 역할을 하고 있습니다!")
        elif avg_score >= 6:
            print("👍 결론: 소리새는 양호한 컨트롤 타워 역할을 하고 있습니다.")
        else:
            print("⚠️ 결론: 컨트롤 타워 구조에 개선이 필요합니다.")

        return scores, avg_score


if __name__ == "__main__":
    analyzer = ProjectArchitectureAnalyzer()
    analyzer.run_full_analysis()
