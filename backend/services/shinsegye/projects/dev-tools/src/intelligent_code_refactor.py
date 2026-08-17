#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
지능형 코드 리팩터링 도구
소리새 시스템의 코드를 자동으로 분석하고 개선하는 도구입니다.
"""

import ast
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class IntelligentCodeRefactor:
    def __init__(self):
        self.refactor_rules = {
            'long_functions': {'max_lines': 50, 'priority': 'high'},
            'duplicate_code': {'min_similarity': 0.8, 'priority': 'medium'},
            'complex_conditions': {'max_complexity': 10, 'priority': 'high'},
            'unused_imports': {'check_usage': True, 'priority': 'low'},
            'magic_numbers': {'extract_constants': True, 'priority': 'medium'},
            'naming_conventions': {'enforce_pep8': True, 'priority': 'medium'}
        }

        self.refactor_suggestions = []
        self.analysis_results = {}

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Python 파일을 분석하여 리팩터링 기회 탐지"""
        if not os.path.exists(file_path):
            return {'error': f'파일을 찾을 수 없습니다: {file_path}'}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # AST 파싱
            tree = ast.parse(content)

            analysis = {
                'file_path': file_path,
                'total_lines': len(content.split('\n')),
                'functions': self._analyze_functions(tree),
                'classes': self._analyze_classes(tree),
                'imports': self._analyze_imports(tree),
                'complexity_score': self._calculate_complexity(tree),
                'suggestions': []
            }

            # 리팩터링 제안 생성
            self._generate_refactor_suggestions(analysis)

            return analysis

        except SyntaxError as e:
            return {'error': f'구문 오류: {e}'}
        except Exception as e:
            return {'error': f'분석 오류: {e}'}

    def _analyze_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """함수들을 분석"""
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'line_start': node.lineno,
                    'line_end': getattr(node, 'end_lineno', node.lineno),
                    'args_count': len(node.args.args),
                    'has_docstring': ast.get_docstring(node) is not None,
                    'complexity': self._calculate_function_complexity(node)
                }

                func_info['line_count'] = func_info['line_end'] - func_info['line_start'] + 1
                functions.append(func_info)

        return functions

    def _analyze_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """클래스들을 분석"""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'line_start': node.lineno,
                    'methods': [],
                    'has_docstring': ast.get_docstring(node) is not None
                }

                # 메서드 분석
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        class_info['methods'].append(item.name)

                classes.append(class_info)

        return classes

    def _analyze_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """import 문들을 분석"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                else:  # ImportFrom
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': node.module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })

        return imports

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """전체 복잡도 계산 (순환 복잡도 기반)"""
        complexity = 1  # 기본 복잡도

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """함수의 복잡도 계산"""
        complexity = 1

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1

        return complexity

    def _generate_refactor_suggestions(self, analysis: Dict[str, Any]) -> None:
        """리팩터링 제안 생성"""
        suggestions = []

        # 긴 함수 체크
        for func in analysis['functions']:
            if func['line_count'] > self.refactor_rules['long_functions']['max_lines']:
                suggestions.append({
                    'type': 'long_function',
                    'priority': 'high',
                    'message': f"함수 '{func['name']}'가 너무 깁니다 ({func['line_count']}줄). 분할을 고려해보세요.",
                    'line': func['line_start'],
                    'suggestion': f"함수를 여러 개의 작은 함수로 분할하세요."
                })

        # 복잡한 함수 체크
        for func in analysis['functions']:
            if func['complexity'] > self.refactor_rules['complex_conditions']['max_complexity']:
                suggestions.append({
                    'type': 'complex_function',
                    'priority': 'high',
                    'message': f"함수 '{func['name']}'의 복잡도가 높습니다 (복잡도: {func['complexity']}).",
                    'line': func['line_start'],
                    'suggestion': "조건문을 단순화하거나 함수를 분할하세요."
                })

        # 문서화 체크
        for func in analysis['functions']:
            if not func['has_docstring']:
                suggestions.append({
                    'type': 'missing_docstring',
                    'priority': 'medium',
                    'message': f"함수 '{func['name']}'에 문서화가 필요합니다.",
                    'line': func['line_start'],
                    'suggestion': "함수에 docstring을 추가하세요."
                })

        analysis['suggestions'] = suggestions

    def refactor_file(self, file_path: str, apply_fixes: bool = False) -> Dict[str, Any]:
        """파일 리팩터링 수행"""
        analysis = self.analyze_file(file_path)

        if 'error' in analysis:
            return analysis

        refactor_result = {
            'original_file': file_path,
            'analysis': analysis,
            'fixes_applied': [],
            'backup_created': False
        }

        if apply_fixes:
            # 백업 생성
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                refactor_result['backup_created'] = True
                refactor_result['backup_path'] = backup_path
            except Exception as e:
                refactor_result['backup_error'] = str(e)

            # 실제 수정 적용 (예시)
            fixes_applied = self._apply_automatic_fixes(file_path, analysis)
            refactor_result['fixes_applied'] = fixes_applied

        return refactor_result

    def _apply_automatic_fixes(self, file_path: str, analysis: Dict[str, Any]) -> List[str]:
        """자동 수정 적용"""
        fixes_applied = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            modified_content = content

            # 간단한 자동 수정들
            # 1. 불필요한 공백 제거
            if re.search(r'\s+$', content, re.MULTILINE):
                modified_content = re.sub(r'\s+$', '', modified_content, flags=re.MULTILINE)
                fixes_applied.append("trailing_whitespace_removed")

            # 2. 여러 개의 빈 줄을 2개로 제한
            if re.search(r'\n\n\n+', modified_content):
                modified_content = re.sub(r'\n\n\n+', '\n\n', modified_content)
                fixes_applied.append("excessive_blank_lines_fixed")

            # 수정된 내용 저장
            if modified_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)

        except Exception as e:
            fixes_applied.append(f"error: {e}")

        return fixes_applied

    def analyze_directory(self, directory_path: str) -> Dict[str, Any]:
        """디렉토리 내 모든 Python 파일 분석"""
        if not os.path.exists(directory_path):
            return {'error': f'디렉토리를 찾을 수 없습니다: {directory_path}'}

        python_files = list(Path(directory_path).rglob('*.py'))

        directory_analysis = {
            'directory': directory_path,
            'total_files': len(python_files),
            'analyzed_files': 0,
            'total_suggestions': 0,
            'files_analysis': {},
            'summary': {
                'high_priority_issues': 0,
                'medium_priority_issues': 0,
                'low_priority_issues': 0
            }
        }

        for py_file in python_files:
            file_analysis = self.analyze_file(str(py_file))

            if 'error' not in file_analysis:
                directory_analysis['analyzed_files'] += 1
                directory_analysis['files_analysis'][str(py_file)] = file_analysis

                # 제안사항 집계
                for suggestion in file_analysis.get('suggestions', []):
                    directory_analysis['total_suggestions'] += 1
                    if suggestion['priority'] == 'high':
                        directory_analysis['summary']['high_priority_issues'] += 1
                    elif suggestion['priority'] == 'medium':
                        directory_analysis['summary']['medium_priority_issues'] += 1
                    else:
                        directory_analysis['summary']['low_priority_issues'] += 1

        return directory_analysis

    def generate_refactor_report(self, analysis_result: Dict[str, Any]) -> str:
        """리팩터링 보고서 생성"""
        if 'directory' in analysis_result:
            return self._generate_directory_report(analysis_result)
        else:
            return self._generate_file_report(analysis_result)

    def _generate_file_report(self, analysis: Dict[str, Any]) -> str:
        """단일 파일 리팩터링 보고서"""
        if 'error' in analysis:
            return f"❌ 파일 분석 실패: {analysis['error']}"

        report = f"""
