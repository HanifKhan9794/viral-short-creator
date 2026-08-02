import os
import subprocess
from typing import List, Dict, Any

def render_final_viral_clip(
    main_video_path: str,
    clip_start: float,
    clip_end: float,
    broll_specs: List[Dict[str, Any]],
    ass_subtitle_path: str,
    output_video_path: str
):
    """
    2-Pass Rock Solid GPU Render Pipeline:
    Pass 1: Trims main video and renders 9:16 dual split-screen with ASS captions.
    Pass 2: Applies B-roll overlays sequentially on top of Pass 1 output.
    """
    clip_duration = clip_end - clip_start
    temp_dir = os.path.dirname(output_video_path) or "."
    pass1_output = os.path.join(temp_dir, f"pass1_{os.path.basename(output_video_path)}")

    # Escape ASS path for FFmpeg filter on Windows
    escaped_ass = ass_subtitle_path.replace("\\", "/").replace(":", "\\:")

    # Pass 1 Filter Graph: Split Screen + Captions
    pass1_filter = (
        f"[0:v]split=2[topin][botin];"
        f"[topin]crop=iw:ih/2:0:0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[tophalf];"
        f"[botin]crop=iw:ih/2:0:ih/2,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bothalf];"
        f"[tophalf][bothalf]vstack=inputs=2[splitv];"
        f"[splitv]ass='{escaped_ass}'[basev]"
    )

    cmd_pass1 = [
        "ffmpeg", "-y",
        "-ss", str(clip_start),
        "-to", str(clip_end),
        "-i", main_video_path,
        "-filter_complex", pass1_filter,
        "-map", "[basev]",
        "-map", "0:a",
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-b:v", "6M",
        "-c:a", "aac",
        "-b:a", "192k",
        pass1_output
    ]

    print(f"Executing Pass 1 GPU Split-Screen & Subtitle Render...")
    try:
        subprocess.run(cmd_pass1, check=True)
    except subprocess.CalledProcessError as e:
        print(f"GPU NVENC failed for Pass 1 ({e}), falling back to CPU libx264...")
        cmd_pass1_cpu = [
            "ffmpeg", "-y",
            "-ss", str(clip_start),
            "-to", str(clip_end),
            "-i", main_video_path,
            "-filter_complex", pass1_filter,
            "-map", "[basev]",
            "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            pass1_output
        ]
        subprocess.run(cmd_pass1_cpu, check=True)

    # Valid B-rolls list
    valid_brolls = [b for b in broll_specs if b.get("file_path") and os.path.exists(b.get("file_path"))]

    if not valid_brolls:
        if os.path.exists(output_video_path):
            os.remove(output_video_path)
        os.rename(pass1_output, output_video_path)
        print(f"Render finished (No B-rolls): {output_video_path}")
        return output_video_path

    # Check optional background music & transition SFX assets
    bg_music_path = "assets/audio/bg_music.mp3"
    whoosh_sfx_path = "assets/sfx/whoosh.wav"
    has_bg_music = os.path.exists(bg_music_path)
    has_whoosh_sfx = os.path.exists(whoosh_sfx_path)

    # Pass 2: Apply B-rolls & Audio SFX/Music over Pass 1 Base
    pass2_inputs = ["ffmpeg", "-y", "-i", pass1_output]
    pass2_filter = ""
    curr_v = "0:v"
    curr_a = "0:a"

    audio_inputs_count = 0
    audio_mix_labels = ["[0:a]"]

    # 1. Video Overlays & SFX whoosh triggers
    for idx, b in enumerate(valid_brolls, start=1):
        rel_b_start = max(0.0, b["start_time"] - clip_start)
        rel_b_end = min(clip_duration, b["end_time"] - clip_start)

        pass2_inputs.extend(["-i", b["file_path"]])
        pass2_filter += (
            f"[{idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setpts=PTS-STARTPTS[b{idx}];"
            f"[{curr_v}][b{idx}]overlay=0:0:enable='between(t,{rel_b_start},{rel_b_end})'[v{idx}];"
        )
        curr_v = f"v{idx}"

        # Insert WHOOSH SFX at B-roll start if present
        if has_whoosh_sfx:
            sfx_in_idx = len(valid_brolls) + 1
            if audio_inputs_count == 0:
                pass2_inputs.extend(["-i", whoosh_sfx_path])
            sfx_delay_ms = int(rel_b_start * 1000)
            pass2_filter += f"[{sfx_in_idx}:a]adelay={sfx_delay_ms}|{sfx_delay_ms},volume=0.6[sfx{idx}];"
            audio_mix_labels.append(f"[sfx{idx}]")
            audio_inputs_count += 1

    # 2. Background Music with Sidechain Ducking
    if has_bg_music:
        bg_in_idx = len(valid_brolls) + (1 if has_whoosh_sfx else 0) + 1
        pass2_inputs.extend(["-i", bg_music_path])
        pass2_filter += f"[{bg_in_idx}:a]volume=0.15,aloop=loop=-1:size=2e+09,atrim=0:{clip_duration}[bgm];"
        audio_mix_labels.append("[bgm]")

    # Mix Audio Tracks if music or SFX were added
    if len(audio_mix_labels) > 1:
        mix_inputs = "".join(audio_mix_labels)
        pass2_filter += f"{mix_inputs}amix=inputs={len(audio_mix_labels)}:duration=first:dropout_transition=2[final_a];"
        curr_a = "[final_a]"
        pass2_filter = pass2_filter.rstrip(";")
    else:
        pass2_filter = pass2_filter.rstrip(";")

    cmd_pass2 = pass2_inputs + [
        "-filter_complex", pass2_filter,
        "-map", f"[{curr_v}]",
        "-map", curr_a,
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-b:v", "6M",
        "-c:a", "aac",
        "-b:a", "192k",
        output_video_path
    ]

    print(f"Executing Pass 2 GPU B-roll Overlay & Audio SFX Render...")
    try:
        subprocess.run(cmd_pass2, check=True)
    except subprocess.CalledProcessError as e:
        print(f"GPU NVENC failed for Pass 2 ({e}), falling back to CPU libx264...")
        cmd_pass2_cpu = pass2_inputs + [
            "-filter_complex", pass2_filter,
            "-map", f"[{curr_v}]",
            "-map", curr_a,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_video_path
        ]
        subprocess.run(cmd_pass2_cpu, check=True)

    if os.path.exists(pass1_output):
        os.remove(pass1_output)

    print(f"Render finished: {output_video_path}")
    return output_video_path
