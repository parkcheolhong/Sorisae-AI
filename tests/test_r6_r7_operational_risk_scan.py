from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKER_COMPOSE_PATH = REPO_ROOT / 'docker-compose.yml'
ENV_EXAMPLE_PATH = REPO_ROOT / '.env.example'
NGINX_CONFIG_PATH = REPO_ROOT / 'nginx' / 'nginx.conf' / 'nginx.conf'


def _read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _extract_braced_block(text: str, block_header: str) -> str | None:
    block_start = text.find(block_header)
    if block_start == -1:
        return None

    brace_start = text.find('{', block_start + len(block_header))
    if brace_start == -1:
        return None

    depth = 0
    for index in range(brace_start, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[brace_start + 1 : index]

    return None


def test_r6_operational_exposure_markers_mitigated() -> None:
    compose_text = _read_text(DOCKER_COMPOSE_PATH)
    env_text = _read_text(ENV_EXAMPLE_PATH)
    nginx_text = _read_text(NGINX_CONFIG_PATH)

    expected_ports = [
        '127.0.0.1:5432:5432',
        '127.0.0.1:9000:9000',
        '127.0.0.1:9001:9001',
        '127.0.0.1:6380:6379',
        '127.0.0.1:6333:6333',
        '127.0.0.1:3005:3005',
        '127.0.0.1:3000:3000',
        '127.0.0.1:8000:8000',
    ]
    for port in expected_ports:
        assert port in compose_text

    assert 'APP_DEBUG=false' in env_text
    assert 'APP_DEBUG=true' not in env_text
    assert 'location ^~ /docs {' in nginx_text
    assert 'location = /openapi.json {' in nginx_text
    assert 'allow 127.0.0.1;' in nginx_text
    assert 'deny all;' in nginx_text
    assert 'return 302 $scheme://$http_host/health;' in nginx_text
    assert 'return 302 $scheme://$http_host/docs;' not in nginx_text


def test_r7_long_timeout_markers_mitigated() -> None:
    nginx_text = _read_text(NGINX_CONFIG_PATH)

    assert 'proxy_read_timeout 3600s;' not in nginx_text
    assert 'proxy_send_timeout 3600s;' not in nginx_text

    first_server_block = re.search(
        r'server \{\s*listen 443 ssl;\s*server_name localhost xn--114-2p7l635dz3bh5j\.com;(?P<body>.*?)\n\s*}\s*\n\s*server \{',
        nginx_text,
        re.DOTALL,
    )
    second_server_block = re.search(
        r'server \{\s*listen 443 ssl;\s*server_name metanova1004\.com;(?P<body>.*?)\n\s*}\s*\n\s*server \{',
        nginx_text,
        re.DOTALL,
    )

    first_server_body = first_server_block.group('body')
    second_server_body = second_server_block.group('body')

    assert 'location /api/ {' in first_server_body

    api_location_body = _extract_braced_block(first_server_body, 'location /api/')
    assert (
        api_location_body is not None
    ), 'Expected to find `location /api/ { ... }` block in first server nginx config'

    assert 'location = /api/admin/system-settings {' in first_server_body
    assert 'proxy_read_timeout 120s;' in first_server_body
    assert 'proxy_send_timeout 120s;' in first_server_body

    assert 'proxy_read_timeout 300s;' in api_location_body
    assert 'proxy_send_timeout 300s;' in api_location_body

    assert second_server_body.count('location = /api/llm/ws {') == 1
    assert second_server_body.count('proxy_read_timeout 300s;') >= 2
    assert second_server_body.count('proxy_send_timeout 300s;') >= 2
    assert 'location ^~ /api/llm/ {' in second_server_body
