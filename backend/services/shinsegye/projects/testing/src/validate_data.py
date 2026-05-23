#!/usr/bin/env python3
"""
데이터 검증 스크립트 (Data Validation Script)

이 스크립트는 프로젝트의 데이터 파일들을 자동으로 검증합니다.
This script automatically validates the project's data files.

사용법 (Usage):
    python validate_data.py
"""

import json
import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict


class DataValidator:
    """데이터 검증 클래스"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.errors = []
        self.warnings = []
        self.info = []

    def validate_all(self) -> Dict[str, Any]:
        """모든 데이터 파일을 검증합니다"""
        print("🔍 데이터 검증을 시작합니다...")
        print("=" * 60)

        results = {
            'timestamp': datetime.now().isoformat(),
            'files_checked': 0,
            'errors': [],
            'warnings': [],
            'info': [],
            'summary': {}
        }

        # 1. autonomous_mall_data.json 검증
        mall_result = self.validate_mall_data()
        if mall_result:
            results['files_checked'] += 1
            results['summary']['mall_data'] = mall_result

        # 2. knowledge_base.json 검증
        kb_result = self.validate_knowledge_base()
        if kb_result:
            results['files_checked'] += 1
            results['summary']['knowledge_base'] = kb_result

        # 3. autonomous_marketing_data.json 검증
        marketing_result = self.validate_marketing_data()
        if marketing_result:
            results['files_checked'] += 1
            results['summary']['marketing_data'] = marketing_result

        # 결과 취합
        results['errors'] = self.errors
        results['warnings'] = self.warnings
        results['info'] = self.info

        return results

    def validate_mall_data(self) -> Dict[str, Any]:
        """자율 쇼핑몰 데이터 검증"""
        filepath = os.path.join(self.data_dir, "autonomous_mall_data.json")

        print("\n📦 자율 쇼핑몰 데이터 검증 중...")

        if not os.path.exists(filepath):
            self.errors.append(f"파일 없음: {filepath}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON 형식 오류: {filepath} - {e}")
            return None

        result = {
            'file_exists': True,
            'valid_json': True,
            'issues': []
        }

        # 필수 키 확인
        required_keys = ['products', 'customers', 'orders', 'inventory', 'mall_stats']
        for key in required_keys:
            if key not in data:
                self.errors.append(f"필수 키 누락: {key}")
                result['issues'].append(f"missing_key_{key}")

        # 제품 데이터 검증
        products = data.get('products', [])
        print(f"  ✓ 제품: {len(products)}개")

        product_ids = [p.get('id') for p in products]
        duplicates = [pid for pid, count in Counter(product_ids).items() if count > 1]
        if duplicates:
            self.warnings.append(f"중복 제품 ID: {duplicates}")
            result['issues'].append('duplicate_product_ids')

        # 주문 데이터 검증
        orders = data.get('orders', [])
        print(f"  ✓ 주문: {len(orders)}건")

        order_ids = [o.get('order_id') for o in orders]
        duplicate_orders = [oid for oid, count in Counter(order_ids).items() if count > 1]
        if duplicate_orders:
            self.errors.append(f"🔴 중복 주문 ID: {len(duplicate_orders)}개 발견")
            print(f"    ⚠️  중복 주문 ID: {len(duplicate_orders)}개")
            result['issues'].append('duplicate_order_ids')
            result['duplicate_order_count'] = len(duplicate_orders)

        # 고객 데이터 검증
        customers = data.get('customers', [])
        print(f"  ✓ 고객: {len(customers)}명")

        if len(customers) == 0 and len(orders) > 0:
            self.warnings.append("주문은 있지만 고객 데이터가 없습니다")
            print("    ⚠️  고객 데이터 누락")
            result['issues'].append('missing_customer_data')

        # 재고 데이터 검증
        inventory = data.get('inventory', {})
        print(f"  ✓ 재고: {len(inventory)}개 항목")

        # 재고와 제품 ID 일치 확인
        for pid in product_ids:
            if pid not in inventory:
                self.warnings.append(f"재고 정보 없음: {pid}")
                result['issues'].append(f'missing_inventory_{pid}')

        # 매출 검증
        mall_stats = data.get('mall_stats', {})
        total_revenue = mall_stats.get('total_revenue', 0)

        # 주문 금액 합계 계산
        calculated_revenue = sum(o.get('price', 0) for o in orders)

        if abs(total_revenue - calculated_revenue) > 0.01:
            self.errors.append(
                f"매출 불일치: 기록={total_revenue:,}, 계산={calculated_revenue:,}"
            )
            result['issues'].append('revenue_mismatch')
        else:
            print(f"  ✓ 매출 검증: {total_revenue:,}원")

        return result

    def validate_knowledge_base(self) -> Dict[str, Any]:
        """지식 베이스 검증"""
        filepath = os.path.join(self.data_dir, "knowledge_base.json")

        print("\n🧠 지식 베이스 검증 중...")

        if not os.path.exists(filepath):
            self.errors.append(f"파일 없음: {filepath}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON 형식 오류: {filepath} - {e}")
            return None

        result = {
            'file_exists': True,
            'valid_json': True,
            'issues': []
        }

        # 학습된 명령어 통계
        successful = data.get('successful_responses', {})
        failed = data.get('failed_responses', {})

        print(f"  ✓ 성공 명령어: {len(successful)}개")
        print(f"  ✓ 실패 명령어: {len(failed)}개")

        # 웹 검색 캐시
        cache = data.get('web_search_cache', {})
        print(f"  ✓ 웹 검색 캐시: {len(cache)}개")

        # 기능 목록
        capabilities = data.get('capabilities', [])
        print(f"  ✓ 기능: {len(capabilities)}개")

        if len(successful) == 0:
            self.warnings.append("학습된 명령어가 없습니다")
            result['issues'].append('no_learned_commands')

        return result

    def validate_marketing_data(self) -> Dict[str, Any]:
        """마케팅 데이터 검증"""
        filepath = os.path.join(self.data_dir, "autonomous_marketing_data.json")

        print("\n📊 마케팅 데이터 검증 중...")

        if not os.path.exists(filepath):
            self.errors.append(f"파일 없음: {filepath}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON 형식 오류: {filepath} - {e}")
            return None

        result = {
            'file_exists': True,
            'valid_json': True,
            'issues': []
        }

        # 마케팅 데이터 확인
        campaigns = data.get('ad_campaigns', [])
        analytics = data.get('sales_analytics', {})
        feedback = data.get('customer_feedback', [])

        print(f"  ✓ 광고 캠페인: {len(campaigns)}개")
        print(f"  ✓ 판매 분석: {len(analytics)}개 항목")
        print(f"  ✓ 고객 피드백: {len(feedback)}개")

        if len(campaigns) == 0 and len(analytics) == 0:
            self.info.append("마케팅 데이터가 아직 수집되지 않았습니다 (초기 상태)")
            result['issues'].append('empty_marketing_data')

        return result

    def print_summary(self, results: Dict[str, Any]):
        """검증 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📋 검증 결과 요약")
        print("=" * 60)

        print(f"\n검증한 파일: {results['files_checked']}개")
        print(f"검증 시각: {results['timestamp']}")

        # 오류
        if results['errors']:
            print(f"\n🔴 오류: {len(results['errors'])}건")
            for error in results['errors']:
                print(f"  - {error}")
        else:
            print("\n✅ 오류 없음")

        # 경고
        if results['warnings']:
            print(f"\n🟡 경고: {len(results['warnings'])}건")
            for warning in results['warnings']:
                print(f"  - {warning}")
        else:
            print("\n✅ 경고 없음")

        # 정보
        if results['info']:
            print(f"\nℹ️  정보: {len(results['info'])}건")
            for info in results['info']:
                print(f"  - {info}")

        # 전체 평가
        print("\n" + "=" * 60)
        if not results['errors']:
            if not results['warnings']:
                print("🎉 모든 데이터가 정상입니다!")
                print("평가: ⭐⭐⭐⭐⭐ (우수)")
            else:
                print("✅ 데이터가 양호합니다 (일부 개선 권장)")
                print("평가: ⭐⭐⭐⭐ (양호)")
        else:
            print("⚠️  중요한 문제가 발견되었습니다. 수정이 필요합니다.")
            print("평가: ⭐⭐⭐ (개선 필요)")
        print("=" * 60)


def main():
    """메인 함수"""
    validator = DataValidator()
    results = validator.validate_all()
    validator.print_summary(results)

    # 결과를 JSON 파일로 저장
    output_file = "data_validation_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📁 상세 결과가 '{output_file}'에 저장되었습니다.")

    # 오류가 있으면 종료 코드 1 반환
    return 1 if results['errors'] else 0


if __name__ == "__main__":
    exit(main())
