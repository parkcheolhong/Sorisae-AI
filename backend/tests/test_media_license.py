"""콘텐츠 저작권 게이트 테스트 — default-deny / NC 차단 / CC-BY 표기강제."""

from backend.services.media_license import evaluate_media, filter_media, gate_payload_media

IMG = "https://example.org/p.jpg"


def test_unknown_license_denied():
    assert evaluate_media({"url": IMG})["allowed"] is False
    assert evaluate_media({"url": IMG, "license": "All Rights Reserved"})["allowed"] is False
    assert evaluate_media({"url": IMG, "license": "unknown"})["allowed"] is False


def test_missing_url_denied():
    assert evaluate_media({"license": "CC0"})["allowed"] is False


def test_cc0_allowed_no_attribution_required():
    d = evaluate_media({"url": IMG, "license": "CC0-1.0"})
    assert d["allowed"] is True
    assert d["requires_attribution"] is False
    assert d["license_label"] in {"CC0", "Public Domain"}


def test_public_domain_allowed():
    assert evaluate_media({"url": IMG, "license": "Public Domain"})["allowed"] is True


def test_nc_denied():
    for lic in ("CC-BY-NC-4.0", "CC BY-NC-SA 3.0", "by-nc-nd"):
        d = evaluate_media({"url": IMG, "license": lic, "author": "Kim", "source": "Commons"})
        assert d["allowed"] is False, lic
        assert "NonCommercial" in d["reason"]


def test_cc_by_requires_attribution():
    # 작성자/출처 없으면 차단.
    d0 = evaluate_media({"url": IMG, "license": "CC-BY-4.0"})
    assert d0["allowed"] is False
    assert d0["requires_attribution"] is True
    # 작성자 있으면 허용 + 표기 생성.
    d1 = evaluate_media({"url": IMG, "license": "CC-BY-4.0", "author": "Kim", "source": "Wikimedia"})
    assert d1["allowed"] is True
    assert d1["requires_attribution"] is True
    assert "Kim" in d1["attribution"] and "CC BY" in d1["attribution"]
    assert d1["license_url"].startswith("https://creativecommons.org/licenses/by/")


def test_cc_by_sa_nd_non_nc_allowed():
    for lic in ("CC-BY-SA-4.0", "CC-BY-ND-4.0"):
        d = evaluate_media({"url": IMG, "license": lic, "author": "A"})
        assert d["allowed"] is True, lic


def test_owned_commercial_allowed():
    d = evaluate_media({"url": IMG, "license": "owned", "source": "MetaNova"})
    assert d["allowed"] is True
    assert "via MetaNova" in (d["attribution"] or "")


def test_filter_media_keeps_only_allowed():
    items = [
        {"url": IMG, "license": "CC0"},
        {"url": IMG, "license": "CC-BY-NC"},
        {"url": IMG, "license": "CC-BY", "author": "Kim"},
        {"url": IMG},  # unknown
    ]
    out = filter_media(items)
    assert len(out) == 2
    assert all(o["url"] == IMG for o in out)


def test_gate_payload_flat_image_fields():
    payload = {"image": IMG, "image_license": "CC-BY-4.0", "image_author": "Lee", "image_source": "Commons"}
    media = gate_payload_media(payload)
    assert len(media) == 1 and media[0]["requires_attribution"] is True
    # 라이선스 미상이면 비노출.
    assert gate_payload_media({"image": IMG}) == []
