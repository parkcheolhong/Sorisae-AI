// daytrade-ai C++ 코어 — pybind11 바인딩.
//
// Python 에서 `import daytrade_cpp` 로 사용. 골든 테스트(tests/test_cpp_golden.py)가
// 동일 입력에 대해 Python 레퍼런스와 수치 동일성을 검증한다.
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <utility>
#include <vector>

#include "daytrade/detection_engine.hpp"
#include "daytrade/feature_engine.hpp"
#include "daytrade/market.hpp"

namespace py = pybind11;
using namespace daytrade;

// Python 쪽에서 오더북을 list[tuple[price, qty]] 로 넘기는 것을 허용(테스트 편의).
static std::vector<OrderBookLevel> to_levels(const std::vector<std::pair<double, double>>& raw) {
    std::vector<OrderBookLevel> out;
    out.reserve(raw.size());
    for (const auto& p : raw) out.push_back(OrderBookLevel{p.first, p.second});
    return out;
}

PYBIND11_MODULE(daytrade_cpp, m) {
    m.doc() = "daytrade-ai low-latency core (M3) — Python reference numerically-equivalent";

    py::class_<FeatureVector>(m, "FeatureVector")
        .def_readonly("ts_ns", &FeatureVector::ts_ns)
        .def_readonly("symbol", &FeatureVector::symbol)
        .def_readonly("obi", &FeatureVector::obi)
        .def_readonly("obi_norm", &FeatureVector::obi_norm)
        .def_readonly("volume_spike", &FeatureVector::volume_spike)
        .def_readonly("micro_momentum", &FeatureVector::micro_momentum)
        .def_readonly("vwap", &FeatureVector::vwap)
        .def_readonly("vwap_delta", &FeatureVector::vwap_delta)
        .def_readonly("spread", &FeatureVector::spread)
        .def_readonly("mid_price", &FeatureVector::mid_price);

    py::class_<Signal>(m, "Signal")
        .def_property_readonly("side", [](const Signal& s) { return std::string(side_str(s.side)); })
        .def_readonly("confidence", &Signal::confidence)
        .def_readonly("ts_ns", &Signal::ts_ns)
        .def_readonly("symbol", &Signal::symbol);

    py::class_<FeatureEngine>(m, "FeatureEngine")
        .def(py::init<int, int, int, int>(),
             py::arg("depth") = 10, py::arg("vwap_window") = 50,
             py::arg("obi_stat_window") = 200, py::arg("momentum_window") = 1)
        .def("reset", &FeatureEngine::reset)
        .def(
            "update",
            [](FeatureEngine& self, std::int64_t ts_ns, const std::string& symbol,
               const std::vector<std::pair<double, double>>& bids,
               const std::vector<std::pair<double, double>>& asks,
               double last_price, double last_qty) {
                return self.update(ts_ns, symbol, to_levels(bids), to_levels(asks), last_price,
                                   last_qty);
            },
            py::arg("ts_ns"), py::arg("symbol"), py::arg("bids"), py::arg("asks"),
            py::arg("last_price"), py::arg("last_qty"));

    py::class_<DetectionEngine>(m, "DetectionEngine")
        .def(py::init<double, double>(),
             py::arg("obi_threshold") = 1.0e6, py::arg("volume_spike_ratio") = 2.0)
        .def("evaluate", &DetectionEngine::evaluate, py::arg("fv"));
}
