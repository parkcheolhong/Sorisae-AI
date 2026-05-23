#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 자동 코드 품질 개선 도구 v2.0
타입 힌트, 예외 처리, docstring 개선 자동화
"""

import ast
import logging
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('code_quality_improver.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IssueType(Enum):
    """코드 이슈 타입"""
    BARE_EXCEPT = "bare_except"
    MISSING_TYPE_HINT = "missing_type_hint"
    MISSING_DOCSTRING = "missing_docstring"
    IMPORT_ERROR = "import_error"
    UNUSED_IMPORT = "unused_import"
    LONG_FUNCTION = "long_function"
    COMPLEX_FUNCTION = "complex_function"


@dataclass
class CodeIssue:
    """코드 이슈 정보"""
    file_path: str
    line_number: int
    issue_type: IssueType
    description: str
    suggestion: str
    severity: str = "medium"


class PythonCodeAnalyzer:
    """파이썬 코드 분석기"""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.issues: List[CodeIssue] = []
        self.analyzed_files: List[str] = []

    def analyze_file(self, file_path: Path) -> List[CodeIssue]:
        """단일 파일 분석"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # AST 파싱
            tree = ast.parse(content)

            # 다양한 분석 수행
            issues.extend(self._check_bare_except(content, str(file_path)))
            issues.extend(self._check_missing_docstrings(tree, str(file_path)))
            issues.extend(self._check_type_hints(tree, str(file_path)))
            issues.extend(self._check_function_complexity(tree, str(file_path)))

            self.analyzed_files.append(str(file_path))

        except Exception as e:
            logger.error(f"파일 분석 오류 {file_path}: {e}")

        return issues

    def _check_bare_except(self, content: str, file_path: str) -> List[CodeIssue]:
        """Bare except 문 확인"""
        issues = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # except: 패턴 찾기
            if re.search(r'^\s*except\s*:', line):
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=line_num,
                    issue_type=IssueType.BARE_EXCEPT,
                    description="Bare except 문 사용",
                    suggestion="구체적인 예외 타입을 지정하세요: except Exception:",
                    severity="high"
                ))

        return issues

    def _check_missing_docstrings(self, tree: ast.AST, file_path: str) -> List[CodeIssue]:
        """누락된 docstring 확인"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                # docstring이 있는지 확인
                has_docstring = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )

                if not has_docstring:
                    node_type = "함수" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "클래스"
                    issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type=IssueType.MISSING_DOCSTRING,
                        description=f"{node_type} '{node.name}'에 docstring 누락",
                        suggestion=f'"""{node_type} 설명을 추가하세요"""',
                        severity="medium"
                    ))

        return issues

    def _check_type_hints(self, tree: ast.AST, file_path: str) -> List[CodeIssue]:
        """타입 힌트 확인"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 매개변수 타입 힌트 확인
                for arg in node.args.args:
                    if not arg.annotation and arg.arg != 'self':
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type=IssueType.MISSING_TYPE_HINT,
                            description=f"함수 '{node.name}'의 매개변수 '{arg.arg}'에 타입 힌트 누락",
                            suggestion="적절한 타입을 추가하세요: param: str, param: int 등",
                            severity="low"
                        ))

                # 반환 타입 힌트 확인
                if not node.returns:
                    issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type=IssueType.MISSING_TYPE_HINT,
                        description=f"함수 '{node.name}'에 반환 타입 힌트 누락",
                        suggestion="반환 타입을 추가하세요: -> str, -> None 등",
                        severity="low"
                    ))

        return issues

    def _check_function_complexity(self, tree: ast.AST, file_path: str) -> List[CodeIssue]:
        """함수 복잡도 확인"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 함수 길이 확인
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    lines = node.end_lineno - node.lineno
                    if lines > 50:
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type=IssueType.LONG_FUNCTION,
                            description=f"함수 '{node.name}'가 너무 깁니다 ({lines}줄)",
                            suggestion="함수를 작은 단위로 분리하는 것을 고려하세요",
                            severity="medium"
                        ))

        return issues

    def analyze_directory(self) -> Dict[str, Any]:
        """디렉토리 전체 분석"""
        logger.info(f"코드 품질 분석 시작: {self.root_path}")

        # Python 파일 찾기
        python_files = list(self.root_path.rglob("*.py"))
        logger.info(f"발견된 Python 파일: {len(python_files)}개")

        total_issues = []

        for py_file in python_files:
            # 특정 파일 제외
            if any(exclude in str(py_file) for exclude in ['__pycache__', '.git', 'venv', 'env']):
                continue

            logger.info(f"분석 중: {py_file.name}")
            file_issues = self.analyze_file(py_file)
            total_issues.extend(file_issues)

        # 이슈 통계
        issue_stats = self._calculate_statistics(total_issues)

        return {
            'total_files': len(self.analyzed_files),
            'total_issues': len(total_issues),
            'issues': total_issues,
            'statistics': issue_stats,
            'analyzed_files': self.analyzed_files
        }

    def _calculate_statistics(self, issues: List[CodeIssue]) -> Dict[str, Any]:
        """이슈 통계 계산"""
        stats = {
            'by_type': {},
            'by_severity': {},
            'by_file': {}
        }

        for issue in issues:
            # 타입별 통계
            issue_type = issue.issue_type.value
            stats['by_type'][issue_type] = stats['by_type'].get(issue_type, 0) + 1

            # 심각도별 통계
            severity = issue.severity
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1

            # 파일별 통계
            file_name = os.path.basename(issue.file_path)
            stats['by_file'][file_name] = stats['by_file'].get(file_name, 0) + 1

        return stats


class CodeQualityImprover:
    """코드 품질 개선 도구"""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.analyzer = PythonCodeAnalyzer(root_path)
        self.improvements_applied = 0

    def auto_fix_bare_except(self, file_path: str, line_number: int) -> bool:
        """Bare except 자동 수정"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 해당 라인 찾기
            if line_number <= len(lines):
                line = lines[line_number - 1]
                if 'except:' in line:
                    # except: 를 except Exception: 로 변경
                    fixed_line = line.replace('except:', 'except Exception:')
                    lines[line_number - 1] = fixed_line

                    # 파일 저장
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    logger.info(f"Bare except 수정: {file_path}:{line_number}")
                    return True

        except Exception as e:
            logger.error(f"Bare except 수정 실패 {file_path}:{line_number}: {e}")

        return False

    def add_type_hints_to_function(self, file_path: str, function_name: str) -> bool:
        """함수에 기본 타입 힌트 추가"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 간단한 패턴 매칭으로 함수 찾기
            function_pattern = rf'def {function_name}\((.*?)\):'
            match = re.search(function_pattern, content)

            if match:
                # 기본적인 타입 힌트 추가 시뮬레이션
                logger.info(f"타입 힌트 추가 가능: {file_path}의 {function_name}")
                return True

        except Exception as e:
            logger.error(f"타입 힌트 추가 실패: {e}")

        return False

    def add_docstring_to_function(self, file_path: str, function_name: str, line_number: int) -> bool:
        """함수에 기본 docstring 추가"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 함수 정의 다음 줄에 docstring 추가
            if line_number < len(lines):
                indent = '    '  # 기본 들여쓰기

                # 현재 라인의 들여쓰기 감지
                current_line = lines[line_number - 1]
                leading_spaces = len(current_line) - len(current_line.lstrip())
                indent = ' ' * (leading_spaces + 4)

                docstring = f'{indent}"""{function_name} 함수 설명을 추가하세요"""\n'

                # docstring 삽입
                lines.insert(line_number, docstring)

                # 파일 저장
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                logger.info(f"Docstring 추가: {file_path}의 {function_name}")
                return True

        except Exception as e:
            logger.error(f"Docstring 추가 실패: {e}")

        return False

    def run_improvements(self, auto_fix: bool = True) -> Dict[str, Any]:
        """코드 개선 실행"""
        logger.info("코드 품질 분석 및 개선 시작")

        # 1. 코드 분석
        analysis_result = self.analyzer.analyze_directory()

        logger.info(f"분석 완료: {analysis_result['total_issues']}개 이슈 발견")

        # 2. 자동 수정 (옵션)
        if auto_fix:
            logger.info("자동 수정 시작...")

            for issue in analysis_result['issues']:
                if issue.issue_type == IssueType.BARE_EXCEPT:
                    if self.auto_fix_bare_except(issue.file_path, issue.line_number):
                        self.improvements_applied += 1

                # docstring 추가는 더 신중하게
                elif issue.issue_type == IssueType.MISSING_DOCSTRING and issue.severity == "high":
                    function_name = self._extract_function_name_from_description(issue.description)
                    if function_name:
                        if self.add_docstring_to_function(issue.file_path, function_name, issue.line_number):
                            self.improvements_applied += 1

        # 3. 개선 보고서 생성
        improvement_report = {
            'analysis': analysis_result,
            'improvements_applied': self.improvements_applied,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'recommendations': self._generate_recommendations(analysis_result)
        }

        return improvement_report

    def _extract_function_name_from_description(self, description: str) -> Optional[str]:
        """설명에서 함수명 추출"""
        # "함수 'function_name'에 docstring 누락" 패턴에서 함수명 추출
        match = re.search(r"'([^']+)'", description)
        return match.group(1) if match else None

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []

        stats = analysis['statistics']

        # Bare except 권장사항
        if 'bare_except' in stats['by_type']:
            count = stats['by_type']['bare_except']
            recommendations.append(f"🔧 {count}개의 bare except 문을 구체적 예외로 변경하세요")

        # Docstring 권장사항
        if 'missing_docstring' in stats['by_type']:
            count = stats['by_type']['missing_docstring']
            recommendations.append(f"📝 {count}개의 함수/클래스에 docstring을 추가하세요")

        # 타입 힌트 권장사항
        if 'missing_type_hint' in stats['by_type']:
            count = stats['by_type']['missing_type_hint']
            recommendations.append(f"🏷️ {count}개의 함수에 타입 힌트를 추가하세요")

        # 함수 길이 권장사항
        if 'long_function' in stats['by_type']:
            count = stats['by_type']['long_function']
            recommendations.append(f"✂️ {count}개의 긴 함수를 리팩토링하세요")

        return recommendations

    def generate_detailed_report(self, improvement_result: Dict[str, Any]) -> str:
        """상세 보고서 생성"""
        analysis = improvement_result['analysis']

        report = f"""
🔧 코드 품질 개선 보고서
{'=' * 50}

▶ 분석 개요
  • 분석된 파일: {analysis['total_files']}개
  • 발견된 이슈: {analysis['total_issues']}개
  • 적용된 개선: {improvement_result['improvements_applied']}개
  • 분석 시간: {improvement_result['timestamp']}

▶ 이슈 타입별 통계
"""

        for issue_type, count in analysis['statistics']['by_type'].items():
            report += f"  • {issue_type}: {count}개\n"

        report += f"\n▶ 심각도별 통계\n"
        for severity, count in analysis['statistics']['by_severity'].items():
            report += f"  • {severity}: {count}개\n"

        report += f"\n▶ 개선 권장사항\n"
        for rec in improvement_result['recommendations']:
            report += f"  {rec}\n"

        # 파일별 이슈 TOP 5
        file_stats = analysis['statistics']['by_file']
        top_files = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)[:5]

        if top_files:
            report += f"\n▶ 이슈가 많은 파일 TOP 5\n"
            for i, (file_name, count) in enumerate(top_files, 1):
                report += f"  {i}. {file_name}: {count}개\n"

        return report


def main():
    """메인 실행 함수"""
    print("🔧 자동 코드 품질 개선 도구 v2.0")
    print("=" * 50)

    # 현재 디렉토리에서 실행
    current_dir = os.getcwd()
    improver = CodeQualityImprover(current_dir)

    try:
        # 코드 개선 실행
        print("📊 코드 품질 분석 및 개선 중...")
        result = improver.run_improvements(auto_fix=True)

        # 상세 보고서 출력
        detailed_report = improver.generate_detailed_report(result)
        print(detailed_report)

        # 보고서 파일로 저장
        report_file = f"code_quality_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(detailed_report)

        print(f"\n📋 상세 보고서가 저장되었습니다: {report_file}")

        # 개선 요약
        print(f"\n✅ 코드 품질 개선 완료!")
        print(f"  • 분석된 파일: {result['analysis']['total_files']}개")
        print(f"  • 발견된 이슈: {result['analysis']['total_issues']}개")
        print(f"  • 자동 수정: {result['improvements_applied']}개")

    except Exception as e:
        logger.error(f"코드 품질 개선 실행 오류: {e}")
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
