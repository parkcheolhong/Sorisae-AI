from backend.worldlinco.brand import (
    WORLDLINGO_BRAND_NAME,
    WORLDLINGO_PROJECT_MATCH_TOKENS,
    matches_worldlinco_apk_filename,
    matches_worldlinco_project_haystack,
)


def test_worldlinco_brand_constants():
    assert WORLDLINGO_BRAND_NAME == "WorldLinco"
    assert "worldlinco" in WORLDLINGO_PROJECT_MATCH_TOKENS
    assert "나도통역사" in WORLDLINGO_PROJECT_MATCH_TOKENS


def test_matches_worldlinco_project_haystack_accepts_legacy_and_new_names():
    assert matches_worldlinco_project_haystack("WorldLinco · 월드링코")
    assert matches_worldlinco_project_haystack("나도통역사 실시간 통역")
    assert matches_worldlinco_project_haystack("nadotongryoksa-v1.0.25-build35-current.apk")
    assert not matches_worldlinco_project_haystack("unrelated marketplace item")


def test_matches_worldlinco_apk_filename_accepts_both_prefixes():
    assert matches_worldlinco_apk_filename("worldlinco-v1.0.25-build35-current.apk")
    assert matches_worldlinco_apk_filename("nadotongryoksa-v1.0.25-build35-current.apk")
    assert not matches_worldlinco_apk_filename("other-app-v1.apk")
