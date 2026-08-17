#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 파일 상태 재진단 도구
모든 파일의 정확한 손상 상태를 파악하고 복구 전략을 수립
"""

import ast
import os
from pathlib import Path


class ComprehensiveFileAnalyzer:
    def __init__(self):
        self.project_root = Path.cwd()
        self.critical_files = []
        self.damaged_files = []
        self.healthy_files = []
        self.suspicious_files = []

    def analyze_file_structure(self, file_path):
        """파일 구조 상세 분석"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                return "EMPTY", "빈 파일"

            lines = content.split('\n')
            total_chars = len(content)

            # 한 줄로 압축된 파일 탐지 (더 정확한 기준)
            if len(lines) <= 5 and total_chars > 1000:
                return "SEVERELY_COMPRESSED", f"심각한 압축 (1-5줄에 {total_chars}자)"

            if len(lines) <= 10 and total_chars > 2000:
                return "COMPRESSED", f"압축됨 ({len(lines)}줄에 {total_chars}자)"

            # Python 파일 특별 검사
            if file_path.endswith('.py'):
                # BOM 문자 확인
                if content.startswith('\ufeff'):
                    return "BOM_ERROR", "BOM 문자 포함"

                # 구문 검사
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    return "SYNTAX_ERROR", f"구문 오류: {e}"
                except Exception as e:
                    return "PARSE_ERROR", f"파싱 오류: {e}"

            # 파일 내용이 한 줄에 몰려있는지 확인
            avg_line_length = total_chars / len(lines) if lines else 0
            if avg_line_length > 200:  # 평균 줄 길이가 200자 이상
                return "LINE_TOO_LONG", f"평균 줄 길이 {avg_line_length:.0f}자"

            return "HEALTHY", "정상"

        except UnicodeDecodeError:
            return "ENCODING_ERROR", "인코딩 오류"
        except Exception as e:
            return "ACCESS_ERROR", f"접근 오류: {e}"

    def scan_all_files(self):
        """전체 파일 스캔"""
        print("🔍 전체 워크스페이스 파일 상태 재진단 시작...")
        print("=" * 70)

        file_extensions = ['.py', '.json', '.md', '.txt', '.js', '.html', '.css', '.yml', '.yaml']

        for root, dirs, files in os.walk(self.project_root):
            # 제외할 디렉토리
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'node_modules']]

            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)

                    status, message = self.analyze_file_structure(str(file_path))

                    file_info = {
                        'path': str(relative_path),
                        'full_path': str(file_path),
                        'status': status,
                        'message': message,
                        'size': file_path.stat().st_size if file_path.exists() else 0
                    }

                    # 중요 파일 분류
                    if self.is_critical_file(relative_path):
                        file_info['priority'] = 'CRITICAL'
                        if status != 'HEALTHY':
                            self.critical_files.append(file_info)

                    # 상태별 분류
                    if status == 'HEALTHY':
                        self.healthy_files.append(file_info)
                    elif status in ['SEVERELY_COMPRESSED', 'COMPRESSED', 'SYNTAX_ERROR', 'BOM_ERROR']:
                        self.damaged_files.append(file_info)
                    else:
                        self.suspicious_files.append(file_info)

    def is_critical_file(self, file_path):
        """중요 파일 여부 판단"""
        critical_patterns = [
            'run_all_shinsegye.py',
            'README.md',
            'requirements.txt',
            'sorisae_core_controller.py',
            'app_Sorisae.py',
            'modules/__init__.py',
            'modules/ai_code_manager/sorisae_core_controller.py',
            'modules/sorisae_dashboard_web.py',
            'config/settings.json'
        ]

        path_str = str(file_path).replace('\\', '/')
        return any(pattern in path_str for pattern in critical_patterns)

    def print_analysis_results(self):
        """분석 결과 출력"""
        print(f"\n📊 전체 파일 상태 분석 결과")
        print("=" * 70)

        total_files = len(self.healthy_files) + len(self.damaged_files) + len(self.suspicious_files)

        print(f"📈 전체 통계:")
        print(f"  • 전체 파일: {total_files}개")
        print(f"  • ✅ 정상 파일: {len(self.healthy_files)}개")
        print(f"  • ❌ 손상 파일: {len(self.damaged_files)}개")
        print(f"  • ⚠️ 의심 파일: {len(self.suspicious_files)}개")
        print(f"  • 🚨 중요 파일 손상: {len(self.critical_files)}개")

        # 중요 파일 손상 현황
        if self.critical_files:
            print(f"\n🚨 중요 파일 손상 현황:")
            print("-" * 50)
            for file_info in self.critical_files:
                print(f"❌ {file_info['path']}")
                print(f"   상태: {file_info['status']}")
                print(f"   문제: {file_info['message']}")
                print(f"   크기: {file_info['size']} bytes")
                print()

        # 손상된 파일들 (중요하지 않은 것들도)
        if self.damaged_files:
            print(f"\n💔 손상된 파일 목록 (처음 10개):")
            print("-" * 50)
            for file_info in self.damaged_files[:10]:
                if file_info not in self.critical_files:
                    print(f"❌ {file_info['path']} - {file_info['status']}: {file_info['message']}")

            if len(self.damaged_files) > 10:
                print(f"   ... 및 {len(self.damaged_files) - 10}개 더")

        # 전체 상태 평가
        damage_ratio = len(self.damaged_files) / total_files * 100 if total_files > 0 else 0
        critical_damage_ratio = len(self.critical_files)

        print(f"\n🎯 시스템 상태 평가:")
        print(f"  • 손상률: {damage_ratio:.1f}%")
        print(f"  • 중요 파일 손상: {critical_damage_ratio}개")

        if critical_damage_ratio > 5:
            print("  🚨 긴급 상황: 중요 파일 다수 손상")
            print("  💡 권장: 전체 백업에서 복구 필요")
        elif damage_ratio > 30:
            print("  ⚠️ 심각한 상황: 대규모 파일 손상")
            print("  💡 권장: 백업 복구 필요")
        elif damage_ratio > 10:
            print("  🔧 복구 필요: 부분적 파일 손상")
            print("  💡 권장: 개별 파일 복구")
        else:
            print("  ✅ 양호: 대부분 파일 정상")
            print("  💡 권장: 소수 파일만 수정")

    def generate_recovery_plan(self):
        """복구 계획 생성"""
        print(f"\n🔧 복구 계획 수립")
        print("=" * 50)

        if len(self.critical_files) > 5:
            print("📋 전체 시스템 복구 계획:")
            print("  1. 가장 안전한 백업 식별")
            print("  2. 전체 프로젝트 백업 생성")
            print("  3. 안전한 백업에서 전체 복구")
            print("  4. 시스템 검증 및 테스트")
            return "FULL_RECOVERY"

        elif len(self.damaged_files) > 20:
            print("📋 대규모 파일 복구 계획:")
            print("  1. 백업에서 손상된 파일들 일괄 복구")
            print("  2. 중요 파일 우선 복구")
            print("  3. 시스템 기능 검증")
            return "BULK_RECOVERY"

        else:
            print("📋 개별 파일 복구 계획:")
            print("  1. 중요 파일부터 개별 복구")
            print("  2. 구문 오류 수정")
            print("  3. 기능별 테스트")
            return "INDIVIDUAL_RECOVERY"


def main():
    """메인 실행"""
    print("🔍 소리새 AI 시스템 전체 파일 상태 재진단")
    print("=" * 70)
    print("⚠️  이번에는 모든 파일을 정확히 분석합니다...")

    analyzer = ComprehensiveFileAnalyzer()

    # 전체 스캔 실행
    analyzer.scan_all_files()

    # 결과 출력
    analyzer.print_analysis_results()

    # 복구 계획 수립
    recovery_type = analyzer.generate_recovery_plan()

    print(f"\n💡 다음 단계: {recovery_type} 방식으로 진행 예정")
    print("=" * 70)


if __name__ == "__main__":
    main()
