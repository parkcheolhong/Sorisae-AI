from backend.admin_review_utils import build_storyboard_review_diff


def test_build_storyboard_review_diff_tracks_status_change():
    previous_items = [{"cut": 1, "status": "pending", "note": ""}]
    validated_items = [{"cut": 1, "status": "approved", "note": ""}]

    diff = build_storyboard_review_diff(previous_items, validated_items)

    assert diff == [
        {
            "cut": 1,
            "previous_status": "pending",
            "current_status": "approved",
            "previous_note": "",
            "current_note": "",
        }
    ]


def test_build_storyboard_review_diff_tracks_note_change():
    previous_items = [{"cut": 2, "status": "approved", "note": "기존 메모"}]
    validated_items = [{"cut": 2, "status": "approved", "note": "수정된 메모"}]

    diff = build_storyboard_review_diff(previous_items, validated_items)

    assert diff == [
        {
            "cut": 2,
            "previous_status": "approved",
            "current_status": "approved",
            "previous_note": "기존 메모",
            "current_note": "수정된 메모",
        }
    ]


def test_build_storyboard_review_diff_skips_unchanged_items():
    previous_items = [{"cut": 3, "status": "needs-fix", "note": "동일"}]
    validated_items = [{"cut": 3, "status": "needs-fix", "note": "동일"}]

    diff = build_storyboard_review_diff(previous_items, validated_items)

    assert diff == []
