cmake_minimum_required(VERSION 3.18)
project(daytrade_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# 최적화(저지연 코어). MSVC/GCC/Clang 공통 의도.
if(MSVC)
  add_compile_options(/O2)
else()
  add_compile_options(-O3 -march=native)
endif()

# pybind11: pip 설치본 사용 권장 →  -Dpybind11_DIR=$(python -m pybind11 --cmakedir)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(daytrade_cpp src/bindings.cpp)
target_include_directories(daytrade_cpp PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

# MinGW(Windows GCC) 빌드: libstdc++/libgcc/winpthread 를 정적 링크해
# 런타임 DLL 의존 없이 import 가능한 자립형 .pyd 를 만든다(MSVC/Linux 경로엔 영향 없음).
if(MINGW)
  target_link_options(daytrade_cpp PRIVATE -static-libgcc -static-libstdc++ -static)
endif()
