"""FIX 4.4 메시지 인코더/디코더(설계서 §6 Order Router — FIX/FAST 대응).

의존성 없는 순수 파이썬 구현으로, 실제 FIX 와이어 포맷(SOH 구분, BodyLength, CheckSum)을
정확히 생성/파싱한다. 세션/전송 계층(QuickFIX/N 등)은 서버에서 끼우되, **메시지 직렬화는
여기서 검증 가능**(M3/M4 와 동일한 "테스트 가능한 코어 + 서버 전송" 패턴).

지원 메시지:
  - NewOrderSingle (35=D): 신규 주문(시장가/지정가, IOC/Day).
  - ExecutionReport (35=8): 체결/거절 보고.

참고: 태그 8(BeginString)/9(BodyLength)/10(CheckSum)은 자동 계산한다.
"""
from __future__ import annotations

from ..types import Fill, Order, OrderSide, OrderType

SOH = "\x01"
BEGIN_STRING = "FIX.4.4"

# --- FIX enum 매핑 ---
FIX_SIDE = {OrderSide.BUY: "1", OrderSide.SELL: "2"}
FIX_SIDE_INV = {"1": OrderSide.BUY, "2": OrderSide.SELL}
# OrdType(40): 1=Market, 2=Limit. (IOC 는 TimeInForce(59)=3 로 표현)
FIX_ORDTYPE = {OrderType.MARKET: "1", OrderType.LIMIT: "2", OrderType.IOC: "1"}
TIF_IOC = "3"
TIF_DAY = "0"

# OrdStatus(39) / ExecType(150): 0=New, 1=PartiallyFilled, 2=Filled, 8=Rejected
ORD_STATUS_TO_FILL = {"2": "filled", "1": "partial", "8": "rejected", "0": "new"}


def encode(body_tags: list[tuple[int, str]], *, begin_string: str = BEGIN_STRING) -> str:
    """body 태그(35 부터 시작) → 완전한 FIX 메시지 문자열(8/9/10 자동 계산).

    BodyLength(9) = 태그35 SOH 부터 CheckSum 직전 SOH 까지의 바이트 수.
    CheckSum(10)  = 그 앞 전체 바이트 합 mod 256, 3자리 0패딩.
    """
    body = "".join(f"{tag}={val}{SOH}" for tag, val in body_tags)
    head = f"8={begin_string}{SOH}9={len(body)}{SOH}"
    without_checksum = head + body
    checksum = sum(without_checksum.encode("ascii")) % 256
    return f"{without_checksum}10={checksum:03d}{SOH}"


def decode(message: str) -> dict[int, str]:
    """FIX 메시지 → {tag: value}. 중복 태그는 마지막 값 우선(그룹 미지원, 단순 메시지용)."""
    out: dict[int, str] = {}
    for part in message.split(SOH):
        if not part:
            continue
        tag_str, _, val = part.partition("=")
        try:
            out[int(tag_str)] = val
        except ValueError:
            continue
    return out


def verify_checksum(message: str) -> bool:
    """수신 메시지의 CheckSum(10) 무결성 검증."""
    idx = message.rfind(f"{SOH}10=")
    if idx < 0:
        return False
    body = message[: idx + 1]  # 10= 직전 SOH 까지 포함
    expected = sum(body.encode("ascii")) % 256
    tags = decode(message)
    try:
        return int(tags.get(10, "-1")) == expected
    except ValueError:
        return False


def build_new_order_single(
    order: Order,
    *,
    sender: str,
    target: str,
    seq_num: int,
    sending_time: str,
    cl_ord_id: str | None = None,
) -> str:
    """`Order` → NewOrderSingle(35=D) FIX 문자열."""
    coid = cl_ord_id or order.client_order_id or f"COID-{seq_num}"
    tif = TIF_IOC if order.order_type == OrderType.IOC else TIF_DAY
    tags: list[tuple[int, str]] = [
        (35, "D"),
        (49, sender),
        (56, target),
        (34, str(seq_num)),
        (52, sending_time),
        (11, coid),
        (55, order.symbol),
        (54, FIX_SIDE[order.side]),
        (60, sending_time),
        (38, _num(order.qty)),
        (40, FIX_ORDTYPE[order.order_type]),
        (59, tif),
    ]
    if order.order_type == OrderType.LIMIT and order.limit_price is not None:
        tags.append((44, _num(order.limit_price)))
    return encode(tags)


def build_execution_report(
    *,
    sender: str,
    target: str,
    seq_num: int,
    sending_time: str,
    cl_ord_id: str,
    order_id: str,
    exec_id: str,
    symbol: str,
    side: OrderSide,
    ord_status: str,
    last_qty: float,
    last_px: float,
    cum_qty: float,
    leaves_qty: float,
    avg_px: float,
) -> str:
    """ExecutionReport(35=8) FIX 문자열 생성(체결/부분/거절 보고)."""
    tags: list[tuple[int, str]] = [
        (35, "8"),
        (49, sender),
        (56, target),
        (34, str(seq_num)),
        (52, sending_time),
        (37, order_id),
        (11, cl_ord_id),
        (17, exec_id),
        (150, ord_status),   # ExecType
        (39, ord_status),    # OrdStatus
        (55, symbol),
        (54, FIX_SIDE[side]),
        (32, _num(last_qty)),
        (31, _num(last_px)),
        (14, _num(cum_qty)),
        (151, _num(leaves_qty)),
        (6, _num(avg_px)),
    ]
    return encode(tags)


def parse_execution_report(message: str, order: Order) -> Fill:
    """ExecutionReport(35=8) → `Fill`(원 주문 컨텍스트 결합). slippage 는 호출측에서 보정."""
    tags = decode(message)
    status = ORD_STATUS_TO_FILL.get(tags.get(39, ""), "rejected")
    last_qty = float(tags.get(32, "0") or 0.0)
    avg_px = float(tags.get(6, "0") or 0.0)
    last_px = float(tags.get(31, "0") or 0.0)
    price = avg_px if avg_px > 0 else last_px
    ts = int(order.ts_ns)
    if status == "rejected":
        return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=ts, status="rejected")
    return Fill(order=order, filled_qty=last_qty, avg_price=round(price, 6), ts_ns=ts, status=status)


def _num(x: float) -> str:
    """수량/가격 직렬화 — 정수면 정수로, 아니면 소수(불필요한 0 제거)."""
    f = float(x)
    if f == int(f):
        return str(int(f))
    return repr(round(f, 8))
