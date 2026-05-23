#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import glob
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class ComprehensiveProjectAnalyzer:
    """프로젝트 전체 상태 정밀 분석 및 안전 정리 시스템"""

    def __init__(self):
        self.project_root = Path(".")
        self.analysis_results = {}
        self.file_categories = defaultdict(list)
        self.backup_inventory = {}
        self.critical_files = []
        self.documentation_files = []
        self.implementation_files = []

    def execute_comprehensive_analysis(self):
        """포괄적 프로젝트 분석 실행"""

        print("🔍 프로젝트 전체 상태 정밀 분석 시작")
        print("=" * 80)

        # 1. 파일 인벤토리 생성
        self.create_file_inventory()

        # 2. 백업 파일 분석
        self.analyze_backup_files()

        # 3. 핵심 기능 파일 식별
        self.identify_critical_files()

        # 4. 문서 파일 분석
        self.analyze_documentation_files()

        # 5. 구현 파일 분석
        self.analyze_implementation_files()

        # 6. 중복 파일 매핑
        self.map_duplicate_files()

        # 7. Git 상태 분석
        self.analyze_git_status()

        # 8. 종합 보고서 생성
        self.generate_comprehensive_report()

        # 9. 안전 정리 계획 수립
        self.create_safe_cleanup_plan()

        print("🎉 정밀 분석 완료!")

    def create_file_inventory(self):
        """전체 파일 인벤토리 생성"""
        print("📋 파일 인벤토리 생성 중...")

        all_files = []

        # 현재 디렉토리의 모든 파일 스캔
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                file_info = {
                    'path': str(file_path),
                    'name': file_path.name,
                    'suffix': file_path.suffix,
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                    'is_backup': self.is_backup_file(file_path.name),
                    'is_damaged': 'DAMAGED' in file_path.name or 'damaged' in file_path.name,
                    'is_temp': file_path.name.startswith('temp_') or file_path.name.startswith('ultra_')
                }
                all_files.append(file_info)

        # 파일 카테고리별 분류
        for file_info in all_files:
            suffix = file_info['suffix'].lower()

            if suffix == '.py':
                if file_info['is_backup']:
                    self.file_categories['python_backup'].append(file_info)
                elif file_info['is_damaged']:
                    self.file_categories['python_damaged'].append(file_info)
                elif file_info['is_temp']:
                    self.file_categories['python_temp'].append(file_info)
                else:
                    self.file_categories['python_active'].append(file_info)

            elif suffix in ['.md', '.txt']:
                if file_info['is_backup']:
                    self.file_categories['doc_backup'].append(file_info)
                else:
                    self.file_categories['doc_active'].append(file_info)

            elif suffix in ['.json', '.html', '.css', '.js']:
                self.file_categories['config_data'].append(file_info)

            elif suffix in ['.bat', '.sh', '.ps1']:
                self.file_categories['scripts'].append(file_info)

        print(f"   ✅ 전체 {len(all_files)}개 파일 분석 완료")

        # 카테고리별 통계
        for category, files in self.file_categories.items():
            print(f"      📁 {category}: {len(files)}개")

    def is_backup_file(self, filename):
        """백업 파일 여부 확인"""
        backup_patterns = [
            '.backup', '.original_backup', '.compressed_backup',
            '_backup', '.bak', '_bak', '_copy', '_old'
        ]
        return any(pattern in filename for pattern in backup_patterns)

    def analyze_backup_files(self):
        """백업 파일 상세 분석"""
        print("🗄️ 백업 파일 분석 중...")

        # Python 백업 파일들 분석
        python_backups = self.file_categories['python_backup']

        for backup_file in python_backups:
            original_name = self.get_original_filename(backup_file['name'])

            # 원본 파일과 백업 파일 비교
            original_path = self.project_root / original_name
            if original_path.exists():
                original_size = original_path.stat().st_size
                backup_size = backup_file['size']

                self.backup_inventory[original_name] = {
                    'backup_file': backup_file['path'],
                    'backup_size': backup_size,
                    'original_size': original_size,
                    'size_diff': abs(original_size - backup_size),
                    'backup_newer': backup_file['modified'] > datetime.fromtimestamp(original_path.stat().st_mtime),
                    'quality_score': self.assess_file_quality(backup_file['path'])
                }

        print(f"   ✅ {len(self.backup_inventory)}개 파일의 백업 상태 분석 완료")

    def get_original_filename(self, backup_filename):
        """백업 파일명에서 원본 파일명 추출"""
        patterns_to_remove = [
            '.backup', '.original_backup', '.compressed_backup',
            '_backup', '.bak', '_bak', '_copy', '_old', '_DAMAGED'
        ]

        original = backup_filename
        for pattern in patterns_to_remove:
            original = original.replace(pattern, '')

        return original

    def assess_file_quality(self, file_path):
        """파일 품질 평가"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if file_path.endswith('.py'):
                # Python 파일 품질 평가
                try:
                    ast.parse(content)
                    syntax_score = 100
                except SyntaxError:
                    syntax_score = 0

                # 내용 풍부도 평가
                lines = len([line for line in content.split('\n') if line.strip()])
                content_score = min(100, lines * 2)  # 50줄이면 100점

                # 구조 평가
                has_class = 'class ' in content
                has_function = 'def ' in content
                has_imports = any(keyword in content for keyword in ['import ', 'from '])
                structure_score = (has_class * 30) + (has_function * 40) + (has_imports * 30)

                return (syntax_score * 0.5 + content_score * 0.3 + structure_score * 0.2)

            else:
                # 텍스트 파일 품질 평가
                return min(100, len(content) / 10)  # 1000자면 100점

        except Exception:
            return 0

    def identify_critical_files(self):
        """핵심 파일 식별"""
        print("🎯 핵심 파일 식별 중...")

        # 핵심 시스템 파일들 정의
        critical_patterns = [
            'app_Sorisae.py',
            'sorisae_core_controller.py',
            'sorisae_dual_brain_*.py',
            'voice_calling_system.py',
            'voice_command_processor.py',
            'run_all_shinsegye.py',
            'requirements*.txt',
            'README.md',
            '소리새_듀얼브레인_기술분석보고서.txt',
            'setup.py',
            'modules/*/core.py'
        ]

        for pattern in critical_patterns:
            matching_files = glob.glob(pattern, recursive=True)
            for file_path in matching_files:
                if os.path.isfile(file_path):
                    quality = self.assess_file_quality(file_path)
                    self.critical_files.append({
                        'path': file_path,
                        'pattern': pattern,
                        'quality': quality,
                        'size': os.path.getsize(file_path),
                        'has_backup': file_path in self.backup_inventory
                    })

        # 품질 순으로 정렬
        self.critical_files.sort(key=lambda x: x['quality'], reverse=True)

        print(f"   ✅ {len(self.critical_files)}개 핵심 파일 식별")

        # 상위 품질 파일들 출력
        print("   📋 핵심 파일 품질 순위:")
        for i, file_info in enumerate(self.critical_files[:10], 1):
            status = "🟢" if file_info['quality'] > 80 else "🟡" if file_info['quality'] > 50 else "🔴"
            backup_status = "💾" if file_info['has_backup'] else "❌"
            print(f"      {i:2d}. {status} {backup_status} {file_info['path']} (품질: {file_info['quality']:.1f})")

    def analyze_documentation_files(self):
        """문서 파일 분석"""
        print("📚 문서 파일 분석 중...")

        doc_files = glob.glob("*.md") + glob.glob("*.txt") + glob.glob("docs/**/*", recursive=True)

        for doc_file in doc_files:
            if os.path.isfile(doc_file):
                try:
                    with open(doc_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    doc_info = {
                        'path': doc_file,
                        'size': len(content),
                        'lines': len(content.split('\n')),
                        'words': len(content.split()),
                        'has_korean': any('\uac00' <= char <= '\ud7a3' for char in content),
                        'is_technical': any(keyword in content.lower()
                                            for keyword in ['api', 'class', 'function', '구현', '설계', '아키텍처']),
                        'is_report': any(keyword in content.lower()
                                         for keyword in ['보고서', 'report', '분석', '결과', '요약']),
                        'modified': datetime.fromtimestamp(os.path.getmtime(doc_file))
                    }

                    self.documentation_files.append(doc_info)

                except Exception as e:
                    print(f"   ⚠️ 문서 파일 읽기 실패: {doc_file} - {e}")

        # 중요도별 분류
        self.documentation_files.sort(key=lambda x: (x['is_technical'], x['is_report'], x['size']), reverse=True)

        print(f"   ✅ {len(self.documentation_files)}개 문서 파일 분석 완료")

        # 중요 문서들 출력
        print("   📋 주요 문서 파일:")
        for doc in self.documentation_files[:5]:
            doc_type = "📊" if doc['is_report'] else "📖" if doc['is_technical'] else "📄"
            lang = "🇰🇷" if doc['has_korean'] else "🇺🇸"
            print(f"      {doc_type} {lang} {doc['path']} ({doc['words']} words)")

    def analyze_implementation_files(self):
        """구현 파일 분석"""
        print("⚙️ 구현 파일 분석 중...")

        # Python 파일들 상세 분석
        active_python_files = self.file_categories['python_active']

        for file_info in active_python_files:
            try:
                with open(file_info['path'], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 코드 분석
                try:
                    tree = ast.parse(content)

                    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.Import)]

                    impl_info = {
                        'path': file_info['path'],
                        'lines_of_code': len([line for line in content.split('\n') if line.strip()]),
                        'classes': classes,
                        'functions': functions,
                        'imports': imports,
                        'has_main': '__name__ == "__main__"' in content,
                        'complexity_score': len(classes) * 10 + len(functions) * 5 + len(imports) * 2,
                        'syntax_valid': True
                    }

                except SyntaxError as e:
                    impl_info = {
                        'path': file_info['path'],
                        'syntax_valid': False,
                        'syntax_error': str(e),
                        'complexity_score': 0
                    }

                self.implementation_files.append(impl_info)

            except Exception as e:
                print(f"   ⚠️ 파일 분석 실패: {file_info['path']} - {e}")

        # 복잡도 순으로 정렬
        valid_files = [f for f in self.implementation_files if f.get('syntax_valid', False)]
        invalid_files = [f for f in self.implementation_files if not f.get('syntax_valid', False)]

        valid_files.sort(key=lambda x: x['complexity_score'], reverse=True)

        print(f"   ✅ 유효한 구현 파일: {len(valid_files)}개")
        print(f"   ❌ 구문 오류 파일: {len(invalid_files)}개")

        # 주요 구현 파일들 출력
        print("   📋 주요 구현 파일 (복잡도 순):")
        for impl in valid_files[:10]:
            classes_count = len(impl.get('classes', []))
            functions_count = len(impl.get('functions', []))
            print(f"      ⚙️ {impl['path']} (클래스:{classes_count}, 함수:{functions_count}, 복잡도:{impl['complexity_score']})")

    def map_duplicate_files(self):
        """중복 파일 매핑"""
        print("🔍 중복 파일 매핑 중...")

        # 파일명 기준으로 그룹핑
        filename_groups = defaultdict(list)

        for category, files in self.file_categories.items():
            for file_info in files:
                base_name = self.get_original_filename(file_info['name'])
                filename_groups[base_name].append({
                    'category': category,
                    'info': file_info,
                    'quality': self.assess_file_quality(file_info['path'])
                })

        # 중복이 있는 파일들만 필터링
        duplicates = {k: v for k, v in filename_groups.items() if len(v) > 1}

        print(f"   ✅ {len(duplicates)}개 파일에 중복 버전 발견")

        # 중복 파일 상세 정보
        for filename, versions in list(duplicates.items())[:10]:  # 상위 10개만 출력
            print(f"   📁 {filename}:")
            versions.sort(key=lambda x: x['quality'], reverse=True)
            for i, version in enumerate(versions):
                status = "🏆" if i == 0 else "📋"
                print(f"      {status} {version['category']}: {version['info']['path']} (품질: {version['quality']:.1f})")

    def analyze_git_status(self):
        """Git 상태 분석"""
        print("📝 Git 상태 분석 중...")

        try:
            # Git 상태 확인
            import subprocess

            # 수정된 파일들
            result = subprocess.run(['git', 'status', '--porcelain'],
                                    capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                git_status_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

                git_analysis = {
                    'modified_files': [],
                    'untracked_files': [],
                    'staged_files': []
                }

                for line in git_status_lines:
                    if line.strip():
                        status = line[:2]
                        filepath = line[3:]

                        if status.strip() == 'M':
                            git_analysis['modified_files'].append(filepath)
                        elif status.strip() == '??':
                            git_analysis['untracked_files'].append(filepath)
                        elif status[0] != ' ':
                            git_analysis['staged_files'].append(filepath)

                self.analysis_results['git_status'] = git_analysis

                print(f"   ✅ 수정된 파일: {len(git_analysis['modified_files'])}개")
                print(f"   ✅ 추적되지 않은 파일: {len(git_analysis['untracked_files'])}개")
                print(f"   ✅ 스테이지된 파일: {len(git_analysis['staged_files'])}개")

        except Exception as e:
            print(f"   ⚠️ Git 상태 분석 실패: {e}")

    def generate_comprehensive_report(self):
        """종합 분석 보고서 생성"""
        print("📄 종합 분석 보고서 생성 중...")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report_content = f"""# 🔍 프로젝트 종합 분석 보고서

