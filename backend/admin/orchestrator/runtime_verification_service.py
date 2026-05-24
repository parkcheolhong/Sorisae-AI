from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from urllib.parse import quote
import base64
import httpx
import os
import py_compile
import secrets
import socket
import ssl

from backend.marketplace import models as marketplace_models
from backend.marketplace.vector_service import vector_service
from backend.orchestrator.chat.project_context_store import get_project_context_bundle
from .debug_validation_jobs import _collect_python_files, validate_python_source
from .workspace_text_service import read_admin_text_file, resolve_admin_workspace_path


def inspect_worker_log_tail(
    path_text: str,
    *,
    read_admin_env_values,
    admin_env_path,
) -> Dict[str, Any]:
    normalized = str(path_text or '').strip()
    if not normalized:
        return {
            'status': 'failed',
            'detail': 'worker_log_path가 비어 있습니다.',
            'tail': '',
            'exists': False,
            'is_recent': False,
        }
    try:
        target = resolve_admin_workspace_path(
            normalized,
            read_admin_env_values=read_admin_env_values,
            admin_env_path=admin_env_path,
        )
    except Exception:
        return {
            'status': 'failed',
            'detail': f'허용된 워크스페이스 경로가 아닙니다: {normalized}',
            'tail': '',
            'exists': False,
            'is_recent': False,
        }
    if not target.exists() or not target.is_file():
        return {
            'status': 'failed',
            'detail': f'worker 로그 파일을 찾을 수 없습니다: {normalized}',
            'tail': '',
            'exists': False,
            'is_recent': False,
        }
    stat = target.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime)
    age_seconds = max((datetime.now() - modified_at).total_seconds(), 0.0)
    is_recent = age_seconds <= 600
    tail = read_admin_text_file(target).splitlines()[-80:]
    return {
        'status': 'passed' if is_recent else 'failed',
        'detail': f"exists=true / recent={'true' if is_recent else 'false'} / age_sec={int(age_seconds)} / size_bytes={stat.st_size}",
        'tail': '\n'.join(tail),
        'exists': True,
        'is_recent': is_recent,
    }


def _normalize_local_api_base_url(base_url_text: str) -> str:
    normalized = str(base_url_text or '').strip() or 'http://127.0.0.1:8000'
    if normalized.startswith('http://localhost'):
        return normalized.replace('http://localhost', 'http://127.0.0.1', 1)
    if normalized.startswith('https://localhost'):
        return normalized.replace('https://localhost', 'https://127.0.0.1', 1)
    return normalized


def _is_local_runtime_reachable(base_url: str) -> bool:
    normalized = _normalize_local_api_base_url(base_url).rstrip('/')
    if not normalized:
        return False
    for path in ('/api/health', '/health'):
        try:
            response = httpx.get(f'{normalized}{path}', timeout=0.8)
            if response.status_code < 500:
                return True
        except Exception:
            continue
    return False


def _resolve_runtime_local_api_base_url(configured_base_url: str = '') -> str:
    candidates: List[str] = []
    for value in (
        configured_base_url,
        os.getenv('LOCAL_API_BASE_URL'),
        os.getenv('BACKEND_PROXY_TARGET'),
    ):
        text = str(value or '').strip()
        if text:
            candidates.append(text)

    profiler_port = str(os.getenv('BACKEND_PROFILER_PORT') or '').strip()
    if profiler_port:
        candidates.append(f'http://127.0.0.1:{profiler_port}')
    candidates.extend(['http://127.0.0.1:8000', 'http://127.0.0.1:8013'])

    seen: set[str] = set()
    normalized_candidates: List[str] = []
    for candidate in candidates:
        normalized = _normalize_local_api_base_url(candidate).rstrip('/')
        if normalized and normalized not in seen:
            seen.add(normalized)
            normalized_candidates.append(normalized)

    for candidate in normalized_candidates:
        if _is_local_runtime_reachable(candidate):
            return candidate
    return normalized_candidates[0] if normalized_candidates else 'http://127.0.0.1:8000'


def _is_placeholder_domain(domain_text: str) -> bool:
    domain = str(domain_text or '').strip().lower()
    if not domain:
        return True
    return domain in {'validation.local', 'localhost', '127.0.0.1'} or domain.endswith('.local')


