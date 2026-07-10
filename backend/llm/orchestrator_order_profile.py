"""오케스트레이터 고객주문 프로파일 + 도메인계약/통합테스트/stage 빌더 (orchestrator.py 에서 분리).

사용자 task/프로젝트명에서 주문 도메인 프로파일을 추론하고, 도메인 계약·통합 테스트 플랜·개선 루프·
Refiner/Fixer stage·패키징 감사를 구성한다. 외부 의존은 표준 라이브러리뿐 — orchestrator 와 순환 import 없음.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# orchestrator.py 에서 함께 이관한 클러스터 전용 상수(Refiner/Fixer 4.5단계 정의).
ORCH_REFINER_FIXER_STAGE = {
    "id": "ARCH-0045",
    "label": "4.5단계",
    "title": "Refiner/Fixer",
    "state": "REFINER_FIXER",
    "summary": "핵심엔진 직후 로직 전에 구조 정리, 계약 보정, 자동 수정 안전고리를 닫습니다.",
}


def _unique_sequence(items: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for item in items:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _has_mojibake_text(value: Optional[str]) -> bool:
    if value is None:
        return False
    text = str(value)
    if re.search(r"\?{3,}", text):
        return True
    if "�" in text:
        return True
    if re.search(r"[\u0080-\u009F]", text):
        return True
    if re.search(r"(?:Ã.|Â.|ì.|ë.|ê.|í.){2,}", text):
        return True
    return False


def _build_customer_order_profile(task: str, project_name: str) -> Dict[str, Any]:
    task_text = str(task or "").lower()
    project_name_text = str(project_name or "").lower()
    source_text = f"{task_text}\n{project_name_text}"
    workspace_app_target_context = any(
        marker in source_text
        for marker in [
            "source_path: /app",
            "대상 루트: /app",
            "원본 대상 경로: /app",
            "실험 복제본 경로: /app",
            "/app\n",
            " /app",
        ]
    ) or project_name_text.strip() in {"app", "/app"}
    stage_chain = [
        {"index": 1, "tracking_id": "ARCH-001", "title": "구조", "summary": "프로젝트 골조와 실행 엔트리를 고정합니다."},
        {"index": 2, "tracking_id": "ARCH-002", "title": "순수 로직", "summary": "핵심 계산과 판정 로직을 분리합니다."},
        {"index": 3, "tracking_id": "ARCH-003", "title": "데이터", "summary": "입출력 계약과 데이터 공급 레이어를 분리합니다."},
        {"index": 4, "tracking_id": "ARCH-004", "title": "서비스", "summary": "로직과 데이터를 묶는 서비스 흐름을 구성합니다."},
        {"index": 5, "tracking_id": "ARCH-005", "title": "API", "summary": "외부 요청과 서비스 연결을 구성합니다."},
        {"index": 6, "tracking_id": "ARCH-006", "title": "프론트", "summary": "화면, 상태 표현, 시각화를 연결합니다."},
    ]
    profiles: List[Dict[str, Any]] = [
        {
            "profile_id": "autonomous_multimall_platform",
            "label": "자율운영 멀티 쇼핑몰 플랫폼",
            "summary": "tenant 운영, 카탈로그 동기화, 캠페인 최적화, fulfillment 감독을 함께 다루는 멀티 스토어 주문형 프로그램",
            "keywords": ["멀티 쇼핑몰", "멀티쇼핑몰", "multimall", "multi mall", "tenant", "fulfillment", "campaign optimization"],
            "entities": ["tenants", "catalog_sync_jobs", "campaigns", "fulfillment_runs"],
            "requested_outcomes": ["tenant 운영", "카탈로그 동기화", "캠페인 최적화", "fulfillment 감독"],
            "ui_modules": ["tenant 운영 보드", "카탈로그 동기화 패널", "캠페인 최적화 대시보드", "fulfillment 감독 센터"],
            "requested_stack": ["FastAPI", "catalog-ui", "order-workflow", "tenant-ops"],
        },
        {
            "profile_id": "trading_system",
            "label": "자동매매/트레이딩 시스템",
            "summary": "전략 신호, 주문, 포트폴리오, 실행 상태를 관리하는 주문형 프로그램",
            "keywords": ["주식", "트레이딩", "자동매매", "매매", "signal", "portfolio", "trading", "stock"],
            "entities": ["signals", "orders", "positions", "portfolios"],
            "requested_outcomes": ["전략 신호 계산", "리스크 체크", "주문 기록", "포트폴리오 스냅샷"],
            "ui_modules": ["대시보드", "신호 뷰", "주문 이력", "포트폴리오 카드"],
            "requested_stack": ["FastAPI", "service-layer", "dashboard-client"],
        },
        {
            "profile_id": "lottery_prediction_system",
            "label": "AI 로또/복권 예측 프로그램",
            "summary": "추첨 이력, 특징 추출, 후보 번호 생성, 평가 리포트를 다루는 예측형 주문 프로그램",
            "keywords": ["로또", "lotto", "lottery", "복권", "당첨번호", "번호예측", "draw history"],
            "entities": ["draw_histories", "feature_windows", "prediction_runs", "candidate_sets"],
            "requested_outcomes": ["추첨 이력 적재", "특징 추출", "후보 번호 생성", "예측 평가 리포트"],
            "ui_modules": ["추첨 이력 보드", "예측 후보 패널", "평가 리포트 카드", "운영 검증 패널"],
            "requested_stack": ["FastAPI", "prediction-ui", "evaluation-runtime"],
        },
        {
            "profile_id": "website_builder",
            "label": "웹사이트/홈페이지 빌더",
            "summary": "페이지 구조, 콘텐츠 섹션, 문의 흐름, 운영 화면을 함께 구성하는 주문형 프로그램",
            "keywords": ["웹사이트", "홈페이지", "landing", "landing page", "website", "web", "페이지", "브랜딩"],
            "entities": ["pages", "sections", "contacts", "deployments"],
            "requested_outcomes": ["페이지 설계", "콘텐츠 섹션 구성", "문의 접수", "운영 배포 메모"],
            "ui_modules": ["메인 랜딩", "소개 섹션", "문의 폼", "운영 배포 패널"],
            "requested_stack": ["FastAPI", "Next-style frontend", "content-workflow"],
        },
        {
            "profile_id": "deployment_kit_program",
            "label": "실배포 구현형 코드 생성기 배포 키트",
            "summary": "실프로그램 생성, 런타임 정책, 패키징, 배포 스모크 검증까지 닫는 출고형 프로그램",
            "keywords": ["코드 생성기 배포 키트", "deployment kit", "실배포 구현형", "배포 패키징", "publish-readiness", "runtime policy", "실프로그램", "출고형"],
            "entities": ["runtime_policies", "deployment_packages", "validation_reports", "publish_targets"],
            "requested_outcomes": ["실행 가능한 FastAPI 프로그램 생성", "런타임 정책 문서화", "배포 패키징", "배포 스모크 검증"],
            "ui_modules": ["실행 상태 패널", "배포 준비도 카드", "검증 결과 리포트", "출고 패키지 요약"],
            "requested_stack": ["FastAPI", "deployment-runtime", "packaging-audit", "publish-readiness"],
        },
        {
            "profile_id": "admin_console",
            "label": "관리자/운영 콘솔",
            "summary": "사용자, 권한, 감사 로그, 운영 상태를 관리하는 주문형 프로그램",
            "keywords": ["관리자", "어드민", "admin", "dashboard", "backoffice", "운영", "권한"],
            "entities": ["users", "roles", "audit_logs", "runtime_panels"],
            "requested_outcomes": ["운영 대시보드", "권한 관리", "감사 로그 조회", "상태 점검"],
            "ui_modules": ["운영 홈", "사용자 목록", "권한 패널", "감사 로그"],
            "requested_stack": ["FastAPI", "admin-ui", "audit-traceability"],
        },
        {
            "profile_id": "commerce_platform",
            "label": "이커머스/마켓플레이스 플랫폼",
            "summary": "상품, 카탈로그, 주문, 고객 흐름을 다루는 주문형 프로그램",
            "keywords": ["마켓플레이스", "이커머스", "쇼핑몰", "커머스", "product", "catalog", "order", "store"],
            "entities": ["products", "catalogs", "carts", "orders"],
            "requested_outcomes": ["상품 관리", "카탈로그 노출", "주문 추적", "고객 상태 확인"],
            "ui_modules": ["상품 목록", "상품 상세", "주문 현황", "운영 카탈로그"],
            "requested_stack": ["FastAPI", "catalog-ui", "order-workflow"],
        },
        {
            "profile_id": "automation_service",
            "label": "업무 자동화/에이전트 서비스",
            "summary": "작업 큐, 실행 기록, 스케줄, 경고를 포함하는 주문형 프로그램",
            "keywords": ["자동화", "workflow", "agent", "봇", "scheduler", "queue", "pipeline", "etl"],
            "entities": ["jobs", "runs", "alerts", "artifacts"],
            "requested_outcomes": ["잡 등록", "실행 추적", "경고 수집", "결과물 아카이브"],
            "ui_modules": ["작업 큐", "실행 히스토리", "알림 패널", "산출물 뷰어"],
            "requested_stack": ["FastAPI", "queue-runtime", "ops-panel"],
        },
        {
            "profile_id": "crm_suite",
            "label": "CRM/영업 운영 스위트",
            "summary": "리드, 고객, 영업 파이프라인, 활동 로그를 함께 다루는 주문형 프로그램",
            "keywords": ["crm", "영업", "세일즈", "고객관리", "lead", "pipeline", "account"],
            "entities": ["leads", "customers", "accounts", "activities"],
            "requested_outcomes": ["리드 수집", "고객 상태 관리", "영업 파이프라인 추적", "활동 로그 기록"],
            "ui_modules": ["리드 보드", "고객 카드", "파이프라인 대시보드", "활동 로그"],
            "requested_stack": ["FastAPI", "crm-ui", "ops-audit"],
        },
        {
            "profile_id": "booking_platform",
            "label": "예약/스케줄링 플랫폼",
            "summary": "예약, 일정, 자원 배정, 알림 흐름을 관리하는 주문형 프로그램",
            "keywords": ["예약", "booking", "reservation", "schedule", "appointment", "calendar"],
            "entities": ["bookings", "resources", "timeslots", "notifications"],
            "requested_outcomes": ["예약 접수", "일정 관리", "자원 배정", "알림 발송"],
            "ui_modules": ["예약 캘린더", "자원 보드", "예약 목록", "알림 패널"],
            "requested_stack": ["FastAPI", "schedule-ui", "notification-workflow"],
        },
        {
            "profile_id": "education_lms",
            "label": "교육/LMS 플랫폼",
            "summary": "강의, 학습자, 과제, 진도와 평가 흐름을 관리하는 주문형 프로그램",
            "keywords": ["교육", "학습", "lms", "course", "lesson", "student", "강의"],
            "entities": ["courses", "students", "assignments", "progress"],
            "requested_outcomes": ["강의 관리", "학습자 진도 추적", "과제 제출", "평가 리포트"],
            "ui_modules": ["강의 대시보드", "학습자 목록", "과제 보드", "진도 리포트"],
            "requested_stack": ["FastAPI", "learning-ui", "reporting-runtime"],
        },
        {
            "profile_id": "healthcare_portal",
            "label": "헬스케어/상담 포털",
            "summary": "환자, 상담 기록, 예약, 문진 흐름을 다루는 주문형 프로그램",
            "keywords": ["헬스케어", "의료", "상담", "patient", "clinic", "medical", "문진"],
            "entities": ["patients", "consultations", "appointments", "intakes"],
            "requested_outcomes": ["상담 예약", "문진 기록", "상담 이력 조회", "운영 리포트"],
            "ui_modules": ["환자 목록", "상담 보드", "예약 캘린더", "운영 리포트"],
            "requested_stack": ["FastAPI", "portal-ui", "audit-runtime"],
        },
        {
            "profile_id": "analytics_platform",
            "label": "데이터 분석/인사이트 플랫폼",
            "summary": "데이터셋, 대시보드, 리포트, 인사이트 워크플로를 제공하는 주문형 프로그램",
            "keywords": ["분석", "analytics", "dashboard", "bi", "insight", "reporting", "data platform"],
            "entities": ["datasets", "dashboards", "reports", "insights"],
            "requested_outcomes": ["데이터셋 수집", "대시보드 생성", "리포트 발행", "인사이트 추적"],
            "ui_modules": ["분석 홈", "대시보드 뷰", "리포트 목록", "인사이트 패널"],
            "requested_stack": ["FastAPI", "analytics-ui", "report-runtime"],
        },
    ]
    default_profile = {
        "profile_id": "customer_program",
        "label": "고객 주문형 프로그램",
        "summary": "고객이 원하는 요구사항을 기준으로 기능, API, 화면, 운영 구조를 함께 생성하는 주문형 프로그램",
        "entities": ["requests", "modules", "artifacts", "handoffs"],
        "requested_outcomes": ["기능 구조화", "API 연결", "실행 상태 추적", "산출물 패키징"],
        "ui_modules": ["요청 입력", "결과 검토", "작업 패널", "산출물 요약"],
        "requested_stack": ["FastAPI", "customer-runtime", "delivery-panel"],
    }

    def _profile_match_score(profile: Dict[str, Any]) -> int:
        score = 0
        for keyword in profile.get("keywords") or []:
            normalized_keyword = str(keyword or "").strip().lower()
            if not normalized_keyword:
                continue
            if normalized_keyword in project_name_text:
                score += 5
            if normalized_keyword in task_text:
                score += 1
        return score

    profile_by_id = {
        str(item.get("profile_id") or "").strip(): dict(item)
        for item in profiles
    }

    explicit_profile_id = ""
    mojibake_detected = _has_mojibake_text(task) or _has_mojibake_text(project_name)
    explicit_profile_markers = [
        ("deployment_kit_program", ["코드 생성기 배포 키트", "deployment kit", "실배포 구현형", "배포 패키징", "publish-readiness", "runtime policy", "실프로그램", "출고형"]),
        ("autonomous_multimall_platform", ["멀티 쇼핑몰", "멀티쇼핑몰", "multimall", "multi mall", "tenant 운영", "tenant", "fulfillment", "캠페인 최적화"]),
            ("trading_system", ["자동매매", "트레이딩", "주식", "매매", "trading", "stock", "portfolio", "signal"]),
            ("commerce_platform", ["마켓플레이스", "이커머스", "쇼핑몰", "커머스", "catalog", "product", "order", "store"]),
        ("website_builder", ["웹사이트", "홈페이지", "landing page", "website", "브랜딩"]),
        ("automation_service", ["자동화", "workflow", "agent", "scheduler", "queue", "etl", "pipeline"]),
        ("admin_console", ["관리자 콘솔", "admin console", "admin dashboard", "backoffice", "권한 관리", "role management", "감사 로그", "audit trail"]),
    ]
    for candidate_profile_id, markers in explicit_profile_markers:
        if explicit_profile_id and explicit_profile_id != candidate_profile_id:
            continue
        if any(marker.lower() in task_text for marker in markers):
            explicit_profile_id = candidate_profile_id
            break

    if not explicit_profile_id and workspace_app_target_context:
        explicit_profile_id = "commerce_platform"

    if not explicit_profile_id and mojibake_detected:
        commerce_fallback_markers = [
            "marketplace",
            "commerce",
            "shoppingmall",
            "shopping-mall",
            "shopping_mall",
            "catalog-ui",
            "order-workflow",
            "storefront",
            "shopify",
        ]
        normalized_project_name = re.sub(r"[^a-z0-9가-힣]+", "", project_name_text)
        normalized_task_text = re.sub(r"[^a-z0-9가-힣]+", "", task_text)
        if any(marker.replace("-", "").replace("_", "") in normalized_project_name for marker in commerce_fallback_markers):
            explicit_profile_id = "commerce_platform"
        elif any(marker.replace("-", "").replace("_", "") in normalized_task_text for marker in commerce_fallback_markers):
            explicit_profile_id = "commerce_platform"
        elif "ai" in normalized_task_text and any(token in normalized_project_name for token in ["쇼핑몰", "마켓", "커머스"]):
            explicit_profile_id = "commerce_platform"

    if explicit_profile_id and explicit_profile_id in profile_by_id:
        selected = profile_by_id[explicit_profile_id]
    else:
        selected = max(profiles, key=_profile_match_score, default=default_profile)
        if _profile_match_score(selected) <= 0:
            selected = default_profile
    flow_steps = [
        {"flow_id": "FLOW-001", "step_number": 1, "step_id": "FLOW-001-1", "action": "INTAKE", "title": "주문 해석", "trace_id": "FLOW-001:FLOW-001-1:INTAKE"},
        {"flow_id": "FLOW-001", "step_number": 2, "step_id": "FLOW-001-2", "action": "STRUCTURE", "title": "기능 구조화", "trace_id": "FLOW-001:FLOW-001-2:STRUCTURE"},
        {"flow_id": "FLOW-002", "step_number": 1, "step_id": "FLOW-002-1", "action": "SERVICE_BIND", "title": "서비스 연결", "trace_id": "FLOW-002:FLOW-002-1:SERVICE_BIND"},
        {"flow_id": "FLOW-003", "step_number": 1, "step_id": "FLOW-003-1", "action": "DELIVERY", "title": "산출물 패키징", "trace_id": "FLOW-003:FLOW-003-1:DELIVERY"},
    ]
    profile = dict(selected)
    profile["project_name"] = project_name
    profile["task_excerpt"] = str(task or "").strip()[:240]
    profile["flow_steps"] = flow_steps
    profile["validation_profile"] = _resolve_validation_profile(profile, str(task or ""))
    ai_activation_markers = [
        "인공지능",
        "llm",
        "rag",
        "embedding",
        "임베딩",
        "예측",
        "추천",
        "분류",
        "학습",
        "추론",
        "evaluation",
        "train",
        "training",
        "inference",
        "fine-tune",
        "agent",
        "assistant",
        "챗봇",
        "chatbot",
        "오케스트레이터",
    ]
    ai_requested = any(token in source_text for token in ai_activation_markers)
    ai_disable_markers = [
        "no ai",
        "without ai",
        "non-ai",
        "ai 제외",
        "ai 비활성화",
    ]
    ai_forced_default = not any(marker in source_text for marker in ai_disable_markers)
    is_trading_profile = profile.get("profile_id") == "trading_system"
    profile["ai_enabled"] = ai_requested or is_trading_profile or ai_forced_default
    if profile["ai_enabled"]:
        profile["ai_engine_core"] = "sorisae"
    if profile["ai_enabled"]:
        profile["mandatory_engine_contracts"] = [
            "engine-core",
            "feature-pipeline",
            "training-pipeline",
            "inference-runtime",
            "evaluation-report",
            "service-integration",
        ]
        profile["ai_capabilities"] = [
            "feature-engineering",
            "model-training",
            "online-inference",
            "evaluation-report",
            "service-integration",
        ]
        profile["entities"] = _unique_sequence(list(profile.get("entities") or []) + [
            "ai_features",
            "model_versions",
            "inference_runs",
            "evaluation_reports",
        ])
        profile["requested_outcomes"] = _unique_sequence(list(profile.get("requested_outcomes") or []) + [
            "AI 엔진 구성",
            "학습 파이프라인",
            "추론 런타임",
            "평가 리포트",
            "전략/업무 서비스 연동",
        ])
        profile["ui_modules"] = _unique_sequence(list(profile.get("ui_modules") or []) + [
            "AI 상태 패널",
            "모델 버전 뷰",
            "평가 리포트 카드",
        ])
        profile["requested_stack"] = _unique_sequence(list(profile.get("requested_stack") or []) + [
            "ai-engine",
            "training-pipeline",
            "model-registry",
            "sorisae-ai-core",
        ])
        if profile.get("profile_id") == "trading_system":
            profile["mandatory_engine_contracts"] = _unique_sequence(list(profile.get("mandatory_engine_contracts") or []) + [
                "signal-ingestion",
                "risk-guard",
                "order-execution",
                "portfolio-sync",
                "broker-adapter",
            ])
            profile["ai_capabilities"] = _unique_sequence(list(profile.get("ai_capabilities") or []) + [
                "signal-ingestion",
                "risk-guard",
                "order-execution",
                "portfolio-sync",
            ])
            profile["entities"] = _unique_sequence(list(profile.get("entities") or []) + [
                "risk_events",
                "execution_runs",
                "broker_orders",
            ])
            profile["requested_outcomes"] = _unique_sequence(list(profile.get("requested_outcomes") or []) + [
                "시그널 적재 및 정규화",
                "리스크 가드 판정",
                "주문 실행 계획 산출",
                "포트폴리오 동기화",
                "브로커 어댑터 연결",
            ])
            profile["ui_modules"] = _unique_sequence(list(profile.get("ui_modules") or []) + [
                "리스크 가드 패널",
                "주문 실행 보드",
                "브로커 연결 상태 카드",
            ])
            profile["requested_stack"] = _unique_sequence(list(profile.get("requested_stack") or []) + [
                "broker-connector",
                "risk-engine",
                "portfolio-runtime",
            ])
        if profile.get("profile_id") == "lottery_prediction_system":
            profile["mandatory_engine_contracts"] = _unique_sequence(list(profile.get("mandatory_engine_contracts") or []) + [
                "historical-draw-loader",
                "feature-window-builder",
                "candidate-number-generator",
                "prediction-evaluation",
            ])
            profile["requested_outcomes"] = _unique_sequence(list(profile.get("requested_outcomes") or []) + [
                "추첨 회차 이력 정규화",
                "번호 후보 조합 생성",
                "후보 조합 평가",
            ])
            profile["ui_modules"] = _unique_sequence(list(profile.get("ui_modules") or []) + [
                "예측 엔진 패널",
                "후보 번호 조합 뷰",
            ])
            profile["requested_stack"] = _unique_sequence(list(profile.get("requested_stack") or []) + [
                "draw-history-pipeline",
                "candidate-ranking",
            ])
    current_stage = stage_chain[0]
    for stage in stage_chain:
        if stage["tracking_id"].lower() in source_text or f"{stage['index']}단계" in source_text or stage["title"] in str(task or ""):
            current_stage = stage
            break
    profile["stage_chain"] = stage_chain
    profile["current_stage"] = current_stage
    return profile


def _resolve_validation_profile(order_profile: Dict[str, Any], task: str) -> str:
    requested_stack = " ".join(str(item) for item in (order_profile.get("requested_stack") or []))
    source_text = f"{task}\n{requested_stack}".lower()
    next_markers = ["next.js", "nextjs", "next-style frontend", "react", "typescript"]
    if any(marker in source_text for marker in next_markers):
        return "nextjs_app"
    return "python_fastapi"


def _build_domain_contract(order_profile: Dict[str, Any], validation_profile: str, required_files: List[str]) -> Dict[str, Any]:
    profile_id = str(order_profile.get("profile_id") or "customer_program")
    domain_contracts: Dict[str, Dict[str, Any]] = {
        "autonomous_multimall_platform": {
            "required_structure": ["tenant operations", "catalog", "campaign optimization", "fulfillment supervision", "security runtime", "shipping package"],
            "verification_rules": ["tenant/카탈로그/fulfillment 마커 포함", "캠페인 최적화 및 운영 문서 포함", "auth/ops/security/출고 마커 포함"],
            "packaging_requirements": ["README", "배포 문서", "테스트 문서", "configs/app.env.example", "docs/runbook.md", "infra/prometheus.yml", "infra/deploy/security.md"],
        },
        "commerce_platform": {
            "required_structure": ["catalog", "order-workflow", "customer runtime", "ops catalog", "security runtime", "shipping package"],
            "verification_rules": ["상품/카탈로그/주문 흐름 파일 존재", "주문 상태 API/화면 마커 포함", "운영 문서와 env 예시 포함", "auth/ops/security/출고 마커 포함"],
            "packaging_requirements": ["README", "배포 문서", "테스트 문서", "configs/app.env.example", "docs/runbook.md", "infra/prometheus.yml", "infra/deploy/security.md"],
        },
        "admin_console": {
            "required_structure": ["admin dashboard", "role management", "audit trail", "runtime panels", "security runtime", "shipping package"],
            "verification_rules": ["운영/권한/감사 로그 마커 포함", "runtime panel 문서와 테스트 포함", "auth/ops/security/출고 마커 포함"],
            "packaging_requirements": ["README", "docs/runtime.md", "docs/testing.md", "configs/app.env.example", "docs/runbook.md", "infra/prometheus.yml", "infra/deploy/security.md"],
        },
        "website_builder": {
            "required_structure": ["landing sections", "contact flow", "deployment notes", "security runtime", "shipping package"],
            "verification_rules": ["frontend/app/page.tsx 완성", "문의 흐름 문서화", "배포/사용 가이드 포함", "auth/ops/security/출고 마커 포함"],
            "packaging_requirements": ["README", "docs/usage.md", "docs/deployment.md", "docs/runbook.md", "infra/prometheus.yml", "infra/deploy/security.md"],
        },
        "automation_service": {
            "required_structure": ["jobs", "runs", "alerts", "artifacts", "security runtime", "shipping package"],
            "verification_rules": ["queue/runtime 마커 포함", "ops 문서/로그 설정 포함", "auth/ops/security/출고 마커 포함"],
            "packaging_requirements": ["README", "configs/logging.yml", "docs/runtime.md", "docs/runbook.md", "infra/prometheus.yml", "infra/deploy/security.md"],
        },
        "customer_program": {
            "required_structure": ["api", "services", "frontend", "docs", "tests", "security runtime", "shipping package"],
            "verification_rules": ["필수 파일 생성", "runtime completeness 마커 포함", "auth/ops/security/출고 마커 포함"],
            "packaging_requirements": ["README", "docs/testing.md", "configs/app.env.example", "docs/runbook.md", "infra/prometheus.yml", "infra/deploy/security.md"],
        },
        "deployment_kit_program": {
            "required_structure": ["runtime api", "deployment policy", "publish readiness", "shipping package", "validation reports"],
            "verification_rules": ["실행 가능한 FastAPI 엔트리", "publish-readiness 및 ops/auth API 포함", "실프로그램 검증/출고 문서 포함"],
            "packaging_requirements": ["README", "docs/runtime.md", "docs/deployment.md", "docs/testing.md", "docs/runbook.md", "configs/app.env.example"],
        },
    }
    domain_contract = dict(domain_contracts.get(profile_id, domain_contracts["customer_program"]))
    domain_contract.update({
        "profile_id": profile_id,
        "validation_profile": validation_profile,
        "required_files": required_files,
        "mandatory_engine_contracts": list(order_profile.get("mandatory_engine_contracts") or []),
    })
    return domain_contract


def _build_integration_test_plan(order_profile: Dict[str, Any], validation_profile: str) -> Dict[str, Any]:
    if validation_profile == "nextjs_app":
        plan = {
            "validation_profile": validation_profile,
            "required_tests": [
                "package.json",
                "app/layout.tsx",
                "app/page.tsx",
                "scripts/check.sh",
            ],
            "runtime_checks": [
                "next app router structure",
                "npm build contract",
                "semantic audit",
            ],
        }
    else:
        plan = {
            "validation_profile": validation_profile,
            "required_tests": [
                "tests/test_health.py",
                "tests/test_routes.py",
                "tests/test_runtime.py",
            ],
            "runtime_checks": [
                "health endpoint",
                "project context endpoint",
                "semantic audit",
            ],
        }
    if bool(order_profile.get("ai_enabled")):
        plan["required_tests"].append("tests/test_ai_pipeline.py")
        plan["runtime_checks"].append("AI runtime contract")
    if str(order_profile.get("profile_id") or "") in {"commerce_platform", "autonomous_multimall_platform"}:
        plan["runtime_checks"].extend(["catalog flow", "order workflow", "marketplace publish payload"])
    if str(order_profile.get("profile_id") or "") == "deployment_kit_program":
        plan["runtime_checks"].extend([
            "publish readiness flow",
            "ops health flow",
            "auth settings flow",
            "shipping package flow",
        ])
    if str(order_profile.get("profile_id") or "") == "admin_console":
        plan["runtime_checks"].extend(["admin dashboard flow", "role management flow", "audit trail flow"])
    if validation_profile == "python_fastapi":
        plan["runtime_checks"].extend([
            "auth settings flow",
            "ops health flow",
            "shipping package flow",
            "security runtime flow",
        ])
        plan["required_tests"] = list(dict.fromkeys(list(plan.get("required_tests") or []) + ["tests/test_security_runtime.py"]))
    return plan


def _build_improvement_loop_plan(
    *,
    validation_profile: str,
    completion_judge: Dict[str, Any],
    integration_test_plan: Dict[str, Any],
    packaging_audit: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "enabled": bool(completion_judge.get("product_ready")),
        "state": "ready_for_refinement" if completion_judge.get("product_ready") else "blocked_until_pass",
        "validation_profile": validation_profile,
        "refiner_fixer_stage": dict(ORCH_REFINER_FIXER_STAGE),
        "entry_conditions": [
            "completion_gate_ok == true",
            "packaging_audit.packaging_ready == true",
            "integration_test_engine.ok == true",
        ],
        "expansion_steps": [
            "구매자 추가 요구사항 수집",
            "기능 차이 분석 및 확장 요구 정규화",
            "같은 도메인 계약/게이트 기준으로 보정 실행",
            "출고 엔진과 자동 검증 엔진 재실행",
        ],
        "required_tests": list(integration_test_plan.get("required_tests") or []),
        "packaging_targets": list(packaging_audit.get("required_packaging_files") or []),
    }


def _build_stage_history_with_refiner_fixer(completion_gate_ok: bool) -> List[str]:
    return [
        "DESIGN",
        "PLAN",
        "GENERATE",
        "BUILD",
        ORCH_REFINER_FIXER_STAGE["state"],
        "TEST",
        "DONE" if completion_gate_ok else "FAILED",
    ]


def _build_refiner_fixer_stage_payload(
    *,
    completion_gate_ok: bool,
    semantic_gate: Dict[str, Any],
    completion_judge: Dict[str, Any],
    b_brain_result: Dict[str, Any],
) -> Dict[str, Any]:
    failed_reasons = list(completion_judge.get("failed_reasons") or [])
    return {
        **dict(ORCH_REFINER_FIXER_STAGE),
        "status": "passed" if completion_gate_ok else "failed",
        "check_label": "통과" if completion_gate_ok else "미통과",
        "generator_family": b_brain_result.get("generator_family"),
        "generator_profile": b_brain_result.get("generator_profile"),
        "written_files": b_brain_result.get("file_count"),
        "semantic_summary": semantic_gate.get("summary"),
        "failed_reasons": failed_reasons,
    }


def _build_packaging_audit(order_profile: Dict[str, Any], required_files: List[str], written_files: List[str]) -> Dict[str, Any]:
    packaging_targets = [
        "README.md",
        "docs/usage.md",
        "docs/deployment.md",
        "docs/testing.md",
        "configs/app.env.example",
        "docs/runbook.md",
        "infra/prometheus.yml",
        "infra/deploy/security.md",
    ]
    missing = [path for path in packaging_targets if path not in written_files and path in required_files]
    return {
        "required_packaging_files": packaging_targets,
        "missing_packaging_files": missing,
        "packaging_ready": len(missing) == 0,
        "operations_guides": ["docs/runtime.md", "docs/deployment.md", "docs/testing.md"],
    }
