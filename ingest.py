import os
import json
import subprocess
import pathlib
import torch
from typing import Dict, Any, List

def download_youtube_video(url: str, output_dir: str) -> Dict[str, str]:
    """Downloads YouTube video and extracts high quality audio."""
    os.makedirs(output_dir, exist_ok=True)
    video_template = os.path.join(output_dir, "input_video.%(ext)s")
    audio_path = os.path.join(output_dir, "input_audio.wav")

    video_path = os.path.join(output_dir, "input_video.mp4")

    # Validate existing video file size (remove if incomplete/corrupted < 5MB)
    if os.path.exists(video_path) and os.path.getsize(video_path) < 5 * 1024 * 1024:
        print("Removing incomplete/corrupted video file...")
        os.remove(video_path)

    if not os.path.exists(video_path):
        print(f"Downloading video from {url}...")
        cmd_video = [
            "yt-dlp",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "-o", video_path,
            "--recode-video", "mp4",
            "--no-playlist",
            url
        ]
        subprocess.run(cmd_video, check=True)

    # Validate/extract audio cleanly
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        print("Extracting 16kHz WAV audio for Whisper...")
        cmd_audio = [
            "ffmpeg", "-y", "-err_detect", "ignore_err", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path
        ]
        try:
            subprocess.run(cmd_audio, check=True)
        except subprocess.CalledProcessError:
            print("Video stream audio extraction warning. Re-extracting audio directly via yt-dlp...")
            cmd_ytdlp_audio = [
                "yt-dlp", "-x", "--audio-format", "wav",
                "-o", audio_path,
                "--no-playlist",
                url
            ]
            subprocess.run(cmd_ytdlp_audio, check=True)

    return {"video_path": video_path, "audio_path": audio_path}

def transcribe_audio_whisper(audio_path: str, output_json_path: str) -> Dict[str, Any]:
    """Transcribes full audio in seconds using segment-level PyTorch Whisper on GPU."""
    import whisper

    model_name = "tiny"
    print(f"Loading fast Whisper ({model_name}) on CUDA...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model(model_name, device=device)

    print("Transcribing full audio segments on GPU...")
    result = model.transcribe(audio_path, word_timestamps=False, fp16=(device == "cuda"))

    transcript_data = {
        "language": result.get("language", "en"),
        "duration": float(result.get("segments", [{}])[-1].get("end", 0.0)) if result.get("segments") else 0.0,
        "segments": []
    }

    for idx, seg in enumerate(result.get("segments", [])):
        transcript_data["segments"].append({
            "id": idx,
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip()
        })

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)

    print(f"Full transcript saved to {output_json_path}")
    return transcript_data

def get_clip_word_timestamps(audio_path: str, clip_start: float, clip_end: float) -> List[Dict[str, Any]]:
    """Generates word-level timestamps in <0.5 seconds for a specific short clip."""
    import whisper

    temp_clip_audio = os.path.join(os.path.dirname(audio_path), "temp_clip_audio.wav")
    cmd = [
        "ffmpeg", "-y", "-ss", str(clip_start), "-to", str(clip_end),
        "-i", audio_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        temp_clip_audio
    ]
    subprocess.run(cmd, check=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model("tiny", device=device)
    res = model.transcribe(temp_clip_audio, word_timestamps=True, fp16=(device == "cuda"))

    words = []
    for seg in res.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": round(clip_start + w["start"], 3),
                "end": round(clip_start + w["end"], 3),
                "probability": round(w.get("probability", 1.0), 3)
            })

    if os.path.exists(temp_clip_audio):
        os.remove(temp_clip_audio)

    return words
