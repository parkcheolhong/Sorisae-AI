from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Dict, List
from uuid import uuid4
import zipfile

from ..contracts import extract_prompt_keywords, summarize_prompt


def _build_output_root() -> Path:
    root = Path(gettempdir()) / "codeai-marketplace-ppt"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _xml_escape(value: str) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_outline(prompt: str, keywords: List[str]) -> List[Dict[str, Any]]:
    topic = keywords[0] if keywords else "사업 계획"
    summary = summarize_prompt(prompt)
    k1 = keywords[1] if len(keywords) > 1 else "고객 문제"
    k2 = keywords[2] if len(keywords) > 2 else "해결 전략"
    k3 = keywords[3] if len(keywords) > 3 else "시장 검증"
    k4 = keywords[4] if len(keywords) > 4 else "재무 계획"
    k5 = keywords[5] if len(keywords) > 5 else "실행 로드맵"
    return [
        {
            "slide_no": 1,
            "title": f"{topic} 사업계획서",
            "bullets": [
                f"주제: {topic}",
                f"요약: {summary}",
                "사업계획서 표준 목차 기반 12장 구성입니다.",
                "핵심 의사결정 포인트를 장표별로 명확히 분리합니다.",
            ],
        },
        {
            "slide_no": 2,
            "title": "문제 정의",
            "bullets": [
                "현재 고객/시장 관점의 핵심 문제를 정의합니다.",
                f"핵심 문제 키워드: {k1}",
                "문제의 빈도, 강도, 비용 영향을 수치로 제시합니다.",
                "문제 미해결 시 발생하는 손실을 명확히 제시합니다.",
            ],
        },
        {
            "slide_no": 3,
            "title": "해결안(제품/서비스)",
            "bullets": [
                f"핵심 해결 전략: {k2}",
                "문제-해결 매핑을 기능 단위로 정리합니다.",
                "고객 효용(시간/비용/품질 개선)을 구체화합니다.",
                "차별점과 대체재 대비 우위를 명확히 설명합니다.",
            ],
        },
        {
            "slide_no": 4,
            "title": "시장 규모와 타깃",
            "bullets": [
                f"시장 검증 키워드: {k3}",
                "TAM/SAM/SOM 관점으로 시장 범위를 구분합니다.",
                "우선 공략 세그먼트와 고객 페르소나를 정의합니다.",
                "타깃 선정 근거와 진입 순서를 제시합니다.",
            ],
        },
        {
            "slide_no": 5,
            "title": "경쟁 환경 분석",
            "bullets": [
                "주요 경쟁사/대체 솔루션을 비교합니다.",
                "가격, 기능, 채널, 전환비용 기준으로 포지셔닝합니다.",
                "우리의 승부 포인트와 방어 전략을 정의합니다.",
                "경쟁 리스크 발생 시 대응 시나리오를 포함합니다.",
            ],
        },
        {
            "slide_no": 6,
            "title": "비즈니스 모델",
            "bullets": [
                "수익 구조(요금제/과금 단위/업셀 구조)를 정의합니다.",
                "원가 구조와 공헌이익 모델을 제시합니다.",
                "LTV/CAC 가정과 손익분기 시점을 명시합니다.",
                "핵심 파트너/채널 의존도를 함께 점검합니다.",
            ],
        },
        {
            "slide_no": 7,
            "title": "Go-To-Market 전략",
            "bullets": [
                "초기 고객 확보 채널과 메시지를 정의합니다.",
                "세일즈 파이프라인 단계별 전환 목표를 설정합니다.",
                "마케팅/세일즈/CS 연계 운영 리듬을 구성합니다.",
                "런칭 90일 실행 플랜과 책임 조직을 명시합니다.",
            ],
        },
        {
            "slide_no": 8,
            "title": "운영/기술 실행 계획",
            "bullets": [
                "제품, 데이터, 인프라 운영 아키텍처를 제시합니다.",
                "배포/모니터링/장애대응 표준 절차를 정의합니다.",
                "보안·권한·감사 로그·백업 원칙을 반영합니다.",
                "운영 지표 대시보드와 알림 체계를 포함합니다.",
            ],
        },
        {
            "slide_no": 9,
            "title": "재무 추정",
            "bullets": [
                f"재무 핵심 키워드: {k4}",
                "12개월 매출·비용·현금흐름 가정을 제시합니다.",
                "보수/기준/공격 시나리오별 손익을 비교합니다.",
                "운영 레버(가격/전환율/해지율) 민감도 분석을 포함합니다.",
            ],
        },
        {
            "slide_no": 10,
            "title": "리스크 관리",
            "bullets": [
                "시장/기술/운영/법무 리스크를 분류합니다.",
                "리스크별 예방/감지/복구 절차를 정의합니다.",
                "책임자와 대응 SLA를 명확히 설정합니다.",
                "분기별 리스크 리뷰 운영 규칙을 포함합니다.",
            ],
        },
        {
            "slide_no": 11,
            "title": "로드맵 및 마일스톤",
            "bullets": [
                f"실행 로드맵 키워드: {k5}",
                "분기별 핵심 마일스톤과 산출물을 배치합니다.",
                "선행조건/의존성/완료기준을 함께 명시합니다.",
                "지연 발생 시 대체 경로와 우선순위 재조정안을 포함합니다.",
            ],
        },
        {
            "slide_no": 12,
            "title": "팀 구성 및 요청 사항",
            "bullets": [
                "핵심 역할과 책임 범위를 명확히 정의합니다.",
                "즉시 승인 필요한 의사결정 항목을 제시합니다.",
                "승인 후 첫 2주 실행 액션과 담당자를 지정합니다.",
                "필요 지원(예산/인력/권한) 요청을 명확히 정리합니다.",
            ],
        },
    ]


