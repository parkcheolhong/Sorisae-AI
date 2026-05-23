#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 전체 검토 및 최근 파일 반영 여부 확인 스크립트
Project Review and Recent File Verification Script
"""

import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class ProjectReviewer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root).resolve()
        self.issues = []
        self.warnings = []
        self.info = []

    def log_issue(self, message):
        """중대한 문제 기록"""
        self.issues.append(f"❌ {message}")

    def log_warning(self, message):
        """경고 사항 기록"""
        self.warnings.append(f"⚠️  {message}")

    def log_info(self, message):
        """정보 기록"""
        self.info.append(f"ℹ️  {message}")

    def check_duplicate_files(self):
        """중복 파일 확인"""
        print("\n" + "=" * 70)
        print("📂 중복 파일 검사")
        print("=" * 70)

        file_dict = defaultdict(list)

        # venv, .git, backups 제외
        exclude_dirs = {'venv', '.git', 'backups', '__pycache__', '.history'}

        for root, dirs, files in os.walk(self.project_root):
            # 제외할 디렉토리 필터링
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    file_dict[file].append(file_path)

        duplicates_found = False
        for filename, paths in file_dict.items():
            if len(paths) > 1:
                duplicates_found = True
                sizes = [path.stat().st_size for path in paths]

                # 크기가 다른 경우 중복으로 간주
                if len(set(sizes)) > 1:
                    self.log_warning(f"중복 파일 발견: {filename}")
                    for path, size in zip(paths, sizes):
                        rel_path = path.relative_to(self.project_root)
                        print(f"   - {rel_path} ({size} bytes)")

        if not duplicates_found:
            self.log_info("중복 파일 없음")
            print("✅ 중복 파일 없음")

    def check_import_consistency(self):
        """Import 경로 일관성 확인"""
        print("\n" + "=" * 70)
        print("🔍 Import 경로 일관성 검사")
        print("=" * 70)

        # 주요 파일 확인
        main_file = self.project_root / "run_all_shinsegye.py"

        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # SorisaeCore import 확인
            if 'from modules.ai_code_manager.sorisae_core_controller import SorisaeCore' in content:
                self.log_info("SorisaeCore import 경로 정상")
                print("✅ SorisaeCore import: modules.ai_code_manager.sorisae_core_controller")
            else:
                self.log_issue("SorisaeCore import 경로 확인 필요")

            # Dashboard import 확인
            if 'from modules.sorisae_dashboard_web import run_dashboard' in content:
                self.log_info("Dashboard import 경로 정상")
                print("✅ Dashboard import: modules.sorisae_dashboard_web")
            else:
                self.log_warning("Dashboard import 경로 확인 필요")
        else:
            self.log_issue("run_all_shinsegye.py 파일이 존재하지 않음")

    def check_file_structure(self):
        """파일 구조 확인"""
        print("\n" + "=" * 70)
        print("🏗️  파일 구조 검사")
        print("=" * 70)

        expected_structure = {
            'modules': ['ai_code_manager', 'plugins', 'sorisae'],
            'config': [],
            'data': [],
            'logs': [],
            'tests': []
        }

        for dir_name, subdirs in expected_structure.items():
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"✅ {dir_name}/ 존재")

                # 하위 디렉토리 확인
                for subdir in subdirs:
                    subdir_path = dir_path / subdir
                    if subdir_path.exists():
                        py_files = list(subdir_path.glob('*.py'))
                        print(f"   ✅ {dir_name}/{subdir}/ ({len(py_files)} Python 파일)")
                    else:
                        self.log_warning(f"{dir_name}/{subdir}/ 디렉토리 없음")
            else:
                self.log_warning(f"{dir_name}/ 디렉토리 없음")

    def check_core_modules(self):
        """핵심 모듈 존재 확인"""
        print("\n" + "=" * 70)
        print("🧩 핵심 모듈 존재 확인")
        print("=" * 70)

        core_modules = [
            'modules/ai_code_manager/sorisae_core_controller.py',
            'modules/ai_code_manager/nlp_processor.py',
            'modules/ai_code_manager/ai_music_composer.py',
            'modules/ai_code_manager/dream_interpreter.py',
            'modules/ai_code_manager/emotion_color_therapist.py',
            'modules/sorisae_dashboard_web.py',
            'run_all_shinsegye.py'
        ]

        for module in core_modules:
            module_path = self.project_root / module
            if module_path.exists():
                size = module_path.stat().st_size
                print(f"✅ {module} ({size:,} bytes)")
            else:
                self.log_issue(f"핵심 모듈 누락: {module}")

    def check_documentation(self):
        """문서화 상태 확인"""
        print("\n" + "=" * 70)
        print("📚 문서화 상태 확인")
        print("=" * 70)

        docs = [
            'README.md',
            'INSTALL.md',
            'QUICKSTART.md',
            'PROJECT_REVIEW_2025-10-24.md',
            'CURRENT_STATUS_QUICK_KO.md'
        ]

        for doc in docs:
            doc_path = self.project_root / doc
            if doc_path.exists():
                size = doc_path.stat().st_size
                print(f"✅ {doc} ({size:,} bytes)")
            else:
                self.log_warning(f"문서 누락: {doc}")

    def check_gitignore(self):
        """gitignore 설정 확인"""
        print("\n" + "=" * 70)
        print("🚫 .gitignore 설정 확인")
        print("=" * 70)

        gitignore_path = self.project_root / '.gitignore'

        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                content = f.read()

            required_patterns = [
                'venv/',
                '__pycache__/',
                '*.pyc',
                'logs/',
                '.vscode/'
            ]

            for pattern in required_patterns:
                if pattern in content:
                    print(f"✅ {pattern}")
                else:
                    self.log_warning(f".gitignore에 {pattern} 패턴 누락")

            self.log_info(".gitignore 파일 존재")
        else:
            self.log_warning(".gitignore 파일 없음")

    def count_python_files(self):
        """Python 파일 통계"""
        print("\n" + "=" * 70)
        print("📊 Python 파일 통계")
        print("=" * 70)

        exclude_dirs = {'venv', '.git', 'backups', '__pycache__', '.history'}

        py_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith('.py'):
                    py_files.append(Path(root) / file)

        print(f"📝 총 Python 파일: {len(py_files)}개")

        # 디렉토리별 분류
        dir_count = defaultdict(int)
        for py_file in py_files:
            rel_path = py_file.relative_to(self.project_root)
            if len(rel_path.parts) > 1:
                dir_count[rel_path.parts[0]] += 1
            else:
                dir_count['root'] += 1

        for dir_name, count in sorted(dir_count.items()):
            print(f"   - {dir_name}: {count}개")

    def generate_report(self):
        """종합 보고서 생성"""
        print("\n" + "=" * 70)
        print("📋 종합 검토 보고서")
        print("=" * 70)

        print(f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"프로젝트 경로: {self.project_root}")

        if self.issues:
            print(f"\n🔴 중대한 문제 ({len(self.issues)}건):")
            for issue in self.issues:
                print(f"  {issue}")
        else:
            print("\n✅ 중대한 문제 없음")

        if self.warnings:
            print(f"\n🟡 경고 사항 ({len(self.warnings)}건):")
            for warning in self.warnings:
                print(f"  {warning}")
        else:
            print("\n✅ 경고 사항 없음")

        if self.info:
            print(f"\n📝 정보 ({len(self.info)}건):")
            for info in self.info[:5]:  # 처음 5개만 표시
                print(f"  {info}")

        # 종합 평가
        print("\n" + "=" * 70)
        print("🎯 종합 평가")
        print("=" * 70)

        if len(self.issues) == 0 and len(self.warnings) <= 3:
            print("✅ 프로젝트 상태: 우수")
            print("💚 최근 파일들이 적절히 반영되어 있습니다.")
        elif len(self.issues) == 0:
            print("🟡 프로젝트 상태: 양호")
            print("💛 일부 개선이 권장됩니다.")
        else:
            print("🔴 프로젝트 상태: 주의 필요")
            print("❤️  중대한 문제를 해결해야 합니다.")

    def run_all_checks(self):
        """모든 검사 실행"""
        print("\n" + "🔍 프로젝트 전체 검토 시작 🔍".center(70))

        self.check_duplicate_files()
        self.check_import_consistency()
        self.check_file_structure()
        self.check_core_modules()
        self.check_documentation()
        self.check_gitignore()
        self.count_python_files()
        self.generate_report()

        print("\n" + "✨ 검토 완료 ✨".center(70) + "\n")

        return len(self.issues) == 0


def main():
    """메인 함수"""
    reviewer = ProjectReviewer()
    success = reviewer.run_all_checks()

    # 검사 결과에 따라 종료 코드 반환
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
