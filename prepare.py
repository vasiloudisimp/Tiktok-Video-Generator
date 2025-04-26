import os
import shutil
from pathlib import Path
import re

def prepare():
    base_dir = Path(__file__).parent

    output_videos_dir = base_dir / "output_videos"
    videos_dir = base_dir / "videos"
    all_videos_dir = base_dir / "all_videos"
    used_videos_dir = all_videos_dir / "used"

    # Step 1: Find last numbered mp4 in output_videos
    existing = [f.stem for f in output_videos_dir.glob("*.mp4") if f.stem.isdigit()]
    last_num = max(map(int, existing), default=0)
    next_num = last_num + 1

    # Step 2: Rename output_video.mp4 to {next_num}.mp4 and move it
    output_video_file = base_dir / "output_video.mp4"
    if output_video_file.exists():
        new_name = output_videos_dir / f"{next_num}.mp4"
        shutil.move(str(output_video_file), str(new_name))

    # Step 3: Move video from /videos to /all_videos/used
    for file in videos_dir.glob("*.mp4"):
        shutil.move(str(file), used_videos_dir / file.name)
        break  # Only move one

    def numeric_sort_key(f):
        # Extract number from filename like "1.mp4" -> 1
        return int(re.findall(r'\d+', f.stem)[0])

    # Step 4: Move first file from /all_videos to /videos
    available = sorted([f for f in all_videos_dir.glob("*.mp4")], key=numeric_sort_key)
    if not available:
        # Refill from used
        used = sorted([f for f in used_videos_dir.glob("*.mp4")], key=numeric_sort_key)
        for f in used:
            shutil.move(str(f), all_videos_dir / f.name)
        available = sorted([f for f in all_videos_dir.glob("*.mp4")], key=numeric_sort_key)

    if available:
        shutil.move(str(available[0]), videos_dir / available[0].name)
        
    # Step 5: Remove temp files
    for temp_file in ["image.webp", "scenario_audio.mp3", "subtitles.ass", "transcription.json"]:
        temp_path = base_dir / temp_file
        if temp_path.exists():
            temp_path.unlink()

if __name__ == "__main__":
    prepare()
