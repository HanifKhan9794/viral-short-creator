import os
import json
from typing import Dict, Any, List
from google import genai
from google.genai import types

from dotenv import load_dotenv

def get_client() -> genai.Client:
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)

def select_viral_clips(transcript_data: Dict[str, Any], num_clips: int = 4, exclude_ranges: List[tuple] = None) -> List[Dict[str, Any]]:
    """Master Prompt 1: Selects top 1-2 minute viral segments from transcript."""
    client = get_client()

    transcript_lines = []
    for seg in transcript_data.get("segments", []):
        transcript_lines.append(f"[{seg['start']:.2f}s - {seg['end']:.2f}s]: {seg['text']}")
    full_transcript_text = "\n".join(transcript_lines)

    exclude_str = ""
    if exclude_ranges:
        exclude_str = "\nDO NOT select clips overlapping with these previously used timestamps:\n" + \
                      "\n".join([f"- {s}s to {e}s" for s, e in exclude_ranges])

    prompt = f"""You are an expert viral video producer.
Read the following podcast transcript with exact timestamps.
Identify EXACTLY {num_clips} highly engaging, high-retention, controversial, or emotional segments that are between 60 and 110 seconds long.{exclude_str}
Ensure each segment has a powerful hook in the first 5 seconds.

STRICT REQUIREMENTS:
- Use exact timestamps provided in the input text.
- Output MUST be valid JSON conforming to the schema below.

Transcript:
{full_transcript_text[:120000]}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "clip_title": {"type": "STRING"},
                        "start_time": {"type": "NUMBER"},
                        "end_time": {"type": "NUMBER"},
                        "hook_summary": {"type": "STRING"},
                        "viral_score": {"type": "NUMBER"}
                    },
                    "required": ["clip_title", "start_time", "end_time", "hook_summary", "viral_score"]
                }
            }
        )
    )

    return json.loads(response.text)

def generate_broll_blueprint(clip_transcript_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Master Prompt 2: Visual Director planning B-roll overlays."""
    client = get_client()

    words_text = "\n".join([f"[{w['start']:.2f}s - {w['end']:.2f}s]: {w['word']}" for w in clip_transcript_words])

    clip_start = clip_transcript_words[0]['start'] if clip_transcript_words else 0.0
    duration_sec = 60.0
    if clip_transcript_words:
        duration_sec = max(10.0, clip_transcript_words[-1]['end'] - clip_transcript_words[0]['start'])
    target_count = max(6, int(round((duration_sec / 60.0) * 6.5)))

    prompt = f"""You are a Master Video Director specializing in high-pacing viral TikTok/Shorts.
Analyze this word-level clip transcript.
Select EXACTLY {target_count} key moments (maintaining a high-density rate of 6 to 7 B-rolls per minute) where visual B-roll video overlay is required to maximize retention.

STRICT HOOK & PROMPT RULES:
1. THE 3-SECOND A-ROLL HOOK RULE: The first 3.0 seconds of the clip (from {clip_start:.2f}s to {clip_start + 3.0:.2f}s) MUST BE EXCLUSIVELY A-ROLL (the speaker's face). DO NOT place any B-roll overlay starting before {clip_start + 3.0:.2f}s!
2. B-roll clip durations must be fast-paced: between 1.5 and 2.5 seconds.
3. Space B-rolls evenly across the clip (roughly every 7 to 9 seconds).
4. PROMPT RESTRICTION: Do NOT include proper names in search_keyword. Use generic terms like "man", "woman", "character", "person", "leader", "crowd" to guarantee stock footage matches.

Transcript:
{words_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "start_time": {"type": "NUMBER"},
                        "end_time": {"type": "NUMBER"},
                        "search_keyword": {"type": "STRING"},
                        "visual_reason": {"type": "STRING"}
                    },
                    "required": ["start_time", "end_time", "search_keyword"]
                }
            }
        )
    )

    return json.loads(response.text)