## 📅 분석 일시
{timestamp}

## 📊 전체 파일 현황

### Python 파일
- 활성 파일: {len(self.file_categories['python_active'])}개
- 백업 파일: {len(self.file_categories['python_backup'])}개
- 손상된 파일: {len(self.file_categories['python_damaged'])}개
- 임시 파일: {len(self.file_categories['python_temp'])}개

### 문서 파일
- 활성 문서: {len(self.file_categories['doc_active'])}개
- 백업 문서: {len(self.file_categories['doc_backup'])}개

### 기타 파일
- 설정/데이터 파일: {len(self.file_categories['config_data'])}개
- 스크립트 파일: {len(self.file_categories['scripts'])}개

## 🎯 핵심 파일 상태

### 최고 품질 파일들
"""

        for i, file_info in enumerate(self.critical_files[:10], 1):
            report_content += f"{i}. **{file_info['path']}** (품질: {file_info['quality']:.1f}/100)\n"

        report_content += f"""

## 📚 주요 문서 파일

"""

        for doc in self.documentation_files[:10]:
            doc_type = "기술문서" if doc['is_technical'] else "보고서" if doc['is_report'] else "일반문서"
            report_content += f"- **{doc['path']}** ({doc_type}, {doc['words']} words)\n"

        report_content += f"""

