#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚔 CYBER-Detective AI: 사이버 범죄 수사 전문 AI 시스템
불법거래, 사이버 범죄, 디지털 포렌식 전문 수사관 AI
"""

import hashlib
import random
import re
import sqlite3
import time
from datetime import datetime, timedelta


class CyberDetectiveAI:
    """사이버 범죄 수사 전문 AI"""

    def __init__(self):
        """사이버 수사관 AI 초기화"""
        self.case_id_counter = 1000
        self.active_cases = {}
        self.evidence_database = {}
        self.surveillance_patterns = {}

        # 수사 데이터베이스 초기화
        self.init_investigation_database()

        # 불법거래 패턴 데이터베이스 로드
        self.load_illegal_trade_patterns()

        # 사이버 범죄 시그니처 로드
        self.load_cybercrime_signatures()

        print("🚔 CYBER-Detective AI가 준비되었습니다!")
        print("🔍 사이버 범죄 수사 시스템 활성화")

    def init_investigation_database(self):
        """수사 데이터베이스 초기화"""
        self.conn = sqlite3.connect('cyber_investigation.db')
        cursor = self.conn.cursor()

        # 사건 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                case_type TEXT,
                severity_level INTEGER,
                status TEXT,
                created_date TIMESTAMP,
                last_updated TIMESTAMP,
                evidence_count INTEGER,
                suspect_count INTEGER,
                case_summary TEXT
            )
        ''')

        # 증거 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                case_id TEXT,
                evidence_type TEXT,
                hash_value TEXT,
                metadata TEXT,
                analysis_result TEXT,
                chain_of_custody TEXT,
                created_date TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases (case_id)
            )
        ''')

        # 수상한 활동 로그
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suspicious_activities (
                activity_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                activity_type TEXT,
                source_ip TEXT,
                target_info TEXT,
                pattern_match TEXT,
                risk_score INTEGER,
                status TEXT
            )
        ''')

        self.conn.commit()
        print("🗃️ 수사 데이터베이스 초기화 완료")

    def load_illegal_trade_patterns(self):
        """불법거래 패턴 데이터베이스 로드"""
        self.illegal_patterns = {
            # 암호화폐 관련 불법거래
            'cryptocurrency_fraud': {
                'keywords': ['빠른수익', '투자보장', '원금보장', '고수익확정', '코인투자'],
                'patterns': [r'(\d+)%\s*수익보장', r'원금\s*(\d+)\s*배', r'확정\s*수익'],
                'risk_level': 9,
                'description': '암호화폐 투자사기'
            },

            # 마약 거래
            'drug_trafficking': {
                'keywords': ['떨', '뽕', '아이스', '몰리', '엑스터시', '대마', '마리화나'],
                'patterns': [r'(떨|뽕|아이스)\s*(\d+)g', r'순도\s*(\d+)%', r'직거래\s*가능'],
                'risk_level': 10,
                'description': '마약 밀매'
            },

            # 무기 거래
            'weapon_trafficking': {
                'keywords': ['총기', '권총', '소총', '폭발물', '수류탄', '화약'],
                'patterns': [r'(권총|소총|총기)\s*판매', r'실탄\s*(\d+)발', r'무기\s*거래'],
                'risk_level': 10,
                'description': '무기 밀매'
            },

            # 신분증 위조
            'fake_documents': {
                'keywords': ['주민등록증', '신분증위조', '여권위조', '면허증제작', '증명서위조'],
                'patterns': [r'(주민등록증|신분증|여권)\s*제작', r'위조\s*(증명서|서류)', r'대포\s*계좌'],
                'risk_level': 8,
                'description': '신분증 위조'
            },

            # 개인정보 거래
            'personal_data_trade': {
                'keywords': ['개인정보판매', '주민번호', '신용정보', '통장사본', '대출정보'],
                'patterns': [r'개인정보\s*(\d+)건', r'주민번호\s*리스트', r'신용정보\s*판매'],
                'risk_level': 9,
                'description': '개인정보 불법거래'
            },

            # 피싱/스미싱
            'phishing': {
                'keywords': ['카드정보입력', '인증번호확인', '긴급확인', '계좌확인', '본인인증'],
                'patterns': [r'(카드|계좌)\s*정보\s*입력', r'인증번호\s*(\d+)', r'긴급\s*확인'],
                'risk_level': 7,
                'description': '피싱/스미싱 사기'
            },

            # 랜섬웨어
            'ransomware': {
                'keywords': ['파일암호화', '복구비용', '비트코인지불', '데이터복구', '시간제한'],
                'patterns': [r'파일.*암호화', r'비트코인\s*(\d+\.?\d*)', r'(\d+)시간\s*내\s*지불'],
                'risk_level': 10,
                'description': '랜섬웨어 공격'
            }
        }

        print(f"🎯 {len(self.illegal_patterns)}개 불법거래 패턴 로드 완료")

    def load_cybercrime_signatures(self):
        """사이버 범죄 시그니처 로드"""
        self.crime_signatures = {
            # 해킹 시그니처
            'hacking_attempts': [
                'SQL injection',
                'Cross-site scripting',
                'Buffer overflow',
                'Directory traversal',
                'Command injection',
                'Remote code execution'
            ],

            # 악성코드 시그니처
            'malware_signatures': [
                'Trojan',
                'Backdoor',
                'Keylogger',
                'Rootkit',
                'Botnet',
                'Spyware'
            ],

            # 금융 사기 시그니처
            'financial_fraud': [
                '보이스피싱',
                '스미싱',
                '메신저피싱',
                '대출사기',
                '투자사기',
                '중고거래사기'
            ]
        }

    def analyze_content(self, content, source="unknown"):
        """콘텐츠 분석 및 불법거래 탐지"""
        analysis_result = {
            'timestamp': datetime.now(),
            'source': source,
            'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16],
            'detected_patterns': [],
            'risk_score': 0,
            'threat_level': 'LOW',
            'recommendations': []
        }

        print(f"\n🔍 콘텐츠 분석 시작: {source}")
        print(f"📄 내용 길이: {len(content)}자")

        # 각 불법거래 패턴에 대해 검사
        for pattern_name, pattern_data in self.illegal_patterns.items():
            matches = self._check_pattern_match(content, pattern_data)

            if matches['found']:
                detection = {
                    'pattern_type': pattern_name,
                    'description': pattern_data['description'],
                    'matched_keywords': matches['keywords'],
                    'matched_patterns': matches['patterns'],
                    'risk_level': pattern_data['risk_level']
                }

                analysis_result['detected_patterns'].append(detection)
                analysis_result['risk_score'] += pattern_data['risk_level']

                print(f"🚨 {pattern_data['description']} 패턴 감지!")
                print(f"   키워드: {matches['keywords']}")
                if matches['patterns']:
                    print(f"   패턴: {matches['patterns']}")

        # 위험도 레벨 결정
        if analysis_result['risk_score'] >= 25:
            analysis_result['threat_level'] = 'CRITICAL'
            analysis_result['recommendations'].append('즉시 수사기관 신고 필요')
        elif analysis_result['risk_score'] >= 15:
            analysis_result['threat_level'] = 'HIGH'
            analysis_result['recommendations'].append('정밀 조사 필요')
        elif analysis_result['risk_score'] >= 8:
            analysis_result['threat_level'] = 'MEDIUM'
            analysis_result['recommendations'].append('모니터링 강화')
        elif analysis_result['risk_score'] > 0:
            analysis_result['threat_level'] = 'LOW'
            analysis_result['recommendations'].append('주의 관찰')

        # 자동 사건 생성 (고위험의 경우)
        if analysis_result['threat_level'] in ['CRITICAL', 'HIGH']:
            case_id = self.create_investigation_case(analysis_result, content)
            analysis_result['case_id'] = case_id

        return analysis_result

    def _check_pattern_match(self, content, pattern_data):
        """패턴 매칭 검사"""
        result = {
            'found': False,
            'keywords': [],
            'patterns': []
        }

        content_lower = content.lower()

        # 키워드 검사
        for keyword in pattern_data['keywords']:
            if keyword.lower() in content_lower:
                result['keywords'].append(keyword)
                result['found'] = True

        # 정규식 패턴 검사
        for pattern in pattern_data['patterns']:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                result['patterns'].extend(matches)
                result['found'] = True

        return result

    def create_investigation_case(self, analysis_result, evidence_content):
        """수사 사건 생성"""
        case_id = f"CASE-{self.case_id_counter:04d}"
        self.case_id_counter += 1

        # 사건 유형 결정
        if analysis_result['detected_patterns']:
            primary_pattern = max(analysis_result['detected_patterns'],
                                  key=lambda x: x['risk_level'])
            case_type = primary_pattern['description']
        else:
            case_type = "수상한 활동"

        case_info = {
            'case_id': case_id,
            'case_type': case_type,
            'severity_level': analysis_result['risk_score'],
            'status': 'ACTIVE',
            'created_date': datetime.now(),
            'evidence_content': evidence_content,
            'analysis_result': analysis_result
        }

        self.active_cases[case_id] = case_info

        # 데이터베이스에 저장
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO cases (case_id, case_type, severity_level, status,
                             created_date, last_updated, evidence_count, suspect_count, case_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id, case_type, analysis_result['risk_score'], 'ACTIVE',
            datetime.now(), datetime.now(), 1, 0,
            f"{case_type} - 위험도: {analysis_result['threat_level']}"
        ))

        self.conn.commit()

        print(f"\n📋 수사 사건 생성: {case_id}")
        print(f"   사건 유형: {case_type}")
        print(f"   위험도: {analysis_result['threat_level']} ({analysis_result['risk_score']}점)")

        return case_id

    def monitor_network_traffic(self, duration_minutes=5):
        """네트워크 트래픽 모니터링 시뮬레이션"""
        print(f"\n🌐 네트워크 트래픽 모니터링 시작 ({duration_minutes}분)")

        suspicious_activities = []

        # 시뮬레이션 데이터 생성
        for i in range(duration_minutes * 10):  # 6초마다 체크
            activity = self._generate_network_activity()

            if activity['suspicious']:
                suspicious_activities.append(activity)
                self._log_suspicious_activity(activity)

                print(f"🚨 수상한 활동 감지: {activity['description']}")
                print(f"   출발지: {activity['source_ip']}")
                print(f"   대상: {activity['target']}")
                print(f"   위험도: {activity['risk_score']}/10")

            time.sleep(0.1)  # 실제로는 더 짧은 간격

        print(f"\n📊 모니터링 결과:")
        print(f"   총 수상한 활동: {len(suspicious_activities)}건")

        if suspicious_activities:
            high_risk = [a for a in suspicious_activities if a['risk_score'] >= 8]
            if high_risk:
                print(f"   고위험 활동: {len(high_risk)}건")
                for activity in high_risk[:3]:  # 상위 3건만 표시
                    print(f"     • {activity['description']} (위험도: {activity['risk_score']})")

        return suspicious_activities

    def _generate_network_activity(self):
        """네트워크 활동 시뮬레이션"""
        activities = [
            {
                'type': 'port_scan',
                'description': '포트 스캔 시도',
                'suspicious': True,
                'risk_score': random.randint(6, 8)
            },
            {
                'type': 'ddos_attempt',
                'description': 'DDoS 공격 시도',
                'suspicious': True,
                'risk_score': random.randint(8, 10)
            },
            {
                'type': 'malware_download',
                'description': '악성코드 다운로드',
                'suspicious': True,
                'risk_score': random.randint(7, 9)
            },
            {
                'type': 'normal_web',
                'description': '일반 웹 트래픽',
                'suspicious': False,
                'risk_score': 0
            },
            {
                'type': 'data_exfiltration',
                'description': '데이터 유출 시도',
                'suspicious': True,
                'risk_score': random.randint(9, 10)
            }
        ]

        activity = random.choice(activities)
        activity.update({
            'timestamp': datetime.now(),
            'source_ip': f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
            'target': f"external-{random.randint(1000, 9999)}.com"
        })

        return activity

    def _log_suspicious_activity(self, activity):
        """수상한 활동 로그"""
        activity_id = f"ACT-{int(time.time())}-{random.randint(1000, 9999)}"

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO suspicious_activities
            (activity_id, timestamp, activity_type, source_ip, target_info,
             pattern_match, risk_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            activity_id, activity['timestamp'], activity['type'],
            activity['source_ip'], activity['target'], activity['description'],
            activity['risk_score'], 'DETECTED'
        ))

        self.conn.commit()

    def digital_forensics_analysis(self, file_path_simulation=None):
        """디지털 포렌식 분석 시뮬레이션"""
        print("\n🔬 디지털 포렌식 분석 시작")

        # 시뮬레이션 데이터
        forensic_findings = {
            'file_analysis': {
                'total_files': random.randint(1000, 5000),
                'deleted_files': random.randint(50, 200),
                'encrypted_files': random.randint(10, 50),
                'suspicious_files': random.randint(5, 25)
            },
            'timeline_analysis': {
                'suspicious_activities': [],
                'file_modifications': [],
                'network_connections': []
            },
            'metadata_analysis': {
                'gps_locations': [],
                'device_info': {},
                'application_usage': {}
            }
        }

        # 타임라인 분석
        for i in range(5):
            suspicious_time = datetime.now() - timedelta(days=random.randint(1, 30))
            forensic_findings['timeline_analysis']['suspicious_activities'].append({
                'timestamp': suspicious_time,
                'activity': random.choice([
                    '대량 파일 삭제',
                    '암호화 소프트웨어 실행',
                    '익명 브라우저 사용',
                    '외부 저장장치 연결',
                    'VPN 소프트웨어 실행'
                ]),
                'evidence_level': random.choice(['HIGH', 'MEDIUM', 'LOW'])
            })

        print("📋 포렌식 분석 결과:")
        print(f"   전체 파일: {forensic_findings['file_analysis']['total_files']}개")
        print(f"   삭제된 파일: {forensic_findings['file_analysis']['deleted_files']}개")
        print(f"   암호화된 파일: {forensic_findings['file_analysis']['encrypted_files']}개")
        print(f"   수상한 파일: {forensic_findings['file_analysis']['suspicious_files']}개")

        print("\n⏰ 수상한 활동 타임라인:")
        for activity in forensic_findings['timeline_analysis']['suspicious_activities']:
            print(
                f"   {activity['timestamp'].strftime('%Y-%m-%d %H:%M')} - {activity['activity']} ({activity['evidence_level']})")

        return forensic_findings

    def generate_investigation_report(self, case_id):
        """수사 보고서 생성"""
        if case_id not in self.active_cases:
            return f"❌ 사건 ID {case_id}를 찾을 수 없습니다."

        case = self.active_cases[case_id]

        report = f"""
