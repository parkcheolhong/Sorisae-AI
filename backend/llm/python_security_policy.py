"""Python 보안 정책 점검 도구.

오케스트레이터 생성 산출물과 현재 백엔드 코드를 같은 기준으로 검사하기 위한
공용 스캐너다.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_EXCLUDED_DIR_NAMES = {
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "node_modules",
    "uploads",
    "models",
    "archive",
}
SECRET_NAME_TOKENS = (
    "secret",
    "password",
    "passwd",
    "api_key",
    "access_key",
    "private_key",
    "client_secret",
    "webhook_secret",
)
SECRET_NAME_EXACT = {
    "token",
    "github_token",
    "access_token",
    "refresh_token",
    "bearer_token",
}
NON_SECRET_NAME_MARKERS = (
    "expire",
    "expiry",
    "expiration",
    "minute",
    "minutes",
    "hour",
    "hours",
    "ttl",
    "timeout",
    "max",
    "count",
    "type",
    "tuning",
    "level",
    "budget",
    "limit",
)
WEAK_SECRET_MARKERS = (
    "change-me",
    "changeme",
    "change_in_production",
    "change-in-production",
    "default",
    "demo",
    "test",
    "local-secret",
    "devanalysis114-secret-key-change-in-production",
    "sk_test_",
)
BLOCKED_CALL_NAMES = {"eval", "exec", "os.system"}
BLOCKED_DESERIALIZATION_CALLS = {
    "pickle.load",
    "pickle.loads",
    "dill.load",
    "dill.loads",
    "marshal.load",
    "marshal.loads",
    "shelve.open",
}
WEAK_HASH_CALLS = {"hashlib.md5", "hashlib.sha1", "md5", "sha1"}
UNSAFE_YAML_LOADERS = {
    "yaml.Loader",
    "yaml.UnsafeLoader",
    "Loader",
    "UnsafeLoader",
}
SAFE_YAML_LOADERS = {
    "yaml.SafeLoader",
    "yaml.CSafeLoader",
    "SafeLoader",
    "CSafeLoader",
}


def _relative_display(path: Path, base_dir: Path) -> str:
    try:
        return str(path.relative_to(base_dir)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _attr_chain(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _attr_chain(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _attr_chain(node.func)
    return ""


def _string_value(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _secret_like_name(name: str) -> bool:
    lowered = str(name or "").strip().lower().replace("-", "_")
    if not lowered:
        return False
    if lowered.endswith("_env") or lowered.endswith("_envs"):
        return False
    if lowered in {"token_type", "access_token_expire_minutes"}:
        return False
    if any(marker in lowered for marker in NON_SECRET_NAME_MARKERS):
        return False
    if lowered in SECRET_NAME_EXACT or lowered.endswith("_token"):
        return True
    return any(token in lowered for token in SECRET_NAME_TOKENS)


def _weak_secret_value(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    if len(lowered) < 16:
        return True
    return any(marker in lowered for marker in WEAK_SECRET_MARKERS)


def _iter_python_files(
    base_dir: Path,
    excluded_dir_names: Iterable[str],
) -> Iterable[Path]:
    excluded = set(excluded_dir_names)
    for path in base_dir.rglob("*.py"):
        if any(part in excluded for part in path.parts):
            continue
        yield path


def _build_finding(
    findings: List[Dict[str, Any]],
    *,
    severity: str,
    rule_id: str,
    message: str,
    path: str,
    line: int,
    evidence: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "rule_id": rule_id,
            "message": message,
            "path": path,
            "line": line,
            "evidence": evidence,
        }
    )


def _scan_python_file(file_path: Path, base_dir: Path) -> Dict[str, Any]:
    rel_path = _relative_display(file_path, base_dir)
    findings: List[Dict[str, Any]] = []
    source = file_path.read_text(encoding="utf-8-sig", errors="ignore")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        _build_finding(
            findings,
            severity="error",
            rule_id="python_syntax",
            message="보안 정책 점검 전 Python 구문 해석에 실패했습니다.",
            path=rel_path,
            line=int(getattr(exc, "lineno", 0) or 0),
            evidence=str(exc.msg or "syntax error"),
        )
        return {"path": rel_path, "findings": findings}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _attr_chain(node.func)
            if call_name in BLOCKED_CALL_NAMES:
                _build_finding(
                    findings,
                    severity="error",
                    rule_id="blocked_runtime_execution",
                    message="직접 코드 실행 계열 호출은 자동 생성 기준에서 금지됩니다.",
                    path=rel_path,
                    line=int(getattr(node, "lineno", 0) or 0),
                    evidence=call_name,
                )
            if call_name in BLOCKED_DESERIALIZATION_CALLS:
                _build_finding(
                    findings,
                    severity="error",
                    rule_id="unsafe_deserialization",
                    message="신뢰되지 않은 입력에 취약한 역직렬화 호출이 감지되었습니다.",
                    path=rel_path,
                    line=int(getattr(node, "lineno", 0) or 0),
                    evidence=call_name,
                )
            if call_name.startswith("subprocess."):
                for keyword in node.keywords:
                    if (
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ):
                        _build_finding(
                            findings,
                            severity="error",
                            rule_id="subprocess_shell_true",
                            message="subprocess 계열 호출에서 shell=True 사용은 금지됩니다.",
                            path=rel_path,
                            line=int(getattr(node, "lineno", 0) or 0),
                            evidence=call_name,
                        )
            if call_name in WEAK_HASH_CALLS:
                _build_finding(
                    findings,
                    severity="warning",
                    rule_id="weak_hash_algorithm",
                    message="보안 용도로 오해될 수 있는 약한 해시 알고리즘이 감지되었습니다.",
                    path=rel_path,
                    line=int(getattr(node, "lineno", 0) or 0),
                    evidence=call_name,
                )
            if call_name == "yaml.load":
                loader_name = ""
                for keyword in node.keywords:
                    if keyword.arg == "Loader":
                        loader_name = _attr_chain(keyword.value)
                        break
                if not loader_name or loader_name in UNSAFE_YAML_LOADERS:
                    _build_finding(
                        findings,
                        severity="error",
                        rule_id="unsafe_yaml_loader",
                        message="yaml.load 는 SafeLoader 계열 없이 사용할 수 없습니다.",
                        path=rel_path,
                        line=int(getattr(node, "lineno", 0) or 0),
                        evidence=loader_name or "Loader 미지정",
                    )
                elif loader_name not in SAFE_YAML_LOADERS:
                    _build_finding(
                        findings,
                        severity="warning",
                        rule_id="unknown_yaml_loader",
                        message="yaml.load 가 허용 목록 밖 Loader 로 호출되었습니다.",
                        path=rel_path,
                        line=int(getattr(node, "lineno", 0) or 0),
                        evidence=loader_name,
                    )
            if call_name == "os.getenv" and len(node.args) >= 2:
                env_name = _string_value(node.args[0]) or ""
                default_value = _string_value(node.args[1])
                if (
                    _secret_like_name(env_name)
                    and default_value
                    and _weak_secret_value(default_value)
                ):
                    _build_finding(
                        findings,
                        severity="error",
                        rule_id="weak_secret_fallback",
                        message="비밀값 환경변수에 약한 기본 fallback 이 설정되었습니다.",
                        path=rel_path,
                        line=int(getattr(node, "lineno", 0) or 0),
                        evidence=f"{env_name}={default_value}",
                    )

        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value_node = node.value
            if value_node is None:
                continue
            targets: List[ast.AST] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            else:
                targets = [node.target]
            literal = _string_value(value_node)
            if literal is None:
                continue
            for target in targets:
                target_name = _attr_chain(target)
                if (
                    _secret_like_name(target_name)
                    and _weak_secret_value(literal)
                ):
                    _build_finding(
                        findings,
                        severity="error",
                        rule_id="hardcoded_weak_secret",
                        message="비밀값으로 보이는 항목에 약한 하드코딩 값이 감지되었습니다.",
                        path=rel_path,
                        line=int(getattr(node, "lineno", 0) or 0),
                        evidence=f"{target_name}={literal}",
                    )

    return {"path": rel_path, "findings": findings}


def scan_python_security_policy(
    base_dir: Path,
    *,
    excluded_dir_names: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    target_dir = Path(base_dir)
    excluded = tuple(excluded_dir_names or DEFAULT_EXCLUDED_DIR_NAMES)
    files = list(_iter_python_files(target_dir, excluded))
    findings: List[Dict[str, Any]] = []
    per_file: List[Dict[str, Any]] = []

    for file_path in files:
        file_result = _scan_python_file(file_path, target_dir)
        per_file.append(file_result)
        findings.extend(file_result["findings"])

    error_count = sum(1 for item in findings if item["severity"] == "error")
    warning_count = sum(
        1 for item in findings if item["severity"] == "warning"
    )
    ok = error_count == 0
    logs = [
        f"[python-security] files_total={len(files)}",
        f"[python-security] findings_total={len(findings)}",
        f"[python-security] errors={error_count}",
        f"[python-security] warnings={warning_count}",
    ]
    for item in findings[:20]:
        logs.append(
            "[python-security] "
            + f"{item['severity']} {item['rule_id']} "
            + f"{item['path']}:{item['line']} | {item['message']} | "
            + f"{item['evidence']}"
        )

    return {
        "ok": ok,
        "files_total": len(files),
        "findings_total": len(findings),
        "error_count": error_count,
        "warning_count": warning_count,
        "findings": findings,
        "per_file": per_file,
        "logs": logs,
    }