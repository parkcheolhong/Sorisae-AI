from backend.services.nadotongryoksa.glossary import build_llm_terminology_block, get_pair_entries, polish_translation


def test_build_llm_terminology_block_ko_zh():
    block = build_llm_terminology_block("ko", "zh")
    assert "환불" in block
    assert "退款" in block
    assert "半导体" in block or "반도체" in block


def test_english_pivot_ko_ja():
    entries = get_pair_entries("ko", "ja")
    sources = {e["source"] for e in entries}
    assert "반도체" in sources or "수술" in sources


def test_polish_translation_replaces_wrong_variant():
    out = polish_translation(
        "请办理退钱手续",
        original="환불 절차",
        from_lang="ko",
        to_lang="zh",
    )
    assert "退款" in out
    assert "退钱" not in out


def test_polish_translation_zh_ko_boarding_gate():
    out = polish_translation(
        "게이트 12번",
        original="登机口 12",
        from_lang="zh",
        to_lang="ko",
    )
    assert "탑승구" in out
