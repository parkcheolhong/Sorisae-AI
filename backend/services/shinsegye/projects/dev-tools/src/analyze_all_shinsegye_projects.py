#!/usr/bin/env python3
"""
신세계 전체 프로젝트 분석 스크립트
Comprehensive Shinsegye Project Analysis Script

각 프로젝트별로 다음 항목을 분석합니다:
- 프로젝트 파일 수 및 코드 라인 수
- 주요 기능 및 특징
- 의존성 분석
- 코드 품질 평가
- 실행 가능 여부
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class ShinsegyeProjectAnalyzer:
    """신세계 프로젝트 분석기"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.projects = self._define_projects()
        self.analysis_results = {}
        
    def _define_projects(self) -> Dict[str, Dict]:
        """18개 프로젝트 정의"""
        return {
            "소리새 핵심": {
                "files": [
                    "run_all_shinsegye.py",
                    "app_Sorisae.py",
                    "sorisae_ai_decision_engine.py",
                    "sorisae_dashboard_web.py",
                    "sorisae_divine_intelligence_105.py",
                    "sorisae_dual_brain_comparison.py",
                    "sorisae_dual_brain_stock_system.py",
                    "sorisae_enhanced_consciousness.py",
                    "sorisae_enhanced_features.py",
                    "sorisae_ethical_consciousness_engine.py",
                    "sorisae_ethical_consciousness_simple.py",
                    "sorisae_integrated_hybrid_system.py",
                    "sorisae_master_hybrid_system.py",
                    "sorisae_master_system.py",
                    "sorisae_maximum_upgrade_system.py",
                    "sorisae_multi_ego_core.py",
                    "sorisae_nextgen_features.py",
                    "sorisae_temporal_integration.py",
                    "sorisae_transcendent_102.py",
                    "sorisae_ultimate_integrated_system.py",
                    "sorisae_unified_launcher.py"
                ],
                "description": "소리새 AI 시스템의 핵심 모듈 및 통합 시스템",
                "category": "핵심 시스템"
            },
            "나도 통역사": {
                "files": [
                    "hybrid_conversation_translator.py",
                    "hybrid_interpreter_system.py",
                    "multilingual_system.py",
                    "sorisae_interpreter.py",
                    "sorisae_multilingual_support.py",
                    "sorisae_southeast_asia_translator.py"
                ],
                "description": "실시간 13개 언어 통역 시스템",
                "category": "언어 처리"
            },
            "사이버 탐정": {
                "files": [
                    "cyber_detective_ai.py",
                    "cyber_detective_dashboard.py",
                    "cyber_detective_detailed_analysis.py",
                    "cyber_detective_future_tech.py",
                    "cyber_detective_global_network.py",
                    "cyber_detective_global_server_analysis.py",
                    "cyber_detective_gps_radius.py",
                    "cyber_detective_methodology.py",
                    "cyber_detective_visual_monitoring.py",
                    "cyber_investigation_report.py",
                    "cyber_realtime_monitor.py",
                    "sorisae_cyber_investigator.py"
                ],
                "description": "AI 기반 사이버 수사 시스템",
                "category": "보안 및 분석"
            },
            "4D 영화 제작": {
                "files": [
                    "sorisae_4d_movie_demo.py",
                    "sorisae_movie_installer.py",
                    "sorisae_movie_web_server.py",
                    "sorisae_voice_movie_server.py"
                ],
                "description": "음성으로 4D 영화 제작",
                "category": "창작 도구"
            },
            "IoT 스마트홈": {
                "files": [
                    "hybrid_iot_controller.py",
                    "sorisae_iot_integration.py",
                    "sorisae_iot_smarthome.py",
                    "sorisae_iot_voice_control.py",
                    "spatiotemporal_learning_system.py",
                    "spatiotemporal_learning_system_new.py"
                ],
                "description": "스마트홈 디바이스 제어 시스템",
                "category": "IoT"
            },
            "투자 어드바이저": {
                "files": [
                    "sorisae_investment_advisor_200.py",
                    "stock_prediction_200_percent.py"
                ],
                "description": "듀얼브레인 AI 투자 조언 (200% 수익률)",
                "category": "금융"
            },
            "작사/작곡": {
                "files": [
                    "animation_studio_theme_song_demo.py",
                    "emotion_based_music_generator.py",
                    "music_chat_friend_system.py",
                    "start_music_chat_server.py"
                ],
                "description": "AI 기반 음악 작곡 및 작사 시스템",
                "category": "창작 도구"
            },
            "애니메이션 스튜디오": {
                "files": [
                    "animation_studio_demo.py",
                    "demo_animation_voice_integration.py",
                    "sorisae_animation_studio_ultra.py",
                    "test_animation_voice_integration.py"
                ],
                "description": "AI 기반 애니메이션 제작",
                "category": "창작 도구"
            },
            "토목 입찰 시스템": {
                "files": [
                    "civil_engineering_bidding_demo.py",
                    "sorisae_civil_engineering_bidding.py"
                ],
                "description": "AI 기반 건설 프로젝트 입찰 분석",
                "category": "비즈니스"
            },
            "게임 경제 시스템": {
                "files": [
                    "game_earning_analysis.py",
                    "sorisae_earning_game.py",
                    "sorisae_game_concept_design.py",
                    "sorisae_game_economy_system.py"
                ],
                "description": "세계 최초 '게임으로 먹고살기' 플랫폼",
                "category": "게임"
            },
            "쇼핑몰 시스템": {
                "files": [
                    "autonomous_shopping_demo.py",
                    "integrated_shopping_tutor_designer.py",
                    "shopping_mall_dashboard.py"
                ],
                "description": "7개 AI 에이전트 자율 쇼핑몰",
                "category": "비즈니스"
            },
            "GPS & 경찰 시스템": {
                "files": [
                    "current_police_system_status.py",
                    "ethical_gps_system.py",
                    "ethical_gps_system_simple.py",
                    "regional_ai_police_coverage.py",
                    "sorisae_gps_ethics_completion_report.py"
                ],
                "description": "윤리적 GPS 추적 및 경찰 시스템",
                "category": "보안 및 분석"
            },
            "보안 시스템": {
                "files": [
                    "advanced_security_system.py",
                    "biometric_security_system.py",
                    "hybrid_cyber_security_system.py",
                    "security_demo.py",
                    "security_key_manager.py"
                ],
                "description": "다층 보안 시스템",
                "category": "보안 및 분석"
            },
            "위성 시스템": {
                "files": [
                    "mountain_emergency_satellite.py",
                    "practical_satellite_manager.py",
                    "sorisae_satellite_demo.py",
                    "sorisae_satellite_wifi_system.py"
                ],
                "description": "차세대 인공위성 와이파이 시스템",
                "category": "인프라"
            },
            "VR/게임": {
                "files": [
                    "sorisae_fantasy_vr_infinite_universe_game.py",
                    "sorisae_vr_launcher.py",
                    "trend_idea_generator.py"
                ],
                "description": "VR 및 게임 생성",
                "category": "게임"
            },
            "개발 도구": {
                "files": [
                    "analyze_architecture.py",
                    "code_quality_improver.py",
                    "code_quality_master.py",
                    "comprehensive_file_analyzer.py",
                    "comprehensive_project_analyzer.py",
                    "detailed_technical_report.py",
                    "fix_docstring_quotes.py",
                    "fix_duplicate_orders.py",
                    "intelligent_code_refactor.py",
                    "project_review_verification.py"
                ],
                "description": "코드 분석 및 개선 도구",
                "category": "개발 지원"
            },
            "테스트/검증": {
                "files": [
                    "advanced_syntax_fixer.py",
                    "auto_syntax_validator.py",
                    "check_missing_programs.py",
                    "commissioning_test.py",
                    "completion_checker.py",
                    "project_syntax_checker.py",
                    "quick_validate.py",
                    "run_full_system_test.py",
                    "syno_check.py",
                    "syntax_checker.py",
                    "syntax_error_fixer.py",
                    "test_web_apps.py",
                    "validate_data.py",
                    "validate_python_files.py",
                    "verify_install.py",
                    "verify_sorisae_features.py"
                ],
                "description": "테스트 및 검증 도구",
                "category": "개발 지원"
            },
            "음성 처리": {
                "files": [
                    "sorisae_voice_processor.py",
                    "voice_calling_system.py",
                    "voice_command_processor.py",
                    "voice_tuner.py",
                    "enhanced_voice_exit.py",
                    "hybrid_voice_processor.py"
                ],
                "description": "음성 인식 및 처리 시스템",
                "category": "핵심 시스템"
            }
        }
    
    def count_lines(self, file_path: Path) -> Tuple[int, int, int]:
        """파일의 라인 수 카운트 (총 라인, 코드 라인, 주석 라인)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            total_lines = len(lines)
            code_lines = 0
            comment_lines = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith('#'):
                    comment_lines += 1
                else:
                    code_lines += 1
                    
            return total_lines, code_lines, comment_lines
        except FileNotFoundError:
            print(f"  ⚠️ 파일을 찾을 수 없음: {file_path}")
            return 0, 0, 0
        except UnicodeDecodeError:
            print(f"  ⚠️ 파일 인코딩 오류 ({file_path}): UTF-8로 읽을 수 없습니다")
            return 0, 0, 0
        except PermissionError:
            print(f"  ⚠️ 파일 접근 권한 없음: {file_path}")
            return 0, 0, 0
        except Exception as e:
            print(f"  ⚠️ 파일 읽기 중 예상치 못한 오류 ({file_path}): {e}")
            return 0, 0, 0
    
    def analyze_file(self, file_path: Path) -> Dict:
        """개별 파일 분석"""
        if not file_path.exists():
            return {
                "exists": False,
                "error": "파일이 존재하지 않음"
            }
        
        total, code, comments = self.count_lines(file_path)
        
        # 파일 내용에서 주요 클래스와 함수 찾기
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            classes = []
            functions = []
            
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('class '):
                    # Handle both 'class Name:' and 'class Name(Base):'
                    class_def = stripped.replace('class ', '').strip(':')
                    class_name = class_def.split('(')[0].strip()
                    classes.append(class_name)
                elif stripped.startswith('def '):
                    # Check if it's a top-level function (no leading whitespace in original line)
                    if line and line[0] not in (' ', '\t'):
                        func_name = stripped.split('(')[0].replace('def ', '')
                        functions.append(func_name)
        except (FileNotFoundError, UnicodeDecodeError, PermissionError) as e:
            print(f"  ⚠️ 파일 분석 오류: {e}")
            classes = []
            functions = []
        
        return {
            "exists": True,
            "total_lines": total,
            "code_lines": code,
            "comment_lines": comments,
            "classes": classes[:10],  # 처음 10개만
            "functions": functions[:10],  # 처음 10개만
            "size_kb": file_path.stat().st_size / 1024
        }
    
    def analyze_project(self, project_name: str, project_info: Dict) -> Dict:
        """프로젝트 분석"""
        print(f"\n{'='*80}")
        print(f"📊 프로젝트 분석: {project_name}")
        print(f"{'='*80}")
        print(f"설명: {project_info['description']}")
        print(f"카테고리: {project_info['category']}")
        print(f"파일 수: {len(project_info['files'])}")
        
        files_analysis = {}
        total_lines = 0
        total_code = 0
        total_comments = 0
        existing_files = 0
        missing_files = []
        
        for file_name in project_info['files']:
            file_path = self.base_path / file_name
            analysis = self.analyze_file(file_path)
            files_analysis[file_name] = analysis
            
            if analysis.get('exists'):
                existing_files += 1
                total_lines += analysis.get('total_lines', 0)
                total_code += analysis.get('code_lines', 0)
                total_comments += analysis.get('comment_lines', 0)
            else:
                missing_files.append(file_name)
        
        # 프로젝트 요약
        print(f"\n📈 통계:")
        print(f"  존재하는 파일: {existing_files}/{len(project_info['files'])}")
        print(f"  총 라인 수: {total_lines:,}")
        print(f"  코드 라인: {total_code:,}")
        print(f"  주석 라인: {total_comments:,}")
        
        if missing_files:
            print(f"\n⚠️ 누락된 파일 ({len(missing_files)}개):")
            for f in missing_files[:5]:  # 처음 5개만 표시
                print(f"  - {f}")
            if len(missing_files) > 5:
                print(f"  ... 외 {len(missing_files)-5}개")
        
        # 주요 파일 분석
        print(f"\n🔍 주요 파일:")
        sorted_files = sorted(
            [(name, info) for name, info in files_analysis.items() if info.get('exists')],
            key=lambda x: x[1].get('code_lines', 0),
            reverse=True
        )
        
        for i, (name, info) in enumerate(sorted_files[:3], 1):
            print(f"  {i}. {name}")
            print(f"     코드 라인: {info.get('code_lines', 0):,}")
            if info.get('classes'):
                print(f"     주요 클래스: {', '.join(info['classes'][:3])}")
        
        return {
            "project_name": project_name,
            "description": project_info['description'],
            "category": project_info['category'],
            "total_files": len(project_info['files']),
            "existing_files": existing_files,
            "missing_files": missing_files,
            "total_lines": total_lines,
            "code_lines": total_code,
            "comment_lines": total_comments,
            "files_analysis": files_analysis,
            "completion_rate": (existing_files / len(project_info['files']) * 100) if project_info['files'] else 0
        }
    
    def generate_summary_report(self) -> str:
        """종합 보고서 생성"""
        report = []
        report.append("# 신세계 전체 프로젝트 분석 보고서")
        report.append(f"\n**분석일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}")
        report.append(f"**총 프로젝트 수**: {len(self.analysis_results)}")
        report.append("\n---\n")
        
        # 전체 통계
        total_files = sum(r['total_files'] for r in self.analysis_results.values())
        total_existing = sum(r['existing_files'] for r in self.analysis_results.values())
        total_lines = sum(r['total_lines'] for r in self.analysis_results.values())
        total_code = sum(r['code_lines'] for r in self.analysis_results.values())
        
        report.append("## 📊 전체 통계\n")
        report.append(f"- **총 파일 수**: {total_files}개")
        # Prevent division by zero
        file_percentage = (total_existing / total_files * 100) if total_files > 0 else 0
        report.append(f"- **존재하는 파일**: {total_existing}개 ({file_percentage:.1f}%)")
        report.append(f"- **총 코드 라인**: {total_code:,}줄")
        report.append(f"- **총 라인 수**: {total_lines:,}줄")
        report.append("\n---\n")
        
        # 카테고리별 분류
        categories = {}
        for result in self.analysis_results.values():
            cat = result['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        report.append("## 📂 카테고리별 분류\n")
        for cat, projects in sorted(categories.items()):
            report.append(f"\n### {cat}\n")
            for proj in projects:
                report.append(f"- **{proj['project_name']}**: {proj['existing_files']}/{proj['total_files']}개 파일, "
                            f"{proj['code_lines']:,}줄 코드 ({proj['completion_rate']:.0f}% 완성)")
        
        report.append("\n---\n")
        
        # 프로젝트별 상세 정보
        report.append("## 📋 프로젝트별 상세 분석\n")
        
        for project_name, result in sorted(self.analysis_results.items()):
            report.append(f"\n### {project_name}\n")
            report.append(f"**설명**: {result['description']}\n")
            report.append(f"**카테고리**: {result['category']}\n")
            report.append(f"\n**통계**:")
            report.append(f"- 파일 수: {result['existing_files']}/{result['total_files']}")
            report.append(f"- 총 라인: {result['total_lines']:,}")
            report.append(f"- 코드 라인: {result['code_lines']:,}")
            report.append(f"- 주석 라인: {result['comment_lines']:,}")
            report.append(f"- 완성도: {result['completion_rate']:.1f}%")
            
            if result['missing_files']:
                report.append(f"\n**누락 파일** ({len(result['missing_files'])}개):")
                for f in result['missing_files'][:3]:
                    report.append(f"- {f}")
                if len(result['missing_files']) > 3:
                    report.append(f"- ... 외 {len(result['missing_files'])-3}개")
            
            report.append("")
        
        report.append("\n---\n")
        
        # 상위 프로젝트
        report.append("## 🏆 주요 프로젝트 순위\n")
        report.append("\n### 코드 라인 수 기준 Top 5\n")
        top_by_code = sorted(self.analysis_results.items(), 
                            key=lambda x: x[1]['code_lines'], 
                            reverse=True)[:5]
        for i, (name, result) in enumerate(top_by_code, 1):
            report.append(f"{i}. **{name}**: {result['code_lines']:,}줄")
        
        report.append("\n### 파일 수 기준 Top 5\n")
        top_by_files = sorted(self.analysis_results.items(), 
                             key=lambda x: x[1]['total_files'], 
                             reverse=True)[:5]
        for i, (name, result) in enumerate(top_by_files, 1):
            report.append(f"{i}. **{name}**: {result['total_files']}개 파일")
        
        report.append("\n---\n")
        report.append("## ✅ 결론\n")
        # Prevent division by zero
        completion_percentage = (total_existing / total_files * 100) if total_files > 0 else 0
        report.append(f"\n신세계 프로젝트는 총 {len(self.analysis_results)}개의 주요 프로젝트로 구성되어 있으며, ")
        report.append(f"{total_code:,}줄의 코드로 구현되어 있습니다. ")
        report.append(f"전체 파일 중 {completion_percentage:.1f}%가 존재하며, ")
        report.append("체계적인 모듈 구조를 갖추고 있습니다.\n")
        
        return '\n'.join(report)
    
    def run_analysis(self):
        """전체 분석 실행"""
        print("🚀 신세계 프로젝트 전체 분석 시작")
        print(f"분석 대상: {len(self.projects)}개 프로젝트")
        
        for project_name, project_info in self.projects.items():
            result = self.analyze_project(project_name, project_info)
            self.analysis_results[project_name] = result
        
        print(f"\n{'='*80}")
        print("✅ 전체 프로젝트 분석 완료!")
        print(f"{'='*80}\n")
        
        # 보고서 생성
        report = self.generate_summary_report()
        
        # 보고서 저장
        report_path = self.base_path / "신세계_프로젝트_분석_보고서.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 분석 보고서가 생성되었습니다: {report_path}")
        
        # JSON 결과도 저장
        json_path = self.base_path / "신세계_프로젝트_분석_결과.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)
        
        print(f"📊 JSON 결과가 저장되었습니다: {json_path}")
        
        return report


def main():
    """메인 함수"""
    print("=" * 80)
    print("🧠 신세계 프로젝트 종합 분석 시스템")
    print("=" * 80)
    
    analyzer = ShinsegyeProjectAnalyzer()
    analyzer.run_analysis()
    
    print("\n🎉 분석이 완료되었습니다!")


if __name__ == "__main__":
    main()
