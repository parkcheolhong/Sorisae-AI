// daytrade-ai C++ 코어 — DetectionEngine (Python `daytrade/detection/engine.py` 미러).
//
// §3-2 의사코드:
//   buy  = (obi >  OBI_THRESH && vol_ratio > VOL_SPIKE && price_delta > 0)
//   sell = (obi < -OBI_THRESH && vol_ratio > VOL_SPIKE && price_delta < 0)
// confidence 합성도 Python 과 동일 가중치/스쿼시.
#pragma once

#include <algorithm>

#include "daytrade/market.hpp"

namespace daytrade {

inline double squash(double x) {
    // 음수 클립 후 [0,1) 매핑: x/(1+x)
    if (x <= 0.0) return 0.0;
    return x / (1.0 + x);
}

class DetectionEngine {
public:
    explicit DetectionEngine(double obi_threshold = 1.0e6, double volume_spike_ratio = 2.0)
        : obi_threshold_(obi_threshold), volume_spike_ratio_(volume_spike_ratio) {}

    Signal evaluate(const FeatureVector& fv) const {
        const bool buy = fv.obi > obi_threshold_ && fv.volume_spike > volume_spike_ratio_ &&
                         fv.micro_momentum > 0.0;
        const bool sell = fv.obi < -obi_threshold_ && fv.volume_spike > volume_spike_ratio_ &&
                          fv.micro_momentum < 0.0;

        Signal s;
        s.ts_ns = fv.ts_ns;
        s.symbol = fv.symbol;
        if (buy) {
            s.side = SignalSide::BUY;
            s.confidence = confidence(fv, SignalSide::BUY);
        } else if (sell) {
            s.side = SignalSide::SELL;
            s.confidence = confidence(fv, SignalSide::SELL);
        } else {
            s.side = SignalSide::FLAT;
            s.confidence = 0.0;
        }
        return s;
    }

private:
    double confidence(const FeatureVector& fv, SignalSide side) const {
        const double obi_strength = squash(std::abs(fv.obi_norm) / 2.0);
        const double denom = volume_spike_ratio_ > 1e-9 ? volume_spike_ratio_ : 1e-9;
        const double vol_ratio = fv.volume_spike / denom;
        const double vol_strength = squash(std::max(0.0, vol_ratio - 1.0));
        const bool mom_ok = (side == SignalSide::BUY && fv.micro_momentum > 0.0) ||
                            (side == SignalSide::SELL && fv.micro_momentum < 0.0);
        const double mom_strength = mom_ok ? 1.0 : 0.0;
        const double conf = 0.45 * obi_strength + 0.35 * vol_strength + 0.20 * mom_strength;
        return std::max(0.0, std::min(1.0, conf));
    }

    double obi_threshold_;
    double volume_spike_ratio_;
};

}  // namespace daytrade