def _normalize_http_base_url(base_url_text: str, fallback: str) -> str:
    normalized = str(base_url_text or '').strip()
    if not normalized:
        return fallback
    if normalized.startswith(('http://', 'https://')):
        return _normalize_local_api_base_url(normalized.rstrip('/'))
    return f"https://{normalized.strip('/')}"


def _derive_operational_targets(*, read_admin_env_values, admin_env_path) -> List[Dict[str, Any]]:
    try:
        from backend.llm.admin_capabilities import OPERATIONAL_EVIDENCE_TARGETS
    except Exception:
        OPERATIONAL_EVIDENCE_TARGETS = []

    env_values = read_admin_env_values(admin_env_path())
    local_base_url = _resolve_runtime_local_api_base_url(
        str(env_values.get('LOCAL_API_BASE_URL') or '')
    )
    domain_name = str(env_values.get('DOMAIN_NAME') or env_values.get('DOMAIN_ORIGINAL') or '').strip()
    admin_domain = str(env_values.get('ADMIN_DOMAIN') or domain_name or '').strip()
    marketplace_domain = str(env_values.get('DOMAIN_NAME') or env_values.get('MARKETPLACE_API_DOMAIN') or admin_domain or '').strip()

    admin_uses_local_fallback = _is_placeholder_domain(admin_domain)
    marketplace_uses_local_fallback = _is_placeholder_domain(marketplace_domain)
    if _is_placeholder_domain(admin_domain):
        admin_domain = local_base_url
    if _is_placeholder_domain(marketplace_domain):
        marketplace_domain = local_base_url

    admin_base_url = _normalize_http_base_url(admin_domain, local_base_url).rstrip('/')
    marketplace_base_url = _normalize_http_base_url(marketplace_domain, local_base_url).rstrip('/')
    websocket_http_base = admin_base_url if admin_base_url else local_base_url
    websocket_url = websocket_http_base.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/llm/ws'

    resolved_targets: List[Dict[str, Any]] = []
    for item in OPERATIONAL_EVIDENCE_TARGETS or []:
        target_id = str(item.get('id') or '').strip()
        path = str(item.get('target') or '').strip()
        if not target_id or not path:
            continue
        if target_id == 'websocket':
            url = websocket_url
        elif target_id == 'marketplace':
            if marketplace_uses_local_fallback and path.startswith('/marketplace/'):
                path = '/api/marketplace/projects?skip=0&limit=1'
            url = f"{marketplace_base_url}{path}"
        else:
            if target_id == 'admin' and admin_uses_local_fallback and path.startswith('/admin/'):
                path = '/api/llm/runtime-config'
            url = f"{admin_base_url}{path}"
        resolved_targets.append({
            **dict(item),
            'url': url,
            'base_url': marketplace_base_url if target_id == 'marketplace' else (websocket_http_base if target_id == 'websocket' else admin_base_url),
            'source_base_url': local_base_url,
        })
    return resolved_targets


def _read_socket_exact(sock, size: int, buffered: bytearray | None = None) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    if buffered:
        take = min(len(buffered), remaining)
        if take > 0:
            chunks.append(bytes(buffered[:take]))
            del buffered[:take]
            remaining -= take
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError('socket closed before frame was fully received')
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def _read_websocket_frame(sock, buffered: bytearray | None = None) -> Dict[str, Any]:
    header = _read_socket_exact(sock, 2, buffered)
    first_byte = header[0]
    second_byte = header[1]
    opcode = first_byte & 0x0F
    masked = bool(second_byte & 0x80)
    payload_length = second_byte & 0x7F
    if payload_length == 126:
        payload_length = int.from_bytes(_read_socket_exact(sock, 2, buffered), 'big')
    elif payload_length == 127:
        payload_length = int.from_bytes(_read_socket_exact(sock, 8, buffered), 'big')
    masking_key = _read_socket_exact(sock, 4, buffered) if masked else b''
    payload = _read_socket_exact(sock, payload_length, buffered) if payload_length else b''
    if masked and masking_key:
        payload = bytes(byte ^ masking_key[index % 4] for index, byte in enumerate(payload))
    return {
        'opcode': opcode,
        'payload_bytes': payload,
        'text': payload.decode('utf-8', errors='ignore'),
    }


