"""Document engine with local artifact packaging."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Dict, Optional
from uuid import uuid4

from ..contracts import extract_prompt_keywords, summarize_prompt


def _build_output_root() -> Path:
    root = Path(gettempdir()) / "codeai-marketplace-document"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_delivery_asset(path: Path, format_name: str, mime_type: str) -> Dict[str, Any]:
    exists = path.exists()
    return {
        "format": format_name,
        "path": str(path),
        "path_hint": str(path),
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size if exists else 0,
        "exists": exists,
        "generated_at": _utc_now(),
    }


def _write_minimal_pdf(path: Path, title: str) -> None:
    text = title.replace("(", "[").replace(")", "]")
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        + f"4 0 obj<</Length {len(text) + 34}>>stream\nBT /F1 12 Tf 20 80 Td ({text}) Tj ET\nendstream endobj\n".encode("latin-1", "ignore")
        + b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000245 00000 n \n0000000355 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n425\n%%EOF"
    )
    path.write_bytes(pdf_bytes)


def build_document_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt") or "").strip()
    project_name = str(payload.get("project_name") or "marketplace-document-run")
    template_id = str(payload.get("template_id") or "document-outline-template")
    keywords = extract_prompt_keywords(prompt, limit=6)
    outline = [
        "배경 및 문제 정의",
        "핵심 제안 내용",
        "실행 계획 및 일정",
        "리스크와 대응",
        "기대 효과",
    ]
    sections = [{"title": title, "summary": f"{title} 섹션 요약"} for title in outline[:3]]
    return {
        "artifact_id": f"ai-document-preview-{uuid4().hex[:8]}",
        "feature_id": "ai-document",
        "phase": "preview",
        "state": "completed",
        "status": "ready",
        "title": project_name,
        "content_type": "application/pdf",
        "prompt_summary": summarize_prompt(prompt),
        "keywords": keywords,
        "outline": outline,
        "sections": sections,
        "notes": [f"template_id={template_id}", "preview 단계에서는 문서 개요를 확정합니다."],
        "generated_at": _utc_now(),
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def render_document_final(payload: Dict[str, Any], preview_artifact: Dict[str, Any]) -> Dict[str, Any]:
    seed = uuid4().hex[:8]
    output_root = _build_output_root() / seed
    output_root.mkdir(parents=True, exist_ok=True)
    pdf_path = output_root / f"{seed}.pdf"
    md_path = output_root / f"{seed}.md"
    _write_minimal_pdf(pdf_path, str(preview_artifact.get("title") or "Document Package"))
    outline = list(preview_artifact.get("outline") or [])
    md_path.write_text(
        "\n".join(["# Document Package", "", f"Summary: {preview_artifact.get('prompt_summary') or ''}"] + [f"- {item}" for item in outline]),
        encoding="utf-8",
    )
    delivery_assets = [
        _build_delivery_asset(pdf_path, "pdf", "application/pdf"),
        _build_delivery_asset(md_path, "md", "text/markdown"),
    ]
    return {
        "artifact_id": f"ai-document-final-{seed}",
        "feature_id": "ai-document",
        "phase": "final",
        "state": "completed",
        "status": "generated",
        "title": "최종 문서 패키지",
        "content_type": "application/pdf",
        "prompt_summary": str(preview_artifact.get("prompt_summary") or ""),
        "keywords": list(preview_artifact.get("keywords") or []),
        "outline": outline,
        "sections": list(preview_artifact.get("sections") or []),
        "package_assets": [
            {"label": "pdf", "value": pdf_path.name},
            {"label": "markdown", "value": md_path.name},
        ],
        "delivery_assets": delivery_assets,
        "generated_at": _utc_now(),
        "notes": [f"output_root={output_root}", "pdf/md 산출물을 생성했습니다."],
        "bridge_payload": dict(payload.get("bridge_payload") or {}),
        "failure_tags": [],
    }


def review_document_quality(
    payload: Dict[str, Any],
    preview_artifact: Dict[str, Any],
    final_artifact: Dict[str, Any],
) -> Dict[str, Any]:
    del payload
    formats = {
        str(item.get("format") or "").lower()
        for item in list(final_artifact.get("delivery_assets") or [])
        if item.get("exists") and Path(str(item.get("path") or "")).exists()
    }
    passed = {"pdf", "md"}.issubset(formats)
    return {
        "passed": passed,
        "status": "approved" if passed else "needs-review",
        "feature_id": "ai-document",
        "fallback_state": "completed" if passed else "completed_preview_only",
        "score": 87 if passed else 59,
        "review_summary": "문서 패키지 산출물(pdf/md) 계약을 검증했습니다.",
        "failure_tags": [] if passed else ["document-delivery-assets-missing"],
        "checks": {
            "pdf_exists": "pdf" in formats,
            "md_exists": "md" in formats,
        },
        "preview_artifact_id": preview_artifact.get("artifact_id"),
        "final_artifact_id": final_artifact.get("artifact_id"),
    }


class DocumentGenerationEngine:
    """Legacy engine class wrapper."""

    ENGINE_ID = "doc-writer"

    async def run_preview(
        self,
        prompt: str,
        *,
        project_name: str = "",
        template: str = "business-proposal",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return build_document_preview(
            {
                "prompt": prompt,
                "project_name": project_name or "marketplace-document-run",
                "template_id": template,
                "bridge_payload": dict(options or {}),
            }
        )

    async def run_final(
        self,
        preview_artifact_id: str,
        *,
        preview_artifact: Dict[str, Any] | None = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        del preview_artifact_id
        return render_document_final({"bridge_payload": dict(options or {})}, preview_artifact or {})
