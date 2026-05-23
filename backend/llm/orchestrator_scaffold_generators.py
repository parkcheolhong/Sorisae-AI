from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


_SCAFFOLD_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORCH_ID_REGISTRY_PATH = "docs/id_registry.json"
_ORCH_TRACEABILITY_MAP_PATH = "docs/traceability_map.json"


def _build_architecture_doc_template(project_name: str) -> str:
    return (
        f"# {project_name} Architecture\n\n"
        "## Purpose\n\n"
        "- Define fixed boundaries for the generated project.\n"
        "- Keep implementation and validation traceable.\n\n"
        "## Boundaries\n\n"
        "- UI handles rendering and API calls only.\n"
        "- Backend owns business logic and validation.\n"
        "- Docs store design, checklist, and traceability artifacts.\n"
    )


def _build_architecture_contract_template(project_name: str) -> str:
    payload = {
        "schema_version": "generated.v1",
        "project": project_name,
        "required_documents": [
            "docs/architecture.md",
            "docs/architecture.contract.json",
            "docs/id_registry.schema.json",
            "docs/id_registry.json",
            "docs/orchestration_rules_checklist.md",
        ],
        "fixed_links": [
            {
                "id": "main-to-router",
                "source": "backend/app/main.py",
                "target": "backend/app/api/routes/**",
                "rule": "앱 진입점은 라우터를 등록해야 한다.",
            },
            {
                "id": "router-to-controller",
                "source": "backend/app/api/routes/**",
                "target": "backend/app/controllers/**",
                "rule": "라우터는 컨트롤러 계층을 통해 요청 흐름을 시작한다.",
            },
            {
                "id": "controller-to-service",
                "source": "backend/app/controllers/**",
                "target": "backend/app/services/**",
                "rule": "컨트롤러는 서비스 계층을 통해 비즈니스 흐름을 조합한다.",
            },
            {
                "id": "service-to-repository",
                "source": "backend/app/services/**",
                "target": "backend/app/repositories/**",
                "rule": "서비스는 저장소 계층을 통해 데이터 접근을 수행한다.",
            },
            {
                "id": "service-to-external-adapter",
                "source": "backend/app/services/**",
                "target": "backend/app/external_adapters/**",
                "rule": "서비스는 외부 연동 호출을 external adapter 계층을 통해 수행한다.",
            },
            {
                "id": "repository-to-infra",
                "source": "backend/app/repositories/**",
                "target": "backend/app/infra/**",
                "rule": "저장소는 infra 계층을 통해 런타임 구현을 사용한다.",
            },
        ],
        "protected_paths": [
            {
                "path": "docs/**",
                "rule": "design and validation artifacts",
            }
        ],
        "structure_rules": [
            {
                "id": "main-router-registration",
                "scope": "backend/app/main.py",
                "requirement": "main entry must import and include routers",
            },
            {
                "id": "router-service-boundary",
                "scope": "backend/**/*router.py, backend/**/routers/**, backend/**/api/routes/**",
                "requirement": "routers must not call repositories directly and should remain HTTP adapters",
            },
            {
                "id": "controller-service-boundary",
                "scope": "backend/**/*controller.py, backend/**/controllers/**",
                "requirement": "controllers must orchestrate services only and must not call repositories or adapters directly",
            },
            {
                "id": "service-no-router-import",
                "scope": "backend/**/*service.py, backend/**/services/**",
                "requirement": "services must not depend on routers or FastAPI HTTP primitives",
            },
            {
                "id": "repository-data-only",
                "scope": "backend/**/*repository.py, backend/**/repositories/**, backend/**/repos/**",
                "requirement": "repositories must stay in data access layer and must not depend on routers or services",
            },
            {
                "id": "infra-isolation",
                "scope": "backend/**/*infra*.py, backend/**/infra/**",
                "requirement": "infra layer must not depend on router, controller, or service layers",
            },
            {
                "id": "external-adapter-isolation",
                "scope": "backend/**/*adapter.py, backend/**/*client.py, backend/**/external/**, backend/**/external_adapters/**",
                "requirement": "external adapters must stay as integration boundaries and must not depend on router, controller, or service layers",
            },
            {
                "id": "design-traceability",
                "scope": "docs/**, src/**, app/**, backend/**, frontend/**",
                "requirement": "design items must be traceable to implementation and validation evidence",
            }
        ],
        "traceability_fields": [
            "design_item_id",
            "implementation_files",
            "api_or_ui_links",
            "validation_evidence",
            "approval_status",
        ],
        "validation_gates": [
            "required_files",
            "structure_compliance",
            "id_registry_required",
            "completion_gate",
            "semantic_audit",
        ],
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _build_generated_id_registry_schema_template() -> str:
    return (_SCAFFOLD_REPO_ROOT / "docs" / "id_registry.schema.json").read_text(encoding="utf-8")


def _build_generated_id_registry_template(
    project_name: str,
    validation_profile: str,
) -> str:
    payload = {
        "$schema": "./id_registry.schema.json",
        "schema_version": "id-registry.v1",
        "registry_id": f"REG-{re.sub(r'[^A-Za-z0-9]+', '-', project_name.upper()).strip('-') or 'PROJECT'}",
        "generated_at": datetime.now().isoformat(),
        "project": {
            "project_id": f"PROJECT-{re.sub(r'[^A-Za-z0-9]+', '-', project_name.upper()).strip('-') or 'PROJECT'}",
            "name": project_name,
            "root_path": ".",
            "scope": "generated-output",
        },
        "governance": {
            "required_documents": [
                "docs/id_registry.schema.json",
                "docs/id_registry.json",
                "docs/traceability_map.json",
                "docs/auto_link_map.json",
                "docs/architecture.contract.json",
                "docs/generator_checklist.md",
            ],
            "required_id_levels": ["file", "section", "feature", "chunk", "flow", "trace", "failure_tag", "repair_tag"],
            "selective_apply_policy": "id-targeted-only",
            "future_generation_mandatory": True,
        },
        "files": [],
        "flows": [],
        "traceability_links": [],
        "failure_tags": [],
        "repair_tags": [],
        "validation_rules": {
            "hard_gate": [
                "모든 신규 소스 파일은 FILE-ID registry 항목이 있어야 한다.",
                "핵심 섹션은 SECTION-ID 와 최소 1개 CHUNK-ID를 가져야 한다.",
                "생성 프로그램은 docs/id_registry.schema.json 과 docs/id_registry.json 을 반드시 포함해야 한다.",
            ],
            "generation_requirements": [
                f"validation_profile={validation_profile}",
                "앞으로 생성되는 모든 프로그램은 docs/id_registry.json, docs/traceability_map.json, docs/auto_link_map.json, docs/architecture.contract.json, docs/generator_checklist.md 를 의무 생성한다.",
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_generated_product_identity_template(
    project_name: str,
    validation_profile: str,
) -> str:
    normalized_project = re.sub(r"[^A-Za-z0-9]+", "-", str(project_name or "project").upper()).strip("-") or "PROJECT"
    payload = {
        "schema_version": "product-identity.v1",
        "product_id": f"PID-{normalized_project}",
        "project_name": project_name,
        "validation_profile": validation_profile,
        "identity_policy": {
            "mandatory": True,
            "description": "생성기 산출물의 고유 인식표(주민번호 수준 식별자)입니다. 배포/검증/복구 모든 단계에서 반드시 유지해야 합니다.",
        },
        "identity_links": {
            "id_registry_path": _ORCH_ID_REGISTRY_PATH,
            "traceability_map_path": _ORCH_TRACEABILITY_MAP_PATH,
            "architecture_contract_path": "docs/architecture.contract.json",
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _decorate_generated_file_with_ids(path: str, content: str) -> str:
    normalized_path = str(path or "").strip().replace("\\", "/")
    if not normalized_path or normalized_path.startswith("docs/"):
        return content
    file_stub = re.sub(r"[^A-Za-z0-9]+", "-", normalized_path.upper()).strip("-") or "GENERATED-FILE"
    section_stub = f"SECTION-{file_stub}-MAIN"
    feature_stub = f"FEATURE-{file_stub}-RUNTIME"
    chunk_stub = f"CHUNK-{file_stub}-001"
    header = (
        f"# FILE-ID: FILE-{file_stub}\n"
        f"# SECTION-ID: {section_stub}\n"
        f"# FEATURE-ID: {feature_stub}\n"
        f"# CHUNK-ID: {chunk_stub}\n\n"
    )
    suffix = normalized_path.rsplit('.', 1)[-1].lower() if '.' in normalized_path else ''
    if suffix in {"py", "pyi", "sh", "yml", "yaml", "toml", "ini", "cfg", "env", "md", "txt"}:
        return header + content if not content.startswith("# FILE-ID:") else content

    if suffix in {"ts", "tsx", "js", "jsx", "css", "scss"}:
        comment_block = (
            f"/* FILE-ID: FILE-{file_stub} */\n"
            f"/* SECTION-ID: {section_stub} */\n"
            f"/* FEATURE-ID: {feature_stub} */\n"
            f"/* CHUNK-ID: {chunk_stub} */\n\n"
        )
        return comment_block + content if "FILE-ID:" not in content[:200] else content

    if suffix == "json":
        return content

    return header + content if not content.startswith("# FILE-ID:") else content


def _strip_generated_id_headers(content: str) -> str:
    text = str(content or "")
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    prefix_index = 0
    while prefix_index < len(lines) and lines[prefix_index].startswith("# ") and "-ID:" in lines[prefix_index]:
        prefix_index += 1
    if prefix_index > 0:
        while prefix_index < len(lines) and not lines[prefix_index].strip():
            prefix_index += 1
        return "\n".join(lines[prefix_index:])
    return normalized


def _decorate_template_candidates_with_ids(template_candidates: Dict[str, str]) -> Dict[str, str]:
    return {
        path: _decorate_generated_file_with_ids(path, content)
        for path, content in template_candidates.items()
    }


def _build_nextjs_vertical_slice_files(project_name: str) -> Dict[str, str]:
    return {
        "README.md": (
            f"# {project_name}\n\n"
            "Generated Next.js operations canvas scaffold.\n\n"
            "## What is included\n\n"
            "- App Router based landing page and dashboard experience\n"
            "- Shared design tokens, editorial layout primitives, and animated sections\n"
            "- Dark and light theme switch with persistent browser preference\n"
            "- Client-side fetch pattern bound to /api/brief for live dashboard hydration\n"
            "- Build-ready TypeScript and Next.js 16 configuration\n"
        ),
        ".gitignore": (
            ".next\n"
            "node_modules\n"
            "npm-debug.log*\n"
        ),
        "package.json": (
            "{\n"
            "  \"name\": \"generated-nextjs-ops-dashboard\",\n"
            "  \"private\": true,\n"
            "  \"scripts\": {\n"
            "    \"dev\": \"next dev\",\n"
            "    \"build\": \"next build\",\n"
            "    \"start\": \"next start\"\n"
            "  },\n"
            "  \"dependencies\": {\n"
            "    \"next\": \"16.1.6\",\n"
            "    \"react\": \"18.3.1\",\n"
            "    \"react-dom\": \"18.3.1\"\n"
            "  },\n"
            "  \"devDependencies\": {\n"
            "    \"@types/node\": \"20.14.12\",\n"
            "    \"@types/react\": \"18.3.3\",\n"
            "    \"@types/react-dom\": \"18.3.0\",\n"
            "    \"typescript\": \"5.5.4\"\n"
            "  }\n"
            "}\n"
        ),
        "tsconfig.json": (
            "{\n"
            "  \"compilerOptions\": {\n"
            "    \"target\": \"ES2022\",\n"
            "    \"lib\": [\"dom\", \"dom.iterable\", \"es2022\"],\n"
            "    \"allowJs\": false,\n"
            "    \"skipLibCheck\": true,\n"
            "    \"strict\": true,\n"
            "    \"noEmit\": true,\n"
            "    \"esModuleInterop\": true,\n"
            "    \"module\": \"esnext\",\n"
            "    \"moduleResolution\": \"bundler\",\n"
            "    \"resolveJsonModule\": true,\n"
            "    \"isolatedModules\": true,\n"
            "    \"jsx\": \"react-jsx\",\n"
            "    \"incremental\": true\n"
            "  },\n"
            "  \"include\": [\"next-env.d.ts\", \"**/*.ts\", \"**/*.tsx\"],\n"
            "  \"exclude\": [\"node_modules\"]\n"
            "}\n"
        ),
        "next-env.d.ts": (
            "/// <reference types=\"next\" />\n"
            "/// <reference types=\"next/image-types/global\" />\n\n"
            "// This file is managed by Next.js.\n"
        ),
        "next.config.js": (
            "const path = require('path');\n\n"
            "/** @type {import('next').NextConfig} */\n"
            "const nextConfig = {\n"
            "  reactStrictMode: true,\n"
            "  turbopack: {\n"
            "    root: path.resolve(__dirname),\n"
            "  },\n"
            "};\n\n"
            "module.exports = nextConfig;\n"
        ),
        "app/layout.tsx": (
            "import './globals.css';\n"
            "import type { ReactNode } from 'react';\n"
            "import { IBM_Plex_Mono, Space_Grotesk } from 'next/font/google';\n\n"
            "const display = Space_Grotesk({\n"
            "  subsets: ['latin'],\n"
            "  variable: '--font-display',\n"
            "});\n\n"
            "const mono = IBM_Plex_Mono({\n"
            "  subsets: ['latin'],\n"
            "  weight: ['400', '500'],\n"
            "  variable: '--font-mono',\n"
            "});\n\n"
            "export const metadata = {\n"
            f"  title: '{project_name}',\n"
            "  description: 'Operations canvas generated by the deterministic scaffold.',\n"
            "};\n\n"
            "export default function RootLayout({ children }: { children: ReactNode }) {\n"
            "  return (\n"
            "    <html lang=\"en\" suppressHydrationWarning>\n"
            "      <body className={`${display.variable} ${mono.variable}`}>\n"
            "        <div className=\"shell\">{children}</div>\n"
            "      </body>\n"
            "    </html>\n"
            "  );\n"
            "}\n"
        ),
        "app/loading.tsx": (
            "export default function Loading() {\n"
            "  return (\n"
            "    <main className=\"page\">\n"
            "      <section className=\"sectionCard\">\n"
            "        <p className=\"eyebrow\">Loading</p>\n"
            "        <h1>Preparing the operations canvas...</h1>\n"
            "      </section>\n"
            "    </main>\n"
            "  );\n"
            "}\n"
        ),
        "app/page.tsx": (
            "import { DashboardClient } from '../components/dashboardclient';\n"
            "import { defaultBriefPayload } from '../lib/data';\n\n"
            "export default function HomePage() {\n"
            "  return <DashboardClient variant=\"overview\" initialPayload={defaultBriefPayload} />;\n"
            "}\n"
        ),
        "app/dashboard/page.tsx": (
            "import { DashboardClient } from '../../components/dashboardclient';\n"
            "import { defaultBriefPayload } from '../../lib/data';\n\n"
            "export default function DashboardPage() {\n"
            "  return <DashboardClient variant=\"detail\" initialPayload={defaultBriefPayload} />;\n"
            "}\n"
        ),
        "app/api/health/route.ts": (
            "import { NextResponse } from 'next/server';\n\n"
            "export async function GET() {\n"
            "  return NextResponse.json({ ok: true });\n"
            "}\n"
        ),
        "app/api/brief/route.ts": (
            "import { NextResponse } from 'next/server';\n\n"
            "export async function GET() {\n"
            "  return NextResponse.json({ refreshedAt: new Date().toISOString() });\n"
            "}\n"
        ),
        "app/globals.css": (
            ":root {\n"
            "  color-scheme: light;\n"
            "  --bg: #f5efe5;\n"
            "  --bg-strong: #efe1cb;\n"
            "  --panel: rgba(255, 250, 242, 0.86);\n"
            "  --panel-strong: rgba(255, 247, 236, 0.98);\n"
            "  --line: rgba(27, 43, 65, 0.12);\n"
            "  --text: #1a2433;\n"
            "  --muted: #6c7684;\n"
            "  --accent: #e6783a;\n"
            "  --accent-strong: #0f766e;\n"
            "  --ink-soft: rgba(26, 36, 51, 0.08);\n"
            "  --shadow: 0 32px 80px rgba(103, 73, 40, 0.16);\n"
            "}\n\n"
            "html[data-theme='dark'] {\n"
            "  color-scheme: dark;\n"
            "  --bg: #07111f;\n"
            "  --bg-strong: #0d1a29;\n"
            "  --panel: rgba(10, 24, 45, 0.88);\n"
            "  --panel-strong: rgba(9, 20, 36, 0.96);\n"
            "  --line: rgba(121, 192, 255, 0.18);\n"
            "  --text: #e6edf3;\n"
            "  --muted: #8aa4c2;\n"
            "  --accent: #f59e0b;\n"
            "  --accent-strong: #5eead4;\n"
            "  --ink-soft: rgba(230, 237, 243, 0.08);\n"
            "  --shadow: 0 32px 90px rgba(0, 0, 0, 0.32);\n"
            "}\n\n"
            "* { box-sizing: border-box; }\n"
            "html, body { margin: 0; padding: 0; min-height: 100%; background: linear-gradient(180deg, var(--bg) 0%, var(--bg-strong) 100%); color: var(--text); transition: background 200ms ease, color 200ms ease; }\n"
            "body { line-height: 1.5; font-family: var(--font-display), 'Segoe UI', sans-serif; }\n"
            "body::before { content: ''; position: fixed; inset: 0; background: radial-gradient(circle at 15% 15%, rgba(230, 120, 58, 0.14), transparent 28%), radial-gradient(circle at 85% 20%, rgba(15, 118, 110, 0.12), transparent 24%), linear-gradient(135deg, rgba(255,255,255,0.24) 0%, transparent 45%); pointer-events: none; }\n"
            "a { color: inherit; text-decoration: none; }\n"
            ".shell { min-height: 100vh; padding: 32px 20px 48px; position: relative; }\n"
            ".page { max-width: 1220px; margin: 0 auto; display: grid; gap: 24px; position: relative; }\n"
            ".hero, .sectionCard { border: 1px solid var(--line); background: var(--panel); backdrop-filter: blur(16px); border-radius: 32px; padding: 28px; box-shadow: var(--shadow); position: relative; overflow: hidden; }\n"
            ".hero::after, .sectionCard::after { content: ''; position: absolute; inset: auto -10% -45% auto; width: 220px; height: 220px; background: radial-gradient(circle, rgba(230, 120, 58, 0.16), transparent 66%); }\n"
            ".eyebrow { margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.18em; color: var(--accent-strong); font-size: 12px; font-family: var(--font-mono), monospace; }\n"
            "h1, h2, h3, p { margin: 0; }\n"
            ".hero { display: grid; gap: 24px; }\n"
            ".heroHeader { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }\n"
            ".heroTitle { font-size: clamp(2.7rem, 7vw, 5.4rem); line-height: 0.95; max-width: 9ch; letter-spacing: -0.05em; }\n"
            ".heroCopy { max-width: 760px; font-size: 1.05rem; color: var(--muted); }\n"
            ".heroBadge { border-radius: 999px; padding: 10px 14px; background: rgba(15, 118, 110, 0.08); border: 1px solid rgba(15, 118, 110, 0.18); font-family: var(--font-mono), monospace; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; }\n"
            ".heroHighlights { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }\n"
            ".heroHighlight { padding: 16px 18px; border-radius: 20px; background: rgba(255,255,255,0.72); border: 1px solid rgba(27, 43, 65, 0.08); box-shadow: inset 0 1px 0 rgba(255,255,255,0.6); }\n"
            ".heroActions { display: flex; gap: 12px; flex-wrap: wrap; }\n"
            ".primaryButton, .secondaryButton, .textLink { display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; font-weight: 600; }\n"
            ".primaryButton { background: var(--text); color: #fff7ef; padding: 12px 18px; }\n"
            ".secondaryButton { border: 1px solid var(--line); padding: 12px 18px; background: rgba(255,255,255,0.56); }\n"
            ".textLink { color: var(--accent-strong); font-family: var(--font-mono), monospace; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.12em; }\n"
            ".utilityBar { display: flex; justify-content: space-between; gap: 16px; align-items: center; flex-wrap: wrap; }\n"
            ".utilityGroup { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }\n"
            ".statusPill { padding: 10px 14px; border-radius: 999px; border: 1px solid var(--line); background: rgba(255,255,255,0.5); font-family: var(--font-mono), monospace; font-size: 0.78rem; }\n"
            ".statusPill.is-error { color: #b91c1c; }\n"
            ".statusPill.is-live { color: var(--accent-strong); }\n"
            ".refreshButton { border: 1px solid var(--line); background: var(--panel-strong); color: var(--text); padding: 10px 14px; border-radius: 999px; font-family: var(--font-mono), monospace; }\n"
            ".themeToggle { display: inline-flex; padding: 4px; gap: 4px; border-radius: 999px; border: 1px solid var(--line); background: rgba(255,255,255,0.52); }\n"
            ".themeChip { border: 0; background: transparent; color: var(--muted); padding: 10px 12px; border-radius: 999px; font-family: var(--font-mono), monospace; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.12em; }\n"
            ".themeChip.is-active { background: var(--text); color: #fff7ef; }\n"
            ".metricGrid, .signalGrid, .featureGrid { display: grid; gap: 18px; }\n"
            ".metricGrid { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }\n"
            ".metricCard { padding: 22px; border-radius: 24px; background: var(--panel-strong); border: 1px solid var(--line); box-shadow: var(--shadow); transform: translateY(0); animation: floatUp 560ms ease both; }\n"
            ".metricLabel, .signalLabel, .microLabel { font-family: var(--font-mono), monospace; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }\n"
            ".metricValue { margin-top: 12px; font-size: 2rem; letter-spacing: -0.04em; }\n"
            ".metricDetail { margin-top: 10px; color: var(--muted); }\n"
            ".signalGrid { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }\n"
            ".signalCard { border: 1px solid var(--line); background: rgba(255,255,255,0.66); border-radius: 26px; padding: 20px; display: grid; gap: 12px; position: relative; overflow: hidden; }\n"
            ".signalTone { position: absolute; inset: 0 auto 0 0; width: 6px; }\n"
            ".signalTone.is-healthy { background: #0f766e; }\n"
            ".signalTone.is-watch { background: #e6783a; }\n"
            ".signalTone.is-planning { background: #3b82f6; }\n"
            ".signalStatus { font-size: 1.1rem; font-weight: 700; }\n"
            ".muted { color: var(--muted); }\n"
            ".list { display: grid; gap: 12px; margin-top: 18px; }\n"
            ".listItem { border-left: 3px solid var(--accent); padding-left: 14px; color: var(--text); }\n"
            ".featureGrid { grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr); }\n"
            ".railList { display: grid; gap: 14px; margin-top: 18px; }\n"
            ".railItem { padding: 16px 18px; border-radius: 20px; background: rgba(255,255,255,0.64); border: 1px solid var(--line); }\n"
            ".sectionHeader { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }\n"
            ".sectionCopy { margin-top: 12px; max-width: 640px; }\n"
            ".compactMetrics .metricCard { padding: 18px; }\n"
            ".dashboardStack { display: grid; gap: 24px; }\n"
            "@keyframes floatUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }\n"
            "@media (max-width: 920px) { .featureGrid { grid-template-columns: 1fr; } .heroHeader, .sectionHeader { flex-direction: column; } }\n"
            "@media (max-width: 720px) { .shell { padding: 20px 14px 36px; } .hero, .sectionCard { padding: 22px; border-radius: 24px; } .heroTitle { font-size: clamp(2.2rem, 15vw, 3.6rem); } }\n"
        ),
        "components/dashboardclient.tsx": (
            "'use client';\n\n"
            "import { useEffect, useState } from 'react';\n"
            "import { ExecutionBoard } from './executionboard';\n"
            "import { FocusRail } from './focusrail';\n"
            "import { HeroPanel } from './heropanel';\n"
            "import { InsightTimeline } from './insighttimeline';\n"
            "import { MetricCluster } from './metriccluster';\n"
            "import { SignalMatrix } from './signalmatrix';\n"
            "import { ThemeToggle } from './themetoggle';\n"
            "import type { BriefPayload } from '../lib/types';\n\n"
            "type DashboardVariant = 'overview' | 'detail';\n\n"
            "async function readBrief(): Promise<BriefPayload> {\n"
            "  const response = await fetch('/api/brief', { cache: 'no-store' });\n"
            "  if (!response.ok) {\n"
            "    throw new Error(`brief fetch failed: ${response.status}`);\n"
            "  }\n"
            "  return response.json() as Promise<BriefPayload>;\n"
            "}\n\n"
            "export function DashboardClient({ initialPayload, variant }: { initialPayload: BriefPayload; variant: DashboardVariant }) {\n"
            "  const [payload, setPayload] = useState(initialPayload);\n"
            "  const [phase, setPhase] = useState<'idle' | 'loading' | 'live' | 'error'>('idle');\n"
            "  const [errorMessage, setErrorMessage] = useState('');\n\n"
            "  const refresh = async () => {\n"
            "    setPhase('loading');\n"
            "    setErrorMessage('');\n"
            "    try {\n"
            "      const nextPayload = await readBrief();\n"
            "      setPayload(nextPayload);\n"
            "      setPhase('live');\n"
            "    } catch (error) {\n"
            "      setPhase('error');\n"
            "      setErrorMessage(error instanceof Error ? error.message : 'brief fetch failed');\n"
            "    }\n"
            "  };\n\n"
            "  useEffect(() => {\n"
            "    void refresh();\n"
            "  }, []);\n\n"
            "  const runtimeItems = payload.runtimeSignals.map((signal) => `${signal.label}: ${signal.status} · ${signal.owner}`);\n"
            "  const pillClassName = phase === 'error' ? 'statusPill is-error' : phase === 'live' ? 'statusPill is-live' : 'statusPill';\n\n"
            "  return (\n"
            "    <main className=\"page dashboardStack\">\n"
            "      <section className=\"sectionCard utilityBar\">\n"
            "        <div className=\"utilityGroup\">\n"
            "          <div className=\"statusPill\">Variant · {variant}</div>\n"
            "          <div className={pillClassName}>Fetch · {phase}</div>\n"
            "          <div className=\"statusPill\">Refreshed · {payload.refreshedAt}</div>\n"
            "        </div>\n"
            "        <div className=\"utilityGroup\">\n"
            "          <ThemeToggle />\n"
            "          <button type=\"button\" className=\"refreshButton\" onClick={() => void refresh()}>Refresh live brief</button>\n"
            "        </div>\n"
            "      </section>\n"
            "      {phase === 'error' ? <section className=\"sectionCard\"><p className=\"eyebrow\">Fetch warning</p><p>{errorMessage}</p></section> : null}\n"
            "      {variant === 'overview' ? (\n"
            "        <>\n"
            "          <HeroPanel summary={payload.summary} />\n"
            "          <MetricCluster metrics={payload.metrics} />\n"
            "          <SignalMatrix signals={payload.runtimeSignals} />\n"
            "          <section className=\"featureGrid\">\n"
            "            <FocusRail title=\"Focus rail\" items={payload.focusRail} />\n"
            "            <InsightTimeline title=\"Release timeline\" items={payload.releaseTimeline} />\n"
            "          </section>\n"
            "        </>\n"
            "      ) : (\n"
            "        <>\n"
            "          <header className=\"sectionCard sectionHeader\">\n"
            "            <div>\n"
            "              <p className=\"eyebrow\">Dashboard</p>\n"
            "              <h1>Operational release cockpit</h1>\n"
            "              <p className=\"muted sectionCopy\">This view compresses the same live brief into a denser board for owners and release reviewers.</p>\n"
            "            </div>\n"
            "            <a href=\"/api/brief\" className=\"textLink\">Open raw brief JSON</a>\n"
            "          </header>\n"
            "          <MetricCluster metrics={payload.metrics} compact />\n"
            "          <section className=\"featureGrid\">\n"
            "            <ExecutionBoard title=\"Runtime signals\" items={runtimeItems} />\n"
            "            <InsightTimeline title=\"Release timeline\" items={payload.releaseTimeline} />\n"
            "          </section>\n"
            "        </>\n"
            "      )}\n"
            "    </main>\n"
            "  );\n"
            "}\n"
        ),
        "components/heropanel.tsx": (
            "import type { DashboardSummary } from '../lib/types';\n\n"
            "export function HeroPanel({ summary }: { summary: DashboardSummary }) {\n"
            "  return (\n"
            "    <section className=\"hero\">\n"
            "      <div className=\"heroHeader\">\n"
            "        <div>\n"
            "          <p className=\"eyebrow\">{summary.eyebrow}</p>\n"
            "          <h1 className=\"heroTitle\">{summary.headline}</h1>\n"
            "        </div>\n"
            "        <div className=\"heroBadge\">{summary.badge}</div>\n"
            "      </div>\n"
            "      <p className=\"heroCopy\">{summary.description}</p>\n"
            "      <div className=\"heroHighlights\">\n"
            "        {summary.highlights.map((item) => (\n"
            "          <div key={item} className=\"heroHighlight\">{item}</div>\n"
            "        ))}\n"
            "      </div>\n"
            "      <div className=\"heroActions\">\n"
            "        <a href={summary.primaryHref} className=\"primaryButton\">{summary.primaryLabel}</a>\n"
            "        <a href={summary.secondaryHref} className=\"secondaryButton\">{summary.secondaryLabel}</a>\n"
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        ),
        "components/metriccluster.tsx": (
            "import type { SummaryMetric } from '../lib/types';\n\n"
            "export function MetricCluster({ metrics, compact = false }: { metrics: SummaryMetric[]; compact?: boolean }) {\n"
            "  return (\n"
            "    <section className={compact ? 'metricGrid compactMetrics' : 'metricGrid'}>\n"
            "      {metrics.map((metric) => (\n"
            "        <article key={metric.label} className=\"metricCard\">\n"
            "          <div className=\"metricLabel\">{metric.label}</div>\n"
            "          <div className=\"metricValue\">{metric.value}</div>\n"
            "          <p className=\"metricDetail\">{metric.detail}</p>\n"
            "        </article>\n"
            "      ))}\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        ),
        "components/signalmatrix.tsx": (
            "import type { RuntimeSignal } from '../lib/types';\n\n"
            "export function SignalMatrix({ signals }: { signals: RuntimeSignal[] }) {\n"
            "  return (\n"
            "    <section className=\"signalGrid\">\n"
            "      {signals.map((signal) => (\n"
            "        <article key={signal.label} className=\"signalCard\">\n"
            "          <div className={`signalTone is-${signal.tone}`} />\n"
            "          <div className=\"signalLabel\">{signal.label}</div>\n"
            "          <div className=\"signalStatus\">{signal.status}</div>\n"
            "          <p className=\"muted\">{signal.detail}</p>\n"
            "          <div className=\"microLabel\">Owner · {signal.owner}</div>\n"
            "        </article>\n"
            "        ))}\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        ),
        "components/focusrail.tsx": (
            "import type { FocusItem } from '../lib/types';\n\n"
            "export function FocusRail({ title, items }: { title: string; items: FocusItem[] }) {\n"
            "  return (\n"
            "    <section className=\"sectionCard\">\n"
            "      <p className=\"eyebrow\">Focus</p>\n"
            "      <h2>{title}</h2>\n"
            "      <div className=\"railList\">\n"
            "        {items.map((item) => (\n"
            "          <article key={item.title} className=\"railItem\">\n"
            "            <div className=\"microLabel\">{item.owner}</div>\n"
            "            <h3 style={{ marginTop: 8 }}>{item.title}</h3>\n"
            "            <p className=\"muted\" style={{ marginTop: 8 }}>{item.summary}</p>\n"
            "          </article>\n"
            "        ))}\n"
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        ),
        "components/insighttimeline.tsx": (
            "export function InsightTimeline({ title, items }: { title: string; items: string[] }) {\n"
            "  return (\n"
            "    <section className=\"sectionCard\">\n"
            "      <p className=\"eyebrow\">Timeline</p>\n"
            "      <h2>{title}</h2>\n"
            "      <div className=\"list\">\n"
            "        {items.map((item, index) => (\n"
            "          <div key={`${title}-${index}`} className=\"listItem\">\n"
            "            <strong style={{ color: 'var(--accent-strong)' }}>0{index + 1}</strong> {item}\n"
            "          </div>\n"
            "        ))}\n"
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        ),
        "components/executionboard.tsx": (
            "export function ExecutionBoard({ title, items }: { title: string; items: string[] }) {\n"
            "  return (\n"
            "    <section className=\"sectionCard\">\n"
            "      <p className=\"eyebrow\">Execution</p>\n"
            "      <h2>{title}</h2>\n"
            "      <div className=\"list\">\n"
            "        {items.map((item, index) => (\n"
            "          <div key={`${title}-${index}`} className=\"listItem\">\n"
            "            <strong style={{ color: 'var(--accent)' }}>Step {index + 1}</strong> {item}\n"
            "          </div>\n"
            "        ))}\n"
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        ),
        "components/themetoggle.tsx": (
            "'use client';\n\n"
            "import { useEffect, useState } from 'react';\n\n"
            "type ThemeMode = 'light' | 'dark';\n\n"
            "function applyTheme(theme: ThemeMode) {\n"
            "  document.documentElement.dataset.theme = theme;\n"
            "  window.localStorage.setItem('ops-theme', theme);\n"
            "}\n\n"
            "export function ThemeToggle() {\n"
            "  const [theme, setTheme] = useState<ThemeMode>('light');\n\n"
            "  useEffect(() => {\n"
            "    const stored = window.localStorage.getItem('ops-theme');\n"
            "    const resolved = stored === 'dark' ? 'dark' : 'light';\n"
            "    setTheme(resolved);\n"
            "    applyTheme(resolved);\n"
            "  }, []);\n\n"
            "  const updateTheme = (nextTheme: ThemeMode) => {\n"
            "    setTheme(nextTheme);\n"
            "    applyTheme(nextTheme);\n"
            "  };\n\n"
            "  return (\n"
            "    <div className=\"themeToggle\">\n"
            "      <button type=\"button\" className={theme === 'light' ? 'themeChip is-active' : 'themeChip'} onClick={() => updateTheme('light')}>Light</button>\n"
            "      <button type=\"button\" className={theme === 'dark' ? 'themeChip is-active' : 'themeChip'} onClick={() => updateTheme('dark')}>Dark</button>\n"
            "    </div>\n"
            "  );\n"
            "}\n"
        ),
        "lib/types.ts": (
            "export interface DashboardSummary {\n"
            "  eyebrow: string;\n"
            "  headline: string;\n"
            "  badge: string;\n"
            "  description: string;\n"
            "  highlights: string[];\n"
            "  primaryLabel: string;\n"
            "  primaryHref: string;\n"
            "  secondaryLabel: string;\n"
            "  secondaryHref: string;\n"
            "}\n\n"
            "export interface SummaryMetric {\n"
            "  label: string;\n"
            "  value: string;\n"
            "  detail: string;\n"
            "}\n\n"
            "export interface RuntimeSignal {\n"
            "  label: string;\n"
            "  status: string;\n"
            "  detail: string;\n"
            "  owner: string;\n"
            "  tone: 'healthy' | 'watch' | 'planning';\n"
            "}\n\n"
            "export interface FocusItem {\n"
            "  title: string;\n"
            "  summary: string;\n"
            "  owner: string;\n"
            "}\n\n"
            "export interface BriefPayload {\n"
            "  summary: DashboardSummary;\n"
            "  metrics: SummaryMetric[];\n"
            "  runtimeSignals: RuntimeSignal[];\n"
            "  focusRail: FocusItem[];\n"
            "  releaseTimeline: string[];\n"
            "  refreshedAt: string;\n"
            "}\n"
        ),
        "lib/data.ts": (
            "import type { BriefPayload, DashboardSummary, FocusItem, RuntimeSignal, SummaryMetric } from './types';\n\n"
            "export const dashboardSummary: DashboardSummary = {\n"
            "  eyebrow: 'Operations canvas',\n"
            "  headline: 'Release confidence with visible ownership.',\n"
            "  badge: 'Template 2026.03',\n"
            "  description: 'The generated dashboard acts like an editorial control room: planning context, runtime signals, and ship-readiness cues all sit in one deliberately designed surface.',\n"
            "  highlights: [\n"
            "    'Planning, validation, and release ownership are separated into clear lanes instead of one noisy feed.',\n"
            "    'Each runtime card explains the operational meaning, not only the current color.',\n"
            "    'Landing and dashboard surfaces share one data contract so the generated output remains deterministic.',\n"
            "  ],\n"
            "  primaryLabel: 'Open dashboard',\n"
            "  primaryHref: '/dashboard',\n"
            "  secondaryLabel: 'Read live brief',\n"
            "  secondaryHref: '/api/brief',\n"
            "};\n\n"
            "export const summaryMetrics: SummaryMetric[] = [\n"
            "  { label: 'Evidence coverage', value: '92%', detail: 'Traceability rows already linked to implementation and validation artifacts.' },\n"
            "  { label: 'Runtime window', value: '14m', detail: 'Average time from checklist freeze to release handoff in the last dry-run.' },\n"
            "  { label: 'Approval delta', value: '+3', detail: 'Three ownership gaps were closed before the final shipment review.' },\n"
            "  { label: 'Recovery headroom', value: '2.4x', detail: 'Queue and incident buffers remain below the recovery escalation threshold.' },\n"
            "];\n\n"
            "export const runtimeSignals: RuntimeSignal[] = [\n"
            "  { label: 'Approval gate', status: 'Green and locked', detail: 'Completion and semantic gates passed with no missing release evidence.', owner: 'Reviewer', tone: 'healthy' },\n"
            "  { label: 'Queue watch', status: '6 tasks waiting', detail: 'Background queue remains under the recovery threshold with room for one more rollout.', owner: 'Runtime', tone: 'watch' },\n"
            "  { label: 'Brief posture', status: 'Ready for live handoff', detail: 'The release brief is already reduced to operator-facing language for the final check.', owner: 'Reasoner', tone: 'planning' },\n"
            "  { label: 'Evidence sync', status: 'Docs and code aligned', detail: 'The dashboard and route payloads use the same typed contract and update together.', owner: 'Planner', tone: 'healthy' },\n"
            "];\n\n"
            "export const focusRail: FocusItem[] = [\n"
            "  { title: 'Lock scope early', summary: 'Freeze the visible release promise before the implementation lane expands and turns into rework.', owner: 'Planner' },\n"
            "  { title: 'Explain runtime meaning', summary: 'Turn raw metrics into operator language so the release conversation stays decision-oriented.', owner: 'Reasoner' },\n"
            "  { title: 'Ship only with evidence', summary: 'Keep route checks, build output, and ownership traces attached to the final handoff packet.', owner: 'Reviewer' },\n"
            "];\n\n"
            "export const releaseTimeline = [\n"
            "  'Morning: freeze the change brief and confirm the live evidence packet.',\n"
            "  'Midday: compare dashboard payloads, queue state, and route contract drift.',\n"
            "  'Afternoon: finalize owner handoff notes, then ship from the same release canvas.',\n"
            "];\n\n"
            "export const defaultBriefPayload: BriefPayload = {\n"
            "  summary: dashboardSummary,\n"
            "  metrics: summaryMetrics,\n"
            "  runtimeSignals,\n"
            "  focusRail,\n"
            "  releaseTimeline,\n"
            "  refreshedAt: 'seeded-static-brief',\n"
            "};\n"
        ),
    }


def _build_node_service_vertical_slice_files(project_name: str) -> Dict[str, str]:
    return {
        "README.md": (
            f"# {project_name}\n\n"
            "Generated Node.js operational service scaffold.\n\n"
            "## Included layers\n\n"
            "- Express entrypoint and route composition\n"
            "- Controller, service, and repository boundaries\n"
            "- Runtime store abstraction and central error middleware\n"
            "- TypeScript build path ready for npm run build\n"
        ),
        "package.json": (
            "{\n"
            "  \"name\": \"generated-node-ops-service\",\n"
            "  \"private\": true,\n"
            "  \"type\": \"commonjs\",\n"
            "  \"scripts\": {\n"
            "    \"dev\": \"tsx src/index.ts\",\n"
            "    \"build\": \"tsc -p tsconfig.json\",\n"
            "    \"start\": \"node dist/index.js\"\n"
            "  },\n"
            "  \"dependencies\": {\n"
            "    \"express\": \"4.21.1\",\n"
            "    \"zod\": \"3.23.8\"\n"
            "  },\n"
            "  \"devDependencies\": {\n"
            "    \"@types/express\": \"5.0.0\",\n"
            "    \"@types/node\": \"20.17.6\",\n"
            "    \"tsx\": \"4.19.2\",\n"
            "    \"typescript\": \"5.6.3\"\n"
            "  }\n"
            "}\n"
        ),
        "tsconfig.json": (
            "{\n"
            "  \"compilerOptions\": {\n"
            "    \"target\": \"ES2022\",\n"
            "    \"module\": \"CommonJS\",\n"
            "    \"moduleResolution\": \"node\",\n"
            "    \"outDir\": \"dist\",\n"
            "    \"rootDir\": \"src\",\n"
            "    \"strict\": true,\n"
            "    \"esModuleInterop\": true,\n"
            "    \"resolveJsonModule\": true,\n"
            "    \"skipLibCheck\": true\n"
            "  },\n"
            "  \"include\": [\"src/**/*.ts\"],\n"
            "  \"exclude\": [\"node_modules\", \"dist\"]\n"
            "}\n"
        ),
        "src/types.ts": (
            "export interface OrderRecord {\n"
            "  id: string;\n"
            "  customer: string;\n"
            "  total: number;\n"
            "  status: 'queued' | 'approved' | 'shipped';\n"
            "}\n"
        ),
        "src/config.ts": (
            "export const config = {\n"
            "  serviceName: 'node-ops-service',\n"
            "  port: Number(process.env.PORT || 8080),\n"
            "  runtimeProfile: process.env.RUNTIME_PROFILE || 'local-deterministic',\n"
            "  secretKey: process.env.SECRET_KEY || '',\n"
            "};\n"
        ),
        "src/lib/runtimeStore.ts": (
            "import { config } from '../config';\n\n"
            "export function readRuntimeSummary() {\n"
            "  return {\n"
            "    profile: config.runtimeProfile,\n"
            "    readiness: 'ready',\n"
            "  };\n"
            "}\n"
        ),
        "src/repositories/orderRepository.ts": (
            "import type { OrderRecord } from '../types';\n\n"
            "const orders: OrderRecord[] = [\n"
            "  { id: 'ord-100', customer: 'metanova', total: 182000, status: 'approved' },\n"
            "  { id: 'ord-101', customer: 'pilot-lab', total: 94000, status: 'queued' },\n"
            "];\n\n"
            "export function listOrders(): OrderRecord[] {\n"
            "  return orders.map((order) => ({ ...order }));\n"
            "}\n\n"
            "export function findOrder(orderId: string): OrderRecord | undefined {\n"
            "  return orders.find((order) => order.id === orderId);\n"
            "}\n"
        ),
        "src/services/orderService.ts": (
            "import { findOrder, listOrders } from '../repositories/orderRepository';\n"
            "import { readRuntimeSummary } from '../lib/runtimeStore';\n\n"
            "export function buildHealthPayload() {\n"
            "  return {\n"
            "    ok: true,\n"
            "    service: 'go-ops-service',\n"
            "    timestamp: new Date().toISOString(),\n"
            "    runtime: readRuntimeSummary(),\n"
            "  };\n"
            "}\n\n"
            "export function listOperationalOrders() {\n"
            "  return {\n"
            "    runtime: readRuntimeSummary(),\n"
            "    items: listOrders(),\n"
            "  };\n"
            "}\n\n"
            "export function readOperationalOrder(orderId: string) {\n"
            "  const order = findOrder(orderId);\n"
            "  if (!order) {\n"
            "    return null;\n"
            "  }\n"
            "  return {\n"
            "    order,\n"
            "    runtime: readRuntimeSummary(),\n"
            "    nextStep: order.status === 'queued' ? 'review-and-approve' : 'handoff-ready',\n"
            "  };\n"
            "}\n"
        ),
        "src/http/handlers/health.go": (
            "package handlers\n\n"
            "import (\n"
            "\t\"encoding/json\"\n"
            "\t\"net/http\"\n"
            "\t\"generated/service/internal/service\"\n"
            ")\n\n"
            "type HealthHandler struct {\n"
            "\tservice service.InventoryService\n"
            "}\n\n"
            "func NewHealthHandler(service service.InventoryService) HealthHandler {\n"
            "\treturn HealthHandler{service: service}\n"
            "}\n\n"
            "func (handler HealthHandler) ServeHTTP(writer http.ResponseWriter, _ *http.Request) {\n"
            "\twriter.Header().Set(\"Content-Type\", \"application/json\")\n"
            "\t_ = json.NewEncoder(writer).Encode(handler.service.HealthPayload())\n"
            "}\n"
        ),
        "src/http/handlers/inventory.go": (
            "package handlers\n\n"
            "import (\n"
            "\t\"encoding/json\"\n"
            "\t\"net/http\"\n"
            "\t\"generated/service/internal/service\"\n"
            ")\n\n"
            "type InventoryHandler struct {\n"
            "\tservice service.InventoryService\n"
            "}\n\n"
            "func NewInventoryHandler(service service.InventoryService) InventoryHandler {\n"
            "\treturn InventoryHandler{service: service}\n"
            "}\n\n"
            "func (handler InventoryHandler) ServeHTTP(writer http.ResponseWriter, _ *http.Request) {\n"
            "\twriter.Header().Set(\"Content-Type\", \"application/json\")\n"
            "\t_ = json.NewEncoder(writer).Encode(handler.service.InventoryPayload())\n"
            "}\n"
        ),
        "src/http/router.go": (
            "package httpapi\n\n"
            "import (\n"
            "\t\"net/http\"\n"
            "\t\"generated/service/internal/http/handlers\"\n"
            "\t\"generated/service/internal/repository\"\n"
            "\t\"generated/service/internal/service\"\n"
            ")\n\n"
            "func NewRouter() http.Handler {\n"
            "\trepo := repository.NewInventoryRepository()\n"
            "\tserviceLayer := service.NewInventoryService(repo)\n"
            "\tmux := http.NewServeMux()\n"
            "\tmux.Handle(\"/health\", handlers.NewHealthHandler(serviceLayer))\n"
            "\tmux.Handle(\"/inventory\", handlers.NewInventoryHandler(serviceLayer))\n"
            "\treturn mux\n"
            "}\n"
        ),
    }