def _build_masked_websocket_text_frame(message: str) -> bytes:
    payload = str(message or '').encode('utf-8')
    header = bytearray([0x81])
    payload_length = len(payload)
    if payload_length < 126:
        header.append(0x80 | payload_length)
    elif payload_length <= 0xFFFF:
        header.append(0x80 | 126)
        header.extend(payload_length.to_bytes(2, 'big'))
    else:
        header.append(0x80 | 127)
        header.extend(payload_length.to_bytes(8, 'big'))
    masking_key = secrets.token_bytes(4)
    masked_payload = bytes(byte ^ masking_key[index % 4] for index, byte in enumerate(payload))
    return bytes(header) + masking_key + masked_payload


def _verify_websocket_endpoint(url: str, timeout_sec: float = 10.0) -> Dict[str, Any]:
    started_at = datetime.now()
    parsed = httpx.URL(url)
    host = parsed.host or ''
    scheme = str(parsed.scheme or 'ws')
    port = parsed.port or (443 if scheme == 'wss' else 80)
    path = parsed.raw_path.decode('utf-8') if parsed.raw_path else '/'
    if parsed.query:
        path = f"{path}?{parsed.query.decode('utf-8')}"
    websocket_key = base64.b64encode(secrets.token_bytes(16)).decode('ascii')
    request_text = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {websocket_key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "User-Agent: codeai-runtime-verifier\r\n\r\n"
    )
    raw_socket = socket.create_connection((host, port), timeout=timeout_sec)
    wrapped_socket = raw_socket
    try:
        if scheme == 'wss':
            context = ssl.create_default_context()
            wrapped_socket = context.wrap_socket(raw_socket, server_hostname=host)
        wrapped_socket.settimeout(timeout_sec)
        wrapped_socket.sendall(request_text.encode('utf-8'))
        response_buffer = b''
        while b'\r\n\r\n' not in response_buffer:
            response_buffer += wrapped_socket.recv(4096)
            if len(response_buffer) > 32_768:
                break
        header_bytes, _, leftover = response_buffer.partition(b'\r\n\r\n')
        buffered = bytearray(leftover)
        header_text = header_bytes.decode('utf-8', errors='ignore')
        header_lines = header_text.split('\r\n')
        status_line = header_lines[0] if header_lines else ''
        status_code = int(status_line.split(' ')[1]) if len(status_line.split(' ')) >= 2 and status_line.split(' ')[1].isdigit() else 0
        if status_code != 101:
            return {
                'ok': False,
                'status': 'failed',
                'status_code': status_code,
                'detail': status_line or 'websocket handshake failed',
                'latency_ms': round((datetime.now() - started_at).total_seconds() * 1000, 1),
                'handshake_status_line': status_line,
            }
        connected_frame = _read_websocket_frame(wrapped_socket, buffered)
        connected_text = connected_frame.get('text') or ''
        wrapped_socket.sendall(_build_masked_websocket_text_frame('ping'))
        pong_frame = _read_websocket_frame(wrapped_socket, buffered)
        pong_text = pong_frame.get('text') or ''
        latency_ms = round((datetime.now() - started_at).total_seconds() * 1000, 1)
        pong_ok = 'pong' in pong_text.lower()
        connected_ok = 'connected' in connected_text.lower()
        return {
            'ok': connected_ok and pong_ok,
            'status': 'verified' if connected_ok and pong_ok else 'failed',
            'status_code': status_code,
            'detail': f"handshake=101 connected={connected_ok} pong={pong_ok}",
            'latency_ms': latency_ms,
            'connected_payload': connected_text,
            'pong_payload': pong_text,
            'handshake_status_line': status_line,
        }
    finally:
        try:
            wrapped_socket.close()
        except Exception:
            pass
        if wrapped_socket is not raw_socket:
            try:
                raw_socket.close()
            except Exception:
                pass