## ⚙️ 구현 파일 현황

### 구문 유효 파일
"""

        valid_files = [f for f in self.implementation_files if f.get('syntax_valid', False)]
        for impl in valid_files[:10]:
            classes_count = len(impl.get('classes', []))
            functions_count = len(impl.get('functions', []))
            report_content += f"- **{impl['path']}** (클래스: {classes_count}, 함수: {functions_count})\n"

        invalid_files = [f for f in self.implementation_files if not f.get('syntax_valid', False)]
        if invalid_files:
            report_content += f"""

### ⚠️ 구문 오류 파일 ({len(invalid_files)}개)
"""
            for impl in invalid_files[:10]:
                report_content += f"- **{impl['path']}** - {impl.get('syntax_error', 'Unknown error')}\n"

        if 'git_status' in self.analysis_results:
            git_status = self.analysis_results['git_status']
            report_content += f"""

## 📝 Git 상태

- 수정된 파일: {len(git_status['modified_files'])}개
- 추적되지 않은 파일: {len(git_status['untracked_files'])}개
- 스테이지된 파일: {len(git_status['staged_files'])}개
"""

        report_content += f"""

## 🔄 백업 파일 분석

총 {len(self.backup_inventory)}개 파일에 백업 존재

### 백업 품질 분석
"""

        for original, backup_info in list(self.backup_inventory.items())[:10]:
            report_content += f"- **{original}** (백업 품질: {backup_info['quality_score']:.1f}/100)\n"

        report_content += """

