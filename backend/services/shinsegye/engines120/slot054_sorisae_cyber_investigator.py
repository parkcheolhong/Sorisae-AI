#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 소리새 사이버 수사대 시스템
불법거래 탐지, 사이버 범죄 수사, 디지털 포렌식
"""

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime


class SorisaeCyberInvestigator:
    """소리새 사이버 수사대"""

    def __init__(self):
        """사이버 수사대 시스템 초기화"""
        self.investigation_db = None
        self.suspicious_patterns = {}
        self.case_history = []
        self.alert_level = 1  # 1: 정상, 2: 주의, 3: 경고, 4: 위험, 5: 긴급

        # 데이터베이스 초기화
        self._init_investigation_database()

        # 불법거래 탐지 패턴 로드
        self._load_illegal_trade_patterns()

        # 사이버 범죄 시그니처 로드
        self._load_cybercrime_signatures()

        print("🔍 소리새 사이버 수사대가 활성화되었습니다!")
        print("🚨 불법거래 및 사이버범죄 실시간 모니터링 시작!")

    def _init_investigation_database(self):
        """수사 데이터베이스 초기화"""
        self.investigation_db = sqlite3.connect('sorisae_cyber_investigation.db')
        cursor = self.investigation_db.cursor()

        # 수사 케이스 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investigation_cases (
                case_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_type TEXT NOT NULL,
                severity_level INTEGER,
                evidence_hash TEXT,
                description TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 의심스러운 활동 로그
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suspicious_activities (
                activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_type TEXT NOT NULL,
                risk_score INTEGER,
                content_hash TEXT,
                metadata TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 디지털 증거 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS digital_evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                evidence_type TEXT,
                file_hash TEXT,
                file_path TEXT,
                analysis_result TEXT,
                chain_of_custody TEXT,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES investigation_cases (case_id)
            )
        ''')

        self.investigation_db.commit()
        print("🗃️ 사이버 수사 데이터베이스 초기화 완료")

    def _load_illegal_trade_patterns(self):
        """불법거래 탐지 패턴 로드"""
        self.illegal_trade_patterns = {
            # 마약 관련
            'drugs': {
                'keywords': ['마약', '대마초', '코카인', '헤로인', '펜타닐', '메스암페타민',
                             'drug', 'cocaine', 'heroin', 'marijuana', 'meth'],
                'patterns': [
                    r'(?i)(판매|구매|거래).*(마약|대마|코카인)',
                    r'(?i)(weed|grass|blow|snow).*(for sale|selling)',
                    r'(?i)(고순도|순도\s*\d+%).*(제품|상품)',
                ],
                'risk_score': 95
            },

            # 무기 거래
            'weapons': {
                'keywords': ['총기', '권총', '소총', '폭탄', '화약', '총알', 'grenade', 'explosive'],
                'patterns': [
                    r'(?i)(판매|구매).*(총|권총|소총|폭탄)',
                    r'(?i)(gun|pistol|rifle).*(for sale|selling)',
                    r'(?i)(실탄|공포탄|화약).*(거래|판매)',
                ],
                'risk_score': 98
            },

            # 신분증 위조
            'fake_documents': {
                'keywords': ['위조', '가짜', '신분증', '여권', '운전면허', 'fake', 'counterfeit', 'forged'],
                'patterns': [
                    r'(?i)(위조|가짜).*(신분증|여권|면허)',
                    r'(?i)(fake|counterfeit).*(id|passport|license)',
                    r'(?i)(제작|판매).*(위조.*서류)',
                ],
                'risk_score': 85
            },

            # 인신매매
            'human_trafficking': {
                'keywords': ['인신매매', '성매매', '노예', '강제노동', 'trafficking', 'slavery'],
                'patterns': [
                    r'(?i)(인신매매|성매매)',
                    r'(?i)(human.*trafficking|sex.*trafficking)',
                    r'(?i)(강제.*노동|forced.*labor)',
                ],
                'risk_score': 100
            },

            # 사기
            'fraud': {
                'keywords': ['사기', '피싱', '스미싱', '보이스피싱', 'scam', 'phishing', 'fraud'],
                'patterns': [
                    r'(?i)(보이스.*피싱|전화.*사기)',
                    r'(?i)(피싱.*사이트|가짜.*사이트)',
                    r'(?i)(scam|fraud).*(easy.*money|quick.*cash)',
                ],
                'risk_score': 80
            },

            # 해킹 도구
            'hacking_tools': {
                'keywords': ['해킹', '크랙', '키로거', 'malware', 'virus', 'trojan', 'keylogger'],
                'patterns': [
                    r'(?i)(해킹.*도구|크랙.*프로그램)',
                    r'(?i)(malware|virus|trojan).*(for sale|download)',
                    r'(?i)(키로거|keylogger).*(판매|구매)',
                ],
                'risk_score': 90
            }
        }

    def _load_cybercrime_signatures(self):
        """사이버범죄 시그니처 로드"""
        self.cybercrime_signatures = {
            # 다크웹 관련
            'darkweb_indicators': [
                r'\.onion',
                r'tor.*browser',
                r'deep.*web',
                r'dark.*net',
                r'암호화.*통신'
            ],

            # 암호화폐 불법 거래
            'crypto_illegal': [
                r'(?i)(bitcoin|btc|ethereum|eth).*(laundering|washing)',
                r'(?i)(암호화폐|비트코인).*(세탁|은닉)',
                r'(?i)mixer.*service',
                r'(?i)privacy.*coin'
            ],

            # 랜섬웨어
            'ransomware': [
                r'(?i)ransom.*ware',
                r'(?i)encrypt.*files.*payment',
                r'(?i)(파일.*암호화).*(복구.*비용)',
                r'(?i)bitcoin.*decrypt'
            ],

            # 신용카드 정보 불법 거래
            'credit_card_fraud': [
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 카드번호 패턴
                r'(?i)cvv.*\d{3,4}',
                r'(?i)(dump|fullz).*(cc|credit.*card)',
                r'(?i)(신용카드.*정보).*(판매|거래)'
            ]
        }

    def analyze_content(self, content, content_type="text", source="unknown"):
        """콘텐츠 분석 및 불법 활동 탐지"""
        analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'content_type': content_type,
            'source': source,
            'risk_level': 1,
            'detected_threats': [],
            'evidence_hash': hashlib.sha256(content.encode()).hexdigest()[:16],
            'recommendations': []
        }

        # 불법거래 패턴 검사
        illegal_trade_results = self._check_illegal_trade_patterns(content)
        if illegal_trade_results:
            analysis_result['detected_threats'].extend(illegal_trade_results)

        # 사이버범죄 시그니처 검사
        cybercrime_results = self._check_cybercrime_signatures(content)
        if cybercrime_results:
            analysis_result['detected_threats'].extend(cybercrime_results)

        # 전체 위험도 계산
        if analysis_result['detected_threats']:
            analysis_result['risk_level'] = max([threat['risk_score']
                                                for threat in analysis_result['detected_threats']])

        # 수사 케이스 생성 (위험도 80 이상)
        if analysis_result['risk_level'] >= 80:
            case_id = self._create_investigation_case(analysis_result)
            analysis_result['case_id'] = case_id

        # 의심스러운 활동 로그
        self._log_suspicious_activity(analysis_result)

        return analysis_result

    def _check_illegal_trade_patterns(self, content):
        """불법거래 패턴 검사"""
        detected_threats = []

        for trade_type, patterns in self.illegal_trade_patterns.items():
            # 키워드 검사
            for keyword in patterns['keywords']:
                if keyword.lower() in content.lower():
                    # 패턴 매칭으로 정확도 높이기
                    for pattern in patterns.get('patterns', []):
                        if re.search(pattern, content):
                            threat = {
                                'type': 'illegal_trade',
                                'category': trade_type,
                                'risk_score': patterns['risk_score'],
                                'matched_pattern': pattern,
                                'matched_keyword': keyword,
                                'description': f'{trade_type.replace("_", " ").title()} 관련 불법거래 의심'
                            }
                            detected_threats.append(threat)
                            break

        return detected_threats

    def _check_cybercrime_signatures(self, content):
        """사이버범죄 시그니처 검사"""
        detected_threats = []

        for crime_type, signatures in self.cybercrime_signatures.items():
            for signature in signatures:
                if re.search(signature, content, re.IGNORECASE):
                    threat = {
                        'type': 'cybercrime',
                        'category': crime_type,
                        'risk_score': 75,  # 기본 사이버범죄 위험도
                        'matched_signature': signature,
                        'description': f'{crime_type.replace("_", " ").title()} 사이버범죄 시그니처 탐지'
                    }
                    detected_threats.append(threat)

        return detected_threats

    def _create_investigation_case(self, analysis_result):
        """수사 케이스 생성"""
        cursor = self.investigation_db.cursor()

        case_type = "Mixed" if len(analysis_result['detected_threats']
                                   ) > 1 else analysis_result['detected_threats'][0]['category']
        severity = min(5, max(1, analysis_result['risk_level'] // 20))

        cursor.execute('''
            INSERT INTO investigation_cases
            (case_type, severity_level, evidence_hash, description, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            case_type,
            severity,
            analysis_result['evidence_hash'],
            f"자동 탐지된 {case_type} 관련 사건",
            "ACTIVE"
        ))

        case_id = cursor.lastrowid
        self.investigation_db.commit()

        print(f"🚨 새로운 수사 케이스 생성: Case #{case_id} ({case_type}, 위험도: {severity}/5)")
        return case_id

    def _log_suspicious_activity(self, analysis_result):
        """의심스러운 활동 로그"""
        cursor = self.investigation_db.cursor()

        for threat in analysis_result['detected_threats']:
            cursor.execute('''
                INSERT INTO suspicious_activities
                (activity_type, risk_score, content_hash, metadata)
                VALUES (?, ?, ?, ?)
            ''', (
                threat['category'],
                threat['risk_score'],
                analysis_result['evidence_hash'],
                json.dumps(threat)
            ))

        self.investigation_db.commit()

    def get_investigation_summary(self):
        """수사 현황 요약"""
        cursor = self.investigation_db.cursor()

        # 전체 케이스 수
        cursor.execute("SELECT COUNT(*) FROM investigation_cases")
        total_cases = cursor.fetchone()[0]

        # 활성 케이스 수
        cursor.execute("SELECT COUNT(*) FROM investigation_cases WHERE status = 'ACTIVE'")
        active_cases = cursor.fetchone()[0]

        # 심각도별 케이스 분포
        cursor.execute('''
            SELECT severity_level, COUNT(*)
            FROM investigation_cases
            GROUP BY severity_level
            ORDER BY severity_level DESC
        ''')
        severity_distribution = dict(cursor.fetchall())

        # 최근 24시간 의심스러운 활동
        cursor.execute('''
            SELECT COUNT(*) FROM suspicious_activities
            WHERE detected_at > datetime('now', '-1 day')
        ''')
        recent_activities = cursor.fetchone()[0]

        # 범죄 유형별 통계
        cursor.execute('''
            SELECT case_type, COUNT(*)
            FROM investigation_cases
            GROUP BY case_type
            ORDER BY COUNT(*) DESC
            LIMIT 5
        ''')
        crime_types = dict(cursor.fetchall())

        return {
            'total_cases': total_cases,
            'active_cases': active_cases,
            'severity_distribution': severity_distribution,
            'recent_activities': recent_activities,
            'crime_types': crime_types,
            'alert_level': self.alert_level
        }

    def investigate_digital_evidence(self, file_path):
        """디지털 증거 분석"""
        if not os.path.exists(file_path):
            return {"error": "파일을 찾을 수 없습니다"}

        evidence = {
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'created_time': datetime.fromtimestamp(os.path.getctime(file_path)),
            'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path)),
            'file_hash': self._calculate_file_hash(file_path),
            'analysis_results': []
        }

        # 파일 내용 분석 (텍스트 파일인 경우)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                analysis = self.analyze_content(content, "file", file_path)
                evidence['content_analysis'] = analysis
        except (UnicodeDecodeError, PermissionError):
            evidence['content_analysis'] = {"error": "파일을 읽을 수 없습니다"}

        return evidence

    def _calculate_file_hash(self, file_path):
        """파일 해시 계산"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return "unable_to_calculate"

    def generate_investigation_report(self, case_id=None):
        """수사 보고서 생성"""
        cursor = self.investigation_db.cursor()

        if case_id:
            # 특정 케이스 보고서
            cursor.execute('''
                SELECT * FROM investigation_cases WHERE case_id = ?
            ''', (case_id,))
            case = cursor.fetchone()

            if not case:
                return {"error": f"Case #{case_id}를 찾을 수 없습니다"}

            # 관련 증거 수집
            cursor.execute('''
                SELECT * FROM digital_evidence WHERE case_id = ?
            ''', (case_id,))
            evidence = cursor.fetchall()

            return {
                'case_id': case_id,
                'case_details': case,
                'evidence_count': len(evidence),
                'evidence': evidence,
                'report_generated': datetime.now().isoformat()
            }
        else:
            # 전체 현황 보고서
            summary = self.get_investigation_summary()
            return {
                'report_type': 'summary',
                'summary': summary,
                'report_generated': datetime.now().isoformat()
            }

    def demonstrate_cyber_investigation(self):
        """사이버 수사 시연"""
        print("\n🔍 === 소리새 사이버 수사대 시연 ===")

        # 테스트 시나리오들
        test_scenarios = [
            {
                'name': '마약 거래 의심 메시지',
                'content': '고순도 대마초 판매합니다. 비트코인 결제 가능. 텔레그램으로 연락주세요.',
                'expected': '마약 거래 및 암호화폐 관련 패턴 탐지'
            },
            {
                'name': '무기 거래 시도',
                'content': 'Looking to sell handgun, good condition. Cash only, no questions asked.',
                'expected': '무기 거래 관련 패턴 탐지'
            },
            {
                'name': '피싱 사기 시도',
                'content': '은행 보안 업데이트입니다. 계좌정보를 확인해주세요: http://fake-bank.onion',
                'expected': '피싱 사기 및 다크웹 관련 탐지'
            },
            {
                'name': '신용카드 정보 거래',
                'content': 'Fresh CC dumps available. Fullz with SSN. 4532-1234-5678-9012 CVV 123',
                'expected': '신용카드 사기 관련 탐지'
            },
            {
                'name': '정상적인 대화',
                'content': '안녕하세요, 오늘 날씨가 좋네요. 점심 뭐 드실 예정이세요?',
                'expected': '위험 요소 없음'
            }
        ]

        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n[시나리오 {i}] {scenario['name']}")
            print(f"내용: {scenario['content']}")
            print(f"예상: {scenario['expected']}")

            result = self.analyze_content(scenario['content'], source=f"test_scenario_{i}")

            print(f"🎯 분석 결과:")
            print(f"   위험도: {result['risk_level']}/100")
            print(f"   탐지된 위협: {len(result['detected_threats'])}건")

            for threat in result['detected_threats']:
                print(f"   ⚠️ {threat['description']} (위험도: {threat['risk_score']})")

            if result['risk_level'] >= 80:
                print(f"   🚨 수사 케이스 생성됨: Case #{result.get('case_id', 'N/A')}")

            print("-" * 60)

        # 수사 현황 요약
        summary = self.get_investigation_summary()
        print(f"\n📊 수사 현황 요약:")
        print(f"   총 케이스: {summary['total_cases']}건")
        print(f"   활성 케이스: {summary['active_cases']}건")
        print(f"   최근 24시간 의심활동: {summary['recent_activities']}건")
        print(f"   현재 경보 레벨: {summary['alert_level']}/5")


def main():
    """메인 함수"""
    investigator = SorisaeCyberInvestigator()
    investigator.demonstrate_cyber_investigation()

    print(f"\n🎊 소리새 사이버 수사대 준비 완료!")
    print("불법거래 및 사이버범죄를 실시간으로 탐지하고 수사합니다! 🔍🚨")


if __name__ == "__main__":
    main()