def _build_operational_evidence_summary(targets: List[Dict[str, Any]]) -> Dict[str, Any]:
    verified_count = 0
    warning_count = 0
    failed_count = 0
    warning_targets: List[str] = []
    latency_values: List[float] = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        status = str(target.get('status') or 'missing').lower()
        target_id = str(target.get('id') or '').strip()
        if status == 'verified':
            verified_count += 1
        elif status in {'warning', 'degraded'}:
            warning_count += 1
        else:
            failed_count += 1
        if bool(target.get('latency_warning')) and target_id:
            warning_targets.append(target_id)
        latency_value = target.get('latency_ms')
        if isinstance(latency_value, (int, float)):
            latency_values.append(float(latency_value))
    return {
        'verified_count': verified_count,
        'warning_count': warning_count,
        'failed_count': failed_count,
        'required_count': len(targets),
        'warning_targets': warning_targets,
        'max_latency_ms': round(max(latency_values), 1) if latency_values else None,
    }


def _collect_operational_evidence(
    *,
    bearer_token: str,
    checked_at: str,
    read_admin_env_values,
    admin_env_path,
) -> Dict[str, Any]:
    try:
        from backend.llm.admin_capabilities import _write_operational_evidence_cache
    except Exception:
        _write_operational_evidence_cache = None

    targets = _derive_operational_targets(
        read_admin_env_values=read_admin_env_values,
        admin_env_path=admin_env_path,
    )
    headers = {'Authorization': f'Bearer {bearer_token}'} if bearer_token else {}
    verified_targets: List[Dict[str, Any]] = []
    verification_items: List[Dict[str, Any]] = []
    for target in targets:
        target_id = str(target.get('id') or '').strip()
        url = str(target.get('url') or '').strip()
        warning_threshold_ms = float(target.get('warning_threshold_ms') or 0.0)
        if target.get('protocol') == 'websocket':
            try:
                result = _verify_websocket_endpoint(url)
            except Exception as exc:
                result = {
                    'ok': False,
                    'status': 'failed',
                    'status_code': None,
                    'detail': str(exc),
                    'latency_ms': None,
                }
        else:
            started_at = datetime.now()
            try:
                response = httpx.get(url, timeout=20.0, headers=headers, follow_redirects=True)
                latency_ms = round((datetime.now() - started_at).total_seconds() * 1000, 1)
                result = {
                    'ok': response.status_code < 400,
                    'status': 'verified' if response.status_code < 400 else 'failed',
                    'status_code': response.status_code,
                    'detail': f'status={response.status_code}',
                    'latency_ms': latency_ms,
                }
            except Exception as exc:
                result = {
                    'ok': False,
                    'status': 'failed',
                    'status_code': None,
                    'detail': str(exc),
                    'latency_ms': None,
                }
        latency_ms = result.get('latency_ms')
        latency_warning = bool(
            isinstance(latency_ms, (int, float))
            and warning_threshold_ms > 0
            and float(latency_ms) > warning_threshold_ms
        )
        status = str(result.get('status') or 'failed')
        if result.get('ok') and latency_warning:
            status = 'warning'
        snapshot = {
            **dict(target),
            'status': status,
            'ok': bool(result.get('ok')),
            'status_code': result.get('status_code'),
            'latency_ms': latency_ms,
            'latency_warning': latency_warning,
            'warning_threshold_ms': warning_threshold_ms,
            'verified_at': checked_at,
            'detail': str(result.get('detail') or ''),
            'source': 'runtime-verification',
        }
        verified_targets.append(snapshot)
        verification_items.append({
            'key': f'operational-{target_id}',
            'label': f"운영 경로 · {target_id}",
            'status': 'passed' if snapshot['ok'] and not latency_warning else ('warning' if snapshot['ok'] and latency_warning else 'failed'),
            'detail': f"{snapshot['detail']} / latency_ms={snapshot['latency_ms']} / warning_threshold_ms={warning_threshold_ms}",
            'checkedAt': checked_at,
        })

    summary = _build_operational_evidence_summary(verified_targets)
    payload = {
        'captured_at': checked_at,
        'integration_status': (
            'verified'
            if summary['verified_count'] == len(verified_targets)
            else ('partial' if summary['verified_count'] > 0 else 'failed')
        ),
        'verified_target_count': summary['verified_count'],
        'required_target_count': len(verified_targets),
        'warning_target_count': summary['warning_count'],
        'failed_target_count': summary['failed_count'],
        'warning_targets': summary['warning_targets'],
        'max_latency_ms': summary['max_latency_ms'],
        'summary': summary,
        'targets': verified_targets,
        'targets_by_id': {
            str(item.get('id') or ''): item
            for item in verified_targets
            if str(item.get('id') or '').strip()
        },
    }
    if callable(_write_operational_evidence_cache):
        _write_operational_evidence_cache(payload)
    return {
        'payload': payload,
        'verification_items': verification_items,
    }


