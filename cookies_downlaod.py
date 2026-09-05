"""
YouTube Playlist Transcript Downloader
--------------------------------------
✔ Uses authenticated YouTube cookies
✔ Downloads manual + auto-generated captions
✔ Supports full playlists
✔ Supports members-only videos you can access
✔ Skips actual video downloads
✔ Prefixes playlist index (01 - Title)
✔ Converts VTT -> TXT
✔ Organizes output by playlist name
✔ Creates a download report
"""

from yt_dlp import YoutubeDL
from pathlib import Path
import re
import ssl
import certifi
import sys


# ============================================================
# FIX SSL (PyCharm / macOS)
# ============================================================

ssl._create_default_https_context = lambda: ssl.create_default_context(
    cafile=certifi.where()
)


# ============================================================
# CONFIG
# ============================================================

PLAYLIST_URL = (
    "https://www.youtube.com/watch?"
    "v=QNfIUIZQ9Vo"
    "&list=PL6W8uoQQ2c62YCR2kkE-0tg3-y1QwaIWk"
)

# Use lowercase YouTube language codes
LANGUAGES = ["en"]

# Main output directory
OUTPUT_DIR = Path("transcripts")

# Cookie file exported from your logged-in YouTube browser
COOKIE_FILE = Path("cookies.txt")

# Report file
REPORT_FILE = OUTPUT_DIR / "download_report.txt"


# ============================================================
# HELPERS
# ============================================================

def sanitize_filename(name: str) -> str:
    """
    Remove characters that are invalid in filenames.
    """
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def write_report(message: str):
    """
    Write a message to the download report and print it.
    """
    print(message)

    with REPORT_FILE.open(
        "a",
        encoding="utf-8"
    ) as f:
        f.write(message + "\n")


# ============================================================
# VTT -> TEXT
# ============================================================

def vtt_to_text(vtt_file: Path) -> str:
    """
    Convert a WebVTT subtitle file into plain text.
    Attempts to remove timestamps, metadata and duplicate
    consecutive caption lines.
    """

    text = []

    timestamp_pattern = re.compile(
        r"\d{2}:\d{2}(?::\d{2})?\.\d{3}"
    )

    # Matches things like:
    # <00:00:01.000>
    # <c.color>
    # </c>
    tag_pattern = re.compile(r"<[^>]+>")

    previous_line = None

    with vtt_file.open(
        encoding="utf-8-sig"
    ) as f:

        for raw_line in f:

            line = raw_line.strip()

            # Empty line
            if not line:
                continue

            # VTT header / metadata
            if line.startswith(
                (
                    "WEBVTT",
                    "Kind:",
                    "Language:",
                    "NOTE",
                    "STYLE",
                    "REGION:",
                )
            ):
                continue

            # Timestamp line
            if timestamp_pattern.search(line):
                continue

            # Remove VTT tags
            line = tag_pattern.sub("", line)

            # Remove alignment / positioning artifacts
            line = re.sub(
                r"\{\\.*?\}",
                "",
                line
            )

            line = line.strip()

            if not line:
                continue

            # Remove duplicate consecutive captions
            if line == previous_line:
                continue

            text.append(line)
            previous_line = line

    # Join into readable paragraphs
    result = " ".join(text)

    # Clean excessive whitespace
    result = re.sub(r"\s+", " ", result).strip()

    return result


# ============================================================
# DOWNLOAD PLAYLIST
# ============================================================

