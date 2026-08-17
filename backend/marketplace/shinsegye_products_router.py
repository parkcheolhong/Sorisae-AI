"""
신세계 완제품 패키지 마켓 라우터
Shinsegye Complete Product Suite Marketplace Router

7개 신세계 완제품 패키지를 API로 노출합니다.
각 패키지는 여러 단일 기능(engines120 슬롯)을 묶은 완제품입니다.

패키지 구성:
  1. 통번역 스위트   – sorisae-interpreter + voice-processing + sorisae-core
  2. 미디어 스튜디오 – music-composer + animation-studio + movie-studio
  3. 보안/탐정       – cyber-detective + security + gps-police
  4. 게임 완전판     – vr-games + game-economy
  5. 스마트홈 IoT    – iot-smarthome + satellite
  6. 비즈니스        – investment-advisor + shopping-mall + civil-bidding
  7. 개발도구        – dev-tools + testing

endpoints:
  GET  /api/marketplace/shinsegye/products          → 전체 완제품 목록
  GET  /api/marketplace/shinsegye/products/{key}    → 패키지 상세 + 포함 기능 목록
  POST /api/marketplace/shinsegye/products/{key}/demo → 대표 엔진 데모 실행
  GET  /api/marketplace/shinsegye/engine/{key}/status → 대표 엔진 상태 체크
"""
from __future__ import annotations