---
*이 보고서는 프로젝트의 현재 상태를 정밀 분석한 결과입니다.*
*안전한 정리 작업을 위한 기초 자료로 활용하세요.*
"""

        with open("COMPREHENSIVE_PROJECT_ANALYSIS.md", "w", encoding="utf-8") as f:
            f.write(report_content)

        print("   ✅ 종합 분석 보고서 생성: COMPREHENSIVE_PROJECT_ANALYSIS.md")

    def create_safe_cleanup_plan(self):
        """안전 정리 계획 수립"""
        print("🛡️ 안전 정리 계획 수립 중...")

        cleanup_plan = {
            'phase1_safe_removals': [],  # 안전하게 제거 가능한 파일들
            'phase2_backup_merges': [],  # 백업과 원본 병합이 필요한 파일들
            'phase3_recovery_needed': [],  # 복구가 필요한 파일들
            'phase4_manual_review': []   # 수동 검토가 필요한 파일들
        }

        # Phase 1: 안전 제거 대상 (임시파일, 명확한 중복파일)
        for file_info in self.file_categories['python_temp']:
            cleanup_plan['phase1_safe_removals'].append({
                'file': file_info['path'],
                'reason': '임시 파일',
                'safe_to_remove': True
            })

        # Phase 2: 백업 병합 대상
        for original, backup_info in self.backup_inventory.items():
            if backup_info['quality_score'] > 80:
                cleanup_plan['phase2_backup_merges'].append({
                    'original': original,
                    'backup': backup_info['backup_file'],
                    'recommendation': '백업을 원본으로 교체' if backup_info['backup_newer'] else '원본 유지'
                })

        # Phase 3: 복구 필요 대상
        for impl in self.implementation_files:
            if not impl.get('syntax_valid', False):
                cleanup_plan['phase3_recovery_needed'].append({
                    'file': impl['path'],
                    'error': impl.get('syntax_error', 'Unknown'),
                    'has_backup': impl['path'] in [info['backup_file'] for info in self.backup_inventory.values()]
                })

        # Phase 4: 수동 검토 대상 (핵심 파일 중 품질이 낮은 것들)
        for file_info in self.critical_files:
            if file_info['quality'] < 80:
                cleanup_plan['phase4_manual_review'].append({
                    'file': file_info['path'],
                    'quality': file_info['quality'],
                    'reason': '핵심 파일이지만 품질이 낮음'
                })

        # 정리 계획 저장
        plan_content = f"""# 🛡️ 안전 프로젝트 정리 계획