def download_playlist_transcripts():

    if not COOKIE_FILE.exists():
        print()
        print("ERROR: cookies.txt was not found.")
        print()
        print(
            f"Expected cookie file here:"
            f"\n{COOKIE_FILE.absolute()}"
        )
        print()
        sys.exit(1)

    # Make sure output exists
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Reset report
    REPORT_FILE.write_text(
        "YouTube Transcript Download Report\n"
        "=================================\n\n",
        encoding="utf-8"
    )

    ydl_opts = {

        # ----------------------------------------------------
        # DO NOT DOWNLOAD VIDEO
        # ----------------------------------------------------

        "skip_download": True,

        # ----------------------------------------------------
        # CAPTIONS
        # ----------------------------------------------------

        "writesubtitles": True,
        "writeautomaticsub": True,

        "subtitleslangs": LANGUAGES,
        "subtitlesformat": "vtt",

        # ----------------------------------------------------
        # PLAYLIST
        # ----------------------------------------------------

        "yesplaylist": True,

        # ----------------------------------------------------
        # AUTHENTICATION
        # ----------------------------------------------------

        "cookiefile": str(COOKIE_FILE),

        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        "outtmpl": str(
            OUTPUT_DIR
            / "%(playlist_title)s"
            / "%(playlist_index)02d - %(title)s.%(ext)s"
        ),

        "windowsfilenames": True,

        # ----------------------------------------------------
        # DEBUGGING
        # ----------------------------------------------------

        # Keep False while diagnosing missing videos.
        "ignoreerrors": False,

        "quiet": False,

        # Uncomment if you need detailed yt-dlp debugging:
        # "verbose": True,
    }

    print()
    print("=" * 70)
    print("DOWNLOADING PLAYLIST TRANSCRIPTS")
    print("=" * 70)
    print()

    print(f"Playlist:")
    print(PLAYLIST_URL)
    print()

    print(f"Cookie file:")
    print(COOKIE_FILE.absolute())
    print()

    print(f"Languages:")
    print(LANGUAGES)
    print()

    print("Authenticated session: ENABLED")
    print()

    try:

        with YoutubeDL(ydl_opts) as ydl:

            result = ydl.download(
                [PLAYLIST_URL]
            )

            if result != 0:
                write_report(
                    f"yt-dlp returned exit code: {result}"
                )

    except Exception as e:

        write_report(
            "DOWNLOAD ERROR:"
        )

        write_report(
            str(e)
        )

        print()
        print(
            "The download stopped because of the error above."
        )
        print(
            "Check your cookies.txt and yt-dlp version."
        )

        return


# ============================================================
# CONVERT ALL VTT FILES
# ============================================================

def convert_all_vtt_to_txt():

    print()
    print("=" * 70)
    print("CONVERTING VTT -> TXT")
    print("=" * 70)
    print()

    vtt_files = list(
        OUTPUT_DIR.rglob("*.vtt")
    )

    if not vtt_files:

        print(
            "No VTT files were found."
        )

        return

    converted = 0

    for vtt in vtt_files:

        safe_name = sanitize_filename(
            vtt.stem
        )

        txt_path = vtt.with_name(
            f"{safe_name}.txt"
        )

        try:

            transcript = vtt_to_text(
                vtt
            )

            txt_path.write_text(
                transcript,
                encoding="utf-8"
            )

            converted += 1

            print(
                f"Converted -> {txt_path}"
            )

        except Exception as e:

            print(
                f"FAILED -> {vtt}"
            )

            print(
                f"Reason: {e}"
            )

    print()
    print(
        f"Converted {converted} VTT file(s)."
    )


# ============================================================
# SHOW DOWNLOADED FILES
# ============================================================

def show_summary():

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    txt_files = list(
        OUTPUT_DIR.rglob("*.txt")
    )

    # Don't count the report
    txt_files = [
        f for f in txt_files
        if f.name != REPORT_FILE.name
    ]

    vtt_files = list(
        OUTPUT_DIR.rglob("*.vtt")
    )

    print(
        f"TXT transcripts : {len(txt_files)}"
    )

    print(
        f"VTT files       : {len(vtt_files)}"
    )

    print()
    print(
        f"Output folder:"
    )

    print(
        OUTPUT_DIR.absolute()
    )

    print()
    print(
        f"Report:"
    )

    print(
        REPORT_FILE.absolute()
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("YOUTUBE PLAYLIST TRANSCRIPT DOWNLOADER")
    print("=" * 70)

    # Check yt-dlp installation
    try:

        import yt_dlp

        print()
        print(
            f"yt-dlp version: {yt_dlp.version.__version__}"
        )

    except Exception:
        print(
            "WARNING: Could not determine yt-dlp version."
        )

    # Check cookies
    if not COOKIE_FILE.exists():

        print()
        print("ERROR")
        print("-" * 70)
        print(
            "cookies.txt was not found."
        )
        print()
        print(
            "Put cookies.txt in the same folder as this script."
        )
        print()

        sys.exit(1)

    # Create output directory
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Download
    download_playlist_transcripts()

    # Convert
    convert_all_vtt_to_txt()

    # Summary
    show_summary()

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)