import importlib
import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# ── 완제품 패키지 레지스트리 ──────────────────────────────────────
# key: URL 키, slots: 포함된 engines120 슬롯 목록, lead_slot/lead_class: 대표 엔진
SHINSEGYE_PRODUCTS: List[Dict[str, Any]] = [
    {
        "key": "suite-translation",
        "title": "소리새 통번역 스위트 – AI 실시간 13개 언어 완제품",
        "description": (
            "나도통역사(실시간 13개 언어 통역) + AI 자연어 음성 처리 + 소리새 의식 코어가 "
            "통합된 완제품 패키지. 설치 즉시 운영 가능한 통번역 시스템."
        ),
        "slots": [
            {"slot": "slot003_hybrid_conversation_translator", "class": "HybridConversationSystem", "name": "나도 통역사"},
            {"slot": "slot004_sorisae_voice_processor", "class": "NaturalLanguageProcessor", "name": "음성 처리 시스템"},
            {"slot": "slot088_sorisae_core_new_features_20251019_182012", "class": "SorisaeCore", "name": "소리새 코어"},
        ],
        "lead_slot": "slot003_hybrid_conversation_translator",
        "lead_class": "HybridConversationSystem",
        "db_id": 38,
        "category_id": 3,
        "price": 189000.0,
        "tags": ["통역", "다국어", "AI", "음성", "완제품"],
        "features": ["13개 언어 실시간 통역", "AI 자연어 음성 제어", "소리새 의식 코어 탑재", "위성 연결 자동 전환"],
    },
    {
        "key": "suite-media-studio",
        "title": "소리새 미디어 창작 스튜디오 – AI 음악/애니/영화 완제품",
        "description": (
            "AI 음악 작곡가 & 가사 스튜디오 + 애니메이션 Ultra + 영화 웹 서버가 통합된 "
            "완제품 창작 패키지. 미디어 제작 전 공정을 단일 플랫폼에서 처리."
        ),
        "slots": [
            {"slot": "slot011_ai_music_composer", "class": "AIMusicComposer", "name": "AI 음악 작곡가"},
            {"slot": "slot091_sorisae_animation_studio_ultra", "class": "SorisaeAnimationStudioUltra", "name": "애니메이션 스튜디오 Ultra"},
            {"slot": "slot103_sorisae_movie_web_server", "class": "SorisaeMovieWebServer", "name": "영화 웹 서버"},
        ],
        "lead_slot": "slot011_ai_music_composer",
        "lead_class": "AIMusicComposer",
        "db_id": 39,
        "category_id": 6,
        "price": 259000.0,
        "tags": ["음악", "애니메이션", "영화", "AI", "창작", "완제품"],
        "features": ["AI 음악 자동 작곡 + 가사", "AI 애니메이션 자동 생성", "영화 스트리밍 서버", "미디어 통합 관리"],
    },
    {
        "key": "suite-security",
        "title": "소리새 보안/탐정 완제품 – 사이버보안 + AI 탐정 + GPS 공공안전",
        "description": (
            "사이버 탐정 AI 대시보드 + 하이브리드 사이버 보안 시스템 + 윤리적 GPS 공공안전 "
            "시스템이 통합된 완제품. 기업/공공기관 보안 전 영역 대응."
        ),
        "slots": [
            {"slot": "slot050_cyber_detective_ai", "class": "CyberDetectiveAI", "name": "사이버 탐정 AI"},
            {"slot": "slot039_hybrid_cyber_security_system", "class": "HybridCyberSecuritySystem", "name": "하이브리드 사이버 보안"},
            {"slot": "slot092_ethical_gps_system", "class": "EthicalGPSSystem", "name": "윤리적 GPS 공공안전"},
        ],
        "lead_slot": "slot039_hybrid_cyber_security_system",
        "lead_class": "HybridCyberSecuritySystem",
        "db_id": 40,
        "category_id": 3,
        "price": 229000.0,
        "tags": ["보안", "사이버탐정", "GPS", "공공안전", "완제품"],
        "features": ["사이버 위협 실시간 탐지", "AI 사이버 수사 대시보드", "윤리적 GPS 공공안전 모니터링", "통합 보안 보고서"],
    },
    {
        "key": "suite-game",
        "title": "소리새 게임 완전판 – VR 우주 + 게임 경제 시스템",
        "description": (
            "소리새 판타지 VR 무한우주 게임 + 소리새 게임 경제 시스템이 통합된 완제품 "
            "게임 플랫폼. 가상경제 운영부터 VR 플레이까지 완전 구현."
        ),
        "slots": [
            {"slot": "slot073_sorisae_fantasy_vr_infinite_universe_game", "class": "SorisaeFantasyVRGame", "name": "판타지 VR 무한우주"},
            {"slot": "slot074_sorisae_game_economy_system", "class": "GameEconomyEngine", "name": "게임 경제 시스템"},
        ],
        "lead_slot": "slot073_sorisae_fantasy_vr_infinite_universe_game",
        "lead_class": "SorisaeFantasyVRGame",
        "db_id": 41,
        "category_id": 5,
        "price": 149000.0,
        "tags": ["게임", "VR", "판타지", "게임경제", "완제품"],
        "features": ["AI 무한 우주 생성", "VR 인터랙션", "게임 경제 운영 시스템", "AI 파트너 대화"],
    },
    {
        "key": "suite-smarthome",
        "title": "소리새 스마트홈 IoT 완제품 – IoT 제어 + 위성 WiFi 통합",
        "description": (
            "소리새 IoT 스마트홈 제어 시스템 + 소리새 위성 WiFi 시스템이 통합된 완제품. "
            "인터넷 인프라가 없는 환경에서도 위성 연결로 스마트홈 운영 가능."
        ),
        "slots": [
            {"slot": "slot044_sorisae_iot_smarthome", "class": "SorisaeIoTManager", "name": "IoT 스마트홈 제어"},
            {"slot": "slot115_sorisae_satellite_wifi_system", "class": "SorisaeSatelliteWiFiSystem", "name": "위성 WiFi 시스템"},
        ],
        "lead_slot": "slot044_sorisae_iot_smarthome",
        "lead_class": "SorisaeIoTManager",
        "db_id": 42,
        "category_id": 3,
        "price": 199000.0,
        "tags": ["IoT", "스마트홈", "위성WiFi", "자동화", "완제품"],
        "features": ["스마트홈 통합 제어", "위성 WiFi 자동 전환", "자동화 규칙 설정", "센서 실시간 모니터링"],
    },
    {
        "key": "suite-business",
        "title": "소리새 비즈니스 완제품 – 투자자문 + 쇼핑몰 + AI 건설입찰",
        "description": (
            "AI 투자 자문 시스템 200% + 지능형 e커머스 쇼핑몰 대시보드 + AI 자동 건설입찰 "
            "시스템이 통합된 완제품. 비즈니스 전 영역 AI 자동화."
        ),
        "slots": [
            {"slot": "slot075_sorisae_investment_advisor_200", "class": "IntelligentMarketAnalyzer", "name": "AI 투자 자문 200%"},
            {"slot": "slot120_shopping_mall_dashboard", "class": "ShoppingMallDashboard", "name": "쇼핑몰 대시보드"},
            {"slot": "slot108_sorisae_civil_engineering_bidding", "class": "CivilEngineeringBiddingSystem", "name": "건설 입찰 시스템"},
        ],
        "lead_slot": "slot075_sorisae_investment_advisor_200",
        "lead_class": "IntelligentMarketAnalyzer",
        "db_id": 43,
        "category_id": 4,
        "price": 299000.0,
        "tags": ["투자", "쇼핑몰", "건설입찰", "AI", "비즈니스", "완제품"],
        "features": ["AI 투자 자문 & 수익률 예측", "지능형 e커머스 운영", "AI 건설 입찰 자동화", "비즈니스 통합 대시보드"],
    },
    {
        "key": "suite-devtools",
        "title": "소리새 개발도구 완제품 – AI 개발팀 + 코드 품질 분석기",
        "description": (
            "가상 AI 개발팀 시스템(자동 코드 생성) + 종합 프로젝트 분석기(AI 코드 품질 검사)가 "
            "통합된 완제품. 개발-검수 전 사이클을 AI로 자동화."
        ),
        "slots": [
            {"slot": "slot098_virtual_dev_team", "class": "VirtualDevTeam", "name": "가상 AI 개발팀"},
            {"slot": "slot113_comprehensive_project_analyzer", "class": "ComprehensiveProjectAnalyzer", "name": "종합 프로젝트 분석기"},
        ],
        "lead_slot": "slot098_virtual_dev_team",
        "lead_class": "VirtualDevTeam",
        "db_id": 44,
        "category_id": 1,
        "price": 179000.0,
        "tags": ["개발도구", "코드생성", "코드품질", "AI", "완제품"],
        "features": ["가상 AI 개발팀 협업", "자동 코드 생성 & 리뷰", "AI 코드 품질 분석", "보안 취약점 자동 탐지"],
    },
]

