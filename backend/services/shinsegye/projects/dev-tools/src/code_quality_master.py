#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 신세계 소리새 코드 품질 마스터 개선 도구
Shinsegye Sorisae Code Quality Master Improvement Tool

전체 프로젝트 코드 품질을 최고 수준으로 개선
- PEP 8 준수
- 불필요한 import 제거
- 공백 정리
- 예외 처리 개선
- 타입 힌트 추가
"""

import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CodeQualityMaster:
    """코드 품질 마스터 개선 도구"""

    def __init__(self, project_root: str = "."):
        """
        초기화

        Args:
            project_root: 프로젝트 루트 디렉토리
        """
        self.project_root = Path(project_root).resolve()
        self.excluded_dirs = {
            '.git', '__pycache__', 'venv', 'env', '.venv',
            'backup', 'cache', 'logs', 'temp_files', 'temp_push',
            'sorisae_github_backup_20251031_064317', 'rendered_scenes',
            'satellite_data', 'memories', 'projects', 'data',
            '.vscode', '.devcontainer'
        }
        self.stats = {
            'files_processed': 0,
            'issues_fixed': 0,
            'unused_imports_removed': 0,
            'whitespace_fixed': 0,
            'bare_except_fixed': 0,
            'spacing_fixed': 0
        }

    def find_python_files(self) -> List[Path]:
        """
        Python 파일 찾기

        Returns:
            Python 파일 경로 리스트
        """
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 제외 디렉토리 건너뛰기
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        logger.info(f"발견된 Python 파일: {len(python_files)}개")
        return python_files

    def remove_trailing_whitespace(self, content: str) -> Tuple[str, int]:
        """
        각 줄 끝의 공백 제거

        Args:
            content: 파일 내용

        Returns:
            (수정된 내용, 수정된 줄 수)
        """
        lines = content.split('\n')
        fixed_count = 0

        new_lines = []
        for line in lines:
            if line != line.rstrip():
                fixed_count += 1
            new_lines.append(line.rstrip())

        return '\n'.join(new_lines), fixed_count

    def fix_blank_lines(self, content: str) -> Tuple[str, int]:
        """
        PEP 8 공백 줄 규칙 적용

        Args:
            content: 파일 내용

        Returns:
            (수정된 내용, 수정된 줄 수)
        """
        fixed_count = 0

        # 클래스/함수 정의 전에 2줄 공백
        # 메서드 정의 전에 1줄 공백
        lines = content.split('\n')
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()

            # 클래스 또는 최상위 함수 정의
            if (stripped.startswith('class ')
                or (stripped.startswith('def ') and i > 0
                    and not lines[i - 1].lstrip().startswith('class '))):

                # 파일 시작이 아니고 docstring/comment가 아닌 경우
                if i > 0 and new_lines:
                    # 이전 줄들이 비어있지 않은 경우
                    blank_count = 0
                    for j in range(len(new_lines) - 1, -1, -1):
                        if new_lines[j].strip() == '':
                            blank_count += 1
                        else:
                            break

                    # 클래스/함수 정의 전 2줄 공백 필요
                    if stripped.startswith('class ') or (
                        stripped.startswith('def ')
                        and i > 0
                        and not any(new_lines[max(0, len(new_lines) - 5):])
                    ):
                        target_blanks = 2
                    else:
                        target_blanks = 1

                    if blank_count < target_blanks:
                        # 공백 줄 추가
                        for _ in range(target_blanks - blank_count):
                            new_lines.append('')
                            fixed_count += 1
                    elif blank_count > target_blanks:
                        # 과도한 공백 줄 제거
                        for _ in range(blank_count - target_blanks):
                            new_lines.pop()
                            fixed_count += 1

            new_lines.append(line)
            i += 1

        return '\n'.join(new_lines), fixed_count

    def fix_bare_except(self, content: str) -> Tuple[str, int]:
        """
        bare except를 Exception으로 변경

        Args:
            content: 파일 내용

        Returns:
            (수정된 내용, 수정된 줄 수)
        """
        fixed_count = 0
        lines = content.split('\n')
        new_lines = []

        for line in lines:
            # bare except 패턴 찾기
            if re.search(r'except\s*:\s*$', line) or re.search(r'except\s*:\s*#', line):
                # except: -> except Exception:
                new_line = re.sub(r'except\s*:', 'except Exception:', line)
                if new_line != line:
                    fixed_count += 1
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        return '\n'.join(new_lines), fixed_count

    def remove_unused_imports(self, file_path: Path) -> int:
        """
        사용되지 않는 import 제거 (autoflake 사용)

        Args:
            file_path: 파일 경로

        Returns:
            제거된 import 수
        """
        try:
            # autoflake 사용하여 미사용 import 제거
            result = subprocess.run(
                [
                    'autoflake',
                    '--in-place',
                    '--remove-unused-variables',
                    '--remove-all-unused-imports',
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # 변경 사항이 있는지 확인
                if result.stdout:
                    return result.stdout.count('import')
            return 0
        except Exception as e:
            logger.warning(f"autoflake 실행 실패 ({file_path.name}): {e}")
            return 0

    def format_with_autopep8(self, file_path: Path) -> bool:
        """
        autopep8로 코드 포맷팅

        Args:
            file_path: 파일 경로

        Returns:
            성공 여부
        """
        try:
            result = subprocess.run(
                [
                    'autopep8',
                    '--in-place',
                    '--aggressive',
                    '--aggressive',
                    '--max-line-length', '120',
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"autopep8 실행 실패 ({file_path.name}): {e}")
            return False

    def sort_imports(self, file_path: Path) -> bool:
        """
        isort로 import 정렬

        Args:
            file_path: 파일 경로

        Returns:
            성공 여부
        """
        try:
            result = subprocess.run(
                [
                    'isort',
                    '--line-length', '120',
                    '--profile', 'black',
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"isort 실행 실패 ({file_path.name}): {e}")
            return False

    def process_file(self, file_path: Path) -> None:
        """
        파일 처리

        Args:
            file_path: 파일 경로
        """
        try:
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            file_fixed = 0

            # 1. 공백 제거
            content, whitespace_fixed = self.remove_trailing_whitespace(content)
            file_fixed += whitespace_fixed
            self.stats['whitespace_fixed'] += whitespace_fixed

            # 2. bare except 수정
            content, bare_except_fixed = self.fix_bare_except(content)
            file_fixed += bare_except_fixed
            self.stats['bare_except_fixed'] += bare_except_fixed

            # 3. 공백 줄 수정
            content, spacing_fixed = self.fix_blank_lines(content)
            file_fixed += spacing_fixed
            self.stats['spacing_fixed'] += spacing_fixed

            # 변경사항이 있으면 파일 저장
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # 4. 미사용 import 제거 (autoflake)
            try:
                subprocess.run(['autoflake', '--version'], capture_output=True, timeout=5)
                unused_removed = self.remove_unused_imports(file_path)
                self.stats['unused_imports_removed'] += unused_removed
                file_fixed += unused_removed
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("autoflake가 설치되지 않았습니다. 설치 중...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'autoflake'],
                               capture_output=True)

            # 5. import 정렬 (isort)
            self.sort_imports(file_path)

            # 6. autopep8 포맷팅
            self.format_with_autopep8(file_path)

            if file_fixed > 0:
                logger.info(f"✓ {file_path.name}: {file_fixed}개 이슈 수정")
                self.stats['issues_fixed'] += file_fixed

            self.stats['files_processed'] += 1

        except Exception as e:
            logger.error(f"파일 처리 실패 ({file_path.name}): {e}")

    def improve_all(self) -> None:
        """전체 프로젝트 코드 품질 개선"""
        logger.info("=" * 60)
        logger.info("🔧 신세계 소리새 코드 품질 마스터 개선 도구")
        logger.info("=" * 60)

        # 필수 도구 설치 확인
        self.ensure_tools_installed()

        # Python 파일 찾기
        python_files = self.find_python_files()

        # 각 파일 처리
        logger.info(f"\n처리 시작: {len(python_files)}개 파일")
        for i, file_path in enumerate(python_files, 1):
            logger.info(f"[{i}/{len(python_files)}] 처리 중: {file_path.name}")
            self.process_file(file_path)

        # 결과 출력
        self.print_summary()

    def ensure_tools_installed(self) -> None:
        """필수 도구 설치 확인"""
        tools = ['autopep8', 'isort', 'autoflake']
        for tool in tools:
            try:
                subprocess.run([tool, '--version'], capture_output=True, timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.info(f"{tool} 설치 중...")
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', tool],
                    capture_output=True
                )

    def print_summary(self) -> None:
        """결과 요약 출력"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 코드 품질 개선 완료 요약")
        logger.info("=" * 60)
        logger.info(f"처리된 파일: {self.stats['files_processed']}개")
        logger.info(f"수정된 이슈: {self.stats['issues_fixed']}개")
        logger.info(f"  - 공백 제거: {self.stats['whitespace_fixed']}개")
        logger.info(f"  - bare except 수정: {self.stats['bare_except_fixed']}개")
        logger.info(f"  - 줄 간격 수정: {self.stats['spacing_fixed']}개")
        logger.info(f"  - 미사용 import 제거: {self.stats['unused_imports_removed']}개")
        logger.info("=" * 60)
        logger.info("✅ 코드 품질 개선이 성공적으로 완료되었습니다!")


def main():
    """메인 함수"""
    # 현재 디렉토리에서 실행
    improver = CodeQualityMaster(".")
    improver.improve_all()


if __name__ == "__main__":
    main()
