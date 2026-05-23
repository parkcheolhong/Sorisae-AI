#!/usr/bin/env python3
"""
주문 ID 중복 문제 해결 스크립트
Fix Script for Duplicate Order IDs

이 스크립트는 중복된 주문 ID를 수정하고 각 주문 항목에 고유 ID를 부여합니다.
This script fixes duplicate order IDs and assigns unique IDs to each order item.

사용법 (Usage):
    python fix_duplicate_orders.py [--dry-run]

    --dry-run: 실제로 파일을 변경하지 않고 미리보기만 표시
"""

import argparse
import json
from datetime import datetime
from typing import Dict


def fix_duplicate_orders(data: Dict, dry_run: bool = False) -> Dict:
    """
    중복된 주문 ID를 수정합니다.

    전략:
    1. 각 주문에 고유한 line_item_id 추가
    2. 원래 order_id는 유지 (여러 제품이 같은 주문에 속할 수 있음)
    3. line_item_id = ORDER_ID + "_" + sequential_number
    """
    orders = data.get('orders', [])

    if not orders:
        print("주문 데이터가 없습니다.")
        return data

    print(f"총 {len(orders)}건의 주문을 처리합니다...")

    # 주문 ID별로 항목 카운트
    order_counts = {}

    # 각 주문에 line_item_id 추가
    for i, order in enumerate(orders):
        order_id = order.get('order_id', f'ORD_UNKNOWN_{i}')

        # 이 주문 ID의 몇 번째 항목인지 계산
        if order_id not in order_counts:
            order_counts[order_id] = 0
        order_counts[order_id] += 1

        # line_item_id 생성
        line_item_id = f"{order_id}_ITEM_{order_counts[order_id]:03d}"

        # line_item_id 추가 (이미 있으면 건너뛰기)
        if 'line_item_id' not in order:
            order['line_item_id'] = line_item_id

            if not dry_run and i < 5:  # 처음 5개만 출력
                print(f"  ✓ {order_id} → {line_item_id}")

    # 통계
    total_orders = len(orders)
    unique_orders = len(order_counts)
    multiple_items = sum(1 for count in order_counts.values() if count > 1)

    print(f"\n📊 통계:")
    print(f"  - 전체 주문 항목: {total_orders}건")
    print(f"  - 고유 주문 번호: {unique_orders}개")
    print(f"  - 복수 항목 주문: {multiple_items}개")

    data['orders'] = orders
    return data


def create_backup(filepath: str) -> str:
    """파일 백업 생성"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{filepath}.backup_{timestamp}"

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ 백업 생성: {backup_path}")
    return backup_path


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='주문 ID 중복 문제 해결')
    parser.add_argument('--dry-run', action='store_true',
                        help='실제로 변경하지 않고 미리보기만 표시')
    args = parser.parse_args()

    filepath = 'data/autonomous_mall_data.json'

    print("🔧 주문 ID 중복 문제 해결 스크립트")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  DRY-RUN 모드: 파일을 실제로 변경하지 않습니다.\n")

    # 데이터 로드
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {filepath}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ JSON 형식 오류: {e}")
        return 1

    # 수정 전 상태 확인
    original_orders = len(data.get('orders', []))
    print(f"원본 주문 항목: {original_orders}건\n")

    # 중복 수정
    data = fix_duplicate_orders(data, dry_run=args.dry_run)

    # 저장
    if not args.dry_run:
        # 백업 생성
        backup_path = create_backup(filepath)

        # 수정된 데이터 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 수정 완료: {filepath}")
        print(f"📁 백업 파일: {backup_path}")
    else:
        print("\n⚠️  DRY-RUN 모드였으므로 실제 파일은 변경되지 않았습니다.")
        print("실제로 적용하려면 '--dry-run' 옵션 없이 다시 실행하세요.")

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