## 📋 정리 단계별 계획

### Phase 1: 안전 제거 ({len(cleanup_plan['phase1_safe_removals'])}개 파일)
> 임시 파일 및 명확한 중복 파일 제거

"""

        for item in cleanup_plan['phase1_safe_removals'][:20]:
            plan_content += f"- 🗑️ `{item['file']}` - {item['reason']}\n"

        plan_content += f"""

### Phase 2: 백업 병합 ({len(cleanup_plan['phase2_backup_merges'])}개 파일)
> 백업 파일과 원본 파일 최적 병합

"""

        for item in cleanup_plan['phase2_backup_merges'][:20]:
            plan_content += f"- 🔄 `{item['original']}` ← `{item['backup']}` ({item['recommendation']})\n"

        plan_content += f"""

### Phase 3: 파일 복구 ({len(cleanup_plan['phase3_recovery_needed'])}개 파일)
> 구문 오류 파일 복구

"""

        for item in cleanup_plan['phase3_recovery_needed'][:20]:
            backup_status = "백업있음" if item['has_backup'] else "백업없음"
            plan_content += f"- 🔧 `{item['file']}` - {item['error'][:50]}... ({backup_status})\n"

        plan_content += f"""

### Phase 4: 수동 검토 ({len(cleanup_plan['phase4_manual_review'])}개 파일)
> 핵심 파일 중 품질 검토 필요

"""

        for item in cleanup_plan['phase4_manual_review'][:20]:
            plan_content += f"- ⚠️ `{item['file']}` - 품질: {item['quality']:.1f}/100\n"

        plan_content += """

## 🚀 실행 순서

1. **Phase 1 실행**: 안전 제거 (유실 위험 없음)
2. **Phase 2 실행**: 백업 병합 (자동 백업 후 진행)
3. **Phase 3 실행**: 파일 복구 (백업 우선 활용)
4. **Phase 4 검토**: 수동 검토 후 결정

## ⚠️ 주의사항

- 각 단계 전에 현재 상태 백업
- Phase 4는 반드시 수동 검토 후 진행
- 핵심 파일은 절대 자동 삭제하지 않음

---
*이 계획을 단계별로 실행하면 안전하게 프로젝트를 정리할 수 있습니다.*
"""

        with open("SAFE_CLEANUP_PLAN.md", "w", encoding="utf-8") as f:
            f.write(plan_content)

        # 계획을 JSON으로도 저장 (자동화용)
        with open("cleanup_plan.json", "w", encoding="utf-8") as f:
            json.dump(cleanup_plan, f, indent=2, ensure_ascii=False, default=str)

        print("   ✅ 안전 정리 계획 생성: SAFE_CLEANUP_PLAN.md")
        print("   ✅ 자동화 계획 저장: cleanup_plan.json")

        return cleanup_plan


if __name__ == "__main__":
    analyzer = ComprehensiveProjectAnalyzer()
    analyzer.execute_comprehensive_analysis()
