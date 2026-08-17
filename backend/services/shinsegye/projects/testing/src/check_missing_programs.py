#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로그램 유실 상태 확인 스크립트
Check for Missing Programs Script

이 스크립트는 프로젝트에서 예상되는 프로그램들이 모두 존재하는지 확인합니다.
This script verifies that all expected programs exist in the project.
"""

import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent

# 예상되는 핵심 프로그램 목록
EXPECTED_PROGRAMS = {
    "core": [
        "run_all_shinsegye.py",
        "app_Sorisae.py",
        "sorisae_core_controller.py",
    ],
    "modules": [
        "modules/ai_code_manager/sorisae_core_controller.py",
        "modules/ai_code_manager/nlp_processor.py",
        "modules/ai_code_manager/ai_music_composer.py",
        "modules/ai_code_manager/dream_interpreter.py",
        "modules/ai_code_manager/emotion_color_therapist.py",
        "modules/ai_code_manager/memory_palace.py",
        "modules/ai_code_manager/future_prediction_engine.py",
        "modules/ai_code_manager/creative_sorisae_engine.py",
        "modules/ai_code_manager/ai_collaboration_network.py",
        "modules/ai_code_manager/creative_coding_assistant.py",
        "modules/ai_code_manager/auto_feature_expansion.py",
        "modules/ai_code_manager/auto_refactor.py",
        "modules/ai_code_manager/analyzer.py",
        "modules/ai_code_manager/code_reviewer.py",
        "modules/ai_code_manager/git_sync.py",
        "modules/ai_code_manager/version_tracker.py",
        "modules/ai_code_manager/virtual_dev_team.py",
        "modules/ai_code_manager/self_learning_engine.py",
        "modules/ai_code_manager/personal_ai_tutor.py",
        "modules/ai_code_manager/persona_system.py",
        "modules/ai_code_manager/smart_plugin_generator.py",
        "modules/ai_code_manager/realtime_game_generator.py",
        "modules/ai_code_manager/ai_speech_tts.py",
        "modules/ai_code_manager/autonomous_shopping_mall.py",
        "modules/ai_code_manager/autonomous_marketing_system.py",
        "modules/ai_code_manager/multi_agent_shopping_system.py",
        "modules/ai_code_manager/music_chat_system.py",
        "modules/ai_code_manager/music_chat_web.py",
    ],
    "dashboard": [
        "sorisae_dashboard_web.py",
        "modules/sorisae_dashboard_web.py",
        "launch_dashboard.py",
        "simple_dashboard.py",
        "shopping_mall_dashboard.py",
    ],
    "utilities": [
        "setup.py",
        "verify_install.py",
        "completion_checker.py",
        "project_review_verification.py",
        "structure_cleaner.py",
        "system_cleanup.py",
    ],
    "demos": [
        "autonomous_shopping_demo.py",
        "security_demo.py",
        "new_features_demo.py",
    ],
    "investment": [
        "sorisae_investment_advisor_200.py",
        "sorisae_dual_brain_stock_system.py",
        "sorisae_dual_brain_comparison.py",
        "stock_prediction_200_percent.py",
    ],
    "games": [
        "sorisae_earning_game.py",
        "sorisae_game_concept_design.py",
        "sorisae_game_economy_system.py",
        "sorisae_creative_revenue_detail.py",
        "game_earning_analysis.py",
    ],
    "advanced": [
        "sorisae_transcendent_102.py",
        "next_gen_features_102_percent.py",
        "sorisae_unified_launcher.py",
        "trend_idea_generator.py",
    ],
    "security": [
        "security_key_manager.py",
        "security_test_suite.py",
        "show_access_keys.py",
    ],
    "analysis": [
        "analyze_architecture.py",
        "control_tower_analysis.py",
        "detailed_technical_report.py",
        "syno_check.py",
    ],
    "servers": [
        "start_music_chat_server.py",
    ],
    "testing": [
        "run_all_tests.py",
        "test_creative_probability.py",
        "test_music_chat_integration.py",
    ],
    "configuration": [
        "voice_tuner.py",
    ],
}

# 예상되는 문서 파일들
EXPECTED_DOCS = [
    "README.md",
    "INSTALL.md",
    "QUICKSTART.md",
    "SECURITY.md",
    "DESIGN.md",
    "LICENSE",
]

# 예상되는 설정 파일들
EXPECTED_CONFIG_FILES = [
    "requirements.txt",
    "requirements-minimal.txt",
    "setup.py",
    ".gitignore",
]


def check_file_exists(filepath):
    """파일이 존재하는지 확인"""
    full_path = PROJECT_ROOT / filepath
    return full_path.exists(), full_path


def get_file_size(filepath):
    """파일 크기 반환"""
    full_path = PROJECT_ROOT / filepath
    if full_path.exists():
        return full_path.stat().st_size
    return 0


def format_size(size_bytes):
    """바이트를 읽기 쉬운 형식으로 변환"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def check_programs():
    """모든 프로그램 파일 확인"""
    print("=" * 80)
    print("🔍 프로그램 유실 상태 확인 보고서")
    print("   Program Status Verification Report")
    print("=" * 80)
    print(f"\n검토 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    missing_files = []
    existing_files = []
    total_files = 0
    total_size = 0

    # 각 카테고리별로 확인
    for category, files in EXPECTED_PROGRAMS.items():
        print(f"\n{'=' * 80}")
        print(f"📂 {category.upper()} 카테고리")
        print(f"{'=' * 80}")

        category_missing = []
        category_existing = []

        for filepath in files:
            total_files += 1
            exists, full_path = check_file_exists(filepath)
            size = get_file_size(filepath)

            if exists:
                existing_files.append(filepath)
                category_existing.append(filepath)
                total_size += size
                status = "✅"
                size_str = format_size(size)
            else:
                missing_files.append(filepath)
                category_missing.append(filepath)
                status = "❌"
                size_str = "N/A"

            print(f"{status} {filepath:60s} {size_str:>10s}")

        # 카테고리 요약
        print(f"\n카테고리 요약: {len(category_existing)}/{len(files)} 파일 존재")
        if category_missing:
            print(f"⚠️  누락된 파일: {len(category_missing)}개")

    # 전체 요약
    print(f"\n{'=' * 80}")
    print("📊 전체 요약")
    print(f"{'=' * 80}")
    print(f"✅ 존재하는 파일: {len(existing_files)}/{total_files} ({len(existing_files) / total_files * 100:.1f}%)")
    print(f"❌ 누락된 파일: {len(missing_files)}/{total_files} ({len(missing_files) / total_files * 100:.1f}%)")
    print(f"💾 전체 파일 크기: {format_size(total_size)}")

    # 누락된 파일 상세 보고
    if missing_files:
        print(f"\n{'=' * 80}")
        print("⚠️  누락된 파일 상세 목록")
        print(f"{'=' * 80}")
        for filepath in missing_files:
            print(f"  ❌ {filepath}")
    else:
        print(f"\n🎉 모든 예상 프로그램이 존재합니다!")

    return missing_files, existing_files


def check_documentation():
    """문서 파일 확인"""
    print(f"\n{'=' * 80}")
    print("📚 문서 파일 확인")
    print(f"{'=' * 80}")

    missing_docs = []

    for doc in EXPECTED_DOCS:
        exists, full_path = check_file_exists(doc)
        size = get_file_size(doc)

        if exists:
            status = "✅"
            size_str = format_size(size)
        else:
            missing_docs.append(doc)
            status = "❌"
            size_str = "N/A"

        print(f"{status} {doc:40s} {size_str:>10s}")

    if missing_docs:
        print(f"\n⚠️  누락된 문서: {len(missing_docs)}개")
        for doc in missing_docs:
            print(f"  ❌ {doc}")
    else:
        print(f"\n✅ 모든 주요 문서가 존재합니다!")

    return missing_docs


def check_configuration_files():
    """설정 파일 확인"""
    print(f"\n{'=' * 80}")
    print("⚙️  설정 파일 확인")
    print(f"{'=' * 80}")

    missing_config = []

    for config_file in EXPECTED_CONFIG_FILES:
        exists, full_path = check_file_exists(config_file)
        size = get_file_size(config_file)

        if exists:
            status = "✅"
            size_str = format_size(size)
        else:
            missing_config.append(config_file)
            status = "❌"
            size_str = "N/A"

        print(f"{status} {config_file:40s} {size_str:>10s}")

    if missing_config:
        print(f"\n⚠️  누락된 설정 파일: {len(missing_config)}개")
        for config in missing_config:
            print(f"  ❌ {config}")
    else:
        print(f"\n✅ 모든 설정 파일이 존재합니다!")

    return missing_config


def scan_for_additional_files():
    """예상 목록에 없는 추가 파일 탐색"""
    print(f"\n{'=' * 80}")
    print("🔎 추가 파일 탐색 (예상 목록에 없는 파일)")
    print(f"{'=' * 80}")

    # 모든 예상 파일을 플랫 리스트로 변환
    all_expected = set()
    for files in EXPECTED_PROGRAMS.values():
        all_expected.update(files)

    # 실제 Python 파일 찾기
    actual_files = set()
    for py_file in PROJECT_ROOT.glob("*.py"):
        if py_file.name != "__init__.py":
            actual_files.add(py_file.name)

    for py_file in PROJECT_ROOT.glob("modules/**/*.py"):
        if py_file.name != "__init__.py":
            relative_path = py_file.relative_to(PROJECT_ROOT)
            actual_files.add(str(relative_path).replace("\\", "/"))

    # 예상 목록과 비교
    additional_files = []
    for actual in sorted(actual_files):
        # 루트 파일인 경우
        if "/" not in actual:
            if actual not in [f for files in EXPECTED_PROGRAMS.values() for f in files]:
                additional_files.append(actual)
        else:
            if actual not in [f for files in EXPECTED_PROGRAMS.values() for f in files]:
                additional_files.append(actual)

    if additional_files:
        print(f"\n발견된 추가 파일: {len(additional_files)}개\n")
        for filepath in additional_files[:20]:  # 처음 20개만 표시
            size = get_file_size(filepath)
            print(f"  📄 {filepath:60s} {format_size(size):>10s}")

        if len(additional_files) > 20:
            print(f"\n... 그 외 {len(additional_files) - 20}개 더 있음")
    else:
        print(f"\n추가 파일 없음 (모든 파일이 예상 목록에 있음)")

    return additional_files


def generate_summary_report(missing_programs, missing_docs, missing_config):
    """최종 요약 보고서 생성"""
    print(f"\n{'=' * 80}")
    print("📋 최종 요약 보고서")
    print(f"{'=' * 80}")

    total_missing = len(missing_programs) + len(missing_docs) + len(missing_config)

    if total_missing == 0:
        print("\n✅ 모든 예상 파일이 존재합니다!")
        print("   프로젝트 상태: 🟢 우수 (Excellent)")
        print("\n   프로그램 유실 없음 - 모든 핵심 파일이 정상적으로 존재합니다.")
        status = "PASS"
    else:
        print(f"\n⚠️  총 {total_missing}개의 파일이 누락되었습니다:")
        print(f"   - 프로그램: {len(missing_programs)}개")
        print(f"   - 문서: {len(missing_docs)}개")
        print(f"   - 설정: {len(missing_config)}개")

        if total_missing <= 5:
            print("\n   프로젝트 상태: 🟡 양호 (Good) - 일부 파일 누락")
            status = "WARNING"
        else:
            print("\n   프로젝트 상태: 🔴 주의 (Attention) - 여러 파일 누락")
            status = "CRITICAL"

    print(f"\n{'=' * 80}")
    print(f"검토 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")

    return status, total_missing


def main():
    """메인 실행 함수"""
    try:
        # 프로그램 확인
        missing_programs, existing_programs = check_programs()

        # 문서 확인
        missing_docs = check_documentation()

        # 설정 파일 확인
        missing_config = check_configuration_files()

        # 추가 파일 탐색
        scan_for_additional_files()

        # 최종 요약
        status, total_missing = generate_summary_report(
            missing_programs, missing_docs, missing_config
        )

        # 종료 코드 설정
        if status == "PASS":
            return 0
        elif status == "WARNING":
            return 1
        else:
            return 2

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
