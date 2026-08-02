import os
from typing import List, Dict, Any

def format_ass_time(seconds: float) -> str:
    """Converts seconds to ASS timestamp format H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_captions(words: List[Dict[str, Any]], output_ass_path: str, clip_start: float = 0.0):
    """Generates CapCut-style animated word-pop karaoke captions in ASS format."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default, Montserrat, 62, &H00FFFFFF, &H0000FFFF, &H00000000, &H80000000, 1, 0, 0, 0, 100, 100, 0, 0, 1, 4, 2, 2, 50, 50, 950, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]

    # Chunk words into small display groups (3-4 words max)
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        if not chunk:
            continue

        chunk_start = chunk[0]['start'] - clip_start
        chunk_end = chunk[-1]['end'] - clip_start

        # Ensure positive relative timings
        chunk_start = max(0.0, chunk_start)
        chunk_end = max(chunk_start + 0.5, chunk_end)

        start_str = format_ass_time(chunk_start)
        end_str = format_ass_time(chunk_end)

        # Build karaoke animated line
        text_parts = []
        for w in chunk:
            w_start = max(0.0, w['start'] - clip_start)
            w_end = max(w_start + 0.1, w['end'] - clip_start)
            duration_cs = int(round((w_end - w_start) * 100))
            word_str = w['word'].upper()
            # \k tag for karaoke highlight + pop animation scale
            text_parts.append(rf"{{\k{duration_cs}\t(0, 100, \fscx115\fscy115)\t(100, 200, \fscx100\fscy100)}}{word_str}")

        formatted_line = " ".join(text_parts)
        lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{formatted_line}\n")

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return output_ass_path
