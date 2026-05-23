#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 구문 검증 시스템
실시간 코드 분석 및 자동 수정
"""

import ast
import re
import sqlite3
from datetime import datetime
from pathlib import Path


class CodeAnalyzer:
    """코드 분석기"""

    def __init__(self):
        self.error_patterns = {
            'syntax_error': r'SyntaxError: (.+)',
            'indentation_error': r'IndentationError: (.+)',
            'name_error': r'NameError: (.+)',
            'import_error': r'ImportError: (.+)',
            'attribute_error': r'AttributeError: (.+)'
        }

        self.fix_rules = {
            'missing_colon': (r'if .+(?<!:)$', lambda m: m.group(0) + ':'),
            'wrong_indentation': (r'^( *)(.+)', self._fix_indentation),
            'missing_import': (r'NameError: name \'(\w+)\' is not defined', self._suggest_import)
        }

    def analyze_syntax(self, code):
        """구문 분석"""
        issues = []

        try:
            # AST 파싱 시도
            ast.parse(code)

        except SyntaxError as e:
            issues.append({
                'type': 'syntax_error',
                'line': e.lineno,
                'message': str(e),
                'text': e.text
            })

        except IndentationError as e:
            issues.append({
                'type': 'indentation_error',
                'line': e.lineno,
                'message': str(e),
                'text': e.text
            })

        return issues

    def analyze_quality(self, code):
        """코드 품질 분석"""
        quality_issues = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            # 긴 라인 검사
            if len(line) > 120:
                quality_issues.append({
                    'type': 'long_line',
                    'line': i,
                    'message': f'라인이 너무 깁니다 ({len(line)} 문자)',
                    'severity': 'warning'
                })

            # 하드코딩된 값 검사
            if re.search(r'["\'][^"\']{20,}["\']', line):
                quality_issues.append({
                    'type': 'hardcoded_string',
                    'line': i,
                    'message': '긴 하드코딩된 문자열',
                    'severity': 'info'
                })

            # TODO/FIXME 코멘트 검사
            if re.search(r'#.*(TODO|FIXME|XXX)', line, re.IGNORECASE):
                quality_issues.append({
                    'type': 'todo_comment',
                    'line': i,
                    'message': '미완성 코드 표시',
                    'severity': 'info'
                })

        return quality_issues

    def _fix_indentation(self, match):
        """들여쓰기 수정"""
        current_indent = match.group(1)
        code = match.group(2)

        # 표준 4칸 들여쓰기로 변환
        indent_level = len(current_indent) // 4
        return '    ' * indent_level + code

    def _suggest_import(self, match):
        """임포트 제안"""
        var_name = match.group(1)

        # 일반적인 모듈 매핑
        common_imports = {
            'os': 'import os',
            'sys': 'import sys',
            'json': 'import json',
            'time': 'import time',
            'datetime': 'from datetime import datetime',
            'Path': 'from pathlib import Path',
            'defaultdict': 'from collections import defaultdict'
        }

        return common_imports.get(var_name, f'# import {var_name}  # 임포트 필요')


class AutoSyntaxValidator:
    """자동 구문 검증기"""

    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.db_path = "syntax_validator.db"
        self.validation_history = []

        self.init_database()

    def init_database(self):
        """데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 검증 결과 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    file_path TEXT,
                    total_issues INTEGER,
                    syntax_errors INTEGER,
                    quality_issues INTEGER,
                    auto_fixed INTEGER,
                    quality_score REAL
                )
            ''')

            # 이슈 상세 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS issue_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    validation_id INTEGER,
                    issue_type TEXT,
                    line_number INTEGER,
                    message TEXT,
                    severity TEXT,
                    auto_fixed INTEGER,
                    FOREIGN KEY (validation_id) REFERENCES validation_results(id)
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"데이터베이스 초기화 오류: {e}")

    def validate_code(self, code, file_path=None):
        """코드 검증"""
        timestamp = datetime.now().isoformat()

        # 구문 분석
        syntax_issues = self.analyzer.analyze_syntax(code)

        # 품질 분석
        quality_issues = self.analyzer.analyze_quality(code)

        # 전체 이슈
        all_issues = syntax_issues + quality_issues

        # 품질 점수 계산
        quality_score = self._calculate_quality_score(code, all_issues)

        result = {
            'timestamp': timestamp,
            'file_path': file_path,
            'syntax_issues': syntax_issues,
            'quality_issues': quality_issues,
            'total_issues': len(all_issues),
            'quality_score': quality_score,
            'status': 'valid' if not syntax_issues else 'invalid'
        }

        # 데이터베이스에 저장
        self._save_validation_result(result)

        return result

    def _calculate_quality_score(self, code, issues):
        """품질 점수 계산 (0-100)"""
        base_score = 100

        # 구문 오류는 큰 감점
        syntax_errors = [i for i in issues if i['type'] in ['syntax_error', 'indentation_error']]
        base_score -= len(syntax_errors) * 20

        # 품질 이슈는 작은 감점
        quality_issues = [i for i in issues if i.get('severity') == 'warning']
        base_score -= len(quality_issues) * 5

        info_issues = [i for i in issues if i.get('severity') == 'info']
        base_score -= len(info_issues) * 2

        # 코드 길이 보너스/패널티
        lines = len(code.split('\n'))
        if 10 <= lines <= 100:
            base_score += 5  # 적절한 길이
        elif lines > 200:
            base_score -= 10  # 너무 긴 코드

        return max(0, min(100, base_score))

    def auto_fix_code(self, code):
        """코드 자동 수정"""
        fixed_code = code
        fixes_applied = []

        try:
            # 기본적인 수정 규칙 적용
            for rule_name, (pattern, fix_func) in self.analyzer.fix_rules.items():
                if callable(fix_func):
                    # 함수형 수정
                    matches = list(re.finditer(pattern, fixed_code, re.MULTILINE))
                    for match in reversed(matches):  # 뒤에서부터 수정
                        try:
                            replacement = fix_func(match)
                            start, end = match.span()
                            fixed_code = fixed_code[:start] + replacement + fixed_code[end:]
                            fixes_applied.append(rule_name)
                        except Exception:
                            continue
                else:
                    # 단순 교체
                    if re.search(pattern, fixed_code):
                        fixed_code = re.sub(pattern, fix_func, fixed_code)
                        fixes_applied.append(rule_name)

            return {
                'fixed_code': fixed_code,
                'fixes_applied': fixes_applied,
                'success': True
            }

        except Exception as e:
            return {
                'fixed_code': code,
                'fixes_applied': [],
                'success': False,
                'error': str(e)
            }

    def validate_file(self, file_path):
        """파일 검증"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            result = self.validate_code(code, file_path)

            # 자동 수정 시도
            if result['syntax_issues']:
                fix_result = self.auto_fix_code(code)
                if fix_result['success'] and fix_result['fixes_applied']:
                    # 수정된 코드 재검증
                    fixed_validation = self.validate_code(fix_result['fixed_code'], file_path)

                    result['auto_fix'] = {
                        'attempted': True,
                        'fixes_applied': fix_result['fixes_applied'],
                        'improved': fixed_validation['total_issues'] < result['total_issues'],
                        'fixed_code': fix_result['fixed_code']
                    }

            return result

        except Exception as e:
            return {
                'file_path': file_path,
                'error': str(e),
                'status': 'error'
            }

    def validate_project(self, project_path="."):
        """프로젝트 전체 검증"""
        print(f"🔍 프로젝트 검증 시작: {project_path}")

        project_root = Path(project_path)
        python_files = list(project_root.rglob("*.py"))

        # 제외할 디렉토리
        exclude_dirs = {'__pycache__', '.git', 'venv', 'node_modules'}
        python_files = [f for f in python_files if not any(exclude in str(f) for exclude in exclude_dirs)]

        print(f"📄 검증할 파일: {len(python_files)}개")

        results = []
        total_issues = 0
        total_fixed = 0

        for file_path in python_files:
            print(f"  검증 중: {file_path.name}")
            result = self.validate_file(file_path)

            if 'error' not in result:
                results.append(result)
                total_issues += result['total_issues']

                if result.get('auto_fix', {}).get('attempted'):
                    total_fixed += len(result['auto_fix']['fixes_applied'])

        summary = {
            'timestamp': datetime.now().isoformat(),
            'project_path': str(project_root),
            'total_files': len(python_files),
            'validated_files': len(results),
            'total_issues': total_issues,
            'total_fixes_applied': total_fixed,
            'average_quality_score': sum(r['quality_score'] for r in results) / len(results) if results else 0,
            'results': results
        }

        print(f"✅ 프로젝트 검증 완료:")
        print(f"  - 검증된 파일: {summary['validated_files']}/{summary['total_files']}")
        print(f"  - 발견된 이슈: {summary['total_issues']}개")
        print(f"  - 자동 수정: {summary['total_fixes_applied']}개")
        print(f"  - 평균 품질 점수: {summary['average_quality_score']:.1f}/100")

        return summary

    def _save_validation_result(self, result):
        """검증 결과 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 메인 결과 저장
            cursor.execute('''
                INSERT INTO validation_results
                (timestamp, file_path, total_issues, syntax_errors, quality_issues, auto_fixed, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['timestamp'],
                str(result.get('file_path', '')),  # Path 객체를 문자열로 변환
                result['total_issues'],
                len(result['syntax_issues']),
                len(result['quality_issues']),
                len(result.get('auto_fix', {}).get('fixes_applied', [])),
                result['quality_score']
            ))

            validation_id = cursor.lastrowid

            # 이슈 상세 저장
            all_issues = result['syntax_issues'] + result['quality_issues']
            for issue in all_issues:
                cursor.execute('''
                    INSERT INTO issue_details
                    (validation_id, issue_type, line_number, message, severity, auto_fixed)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    validation_id,
                    issue['type'],
                    issue.get('line', 0),
                    issue['message'],
                    issue.get('severity', 'error'),
                    0  # auto_fixed 구현 예정
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"검증 결과 저장 오류: {e}")

    def get_validation_report(self):
        """검증 보고서 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 최근 검증 결과
            cursor.execute('''
                SELECT * FROM validation_results
                ORDER BY timestamp DESC LIMIT 10
            ''')
            recent_validations = cursor.fetchall()

            # 이슈 통계
            cursor.execute('''
                SELECT issue_type, COUNT(*) as count
                FROM issue_details
                GROUP BY issue_type
                ORDER BY count DESC
            ''')
            issue_stats = cursor.fetchall()

            conn.close()

            report = {
                'timestamp': datetime.now().isoformat(),
                'recent_validations': [
                    {
                        'timestamp': row[1],
                        'file_path': row[2],
                        'total_issues': row[3],
                        'quality_score': row[7]
                    } for row in recent_validations
                ],
                'issue_statistics': [
                    {'type': row[0], 'count': row[1]} for row in issue_stats
                ]
            }

            return report

        except Exception as e:
            return {'error': str(e)}


def main():
    """메인 실행 함수"""
    print("🔍 자동 구문 검증 시스템")
    print("=" * 30)

    try:
        validator = AutoSyntaxValidator()

        # 프로젝트 전체 검증
        validator.validate_project()

        # 보고서 생성
        report = validator.get_validation_report()

        print(f"\n📊 검증 보고서:")
        if 'issue_statistics' in report:
            print(f"  주요 이슈 유형:")
            for stat in report['issue_statistics'][:5]:
                print(f"    - {stat['type']}: {stat['count']}개")

        print(f"\n🎉 자동 구문 검증 완료!")

    except KeyboardInterrupt:
        print(f"\n사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
