from __future__ import annotations

from typing import Iterable

from backend.movie_studio.contracts.editorial_contract import (
    EditorialTimelineContract,
    EditorialTimelineItemContract,
)


MOVIE_STUDIO_OPERATION_FPS = 8


def _frame_to_timecode(frame_index: int, fps: int) -> str:
    safe_frame_index = max(0, int(frame_index))
    safe_fps = max(1, int(fps))
    total_seconds = safe_frame_index / safe_fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frames = int(safe_frame_index % safe_fps)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def build_editorial_timeline(project_id: str, scene_ids: Iterable[str], scene_windows: Iterable[dict] | None = None) -> EditorialTimelineContract:
    windows = list(scene_windows or [])
    items = []
    for index, scene_id in enumerate(scene_ids):
        scene_window = windows[index] if index < len(windows) else {}
        start_frame = max(1, int(scene_window.get("start_frame") or ((index * 80) + 1)))
        end_frame = max(start_frame, int(scene_window.get("end_frame") or ((index + 1) * 80)))
        frame_count = max(1, end_frame - start_frame + 1)
        items.append(
            EditorialTimelineItemContract(
                item_id=f"timeline-item-{index+1:02d}",
                scene_id=scene_id,
                start_tc=_frame_to_timecode(start_frame - 1, MOVIE_STUDIO_OPERATION_FPS),
                end_tc=_frame_to_timecode(end_frame, MOVIE_STUDIO_OPERATION_FPS),
                transition="cut" if index == 0 else "motivated_cut",
                start_frame=start_frame,
                end_frame=end_frame,
                frame_count=frame_count,
                subtitle_track_mode="overlay_after_sequence_lock",
                music_track_mode="bed_after_sequence_lock",
            )
        )
    return EditorialTimelineContract(project_id=project_id, items=items)