🔍 코드 리팩터링 분석 보고서
=============================
파일: {analysis['file_path']}
총 라인 수: {analysis['total_lines']}
함수 개수: {len(analysis['functions'])}
클래스 개수: {len(analysis['classes'])}
전체 복잡도: {analysis['complexity_score']}

📋 리팩터링 제안사항 ({len(analysis['suggestions'])}개):
"""

        if not analysis['suggestions']:
            report += "✅ 리팩터링이 필요한 문제가 발견되지 않았습니다!"
        else:
            for i, suggestion in enumerate(analysis['suggestions'], 1):
                priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[suggestion['priority']]
                report += f"\n{i}. {priority_icon} {suggestion['message']}"
                report += f"\n   제안: {suggestion['suggestion']}"
                report += f"\n   라인: {suggestion['line']}\n"

        return report

    def _generate_directory_report(self, analysis: Dict[str, Any]) -> str:
        """디렉토리 리팩터링 보고서"""
        summary = analysis['summary']

        report = f"""
📁 디렉토리 리팩터링 분석 보고서
===============================
디렉토리: {analysis['directory']}
총 파일 수: {analysis['total_files']}
분석된 파일: {analysis['analyzed_files']}
총 제안사항: {analysis['total_suggestions']}

📊 우선순위별 이슈:
🔴 높음: {summary['high_priority_issues']}개
🟡 중간: {summary['medium_priority_issues']}개
🟢 낮음: {summary['low_priority_issues']}개

💡 주요 권장사항:
- 높은 우선순위 이슈들을 먼저 해결하세요
- 복잡한 함수들을 작은 단위로 분할하세요
- 누락된 문서화를 추가하세요
"""

        return report


def main():
    """메인 실행 함수"""
    print("🔧 소리새 지능형 코드 리팩터링 도구")
    print("==================================")

    refactor_tool = IntelligentCodeRefactor()

    # 현재 디렉토리의 Python 파일들 분석
    current_dir = "."
    directory_analysis = refactor_tool.analyze_directory(current_dir)

    # 보고서 생성 및 출력
    report = refactor_tool.generate_refactor_report(directory_analysis)
    print(report)

    # 보고서를 파일로 저장
    with open('refactor_analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)

    print("\n💾 상세 분석 보고서가 'refactor_analysis_report.txt'에 저장되었습니다.")


if __name__ == "__main__":
    main()