def _build_delivery_asset(path: Path, format_name: str, mime_type: str) -> Dict[str, Any]:
    exists = path.exists()
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "format": format_name,
        "path": str(path),
        "path_hint": str(path),
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size if exists else 0,
        "exists": exists,
        "generated_at": generated_at,
    }


def _build_slide_xml(title: str, bullets: List[str]) -> str:
    safe_title = _xml_escape(title or "제목")
    safe_bullets = [_xml_escape(item) for item in bullets if str(item or "").strip()]
    paragraph_xml = "".join(
        f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>" for text in safe_bullets if text
    )
    if not paragraph_xml:
        paragraph_xml = "<a:p><a:r><a:t>내용 없음</a:t></a:r></a:p>"

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '<p:sp>'
        '<p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr/>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>'
        + safe_title
        + '</a:t></a:r></a:p></p:txBody>'
        '</p:sp>'
        '<p:sp>'
        '<p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr/>'
        '<p:txBody><a:bodyPr/><a:lstStyle/>'
        + paragraph_xml
        + '</p:txBody>'
        '</p:sp>'
        '</p:spTree></p:cSld></p:sld>'
    )


def _render_minimal_pptx(output_path: Path, slides: List[Dict[str, Any]]) -> None:
    normalized_slides = []
    for index, slide in enumerate(slides, start=1):
        title = str(slide.get("title") or f"슬라이드 {index}")
        bullets = [str(item) for item in list(slide.get("bullets") or [])]
        is_blank = bool(slide.get("blank"))
        normalized_slides.append({"title": title, "bullets": bullets, "blank": is_blank})

    if not normalized_slides:
        normalized_slides = [{"title": "AI PowerPoint", "bullets": ["생성된 내용이 없습니다."]}]

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as package:
        slide_overrides = "".join(
            f'<Override PartName="/ppt/slides/slide{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            for idx in range(1, len(normalized_slides) + 1)
        )
        package.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            + slide_overrides +
            '</Types>',
        )
        package.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
            '</Relationships>',
        )
        slide_id_list = "".join(
            f'<p:sldId id="{255 + idx}" r:id="rId{idx}"/>'
            for idx in range(1, len(normalized_slides) + 1)
        )
        package.writestr(
            "ppt/presentation.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:sldIdLst>' + slide_id_list + '</p:sldIdLst>'
            '</p:presentation>',
        )
        rels = "".join(
            f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{idx}.xml"/>'
            for idx in range(1, len(normalized_slides) + 1)
        )
        package.writestr(
            "ppt/_rels/presentation.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + rels +
            '</Relationships>',
        )
        for idx, slide in enumerate(normalized_slides, start=1):
            package.writestr(f"ppt/slides/slide{idx}.xml", _build_slide_xml(slide["title"], slide["bullets"]))


