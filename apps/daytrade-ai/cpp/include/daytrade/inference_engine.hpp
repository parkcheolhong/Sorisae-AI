// daytrade-ai M4 — AI-Inference 엔진(설계서 §3-3) C++ 스캐폴드.
//
// 저지연 추론 스레드 인터페이스. TensorRT(C++ API) + CUDA stream 비동기(enqueueV2)로
// feature → tensor pack → 추론 → signal queue 연동(≤1ms, warm-up <5ms 목표).
//
// 이 헤더는 **인터페이스 스캐폴드**이며, 실제 구현(.cpp)은 TensorRT/CUDA 헤더가 있는
// 서버(RTX 5090)에서 `DAYTRADE_WITH_TENSORRT` 정의와 함께 컴파일한다(M3 와 동일 패턴).
// pybind 모듈(daytrade_cpp)에는 포함되지 않는다(GPU 의존 분리).
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <string>
#include <vector>

#include "daytrade/market.hpp"

namespace daytrade {

// 추론 출력: 방향 확률(파이썬 InferenceModel 과 동일 계약).
struct InferenceResult {
  float prob_buy = 0.0f;
  float prob_sell = 0.0f;
  std::uint64_t latency_ns = 0;  // enqueue→sync 까지 측정(히스토그램 적재용).
};

// 추론 정밀도(엔진 빌드 시 선택).
enum class Precision { kFP32, kFP16, kINT8 };

// 추론 엔진 추상 인터페이스 — 구현체: TensorRtEngine / OrtEngine / HeuristicEngine(폴백).
class IInferenceEngine {
 public:
  virtual ~IInferenceEngine() = default;

  // 콜드스타트 제거(warm-up < 5ms). 더미 입력으로 1회 추론.
  virtual void Warmup() = 0;

  // 동기 추론(스캐폴드 기본). 운영 경로는 EnqueueAsync + Synchronize 사용.
  virtual InferenceResult Predict(const FeatureVector& fv) = 0;

  // 비동기 추론: CUDA stream 에 enqueue 만 하고 즉시 반환(레이턴시 은닉).
  // 결과는 Synchronize() 후 유효. 미지원 구현은 Predict 로 폴백 가능.
  virtual void EnqueueAsync(const FeatureVector& fv) { last_sync_result_ = Predict(fv); }
  virtual InferenceResult Synchronize() { return last_sync_result_; }

 protected:
  InferenceResult last_sync_result_{};
};

#ifdef DAYTRADE_WITH_TENSORRT
// TensorRT 구현(서버 빌드). 선언만 — 정의는 inference_engine_trt.cpp.
class TensorRtEngine final : public IInferenceEngine {
 public:
  // engine_path: 직렬화된 .plan(build_engine 산출물). input_dim: FEATURE_NAMES 길이.
  explicit TensorRtEngine(const std::string& engine_path, int input_dim = 8);
  ~TensorRtEngine() override;

  void Warmup() override;
  InferenceResult Predict(const FeatureVector& fv) override;
  void EnqueueAsync(const FeatureVector& fv) override;
  InferenceResult Synchronize() override;

 private:
  struct Impl;          // TensorRT/CUDA 타입 은닉(PImpl) — 헤더 의존 최소화.
  Impl* impl_ = nullptr;
};
#endif  // DAYTRADE_WITH_TENSORRT

// 모델 핫스왑(Blue-Green): active 포인터를 원자적으로 교체(진행 추론 무중단).
// 파이썬 `HotSwapModel` 과 동일 의미 — lock-free atomic exchange.
class HotSwapInference {
 public:
  explicit HotSwapInference(IInferenceEngine* active) : active_(active) {}

  // 추론 트래픽: 현재 active 를 atomic load 로 읽어 사용(교체와 race 없음).
  InferenceResult Predict(const FeatureVector& fv) {
    return active_.load(std::memory_order_acquire)->Predict(fv);
  }

  // 새(워밍업 완료) 엔진으로 원자 교체. 반환: 직전 active(호출자가 소유권 정리/롤백).
  IInferenceEngine* Swap(IInferenceEngine* staged) {
    return active_.exchange(staged, std::memory_order_acq_rel);
  }

 private:
  std::atomic<IInferenceEngine*> active_;
};

}  // namespace daytrade