# key → product dict 인덱스
_PRODUCT_INDEX: Dict[str, Dict[str, Any]] = {p["key"]: p for p in SHINSEGYE_PRODUCTS}


# ── Request / Response 모델 ──────────────────────────────────────

class DemoRequest(BaseModel):
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="데모 실행에 전달할 파라미터 (선택)"
    )


class DemoResponse(BaseModel):
    key: str
    title: str
    engine_class: str
    demo_result: Any
    engine_status: str
    message: str


# ── 엔진 로더 ─────────────────────────────────────────────────────

def _load_engine_class(slot: str, class_name: str) -> Any:
    """engines120 슬롯에서 클래스를 동적 임포트합니다."""
    module_path = f"backend.services.shinsegye.engines120.{slot}"
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"엔진 모듈 로드 실패: {slot} — {e}",
        )
    cls = getattr(mod, class_name, None)
    if cls is None:
        # 클래스명이 변경됐을 수 있으므로 모듈 내 첫 번째 클래스 대안
        candidates = [
            name for name in dir(mod)
            if not name.startswith("_") and isinstance(getattr(mod, name), type)
        ]
        if candidates:
            cls = getattr(mod, candidates[0])
        else:
            raise HTTPException(
                status_code=503,
                detail=f"클래스 '{class_name}' 을 찾을 수 없습니다: {slot}",
            )
    return cls


