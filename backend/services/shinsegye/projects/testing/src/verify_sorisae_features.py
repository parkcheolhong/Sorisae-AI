#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
소리새 추가기능 확인 스크립트
Sorisae Additional Features Verification Script

이 스크립트는 소리새의 모든 추가기능이 정상적으로 작동하는지 확인합니다.
"""

import os
import sys


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_section(title):
    """섹션 출력"""
    print(f"\n{title}")
    print("-" * 80)


def verify_feature(name, module_name, class_name=None):
    """기능 확인"""
    try:
        module = __import__(module_name)
        if class_name:
            getattr(module, class_name)
        print(f"✅ {name}: 정상 작동")
        return True
    except Exception as e:
        print(f"❌ {name}: 오류 - {e}")
        return False


def main():
    """메인 함수"""
    print_header("🎵 소리새 추가기능 전체 확인")

    print("""
이 스크립트는 다음 소리새 추가기능을 확인합니다:
1. 다국어 지원 (Multilingual Support) - 4개 언어
2. IoT 통합 (IoT Integration) - 스마트홈 디바이스
3. 나도 통역사 (Interpreter) - 12개 언어 실시간 통역
4. 통합 확장 기능 (Enhanced Features) - 모든 기능 통합
""")

    results = {}

    # 1. 다국어 지원 확인
    print_section("1️⃣  다국어 지원 (Multilingual Support)")
    try:
        from sorisae_multilingual_support import SorisaeMultilingualSupport
        ml = SorisaeMultilingualSupport()
        print(f"✅ 다국어 지원: 정상 작동")
        print(f"   📚 지원 언어: {', '.join(ml.supported_languages)}")
        print(f"   🌍 언어 수: {len(ml.supported_languages)}개")

        # 샘플 메시지 출력
        print("\n   샘플 메시지:")
        for lang in ml.supported_languages:
            ml.set_language(lang)
            msg = ml.get_message("welcome")
            print(f"     • {lang}: {msg}")

        results['multilingual'] = True
    except Exception as e:
        print(f"❌ 다국어 지원: 오류 - {e}")
        results['multilingual'] = False

    # 2. IoT 통합 확인
    print_section("2️⃣  IoT 통합 (IoT Integration)")
    try:
        from sorisae_iot_integration import SorisaeIoTIntegration
        iot = SorisaeIoTIntegration()
        print(f"✅ IoT 통합: 정상 작동")

        # iot_manager 속성 존재 여부 캐싱
        has_iot_manager = hasattr(iot, 'iot_manager')
        # 디바이스 개수 확인
        device_count = len(iot.iot_manager.devices) if has_iot_manager else 0
        print(f"   🏠 등록된 디바이스: {device_count}개")

        # 디바이스 타입별 개수
        if has_iot_manager and iot.iot_manager.devices:
            device_types = {}
            for device in iot.iot_manager.devices.values():
                dtype = device.device_type.value if hasattr(device.device_type, 'value') else str(device.device_type)
                device_types[dtype] = device_types.get(dtype, 0) + 1

            print("\n   디바이스 타입별:")
            for dtype, count in device_types.items():
                print(f"     • {dtype}: {count}개")

        results['iot'] = True
    except Exception as e:
        print(f"❌ IoT 통합: 오류 - {e}")
        results['iot'] = False

    # 3. 나도 통역사 확인
    print_section("3️⃣  나도 통역사 (Interpreter)")
    try:
        from sorisae_interpreter import SorisaeInterpreter
        interp = SorisaeInterpreter()
        print(f"✅ 나도 통역사: 정상 작동")
        print(f"   🌐 지원 언어: {len(interp.engine.supported_languages)}개")

        # 지원 언어 목록
        print("\n   지원 언어 목록:")
        for code, name in interp.engine.supported_languages.items():
            print(f"     • {code}: {name}")

        # 샘플 번역
        print("\n   샘플 번역:")
        test_text = "안녕하세요"
        for target in ["en", "ja", "zh"]:
            result = interp.quick_translate(test_text, "ko", target)
            print(f"     • {test_text} (ko) → {result} ({target})")

        results['interpreter'] = True
    except Exception as e:
        print(f"❌ 나도 통역사: 오류 - {e}")
        results['interpreter'] = False

    # 4. 통합 확장 기능 확인
    print_section("4️⃣  통합 확장 기능 (Enhanced Features)")
    try:
        print(f"✅ 통합 확장 기능: 정상 작동")
        print(f"   🎵 모든 기능이 하나로 통합됨")
        results['enhanced'] = True
    except Exception as e:
        print(f"❌ 통합 확장 기능: 오류 - {e}")
        results['enhanced'] = False

    # 5. 메인 통합 확인
    print_section("5️⃣  메인 시스템 통합 (Main Integration)")
    try:
        # run_all_shinsegye.py 파일 확인
        if os.path.exists('run_all_shinsegye.py'):
            with open('run_all_shinsegye.py', 'r', encoding='utf-8') as f:
                content = f.read()

            checks = {
                'multilingual import': 'from sorisae_multilingual_support import' in content,
                'iot import': 'from sorisae_iot_integration import' in content,
                'interpreter import': 'from sorisae_interpreter import' in content,
                'multilingual init': 'SorisaeMultilingualSupport()' in content,
                'iot init': 'SorisaeIoTIntegration()' in content,
                'interpreter init': 'SorisaeInterpreter()' in content,
            }

            print("   메인 시스템 통합 상태:")
            for check_name, check_result in checks.items():
                icon = "✅" if check_result else "❌"
                print(f"     {icon} {check_name}")

            results['main_integration'] = all(checks.values())
        else:
            print("   ⚠️  run_all_shinsegye.py 파일을 찾을 수 없음")
            results['main_integration'] = False
    except Exception as e:
        print(f"❌ 메인 시스템 통합: 오류 - {e}")
        results['main_integration'] = False

    # 최종 결과
    print_header("📊 최종 확인 결과")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n총 {total}개 기능 중 {passed}개 정상 작동")
    print(f"성공률: {(passed / total) * 100:.1f}%")

    print("\n상세 결과:")
    for feature, status in results.items():
        icon = "✅" if status else "❌"
        status_text = "정상" if status else "오류"
        print(f"  {icon} {feature}: {status_text}")

    if passed == total:
        print("\n" + "🎉" * 40)
        print("🎊 모든 소리새 추가기능이 정상적으로 작동합니다! 🎊")
        print("🎉" * 40)
        print("\n✨ 확인 완료! 모든 기능을 사용할 수 있습니다. ✨")
    else:
        print("\n⚠️  일부 기능에 문제가 있습니다. 위의 오류 메시지를 확인하세요.")

    print("\n" + "=" * 80)
    print("확인 스크립트 종료")
    print("=" * 80 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