def build_powerpoint_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    keywords = extract_prompt_keywords(prompt, limit=6)
    template_id = str(payload.get("template_id") or "pitch-deck-template")
    project_name = str(payload.get("project_name") or "marketplace-powerpoint-run")
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    outline = _build_outline(prompt, keywords)

    return {
        "artifact_id": f"ai-powerpoint-preview-{uuid4().hex[:8]}",
        "feature_id": "ai-powerpoint",
        "phase": "preview",
        "status": "ready",
        "asset_kind": "presentation-outline",
        "title": "파워포인트 구성 preview",
        "prompt": prompt,
        "prompt_summary": summarize_prompt(prompt),
        "keywords": keywords,
        "generated_at": generated_at,
        "notes": [
            f"template_id={template_id}",
            f"project_name={project_name}",
            "preview 단계에서는 슬라이드 제목/핵심 bullet 구성을 확정합니다.",
        ],
        "presentation_outline": outline,
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def render_powerpoint_final(payload: Dict[str, Any], preview_artifact: Dict[str, Any]) -> Dict[str, Any]:
    outline = list(preview_artifact.get("presentation_outline") or [])

    artifact_seed = uuid4().hex[:8]
    output_root = _build_output_root() / artifact_seed
    output_root.mkdir(parents=True, exist_ok=True)
    pptx_path = output_root / f"{artifact_seed}.pptx"
    _render_minimal_pptx(pptx_path, outline)
    delivery_assets = [
        _build_delivery_asset(
            pptx_path,
            "pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    ]
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "artifact_id": f"ai-powerpoint-final-{artifact_seed}",
        "feature_id": "ai-powerpoint",
        "phase": "final",
        "status": "generated",
        "asset_kind": "presentation-package",
        "title": "최종 파워포인트 패키지",
        "preview_artifact_id": preview_artifact.get("artifact_id"),
        "prompt_summary": str(preview_artifact.get("prompt_summary") or ""),
        "keywords": list(preview_artifact.get("keywords") or []),
        "generated_at": generated_at,
        "presentation": {
            "slide_count": max(1, len(outline)),
            "sample_outline": outline[:3],
        },
        "delivery_assets": delivery_assets,
        "notes": [
            "pptx 패키지를 생성했습니다.",
            f"output_root={output_root}",
        ],
        "runtime_source": {
            "engine": "local_powerpoint_packager",
            "output_root": str(output_root),
        },
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def review_powerpoint_quality(
    payload: Dict[str, Any],
    preview_artifact: Dict[str, Any],
    final_artifact: Dict[str, Any],
) -> Dict[str, Any]:
    del payload
    delivery_assets = list(final_artifact.get("delivery_assets") or [])
    existing_assets = [asset for asset in delivery_assets if asset.get("exists") and Path(str(asset.get("path") or "")).exists()]
    format_names = {str(asset.get("format") or "").lower() for asset in existing_assets}
    slide_count = int((final_artifact.get("presentation") or {}).get("slide_count") or 0)
    expected_outline = list(preview_artifact.get("presentation_outline") or [])
    passed = bool(slide_count >= 12 and "pptx" in format_names and len(expected_outline) >= 12)

    return {
        "passed": passed,
        "status": "approved" if passed else "needs-review",
        "feature_id": "ai-powerpoint",
        "fallback_state": "completed" if passed else "completed_preview_only",
        "score": 88 if passed else 60,
        "review_summary": "슬라이드 구성 preview 와 최종 pptx 산출물 계약을 점검했습니다.",
        "failure_tags": [] if passed else ["powerpoint-delivery-assets-missing"],
        "checks": {
            "outline_ready": bool(expected_outline),
            "slide_count_ready": slide_count >= 12,
            "pptx_exists": "pptx" in format_names,
        },
        "preview_artifact_id": preview_artifact.get("artifact_id"),
        "final_artifact_id": final_artifact.get("artifact_id"),
    }


class PowerPointGenerationEngine:
    """팝업 오케스트레이터에서 호출되는 파워포인트 생성 엔진."""

    ENGINE_ID = "powerpoint-builder"

    async def run_preview(
        self,
        prompt: str,
        *,
        project_name: str = "",
        template: str = "pitch-deck-template",
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        payload = {
            "prompt": prompt,
            "project_name": project_name or "marketplace-powerpoint-run",
            "template_id": template,
            "bridge_payload": dict(options or {}),
        }
        return build_powerpoint_preview(payload)

    async def run_final(
        self,
        preview_artifact_id: str,
        *,
        preview_artifact: Dict[str, Any] | None = None,
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        del preview_artifact_id
        preview = preview_artifact or {}
        payload = {"bridge_payload": dict(options or {})}
        return render_powerpoint_final(payload, preview)