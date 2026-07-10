// daytrade-ai M4 — TensorRtEngine 구현(설계서 §3-3). **GPU 서버 빌드 전용**.
//
// 빌드: TensorRT 10.x + CUDA 가 있는 서버(RTX 5090)에서 `-DDAYTRADE_WITH_TENSORRT` 정의로 컴파일.
//   예) nvcc/g++ -DDAYTRADE_WITH_TENSORRT -I/usr/include -I../include \
//        inference_engine_trt.cpp inference_engine.cpp -lnvinfer -lcudart -o libdaytrade_infer.so
// 이 파일은 pybind 모듈(daytrade_cpp)에 포함되지 않는다(GPU 의존 분리 — M3 와 동일 원칙).
//
// 추론 경로: feature → host buffer → H2D async → enqueueV3(stream) → D2H async → stream sync.
// 비동기(EnqueueAsync/Synchronize)로 레이턴시 은닉(≤1ms, warm-up<5ms 목표).
#include "daytrade/inference_engine.hpp"

#ifdef DAYTRADE_WITH_TENSORRT

#include <NvInfer.h>
#include <cuda_runtime_api.h>

#include <chrono>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace daytrade {
namespace {

class TrtLogger : public nvinfer1::ILogger {
  void log(Severity severity, const char* msg) noexcept override {
    if (severity <= Severity::kWARNING) std::fprintf(stderr, "[TRT] %s\n", msg);
  }
};
TrtLogger g_logger;

inline void cudaCheck(cudaError_t e) {
  if (e != cudaSuccess) throw std::runtime_error(cudaGetErrorString(e));
}

std::uint64_t now_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

}  // namespace

// PImpl: TensorRT/CUDA 핸들 은닉(헤더 의존 제거).
struct TensorRtEngine::Impl {
  nvinfer1::IRuntime* runtime = nullptr;
  nvinfer1::ICudaEngine* engine = nullptr;
  nvinfer1::IExecutionContext* context = nullptr;
  cudaStream_t stream = nullptr;

  std::string input_name;
  std::string output_name;
  int input_dim = 8;

  void* d_in = nullptr;   // device 입력 버퍼 [1, input_dim]
  void* d_out = nullptr;  // device 출력 버퍼 [1, 2]
  std::vector<float> h_in;
  std::vector<float> h_out{0.0f, 0.0f};
  std::uint64_t enqueue_t0 = 0;
};

TensorRtEngine::TensorRtEngine(const std::string& engine_path, int input_dim) {
  impl_ = new Impl();
  impl_->input_dim = input_dim;
  impl_->h_in.assign(static_cast<std::size_t>(input_dim), 0.0f);

  std::ifstream f(engine_path, std::ios::binary);
  if (!f) throw std::runtime_error("엔진 파일 열기 실패: " + engine_path);
  std::vector<char> blob((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());

  impl_->runtime = nvinfer1::createInferRuntime(g_logger);
  impl_->engine = impl_->runtime->deserializeCudaEngine(blob.data(), blob.size());
  if (!impl_->engine) throw std::runtime_error("deserializeCudaEngine 실패");
  impl_->context = impl_->engine->createExecutionContext();

  // I/O 텐서 이름 조회(TensorRT 10 명시 텐서 API).
  for (int i = 0; i < impl_->engine->getNbIOTensors(); ++i) {
    const char* name = impl_->engine->getIOTensorName(i);
    if (impl_->engine->getTensorIOMode(name) == nvinfer1::TensorIOMode::kINPUT)
      impl_->input_name = name;
    else
      impl_->output_name = name;
  }

  cudaCheck(cudaStreamCreate(&impl_->stream));
  cudaCheck(cudaMalloc(&impl_->d_in, sizeof(float) * input_dim));
  cudaCheck(cudaMalloc(&impl_->d_out, sizeof(float) * 2));
  impl_->context->setTensorAddress(impl_->input_name.c_str(), impl_->d_in);
  impl_->context->setTensorAddress(impl_->output_name.c_str(), impl_->d_out);
}

TensorRtEngine::~TensorRtEngine() {
  if (!impl_) return;
  if (impl_->d_in) cudaFree(impl_->d_in);
  if (impl_->d_out) cudaFree(impl_->d_out);
  if (impl_->stream) cudaStreamDestroy(impl_->stream);
  delete impl_->context;
  delete impl_->engine;
  delete impl_->runtime;
  delete impl_;
  impl_ = nullptr;
}

void TensorRtEngine::Warmup() {
  FeatureVector fv{};  // 0 입력으로 1회 추론(cold-start 제거).
  Predict(fv);
}

void TensorRtEngine::EnqueueAsync(const FeatureVector& fv) {
  // feature → host buffer(FEATURE_NAMES 순서; FeatureVector::to_array 가정).
  const auto arr = fv.to_array();  // std::array<float, 8> (market.hpp 제공)
  for (int i = 0; i < impl_->input_dim && i < static_cast<int>(arr.size()); ++i)
    impl_->h_in[i] = arr[i];

  impl_->enqueue_t0 = now_ns();
  cudaCheck(cudaMemcpyAsync(impl_->d_in, impl_->h_in.data(), sizeof(float) * impl_->input_dim,
                            cudaMemcpyHostToDevice, impl_->stream));
  if (!impl_->context->enqueueV3(impl_->stream))
    throw std::runtime_error("enqueueV3 실패");
  cudaCheck(cudaMemcpyAsync(impl_->h_out.data(), impl_->d_out, sizeof(float) * 2,
                            cudaMemcpyDeviceToHost, impl_->stream));
}

InferenceResult TensorRtEngine::Synchronize() {
  cudaCheck(cudaStreamSynchronize(impl_->stream));
  InferenceResult r;
  r.prob_buy = impl_->h_out[0];
  r.prob_sell = impl_->h_out[1];
  r.latency_ns = now_ns() - impl_->enqueue_t0;
  return r;
}

InferenceResult TensorRtEngine::Predict(const FeatureVector& fv) {
  EnqueueAsync(fv);
  return Synchronize();
}

}  // namespace daytrade

#endif  // DAYTRADE_WITH_TENSORRT
