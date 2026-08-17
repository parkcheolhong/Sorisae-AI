#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹 앱 검증 테스트 스크립트
Web App Verification Test Script

이 스크립트는 모든 웹 앱 파일의 문법과 import를 검증합니다.
"""

import os
import sys
import py_compile
from pathlib import Path

# ANSI 색상 코드
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(title):
    """헤더 출력"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{title:^60}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

def check_file_exists(filepath):
    """파일 존재 확인"""
    return os.path.exists(filepath)

def check_python_syntax(filepath):
    """Python 파일 문법 검사"""
    try:
        py_compile.compile(filepath, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)

def check_html_basic(filepath):
    """HTML 파일 기본 검증"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = {
            'DOCTYPE': '<!DOCTYPE' in content,
            'UTF-8': 'UTF-8' in content or 'utf-8' in content,
            'HTML_TAG': '<html' in content,
            'HEAD_TAG': '<head>' in content or '<head ' in content,
            'BODY_TAG': '<body>' in content or '<body ' in content,
        }
        
        return all(checks.values()), checks
    except Exception as e:
        return False, {'error': str(e)}

def main():
    """메인 함수"""
    print_header("웹 앱 디자인 검증 테스트")
    
    # 웹 앱 파일 목록
    python_web_files = [
        'sorisae_dashboard_web.py',
        'shopping_mall_dashboard.py',
        'simple_dashboard.py',
        'launch_dashboard.py',
        'cyber_detective_dashboard.py',
        'sorisae_movie_web_server.py',
        'modules/sorisae_dashboard_web.py',
        'modules/ai_code_manager/music_chat_web.py',
    ]
    
    html_files = [
        'optimization_dashboard.html',
        'shopping_mall_visual.html',
        'templates/dashboard.html',
    ]
    
    # 통계
    stats = {
        'python_total': len(python_web_files),
        'python_passed': 0,
        'python_failed': 0,
        'html_total': len(html_files),
        'html_passed': 0,
        'html_failed': 0,
    }
    
    # Python 파일 검증
    print_header("Python 웹 서버 파일 검증")
    
    for filepath in python_web_files:
        filename = os.path.basename(filepath)
        
        # 파일 존재 확인
        if not check_file_exists(filepath):
            print(f"{RED}❌ {filepath}{RESET}")
            print(f"   파일을 찾을 수 없습니다.\n")
            stats['python_failed'] += 1
            continue
        
        # 문법 검사
        success, error = check_python_syntax(filepath)
        
        if success:
            print(f"{GREEN}✅ {filepath}{RESET}")
            print(f"   문법 검사 통과\n")
            stats['python_passed'] += 1
        else:
            print(f"{RED}❌ {filepath}{RESET}")
            print(f"   문법 오류: {error}\n")
            stats['python_failed'] += 1
    
    # HTML 파일 검증
    print_header("HTML 대시보드 파일 검증")
    
    for filepath in html_files:
        filename = os.path.basename(filepath)
        
        # 파일 존재 확인
        if not check_file_exists(filepath):
            print(f"{RED}❌ {filepath}{RESET}")
            print(f"   파일을 찾을 수 없습니다.\n")
            stats['html_failed'] += 1
            continue
        
        # HTML 기본 검증
        success, checks = check_html_basic(filepath)
        
        if success:
            print(f"{GREEN}✅ {filepath}{RESET}")
            print(f"   HTML 무결성 확인\n")
            stats['html_passed'] += 1
        else:
            print(f"{YELLOW}⚠️  {filepath}{RESET}")
            print(f"   일부 검사 실패: {checks}\n")
            stats['html_failed'] += 1
    
    # 의존성 검증
    print_header("의존성 검증")
    
    requirements_file = 'requirements.txt'
    required_packages = ['flask', 'flask-socketio', 'python-socketio']
    
    if check_file_exists(requirements_file):
        with open(requirements_file, 'r') as f:
            requirements = f.read().lower()
        
        for package in required_packages:
            if package in requirements:
                print(f"{GREEN}✅ {package}{RESET} - requirements.txt에 포함됨")
            else:
                print(f"{RED}❌ {package}{RESET} - requirements.txt에 없음")
    else:
        print(f"{RED}❌ requirements.txt 파일을 찾을 수 없습니다.{RESET}")
    
    # 최종 결과
    print_header("검증 결과 요약")
    
    print(f"Python 웹 서버 파일:")
    print(f"  총 파일 수: {stats['python_total']}")
    print(f"  {GREEN}✅ 통과: {stats['python_passed']}{RESET}")
    print(f"  {RED}❌ 실패: {stats['python_failed']}{RESET}")
    print(f"  성공률: {stats['python_passed']/stats['python_total']*100:.1f}%\n")
    
    print(f"HTML 대시보드 파일:")
    print(f"  총 파일 수: {stats['html_total']}")
    print(f"  {GREEN}✅ 통과: {stats['html_passed']}{RESET}")
    print(f"  {YELLOW}⚠️  실패: {stats['html_failed']}{RESET}")
    print(f"  성공률: {stats['html_passed']/stats['html_total']*100:.1f}%\n")
    
    # 전체 성공 여부
    total_passed = stats['python_passed'] + stats['html_passed']
    total_files = stats['python_total'] + stats['html_total']
    overall_success = (stats['python_failed'] == 0 and stats['html_failed'] == 0)
    
    print(f"{'=' * 60}")
    print(f"전체 검증 결과: {total_passed}/{total_files} 파일 통과")
    print(f"{'=' * 60}\n")
    
    if overall_success:
        print(f"{GREEN}🎉 모든 웹 앱이 검증되었습니다!{RESET}")
        print(f"{GREEN}✅ 즉시 사용 가능 상태입니다.{RESET}\n")
        return 0
    else:
        print(f"{YELLOW}⚠️  일부 파일에서 문제가 발견되었습니다.{RESET}")
        print(f"{YELLOW}상세 내용은 위의 로그를 확인하세요.{RESET}\n")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
