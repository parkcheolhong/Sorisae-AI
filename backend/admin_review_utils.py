from typing import Any, Dict, List


def build_storyboard_review_diff(
    previous_items: List[Dict[str, Any]],
    validated_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    previous_map = {
        int(item.get('cut', 0)): item
        for item in previous_items
        if isinstance(item, dict)
    }
    diff_items: List[Dict[str, Any]] = []
    for item in validated_items:
        cut = int(item.get('cut', 0) or 0)
        previous = previous_map.get(cut, {})
        previous_status = str(previous.get('status', 'pending') or 'pending')
        previous_note = str(previous.get('note', '') or '')
        current_status = str(item.get('status', 'pending') or 'pending')
        current_note = str(item.get('note', '') or '')
        if previous_status != current_status or previous_note != current_note:
            diff_items.append(
                {
                    'cut': cut,
                    'previous_status': previous_status,
                    'current_status': current_status,
                    'previous_note': previous_note,
                    'current_note': current_note,
                }
            )
    return diff_items
