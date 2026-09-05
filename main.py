"""
YouTube Playlist Transcript Downloader
-------------------------------------
✔ Downloads manual + auto-generated captions
✔ Supports full playlists
✔ Skips video downloads
✔ Prefixes playlist index (01 - Title)
✔ Converts VTT -> TXT
✔ Organizes output by playlist name
"""

from yt_dlp import YoutubeDL
from pathlib import Path
import re
import ssl
import certifi

# ==========================
# FIX SSL (PyCharm / macOS)
# ==========================

ssl._create_default_https_context = lambda: ssl.create_default_context(
    cafile=certifi.where()
)

# ==========================
# CONFIG
# ==========================

PLAYLIST_URL = "https://www.youtube.com/watch?v=QNfIUIZQ9Vo&list=PL6W8uoQQ2c62YCR2kkE-0tg3-y1QwaIWk"
LANGUAGES = ["EN"]
OUTPUT_DIR = Path("transcripts")

# ==========================
# HELPERS
# ==========================

def sanitize_filename(name: str) -> str:
    """Remove invalid filename characters"""
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()

# ==========================
# DOWNLOAD TRANSCRIPTS
# ==========================

def download_playlist_transcripts():
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": LANGUAGES,
        "subtitlesformat": "vtt",
        "yesplaylist": True,
        "ignoreerrors": True,

        # 👉 PLAYLIST INDEX + VIDEO TITLE
        "outtmpl": str(
            OUTPUT_DIR
            / "%(playlist_title)s"
            / "%(playlist_index)02d - %(title)s.%(ext)s"
        ),

        "windowsfilenames": True,
        "quiet": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([PLAYLIST_URL])

# ==========================
# VTT -> TXT CONVERTER
# ==========================

def vtt_to_text(vtt_file: Path) -> str:
    text = []
    timestamp_pattern = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3}")

    with vtt_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if (
                not line
                or line.startswith(("WEBVTT", "Kind:", "Language:"))
                or timestamp_pattern.search(line)
            ):
                continue
            text.append(line)

    return " ".join(text)

# ==========================
# CONVERT ALL FILES
# ==========================

def convert_all_vtt_to_txt():
    for vtt in OUTPUT_DIR.rglob("*.vtt"):
        safe_name = sanitize_filename(vtt.stem)
        txt_path = vtt.with_name(f"{safe_name}.txt")

        if txt_path.exists():
            continue

        txt_path.write_text(vtt_to_text(vtt), encoding="utf-8")
        print(f"Converted → {txt_path}")

# ==========================
# MAIN
# ==========================

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("▶ Downloading playlist transcripts (indexed + titled)...")
    download_playlist_transcripts()

    print("\n▶ Converting VTT → TXT...")
    convert_all_vtt_to_txt()

    print("\n✅ DONE. Check the 'transcripts/' folder.")