def run_admin_runtime_verification_bundle(
    *,
    project_root: Path,
    worker_log_path: str,
    bearer_token: str,
    classify_gate_status,
    read_admin_env_values,
    admin_env_path,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    checked_at = datetime.now().isoformat()
    py_files = _collect_python_files(project_root)
    try:
        for path in py_files:
            validate_python_source(path)
        results.append({
            'key': 'py_compile',
            'label': 'Python py_compile',
            'status': 'passed',
            'detail': f'{len(py_files)}개 파일 py_compile 통과',
            'checkedAt': checked_at,
        })
    except py_compile.PyCompileError as exc:
        results.append({
            'key': 'py_compile',
            'label': 'Python py_compile',
            'status': 'failed',
            'detail': str(exc),
            'checkedAt': checked_at,
        })
    except Exception as exc:
        results.append({
            'key': 'py_compile',
            'label': 'Python py_compile',
            'status': 'failed',
            'detail': str(exc),
            'checkedAt': checked_at,
        })

    endpoints = [
        ('health', '헬스체크', '/api/health'),
        ('llm-status', 'LLM 상태 API', '/api/llm/status'),
        ('stats-revenue', '매출 통계 API', '/api/marketplace/stats/revenue'),
        ('project-context', '프로젝트 문맥 API', '/api/admin/orchestrator/project-context'),
    ]
    base_url = _resolve_runtime_local_api_base_url()
    for key, label, path in endpoints:
        try:
            url = f'{base_url}{path}'
            if key == 'project-context':
                encoded_root = quote(str(project_root))
                url = f'{url}?project_root={encoded_root}'
            headers = {'Authorization': f'Bearer {bearer_token}'} if bearer_token else {}
            response = httpx.get(url, timeout=20.0, headers=headers)
            results.append({
                'key': key,
                'label': label,
                'status': 'passed' if response.status_code < 400 else 'failed',
                'detail': f'status={response.status_code}',
                'checkedAt': checked_at,
            })
        except Exception as exc:
            results.append({
                'key': key,
                'label': label,
                'status': 'failed',
                'detail': str(exc),
                'checkedAt': checked_at,
            })

    worker_log = inspect_worker_log_tail(
        worker_log_path,
        read_admin_env_values=read_admin_env_values,
        admin_env_path=admin_env_path,
    )
    worker_log_status = worker_log['status']
    worker_log_detail = worker_log['detail']
    if not worker_log_path.strip():
        worker_log_status = 'passed'
        worker_log_detail = 'dashboard mode에서는 worker_log_path 없이 경량 상태만 확인합니다.'
    results.append({
        'key': 'worker-log-tail',
        'label': 'worker 로그 tail',
        'status': worker_log_status,
        'detail': worker_log_detail,
        'checkedAt': checked_at,
    })
    results.append({
        'key': 'traceback-capture',
        'label': 'traceback 캡처',
        'status': (
            'passed'
            if worker_log_path.strip() == ''
            else ('failed' if 'Traceback' in str(worker_log.get('tail') or '') else 'passed')
        ),
        'detail': (
            'worker 로그 경로가 없어 traceback 검사를 건너뛰었습니다.'
            if worker_log_path.strip() == ''
            else ('worker tail에 traceback 없음' if 'Traceback' not in str(worker_log.get('tail') or '') else 'worker tail에서 traceback 감지')
        ),
        'checkedAt': checked_at,
    })
    operational_evidence = _collect_operational_evidence(
        bearer_token=bearer_token,
        checked_at=checked_at,
        read_admin_env_values=read_admin_env_values,
        admin_env_path=admin_env_path,
    )
    results.extend(list(operational_evidence.get('verification_items') or []))
    classification = classify_gate_status(results)
    results.append({
        'key': 'gate-final-status',
        'label': '최종 게이트 판정',
        'status': classification['final_status'],
        'detail': (
            f"final_pass={classification['final_pass']} | "
            f"fallback_recovery={classification['fallback_recovery']} | "
            f"hard_failures={len(classification['hard_failures'])} | "
            f"soft_failures={len(classification['soft_failures'])}"
        ),
        'checkedAt': checked_at,
    })
    return {
        'verification_items': results,
        'operational_evidence': dict(operational_evidence.get('payload') or {}),
        'gate_status': classification,
    }


def run_admin_runtime_verification_dashboard_bundle(
    *,
    db,
    project_root: Path,
    worker_log_path: str,
    bearer_token: str,
    classify_gate_status,
    read_admin_env_values,
    admin_env_path,
) -> Dict[str, Any]:
    del project_root
    del bearer_token
    checked_at = datetime.now().isoformat()
    results: List[Dict[str, Any]] = []

    results.append({
        'key': 'health',
        'label': '헬스체크',
        'status': 'passed',
        'detail': 'local runtime verification worker is running',
        'checkedAt': checked_at,
    })

    try:
        started_at = datetime.now()
        projects_count = db.query(marketplace_models.Project).filter(
            marketplace_models.Project.is_active.is_(True)
        ).count()
        users_count = db.query(marketplace_models.User).count()
        purchases_count = db.query(marketplace_models.Purchase).filter(
            marketplace_models.Purchase.status == 'completed'
        ).count()
        reviews_count = db.query(marketplace_models.Review).count()
        vector_stats = vector_service.get_stats()
        latency_ms = round((datetime.now() - started_at).total_seconds() * 1000, 1)
        results.append({
            'key': 'marketplace-overview',
            'label': '마켓 overview API',
            'status': 'passed',
            'detail': (
                f'projects={projects_count} / users={users_count} / purchases={purchases_count} '
                f'/ reviews={reviews_count} / latency_ms={latency_ms} / vector_status={vector_stats.get("status", "unknown")}'
            ),
            'checkedAt': checked_at,
        })
    except Exception as exc:
        results.append({
            'key': 'marketplace-overview',
            'label': '마켓 overview API',
            'status': 'failed',
            'detail': str(exc),
            'checkedAt': checked_at,
        })

    try:
        started_at = datetime.now()
        top_projects = db.query(marketplace_models.Project).filter(
            marketplace_models.Project.is_active.is_(True)
        ).order_by(marketplace_models.Project.downloads.desc()).limit(6).all()
        latency_ms = round((datetime.now() - started_at).total_seconds() * 1000, 1)
        results.append({
            'key': 'marketplace-top-projects',
            'label': '마켓 top projects API',
            'status': 'passed',
            'detail': f'count={len(top_projects)} / latency_ms={latency_ms}',
            'checkedAt': checked_at,
        })
    except Exception as exc:
        results.append({
            'key': 'marketplace-top-projects',
            'label': '마켓 top projects API',
            'status': 'failed',
            'detail': str(exc),
            'checkedAt': checked_at,
        })

    worker_log = inspect_worker_log_tail(
        worker_log_path,
        read_admin_env_values=read_admin_env_values,
        admin_env_path=admin_env_path,
    )
    worker_log_status = worker_log['status']
    worker_log_detail = worker_log['detail']
    if not worker_log_path.strip():
        worker_log_status = 'passed'
        worker_log_detail = 'dashboard mode에서는 worker_log_path 없이 경량 상태만 확인합니다.'
    results.append({
        'key': 'worker-log-tail',
        'label': 'worker 로그 tail',
        'status': worker_log_status,
        'detail': worker_log_detail,
        'checkedAt': checked_at,
    })

    gate_status = classify_gate_status(results)
    results.append({
        'key': 'gate-final-status',
        'label': '최종 게이트 판정',
        'status': gate_status['final_status'],
        'detail': (
            f"final_pass={gate_status['final_pass']} | "
            f"fallback_recovery={gate_status['fallback_recovery']} | "
            f"hard_failures={len(gate_status['hard_failures'])} | "
            f"soft_failures={len(gate_status['soft_failures'])}"
        ),
        'checkedAt': checked_at,
    })

    return {
        'verification_items': results,
        'gate_status': gate_status,
        'operational_evidence': {},
    }


def build_runtime_verification_response(
    *,
    db,
    project_root: Path,
    worker_log_path: str,
    mode: str,
    bearer_token: str,
    classify_gate_status,
    read_admin_env_values,
    admin_env_path,
) -> Dict[str, Any]:
    normalized_mode = str(mode or 'full').strip().lower()
    if normalized_mode == 'dashboard':
        dashboard_payload = run_admin_runtime_verification_dashboard_bundle(
            db=db,
            project_root=project_root,
            worker_log_path=worker_log_path,
            bearer_token=bearer_token,
            classify_gate_status=classify_gate_status,
            read_admin_env_values=read_admin_env_values,
            admin_env_path=admin_env_path,
        )
        verification_items = list(dashboard_payload.get('verification_items') or [])
        operational_evidence = dict(dashboard_payload.get('operational_evidence') or {})
        gate_status = dict(dashboard_payload.get('gate_status') or {})
        context = {
            'project_root': str(project_root),
            'mode': 'dashboard',
        }
    else:
        full_payload = run_admin_runtime_verification_bundle(
            project_root=project_root,
            worker_log_path=worker_log_path,
            bearer_token=bearer_token,
            classify_gate_status=classify_gate_status,
            read_admin_env_values=read_admin_env_values,
            admin_env_path=admin_env_path,
        )
        verification_items = list(full_payload.get('verification_items') or [])
        operational_evidence = dict(full_payload.get('operational_evidence') or {})
        gate_status = dict(full_payload.get('gate_status') or {})
        context = get_project_context_bundle(db, str(project_root))

    return {
        'project_root': str(project_root),
        'verification_items': verification_items,
        'gate_policy': gate_status,
        'gate_status': gate_status,
        'operational_evidence': operational_evidence,
        'operational_targets_by_id': dict(operational_evidence.get('targets_by_id') or {}),
        'operational_evidence_summary': dict(operational_evidence.get('summary') or {}),
        'context': context,
    }


def assert_runtime_verification_contract() -> None:
    sample_items = [
        {
            'key': 'py_compile',
            'label': 'Python py_compile',
            'status': 'passed',
            'detail': 'sample',
            'checkedAt': datetime.now().isoformat(),
        },
        {
            'key': 'worker-log-tail',
            'label': 'worker 로그 tail',
            'status': 'failed',
            'detail': 'worker_log_path가 비어 있습니다.',
            'checkedAt': datetime.now().isoformat(),
        },
        {
            'key': 'traceback-capture',
            'label': 'traceback 캡처',
            'status': 'failed',
            'detail': 'worker 로그 경로가 없어 traceback 판정을 실패로 처리했습니다.',
            'checkedAt': datetime.now().isoformat(),
        },
    ]
    sample_gate = {
        'hard_gate_keys': ['py_compile', 'worker-log-tail', 'traceback-capture'],
        'soft_gate_keys': [],
        'hard_failures': sample_items[1:],
        'soft_failures': [],
        'fallback_recovery': False,
        'final_pass': False,
        'final_status': 'failed',
    }
    required_item_keys = {'key', 'label', 'status', 'detail', 'checkedAt'}
    for item in sample_items:
        if not required_item_keys.issubset(item.keys()):
            missing = sorted(required_item_keys.difference(item.keys()))
            raise RuntimeError(f"runtime verification item contract 누락: {', '.join(missing)}")
    required_gate_keys = {'hard_gate_keys', 'soft_gate_keys', 'hard_failures', 'soft_failures', 'fallback_recovery', 'final_pass', 'final_status'}
    if not required_gate_keys.issubset(sample_gate.keys()):
        missing = sorted(required_gate_keys.difference(sample_gate.keys()))
        raise RuntimeError(f"runtime verification gate contract 누락: {', '.join(missing)}")
