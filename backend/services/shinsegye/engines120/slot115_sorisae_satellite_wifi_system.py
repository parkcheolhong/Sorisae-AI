#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🛰️ 소리새 차세대 인공위성 와이파이 시스템
Next-Generation Satellite WiFi System for Sorisae AI

이 시스템은 소리새 AI가 차세대 인공위성 네트워크를 통해
전 세계 어디서든 고품질 인터넷 연결을 제공할 수 있도록 합니다.

주요 기능:
- 저궤도 위성 연결 관리 (Starlink, OneWeb 등)
- 자동 위성 선택 및 최적화
- 지구 전체 커버리지 모니터링
- 신호 강도 및 품질 실시간 추적
- 위성 간 핸드오버 자동 처리
- 우주 날씨 영향 모니터링
- 위성 궤도 예측 및 추적
"""

import logging
import math
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# 음성 합성 라이브러리
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️ TTS 라이브러리가 없습니다. 음성 기능이 제한됩니다.")


@dataclass
class SatelliteInfo:
    """위성 정보 데이터 클래스"""
    sat_id: str
    name: str
    orbit_altitude: float  # km
    latitude: float
    longitude: float
    signal_strength: float  # dBm
    bandwidth: float  # Mbps
    latency: float  # ms
    status: str  # 'active', 'maintenance', 'offline'
    constellation: str  # 'starlink', 'oneweb', 'kuiper', 'sorisae'
    coverage_radius: float  # km


@dataclass
class ConnectionStatus:
    """연결 상태 데이터 클래스"""
    connected_satellite: str
    signal_quality: str  # 'excellent', 'good', 'fair', 'poor'
    download_speed: float  # Mbps
    upload_speed: float  # Mbps
    ping: float  # ms
    data_usage: float  # MB
    connection_time: float  # seconds
    is_stable: bool


class SorisaeSatelliteWiFiSystem:
    """소리새 차세대 인공위성 와이파이 시스템"""

    def __init__(self):
        self.logger = logging.getLogger('SorisaeSatelliteWiFi')
        self.setup_logging()

        # 시스템 상태
        self.is_active = False
        self.current_connection: Optional[ConnectionStatus] = None
        self.available_satellites: List[SatelliteInfo] = []
        self.connection_history: List[Dict] = []

        # 위성 데이터베이스 초기화
        self.initialize_satellite_constellation()

        # 음성 엔진 초기화
        self.audio_io_enabled = os.environ.get("SORISAE_DISABLE_AUDIO_IO", "0") != "1"
        self.tts_engine = None
        if TTS_AVAILABLE and self.audio_io_enabled:
            try:
                self.tts_engine = pyttsx3.init()
                self.setup_voice()
            except Exception as e:
                print(f"⚠️ 위성 와이파이 TTS 비활성화: {e}")
        elif TTS_AVAILABLE:
            print("ℹ️ 위성 와이파이 헤드리스 오디오 모드")

        # 모니터링 스레드
        self.monitoring_thread = None
        self.monitoring_active = False

        print("🛰️ 소리새 차세대 인공위성 와이파이 시스템 초기화 완료!")
        self.speak("소리새 인공위성 와이파이 시스템이 준비되었습니다!")

    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def setup_voice(self):
        """음성 엔진 설정"""
        if TTS_AVAILABLE and self.tts_engine:
            voices = self.tts_engine.getProperty('voices')
            # 한국어 음성 설정 시도
            for voice in voices:
                if 'korea' in voice.name.lower() or 'kr' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break

            self.tts_engine.setProperty('rate', 180)
            self.tts_engine.setProperty('volume', 0.8)

    def speak(self, text: str):
        """음성 출력"""
        if TTS_AVAILABLE and self.audio_io_enabled and self.tts_engine:

            def _speak():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception:
                    pass

            threading.Thread(target=_speak, daemon=True).start()

        print(f"🗣️ {text}")

    def initialize_satellite_constellation(self):
        """위성 constellation 초기화"""
        # 가상의 차세대 위성 네트워크 생성
        constellations = {
            'sorisae': {
                'count': 50,
                'altitude': 550,  # km
                'bandwidth_range': (100, 1000),  # Mbps
                'latency_range': (15, 25)  # ms
            },
            'starlink': {
                'count': 30,
                'altitude': 550,
                'bandwidth_range': (50, 500),
                'latency_range': (20, 40)
            },
            'oneweb': {
                'count': 20,
                'altitude': 1200,
                'bandwidth_range': (50, 200),
                'latency_range': (30, 50)
            },
            'kuiper': {
                'count': 25,
                'altitude': 600,
                'bandwidth_range': (80, 400),
                'latency_range': (18, 35)
            }
        }

        satellite_id = 1
        for constellation, config in constellations.items():
            for i in range(config['count']):
                # 랜덤 위치 생성 (전 세계 분산)
                lat = random.uniform(-90, 90)
                lon = random.uniform(-180, 180)

                satellite = SatelliteInfo(
                    sat_id=f"{constellation.upper()}-{satellite_id:03d}",
                    name=f"{constellation.title()} Satellite {i + 1}",
                    orbit_altitude=config['altitude'] + random.uniform(-50, 50),
                    latitude=lat,
                    longitude=lon,
                    signal_strength=random.uniform(-80, -40),  # dBm
                    bandwidth=random.uniform(*config['bandwidth_range']),
                    latency=random.uniform(*config['latency_range']),
                    status=random.choice(['active', 'active', 'active', 'maintenance']),
                    constellation=constellation,
                    coverage_radius=random.uniform(500, 1500)  # km
                )

                self.available_satellites.append(satellite)
                satellite_id += 1

        self.logger.info(f"위성 constellation 초기화 완료: {len(self.available_satellites)}개 위성")

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 지점 간 거리 계산 (km)"""
        R = 6371  # 지구 반지름 (km)

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def find_optimal_satellite(self, user_lat: float = 37.5665, user_lon: float = 126.9780) -> Optional[SatelliteInfo]:
        """사용자 위치 기준 최적 위성 찾기 (기본값: 서울)"""
        available_sats = [sat for sat in self.available_satellites if sat.status == 'active']

        if not available_sats:
            return None

        # 점수 기반 최적 위성 선택
        best_satellite = None
        best_score = -1

        for satellite in available_sats:
            distance = self.calculate_distance(user_lat, user_lon, satellite.latitude, satellite.longitude)

            # 커버리지 내에 있는지 확인
            if distance > satellite.coverage_radius:
                continue

            # 점수 계산 (신호 강도, 대역폭, 지연시간, 거리 고려)
            signal_score = (satellite.signal_strength + 80) / 40 * 100  # -80~-40 dBm을 0~100으로
            bandwidth_score = min(satellite.bandwidth / 10, 100)  # 대역폭 점수
            latency_score = max(0, 100 - satellite.latency * 2)  # 지연시간 점수 (낮을수록 좋음)
            distance_score = max(0, 100 - distance / 10)  # 거리 점수

            # 소리새 위성에 보너스 점수
            constellation_bonus = 50 if satellite.constellation == 'sorisae' else 0

            total_score = (signal_score + bandwidth_score + latency_score + distance_score + constellation_bonus) / 5

            if total_score > best_score:
                best_score = total_score
                best_satellite = satellite

        return best_satellite

    def connect_to_satellite(self, satellite: SatelliteInfo) -> bool:
        """위성에 연결"""
        try:
            self.logger.info(f"위성 {satellite.name}에 연결 시도...")
            self.speak(f"{satellite.name}에 연결을 시도합니다.")

            # 연결 시뮬레이션 (실제로는 하드웨어 제어)
            time.sleep(2)

            # 연결 성공률 (신호 강도에 따라)
            success_rate = min(0.95, (satellite.signal_strength + 80) / 40)

            if random.random() < success_rate:
                # 연결 상태 생성
                self.current_connection = ConnectionStatus(
                    connected_satellite=satellite.sat_id,
                    signal_quality=self._get_signal_quality(satellite.signal_strength),
                    download_speed=satellite.bandwidth * random.uniform(0.7, 0.95),
                    upload_speed=satellite.bandwidth * random.uniform(0.3, 0.6),
                    ping=satellite.latency * random.uniform(0.8, 1.2),
                    data_usage=0.0,
                    connection_time=time.time(),
                    is_stable=True
                )

                self.logger.info(f"위성 {satellite.name} 연결 성공!")
                self.speak(f"위성 연결이 성공했습니다! 다운로드 속도 {self.current_connection.download_speed:.1f} 메가비트입니다.")

                # 연결 기록 저장
                self.connection_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'satellite': satellite.name,
                    'connection_quality': self.current_connection.signal_quality,
                    'speed': self.current_connection.download_speed
                })

                return True
            else:
                self.logger.warning(f"위성 {satellite.name} 연결 실패")
                self.speak("위성 연결에 실패했습니다. 다른 위성을 찾고 있습니다.")
                return False

        except Exception as e:
            self.logger.error(f"위성 연결 중 오류: {e}")
            return False

    def _get_signal_quality(self, signal_strength: float) -> str:
        """신호 강도에 따른 품질 판정"""
        if signal_strength >= -50:
            return 'excellent'
        elif signal_strength >= -60:
            return 'good'
        elif signal_strength >= -70:
            return 'fair'
        else:
            return 'poor'

    def start_satellite_connection(self, user_lat: float = 37.5665, user_lon: float = 126.9780):
        """위성 인터넷 연결 시작"""
        if self.is_active:
            self.speak("이미 위성 인터넷에 연결되어 있습니다.")
            return

        self.logger.info("위성 인터넷 연결을 시작합니다...")
        self.speak("차세대 인공위성 와이파이 연결을 시작합니다.")

        # 최적 위성 찾기
        optimal_satellite = self.find_optimal_satellite(user_lat, user_lon)

        if not optimal_satellite:
            self.logger.error("사용 가능한 위성을 찾을 수 없습니다.")
            self.speak("죄송합니다. 현재 위치에서 연결 가능한 위성이 없습니다.")
            return

        # 위성 연결 시도
        if self.connect_to_satellite(optimal_satellite):
            self.is_active = True
            self.start_monitoring()
            self.display_connection_info()
        else:
            # 다른 위성으로 재시도
            self.retry_connection(user_lat, user_lon)

    def retry_connection(self, user_lat: float, user_lon: float, max_retries: int = 3):
        """연결 재시도"""
        for attempt in range(max_retries):
            self.logger.info(f"연결 재시도 {attempt + 1}/{max_retries}")

            # 다른 위성 찾기
            available_sats = [sat for sat in self.available_satellites if sat.status == 'active' and self.calculate_distance(
                user_lat, user_lon, sat.latitude, sat.longitude) <= sat.coverage_radius]

            if available_sats:
                # 랜덤하게 다른 위성 선택
                satellite = random.choice(available_sats)
                if self.connect_to_satellite(satellite):
                    self.is_active = True
                    self.start_monitoring()
                    self.display_connection_info()
                    return

        self.speak("모든 연결 시도가 실패했습니다. 나중에 다시 시도해주세요.")

    def start_monitoring(self):
        """연결 모니터링 시작"""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("위성 연결 모니터링 시작")

    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.monitoring_active and self.is_active:
            try:
                if self.current_connection:
                    # 연결 상태 업데이트
                    self._update_connection_status()

                    # 핸드오버 필요성 체크
                    if self._should_handover():
                        self.perform_handover()

                time.sleep(5)  # 5초마다 체크

            except Exception as e:
                self.logger.error(f"모니터링 중 오류: {e}")
                time.sleep(10)

    def _update_connection_status(self):
        """연결 상태 업데이트"""
        if not self.current_connection:
            return

        # 실시간 변화 시뮬레이션
        self.current_connection.download_speed *= random.uniform(0.95, 1.05)
        self.current_connection.upload_speed *= random.uniform(0.95, 1.05)
        self.current_connection.ping *= random.uniform(0.9, 1.1)
        self.current_connection.data_usage += random.uniform(0.1, 0.5)  # MB

        # 안정성 체크
        if self.current_connection.ping > 100 or self.current_connection.download_speed < 10:
            self.current_connection.is_stable = False
        else:
            self.current_connection.is_stable = True

    def _should_handover(self) -> bool:
        """핸드오버 필요성 판단"""
        if not self.current_connection:
            return False

        # 연결이 불안정하거나 품질이 떨어지면 핸드오버
        return (not self.current_connection.is_stable
                or self.current_connection.signal_quality == 'poor')

    def perform_handover(self):
        """위성 간 핸드오버 수행"""
        self.logger.info("위성 간 핸드오버를 수행합니다...")
        self.speak("더 나은 연결을 위해 위성을 변경하고 있습니다.")

        # 현재 위성 정보 저장
        current_sat_id = self.current_connection.connected_satellite if self.current_connection else None

        # 새로운 최적 위성 찾기
        optimal_satellite = self.find_optimal_satellite()

        if optimal_satellite and optimal_satellite.sat_id != current_sat_id:
            if self.connect_to_satellite(optimal_satellite):
                self.logger.info(f"핸드오버 성공: {optimal_satellite.name}")
                self.speak("위성 변경이 완료되었습니다.")
            else:
                self.logger.warning("핸드오버 실패")
                self.speak("위성 변경에 실패했습니다.")

    def display_connection_info(self):
        """연결 정보 출력"""
        if not self.current_connection:
            print("❌ 위성에 연결되지 않았습니다.")
            return

        print("\n" + "=" * 60)
        print("🛰️ 소리새 인공위성 와이파이 연결 상태")
        print("=" * 60)
        print(f"📡 연결된 위성: {self.current_connection.connected_satellite}")
        print(f"📶 신호 품질: {self.current_connection.signal_quality.upper()}")
        print(f"⬇️ 다운로드 속도: {self.current_connection.download_speed:.1f} Mbps")
        print(f"⬆️ 업로드 속도: {self.current_connection.upload_speed:.1f} Mbps")
        print(f"🏓 지연시간: {self.current_connection.ping:.1f} ms")
        print(f"📊 데이터 사용량: {self.current_connection.data_usage:.2f} MB")
        print(f"⏱️ 연결 시간: {time.time() - self.current_connection.connection_time:.0f}초")
        print(f"✅ 연결 안정성: {'안정' if self.current_connection.is_stable else '불안정'}")
        print("=" * 60)

    def get_satellite_constellation_info(self) -> Dict[str, Any]:
        """위성 constellation 정보 반환"""
        constellation_stats = {}

        for constellation in ['sorisae', 'starlink', 'oneweb', 'kuiper']:
            sats = [s for s in self.available_satellites if s.constellation == constellation]
            active_sats = [s for s in sats if s.status == 'active']

            constellation_stats[constellation] = {
                'total_satellites': len(sats),
                'active_satellites': len(active_sats),
                'avg_bandwidth': sum(s.bandwidth for s in active_sats) / len(active_sats) if active_sats else 0,
                'avg_latency': sum(s.latency for s in active_sats) / len(active_sats) if active_sats else 0,
                'coverage_percentage': len(active_sats) / len(sats) * 100 if sats else 0
            }

        return constellation_stats

    def run_satellite_diagnostic(self):
        """위성 네트워크 진단"""
        print("\n🔍 위성 네트워크 진단을 시작합니다...")
        self.speak("위성 네트워크 진단을 시작합니다.")

        # Constellation별 통계
        stats = self.get_satellite_constellation_info()

        print("\n📊 위성 Constellation 상태:")
        print("-" * 50)

        for constellation, info in stats.items():
            print(f"\n🛰️ {constellation.upper()} Constellation:")
            print(f"   총 위성 수: {info['total_satellites']}개")
            print(f"   활성 위성: {info['active_satellites']}개")
            print(f"   평균 대역폭: {info['avg_bandwidth']:.1f} Mbps")
            print(f"   평균 지연시간: {info['avg_latency']:.1f} ms")
            print(f"   커버리지: {info['coverage_percentage']:.1f}%")

        # 전체 네트워크 상태
        total_sats = len(self.available_satellites)
        active_sats = len([s for s in self.available_satellites if s.status == 'active'])

        print(f"\n🌐 전체 네트워크 상태:")
        print(f"   총 위성 수: {total_sats}개")
        print(f"   활성 위성: {active_sats}개")
        print(f"   네트워크 가용성: {active_sats / total_sats * 100:.1f}%")

        # 현재 연결 상태
        if self.is_active and self.current_connection:
            print(f"\n📱 현재 연결 상태: 활성")
            self.display_connection_info()
        else:
            print(f"\n📱 현재 연결 상태: 비활성")

        self.speak("진단이 완료되었습니다.")

    def disconnect(self):
        """위성 연결 해제"""
        if not self.is_active:
            self.speak("현재 연결된 위성이 없습니다.")
            return

        self.logger.info("위성 연결을 해제합니다...")
        self.speak("위성 연결을 해제합니다.")

        self.monitoring_active = False
        self.is_active = False
        self.current_connection = None

        print("✅ 위성 연결이 해제되었습니다.")
        self.speak("위성 연결이 해제되었습니다.")

    def emergency_mode(self):
        """비상 모드 - 가장 강한 신호의 위성에 즉시 연결"""
        self.logger.info("비상 모드 활성화")
        self.speak("비상 모드를 활성화합니다. 가장 강한 신호의 위성을 찾고 있습니다.")

        # 신호 강도 기준으로 정렬
        active_sats = [s for s in self.available_satellites if s.status == 'active']
        active_sats.sort(key=lambda x: x.signal_strength, reverse=True)

        if active_sats:
            emergency_sat = active_sats[0]
            self.logger.info(f"비상 연결 위성: {emergency_sat.name}")

            if self.connect_to_satellite(emergency_sat):
                self.is_active = True
                self.start_monitoring()
                self.speak("비상 연결이 성공했습니다.")
                self.display_connection_info()
            else:
                self.speak("비상 연결에 실패했습니다.")
        else:
            self.speak("사용 가능한 위성이 없습니다.")