def _safe_demo(product: Dict[str, Any], params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """엔진 클래스를 인스턴스화하고 안전하게 데모를 실행합니다."""
    slot = product.get("lead_slot")
    class_name = product.get("lead_class")
    if not slot or not class_name:
        raise HTTPException(status_code=500, detail=f"패키지 엔진 메타가 누락되었습니다: {product.get('key')}")

    cls = _load_engine_class(slot, class_name)

    result: Dict[str, Any] = {
        "class_name": cls.__name__,
        "module": slot,
        "init_status": "failed",
        "data": None,
    }

    try:
        instance = cls()
        result["init_status"] = "ok"

        # 인스턴스의 공개 속성/메서드 중 안전하게 호출 가능한 것 수집
        public_attrs: Dict[str, Any] = {}
        for attr_name in dir(instance):
            if attr_name.startswith("_"):
                continue
            try:
                val = getattr(instance, attr_name)
                if not callable(val):
                    # 단순 값 속성
                    if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                        public_attrs[attr_name] = val
            except Exception:
                pass

        result["data"] = public_attrs or {"info": str(instance)}

        # params 키가 있으면 메서드 호출 시도
        if params:
            method_name = params.get("method")
            if method_name:
                method = getattr(instance, method_name, None)
                if method and callable(method):
                    method_args = params.get("args", [])
                    method_kwargs = params.get("kwargs", {})
                    call_result = method(*method_args, **method_kwargs)
                    result["method_result"] = call_result

    except Exception as exc:
        result["init_status"] = "error"
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()[-1000:]  # 마지막 1000자만

    return result


# ── 라우터 빌더 ──────────────────────────────────────────────────

def build_shinsegye_products_router(contract: Any) -> APIRouter:
    """
    신세계 전체 18개 프로젝트 라우터를 빌드합니다.

    marketplace/router.py 에서:
        from .shinsegye_products_router import build_shinsegye_products_router
        router.include_router(build_shinsegye_products_router(sys.modules[__name__]))
    """
    router = APIRouter(prefix="/shinsegye", tags=["marketplace-shinsegye-products"])

    @router.get("/products")
    def list_shinsegye_products() -> Dict[str, Any]:
        """신세계 18개 프로젝트 전체 목록 반환 (공개 엔드포인트)."""
        return {
            "total": len(SHINSEGYE_PRODUCTS),
            "products": [
                {
                    "key": p["key"],
                    "title": p["title"],
                    "description": p["description"],
                    "price": p["price"],
                    "category_id": p["category_id"],
                    "tags": p["tags"],
                    "features": p["features"],
                    "demo_url": f"/api/marketplace/shinsegye/products/{p['key']}/demo",
                }
                for p in SHINSEGYE_PRODUCTS
            ],
        }

    @router.get("/products/{key}")
    def get_shinsegye_product(
        key: str,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """특정 신세계 프로젝트 상세 정보 반환."""
        product = _PRODUCT_INDEX.get(key)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"프로젝트 '{key}' 를 찾을 수 없습니다.",
            )
        return {
            "key": product["key"],
            "title": product["title"],
            "description": product["description"],
            "price": product["price"],
            "category_id": product["category_id"],
            "tags": product["tags"],
            "features": product["features"],
            "slots": product.get("slots", []),
            "engine": {
                "slot": product["lead_slot"],
                "main_class": product["lead_class"],
                "module_path": f"backend.services.shinsegye.engines120.{product['lead_slot']}",
            },
        }

    @router.post("/products/{key}/demo")
    def run_shinsegye_demo(
        key: str,
        req: DemoRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        신세계 프로젝트 데모 실행.
        엔진 클래스를 인스턴스화하고 공개 속성/메서드 결과를 반환합니다.

        선택적 params:
          { "method": "get_status", "args": [], "kwargs": {} }
        """
        product = _PRODUCT_INDEX.get(key)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"프로젝트 '{key}' 를 찾을 수 없습니다.",
            )

        demo_result = _safe_demo(product, req.params)
        return {
            "key": key,
            "title": product["title"],
            "engine_class": product["lead_class"],
            "demo_result": demo_result,
            "engine_status": demo_result.get("init_status", "unknown"),
            "message": (
                "데모 실행 성공" if demo_result.get("init_status") == "ok"
                else "데모 실행 중 오류 발생"
            ),
        }

    @router.get("/engine/{key}/status")
    def check_engine_status(
        key: str,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """엔진 모듈 임포트 가능 여부 및 클래스 존재 여부 확인."""
        product = _PRODUCT_INDEX.get(key)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"프로젝트 '{key}' 를 찾을 수 없습니다.",
            )

        module_path = f"backend.services.shinsegye.engines120.{product['lead_slot']}"
        try:
            mod = importlib.import_module(module_path)
            has_class = hasattr(mod, product["lead_class"])
            classes = [
                name for name in dir(mod)
                if not name.startswith("_") and isinstance(getattr(mod, name), type)
            ]
            return {
                "key": key,
                "slot": product["lead_slot"],
                "module_importable": True,
                "main_class": product["lead_class"],
                "main_class_found": has_class,
                "available_classes": classes[:10],
                "status": "ok" if has_class else "class_not_found",
            }
        except ImportError as e:
            return {
                "key": key,
                "slot": product["lead_slot"],
                "module_importable": False,
                "error": str(e),
                "status": "import_error",
            }

    return router
