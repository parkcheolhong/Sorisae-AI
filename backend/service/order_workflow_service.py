# FILE-ID: FILE-BACKEND-SERVICE-ORDER-WORKFLOW-SERVICE-PY
# SECTION-ID: SECTION-BACKEND-SERVICE-ORDER-WORKFLOW-SERVICE-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-SERVICE-ORDER-WORKFLOW-SERVICE-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-SERVICE-ORDER-WORKFLOW-SERVICE-PY-001

def build_order_workflow_state() -> dict:
    steps = [
        {'id': 'cart', 'title': '장바구니 확인', 'status': 'ready'},
        {'id': 'address', 'title': '배송지 입력', 'status': 'ready'},
        {'id': 'payment', 'title': '결제 수단 확인', 'status': 'ready'},
        {'id': 'confirm', 'title': '주문 확정', 'status': 'ready'},
    ]
    return {'steps': steps, 'checkout_enabled': True, 'order workflow': True}