def main():
    """메인 실행 함수"""
    print("🛰️ 소리새 차세대 인공위성 와이파이 시스템")
    print("=" * 60)

    # 시스템 초기화
    satellite_system = SorisaeSatelliteWiFiSystem()

    try:
        while True:
            print("\n🛰️ 소리새 위성 와이파이 메뉴:")
            print("1. 위성 인터넷 연결")
            print("2. 연결 상태 확인")
            print("3. 위성 네트워크 진단")
            print("4. 비상 모드")
            print("5. 연결 해제")
            print("6. 종료")

            choice = input("\n선택하세요 (1-6): ").strip()

            if choice == '1':
                # 사용자 위치 입력 (선택사항)
                print("\n현재 위치를 입력하세요 (Enter로 서울 기본값 사용):")
                lat_input = input("위도: ").strip()
                lon_input = input("경도: ").strip()

                if lat_input and lon_input:
                    try:
                        lat = float(lat_input)
                        lon = float(lon_input)
                        satellite_system.start_satellite_connection(lat, lon)
                    except ValueError:
                        print("잘못된 좌표입니다. 기본값을 사용합니다.")
                        satellite_system.start_satellite_connection()
                else:
                    satellite_system.start_satellite_connection()

            elif choice == '2':
                satellite_system.display_connection_info()

            elif choice == '3':
                satellite_system.run_satellite_diagnostic()

            elif choice == '4':
                satellite_system.emergency_mode()

            elif choice == '5':
                satellite_system.disconnect()

            elif choice == '6':
                satellite_system.disconnect()
                print("🛰️ 시스템을 종료합니다.")
                break

            else:
                print("잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n\n시스템 종료 중...")
        satellite_system.disconnect()
        print("✅ 시스템이 안전하게 종료되었습니다.")


if __name__ == "__main__":
    main()
