#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import glob


class AdvancedSyntaxFixer:
    """고급 구문 수정기 - 더욱 정밀한 수정"""

    def __init__(self):
        self.fixed_files = 0
        self.failed_files = 0
        self.log_entries = []

    def fix_encoding_issues(self, content: str) -> str:
        """인코딩 문제 수정"""
        # 잘못된 UTF-8 바이트 제거
        content = content.encode('utf-8', errors='ignore').decode('utf-8')

        # BOM 제거
        if content.startswith('\ufeff'):
            content = content[1:]

        return content

    def fix_unicode_issues(self, content: str) -> str:
        """유니코드 문제 수정"""
        # 잘못된 유니코드 문자 제거/변경
        unicode_fixes = {
            '🏢': '"building"',
            '🤖': '"robot"',
            '🎯': '"target"',
            '💡': '"idea"',
            '🚀': '"rocket"',
            '⭐': '"star"',
            '📊': '"chart"',
            '🔧': '"tool"',
            '⚡': '"lightning"',
            '🎨': '"art"'
        }

        for char, replacement in unicode_fixes.items():
            content = content.replace(char, replacement)

        return content

    def fix_string_literals(self, content: str) -> str:
        """문자열 리터럴 수정"""
        lines = content.split('\n')
        fixed_lines = []
        in_triple_quote = False
        triple_quote_type = None

        for i, line in enumerate(lines):
            # 삼중 따옴표 상태 추적
            if '"""' in line or "'''" in line:
                quote_count_double = line.count('"""')
                quote_count_single = line.count("'''")

                if quote_count_double % 2 == 1:
                    in_triple_quote = not in_triple_quote
                    triple_quote_type = '"""'
                elif quote_count_single % 2 == 1:
                    in_triple_quote = not in_triple_quote
                    triple_quote_type = "'''"

            # 종료되지 않은 문자열 수정
            if not in_triple_quote:
                # 홑따옴표 문제 수정
                single_quote_count = line.count("'") - line.count("\\'")
                if single_quote_count % 2 == 1 and not line.strip().endswith('\\'):
                    if not line.strip().endswith("'"):
                        line += "'"

                # 쌍따옴표 문제 수정
                double_quote_count = line.count('"') - line.count('\\"')
                if double_quote_count % 2 == 1 and not line.strip().endswith('\\'):
                    if not line.strip().endswith('"'):
                        line += '"'

            fixed_lines.append(line)

        # 마지막에 삼중 따옴표가 열려있다면 닫기
        if in_triple_quote and triple_quote_type:
            fixed_lines.append(triple_quote_type)

        return '\n'.join(fixed_lines)

    def fix_syntax_errors(self, content: str) -> str:
        """일반적인 구문 오류 수정"""
        # 잘못된 괄호 매칭 수정
        content = self.fix_bracket_matching(content)

        # 잘못된 들여쓰기 수정
        content = self.fix_indentation(content)

        return content

    def fix_bracket_matching(self, content: str) -> str:
        """괄호 매칭 수정"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # {} 괄호 수정
            if line.count('{') != line.count('}'):
                # 잘못된 } 를 ] 로 변경 (리스트/딕셔너리 문맥에 따라)
                if '[' in line and '}' in line and ']' not in line:
                    line = line.replace('}', ']')

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_indentation(self, content: str) -> str:
        """들여쓰기 수정"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 탭을 4개 공백으로 변환
            line = line.replace('\t', '    ')
            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_file(self, file_path: str) -> bool:
        """파일 수정"""
        try:
            print(f"🔧 수정 중: {file_path}")

            # 파일 읽기 (여러 인코딩 시도)
            content = None
            encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin1']

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                print(f"   ❌ 인코딩 읽기 실패")
                return False

            # 백업 생성
            backup_path = f"{file_path}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 수정 적용
            original_content = content
            content = self.fix_encoding_issues(content)
            content = self.fix_unicode_issues(content)
            content = self.fix_string_literals(content)
            content = self.fix_syntax_errors(content)

            # 변경사항이 있는지 확인
            if content != original_content:
                print(f"   ✅ 수정사항 적용됨")

            # 구문 검증
            try:
                ast.parse(content)
                print(f"   ✅ 구문 검증 통과")

                # 수정된 내용 저장
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.fixed_files += 1
                return True

            except SyntaxError as e:
                print(f"   ⚠️  구문 오류 남음: {str(e)[:50]}")
                # 원본 복원
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                return False

        except Exception as e:
            print(f"   ❌ 처리 실패: {str(e)[:50]}")
            self.failed_files += 1
            return False

    def fix_all_python_files(self):
        """모든 Python 파일 수정"""
        print("🔧 고급 구문 수정기 시작!")
        print("=" * 50)

        python_files = glob.glob("*.py")

        # 도구 파일들 제외
        exclude_files = [
            'syntax_error_fixer.py',
            'file_recovery_master.py',
            'validate_python_files.py',
            'advanced_syntax_fixer.py'
        ]

        target_files = [f for f in python_files if f not in exclude_files]

        # 구문 오류가 있는 파일들만 수정
        error_files = []
        for file_path in target_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except Exception:
                error_files.append(file_path)

        print(f"📊 수정 대상 파일: {len(error_files)}개")

        for file_path in error_files:
            self.fix_file(file_path)

        print("=" * 50)
        print(f"🎉 고급 수정 완료!")
        print(f"📊 요약:")
        print(f"   - 수정 성공: {self.fixed_files}개")
        print(f"   - 수정 실패: {self.failed_files}개")


if __name__ == "__main__":
    fixer = AdvancedSyntaxFixer()
    fixer.fix_all_python_files()