🚔 CYBER-Detective AI 수사 보고서
=====================================

📋 사건 정보
-----------
사건 ID: {case['case_id']}
사건 유형: {case['case_type']}
생성 일자: {case['created_date'].strftime('%Y-%m-%d %H:%M:%S')}
위험도: {case['analysis_result']['threat_level']} ({case['severity_level']}점)
상태: {case['status']}

🔍 분석 결과
-----------
"""

        for pattern in case['analysis_result']['detected_patterns']:
            report += f"""
• {pattern['description']}
  - 위험도: {pattern['risk_level']}/10
  - 감지된 키워드: {', '.join(pattern['matched_keywords'])}
"""
            if pattern['matched_patterns']:
                report += f"  - 매칭 패턴: {pattern['matched_patterns']}\n"

        report += f"""
💡 권고사항
---------
"""
        for recommendation in case['analysis_result']['recommendations']:
            report += f"• {recommendation}\n"

        report += f"""
📊 증거 해시
----------
콘텐츠 해시: {case['analysis_result']['content_hash']}

=====================================
보고서 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report

    def show_dashboard(self):
        """사이버 수사대 대시보드"""
        print("\n" + "=" * 60)
        print("🚔 CYBER-Detective AI 수사 대시보드")
        print("=" * 60)

        # 활성 사건 현황
        total_cases = len(self.active_cases)
        critical_cases = sum(1 for case in self.active_cases.values()
                             if case['analysis_result']['threat_level'] == 'CRITICAL')
        high_cases = sum(1 for case in self.active_cases.values()
                         if case['analysis_result']['threat_level'] == 'HIGH')

        print(f"\n📊 사건 현황:")
        print(f"   총 활성 사건: {total_cases}건")
        print(f"   긴급 사건: {critical_cases}건")
        print(f"   고위험 사건: {high_cases}건")

        # 최근 감지된 위협
        if self.active_cases:
            print(f"\n🚨 최근 감지 위협:")
            recent_cases = list(self.active_cases.values())[-3:]
            for case in recent_cases:
                print(f"   • {case['case_id']}: {case['case_type']} "
                      f"({case['analysis_result']['threat_level']})")

        # 패턴 통계
        pattern_counts = {}
        for case in self.active_cases.values():
            for pattern in case['analysis_result']['detected_patterns']:
                pattern_type = pattern['description']
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1

        if pattern_counts:
            print(f"\n📈 위협 유형별 통계:")
            for pattern_type, count in sorted(pattern_counts.items(),
                                              key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {pattern_type}: {count}건")

        print("=" * 60)


def demo_cyber_detective():
    """사이버 수사대 데모"""
    print("🚔 CYBER-Detective AI 데모 시작!")

    # AI 초기화
    detective = CyberDetectiveAI()

    # 테스트 케이스들
    test_cases = [
        {
            'title': '암호화폐 투자사기',
            'content': '빠른수익 보장! 원금 10배 수익 확정! 비트코인 투자로 한달만에 1000% 수익! 연락주세요'
        },
        {
            'title': '마약 거래',
            'content': '떨 10g 판매합니다. 순도 95% 보장. 직거래 가능. 연락 바랍니다.'
        },
        {
            'title': '신분증 위조',
            'content': '주민등록증 제작해드립니다. 완벽한 위조 신분증. 대포계좌 개설 가능'
        },
        {
            'title': '일반 대화',
            'content': '안녕하세요. 오늘 날씨가 정말 좋네요. 커피 한잔 하러 갈까요?'
        },
        {
            'title': '피싱 시도',
            'content': '긴급! 카드정보 입력하세요. 본인인증 필요합니다. 인증번호 1234 입력해주세요.'
        }
    ]

    print(f"\n🧪 {len(test_cases)}개 테스트 케이스 분석:")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 50}")
        print(f"🔍 테스트 {i}: {test_case['title']}")
        print(f"📄 내용: {test_case['content']}")

        # 분석 실행
        result = detective.analyze_content(test_case['content'],
                                           source=f"test_case_{i}")

        print(f"\n📊 분석 결과:")
        print(f"   위험도: {result['threat_level']} ({result['risk_score']}점)")

        if result['detected_patterns']:
            print(f"   감지된 패턴:")
            for pattern in result['detected_patterns']:
                print(f"     • {pattern['description']} (위험도: {pattern['risk_level']}/10)")

        if result.get('case_id'):
            print(f"   🚨 수사 사건 생성: {result['case_id']}")

        time.sleep(1)

    # 대시보드 표시
    detective.show_dashboard()

    # 네트워크 모니터링 데모
    print(f"\n🌐 네트워크 모니터링 데모 (1분):")
    detective.monitor_network_traffic(1)

    # 포렌식 분석 데모
    detective.digital_forensics_analysis()

    # 수사 보고서 생성
    if detective.active_cases:
        case_id = list(detective.active_cases.keys())[0]
        print(f"\n📄 수사 보고서 생성:")
        report = detective.generate_investigation_report(case_id)
        print(report)

    print(f"\n🎊 CYBER-Detective AI 데모 완료!")
    print(f"총 {len(detective.active_cases)}건의 사건이 생성되었습니다.")


if __name__ == "__main__":
    demo_cyber_detective()
