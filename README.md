# Viral Short Creator & AutoPublisher

An automated high-speed video creation and publishing engine built for short-form content creators (TikTok, YouTube Shorts, Instagram Reels, Pinterest Idea Pins).

## 🚀 Features
- **Audio & Transcript Processing**: Fast 2-stage PyTorch GPU Whisper speech-to-text.
- **LLM Content Director**: Automated viral clip detection and B-roll director powered by Gemini 2.5 Flash.
- **Dynamic B-Roll Sourcing**: Automated 9:16 portrait stock video downloader (Pexels / Pixabay waterfall).
- **CapCut Karaoke Subtitles**: Dynamic ASS word-highlighting subtitle generator.
- **GPU Render Engine**: 2-Pass NVIDIA NVENC 1080x1920 vertical compositor with background music volume ducking (-18dB) and transition WHOOSH SFX.
- **Pinterest API Integration**: Automated Pin & Board publishing via Pinterest API v5.

## 🛠️ Installation & Setup
```bash
# Clone the repository
git clone https://github.com/HanifKhan9794/viral-short-creator.git
cd viral-short-creator

# Install dependencies
pip install -r requirements.txt
```

## 📄 Privacy Policy
Read our [Privacy Policy](PRIVACY_POLICY.md) for Pinterest API access and data handling compliance.

## 👤 Author
Developed by **HanifKhan9794** ([GitHub Profile](https://github.com/HanifKhan9794)).
