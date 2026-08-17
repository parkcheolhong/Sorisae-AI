#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 소리새 구문 오류 수정기
Sorisae Syntax Error Fixer

복구된 파일들의 구문 오류를 자동으로 수정합니다.
"""

import re
from pathlib import Path


class SorisaeSyntaxFixer:
    """소리새 구문 오류 수정기"""

    def __init__(self):
        self.root_path = Path.cwd()
        self.fixed_files = []

    def fix_unterminated_strings(self, file_path: Path) -> bool:
        """끝나지 않은 문자열 수정"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 삼중 따옴표 문제 수정
            # ''' 나 """ 이 홀수 개인 경우 수정
            triple_single = content.count("'''")
            triple_double = content.count('"""')

            if triple_single % 2 == 1:
                # 마지막에 ''' 추가
                content = content + "\n'''"

            if triple_double % 2 == 1:
                # 마지막에 """ 추가
                content = content + '\n"""'

            # 일반 문자열 끝 처리
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # 홀따옴표가 홀수 개인 줄 수정
                if line.count("'") % 2 == 1 and not line.strip().startswith('#'):
                    lines[i] = line + "'"

                # 쌍따옴표가 홀수 개인 줄 수정
                if line.count('"') % 2 == 1 and not line.strip().startswith('#'):
                    lines[i] = line + '"'

            content = '\n'.join(lines)

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

        except Exception as e:
            print(f"   ❌ 문자열 수정 실패: {e}")

        return False

    def fix_invalid_characters(self, file_path: Path) -> bool:
        """잘못된 문자 수정"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 잘못된 유니코드 문자들을 안전한 문자로 대체
            replacements = {
                '═': '=',
                '╔': '+',
                '╗': '+',
                '╚': '+',
                '╝': '+',
                '║': '|',
                '━': '-',
                '┌': '+',
                '┐': '+',
                '└': '+',
                '┘': '+',
                '│': '|',
                '├': '+',
                '┤': '+',
                '┬': '+',
                '┴': '+',
                '┼': '+',
                '×': '*',
                '÷': '/',
                '🏙': '',  # 이모지 제거
                '🚀': '',
                '🎯': '',
                '📊': '',
                '💡': '',
                '🔧': '',
                '⚡': '',
                '🌟': '',
            }

            for old_char, new_char in replacements.items():
                content = content.replace(old_char, new_char)

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

        except Exception as e:
            print(f"   ❌ 문자 수정 실패: {e}")

        return False

    def fix_syntax_errors(self, file_path: Path) -> bool:
        """일반적인 구문 오류 수정"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 일반적인 구문 오류 패턴 수정
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # 빈 줄이거나 주석인 경우 건너뛰기
                if not line.strip() or line.strip().startswith('#'):
                    continue

                # 잘못된 들여쓰기 수정 시도
                if line.startswith('  ') and not line.startswith('    '):
                    lines[i] = '    ' + line.lstrip()

                # 콜론 누락 수정 (if, for, def, class 등)
                if re.match(r'^\s*(if|for|while|def|class|try|except|with)\s+.*[^:]\s*$', line):
                    lines[i] = line.rstrip() + ':'

            content = '\n'.join(lines)

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

        except Exception as e:
            print(f"   ❌ 구문 수정 실패: {e}")

        return False

    def fix_encoding_issues(self, file_path: Path) -> bool:
        """인코딩 문제 수정"""
        try:
            # UTF-8 BOM 제거 시도
            with open(file_path, 'rb') as f:
                raw_content = f.read()

            # BOM 제거
            if raw_content.startswith(b'\xff\xfe') or raw_content.startswith(b'\xfe\xff'):
                raw_content = raw_content[2:]
                with open(file_path, 'wb') as f:
                    f.write(raw_content)
                return True
            elif raw_content.startswith(b'\xef\xbb\xbf'):
                raw_content = raw_content[3:]
                with open(file_path, 'wb') as f:
                    f.write(raw_content)
                return True

        except Exception as e:
            print(f"   ❌ 인코딩 수정 실패: {e}")

        return False

    def fix_file(self, file_path: Path) -> bool:
        """단일 파일 수정"""
        print(f"🔧 수정 중: {file_path.name}")

        fixed = False

        # 1. 인코딩 문제 수정
        if self.fix_encoding_issues(file_path):
            print(f"   ✅ 인코딩 수정됨")
            fixed = True

        # 2. 잘못된 문자 수정
        if self.fix_invalid_characters(file_path):
            print(f"   ✅ 잘못된 문자 수정됨")
            fixed = True

        # 3. 끝나지 않은 문자열 수정
        if self.fix_unterminated_strings(file_path):
            print(f"   ✅ 문자열 수정됨")
            fixed = True

        # 4. 일반 구문 오류 수정
        if self.fix_syntax_errors(file_path):
            print(f"   ✅ 구문 수정됨")
            fixed = True

        if fixed:
            self.fixed_files.append(str(file_path))

        return fixed

    def verify_fix(self, file_path: Path) -> bool:
        """수정 결과 검증"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            compile(content, file_path, 'exec')
            return True

        except Exception:
            return False

    def run_syntax_fixes(self):
        """구문 오류가 있는 모든 파일 수정"""
        print("🔧 소리새 구문 오류 수정 시작!")
        print("=" * 50)

        # 구문 오류가 있는 파일들 찾기
        error_files = []

        for py_file in self.root_path.glob("*.py"):
            if "_DAMAGED" in py_file.name or ".compressed_backup" in py_file.name:
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, py_file, 'exec')
            except Exception:
                error_files.append(py_file)

        print(f"📊 구문 오류 파일: {len(error_files)}개")

        # 각 파일 수정
        fixed_count = 0
        verified_count = 0

        for file_path in error_files:
            if self.fix_file(file_path):
                fixed_count += 1

                # 수정 결과 검증
                if self.verify_fix(file_path):
                    verified_count += 1
                    print(f"   ✅ 검증 통과!")
                else:
                    print(f"   ⚠️  추가 수정 필요")

        print("\n" + "=" * 50)
        print("🎉 구문 오류 수정 완료!")
        print(f"📊 요약:")
        print(f"   - 총 오류 파일: {len(error_files)}개")
        print(f"   - 수정 시도: {fixed_count}개")
        print(f"   - 검증 통과: {verified_count}개")

        # 수정 로그 저장
        log_path = self.root_path / "SYNTAX_FIX_LOG.md"
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("# 🔧 구문 오류 수정 로그\n\n")
            f.write(f"**수정 일시**: 방금\n\n")
            f.write("## 수정된 파일들\n\n")
            for file_path in self.fixed_files:
                f.write(f"- {Path(file_path).name}\n")

        print(f"📄 수정 로그 저장: {log_path}")


def main():
    """메인 실행"""
    fixer = SorisaeSyntaxFixer()
    fixer.run_syntax_fixes()


if __name__ == "__main__":
    main()
