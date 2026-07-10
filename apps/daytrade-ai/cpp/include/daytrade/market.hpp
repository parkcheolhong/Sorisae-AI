// daytrade-ai C++ 코어 — 도메인 타입 (Python `daytrade/types.py` / `schemas/market.fbs` 미러).
//
// 목적(M3): §3-2 의 sub-ms C++ 루프 실구현. Python 레퍼런스와 **수치 동일성**을 보장한다.
// 본 헤더의 필드/순서는 types.py·market.fbs 와 일치해야 하며, 골든 테스트로 검증한다.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace daytrade {

struct OrderBookLevel {
    double price{0.0};
    double qty{0.0};
};

// 오더북 한 쪽의 상위 N레벨 수량 합(Python total_qty 미러).
inline double total_qty(const std::vector<OrderBookLevel>& levels, std::size_t depth) {
    double s = 0.0;
    const std::size_t n = depth < levels.size() ? depth : levels.size();
    for (std::size_t i = 0; i < n; ++i) s += levels[i].qty;
    return s;
}

// FEATURE_NAMES 순서와 동일(AI 입력 텐서 순서 SSOT).
struct FeatureVector {
    std::int64_t ts_ns{0};
    std::string symbol;
    double obi{0.0};
    double obi_norm{0.0};
    double volume_spike{1.0};
    double micro_momentum{0.0};
    double vwap{0.0};
    double vwap_delta{0.0};
    double spread{0.0};
    double mid_price{0.0};
};

enum class SignalSide { BUY, SELL, FLAT };

inline const char* side_str(SignalSide s) {
    switch (s) {
        case SignalSide::BUY: return "buy";
        case SignalSide::SELL: return "sell";
        default: return "flat";
    }
}

struct Signal {
    SignalSide side{SignalSide::FLAT};
    double confidence{0.0};
    std::int64_t ts_ns{0};
    std::string symbol;
};

}  // namespace daytrade
