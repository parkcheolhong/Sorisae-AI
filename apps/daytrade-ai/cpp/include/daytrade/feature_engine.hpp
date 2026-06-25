// daytrade-ai C++ 코어 — FeatureEngine (Python `daytrade/features/engine.py` 라인 미러).
//
// 수치 동일성 원칙: 합/분산/누적의 **연산 순서**까지 Python(front→back deque 순회)과 동일하게 유지.
// 부동소수 결과가 1e-9 이내로 일치하도록 한다(골든 테스트 tests/test_cpp_golden.py).
#pragma once

#include <cmath>
#include <cstdint>
#include <deque>
#include <string>
#include <vector>

#include "daytrade/market.hpp"

namespace daytrade {

class FeatureEngine {
public:
    explicit FeatureEngine(int depth = 10, int vwap_window = 50,
                           int obi_stat_window = 200, int momentum_window = 1)
        : depth_(depth),
          vwap_window_(vwap_window),
          obi_stat_window_(obi_stat_window),
          momentum_window_(momentum_window) {}

    void reset() {
        has_prev_price_ = has_prev_volume_ = has_prev_vwap_ = false;
        price_hist_.clear();
        obi_hist_.clear();
        vwap_pv_.clear();
        vwap_v_.clear();
    }

    FeatureVector update(std::int64_t ts_ns, const std::string& symbol,
                         const std::vector<OrderBookLevel>& bids,
                         const std::vector<OrderBookLevel>& asks,
                         double last_price, double last_qty) {
        const double bid_sum = total_qty(bids, static_cast<std::size_t>(depth_));
        const double ask_sum = total_qty(asks, static_cast<std::size_t>(depth_));
        const double obi = bid_sum - ask_sum;

        // OBI z-score (이동 윈도)
        obi_hist_.push_back(obi);
        while (static_cast<int>(obi_hist_.size()) > obi_stat_window_) obi_hist_.pop_front();
        const double obi_norm = zscore(obi, obi_hist_);

        // 거래량 급증
        const double vol = last_qty;
        double volume_spike;
        if (!has_prev_volume_ || prev_volume_ <= 0.0) {
            volume_spike = 1.0;
        } else {
            volume_spike = vol / prev_volume_;
        }

        // 마이크로 모멘텀
        const double price = last_price;
        price_hist_.push_back(price);
        while (static_cast<int>(price_hist_.size()) > momentum_window_ + 1) price_hist_.pop_front();
        double micro_momentum = 0.0;
        if (static_cast<int>(price_hist_.size()) > momentum_window_) {
            micro_momentum = price - price_hist_.front();
        }

        // VWAP (이동 윈도)
        vwap_pv_.push_back(price * (vol > 0.0 ? vol : 0.0));
        vwap_v_.push_back(vol > 0.0 ? vol : 0.0);
        while (static_cast<int>(vwap_v_.size()) > vwap_window_) {
            vwap_pv_.pop_front();
            vwap_v_.pop_front();
        }
        const double vsum = accumulate_front_to_back(vwap_v_);
        const double vwap = vsum > 0.0 ? (accumulate_front_to_back(vwap_pv_) / vsum) : price;
        const double vwap_delta = !has_prev_vwap_ ? 0.0 : (vwap - prev_vwap_);

        // spread / mid (Python: None 이면 각각 0.0 / price 로 폴백)
        double spread = 0.0;
        double mid = price;
        if (!bids.empty() && !asks.empty()) {
            const double best_bid = bids[0].price;
            const double best_ask = asks[0].price;
            spread = best_ask - best_bid;
            mid = (best_bid + best_ask) / 2.0;
        }

        // 상태 갱신
        prev_price_ = price;        has_prev_price_ = true;
        prev_volume_ = vol;         has_prev_volume_ = true;
        prev_vwap_ = vwap;          has_prev_vwap_ = true;

        FeatureVector fv;
        fv.ts_ns = ts_ns;
        fv.symbol = symbol;
        fv.obi = obi;
        fv.obi_norm = obi_norm;
        fv.volume_spike = volume_spike;
        fv.micro_momentum = micro_momentum;
        fv.vwap = vwap;
        fv.vwap_delta = vwap_delta;
        fv.spread = spread;
        fv.mid_price = mid;
        return fv;
    }

private:
    static double accumulate_front_to_back(const std::deque<double>& d) {
        double s = 0.0;
        for (double x : d) s += x;  // Python sum() 과 동일한 순서
        return s;
    }

    static double zscore(double value, const std::deque<double>& hist) {
        const std::size_t n = hist.size();
        if (n < 2) return 0.0;
        double sum = 0.0;
        for (double x : hist) sum += x;
        const double mean = sum / static_cast<double>(n);
        double var_acc = 0.0;
        for (double x : hist) var_acc += (x - mean) * (x - mean);
        const double var = var_acc / static_cast<double>(n - 1);
        if (var <= 0.0) return 0.0;
        return (value - mean) / std::sqrt(var);
    }

    int depth_;
    int vwap_window_;
    int obi_stat_window_;
    int momentum_window_;

    bool has_prev_price_{false};
    bool has_prev_volume_{false};
    bool has_prev_vwap_{false};
    double prev_price_{0.0};
    double prev_volume_{0.0};
    double prev_vwap_{0.0};

    std::deque<double> price_hist_;
    std::deque<double> obi_hist_;
    std::deque<double> vwap_pv_;
    std::deque<double> vwap_v_;
};

}  // namespace daytrade
