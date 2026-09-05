"""Caption download primitives used by the web application and the CLI.

The downloader deliberately processes one entry at a time.  Apart from making
cancel/retry reliable, this means a bad/private video cannot hide the other
failures in a playlist.
"""

from pathlib import Path
import re
import ssl
from typing import Callable, Iterable
from urllib.parse import parse_qs, urlparse

import certifi
from yt_dlp import YoutubeDL

ssl._create_default_https_context = lambda: ssl.create_default_context(
    cafile=certifi.where()
)

OUTPUT_DIR = Path("transcripts")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


class DownloadCancelled(Exception):
    """Raised when a worker notices a cancellation request."""


def validate_youtube_url(value: str, require_playlist: bool = False) -> str:
    """Return a canonical, safe YouTube URL or raise ValueError."""
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Enter a valid YouTube URL.")
    value = value.strip()
    if not value or any(ord(char) < 32 for char in value):
        raise ValueError("Enter a valid YouTube URL.")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host not in YOUTUBE_HOSTS or parsed.username or parsed.password or parsed.port:
        raise ValueError("Only secure youtube.com or youtu.be URLs are allowed.")
    query = parse_qs(parsed.query)
    playlist_id = (query.get("list") or [""])[0]
    video_id = (query.get("v") or [""])[0]
    if host == "youtu.be":
        video_id = parsed.path.strip("/")
    if playlist_id and not VIDEO_ID_RE.match(playlist_id):
        raise ValueError("The playlist ID is invalid.")
    if video_id and not VIDEO_ID_RE.match(video_id):
        raise ValueError("The video ID is invalid.")
    if require_playlist and not playlist_id:
        raise ValueError("Enter a YouTube playlist URL (it must contain a list ID).")
    if not playlist_id and not video_id:
        raise ValueError("The URL does not contain a YouTube video or playlist.")
    # Do not pass tracking parameters or fragments to yt-dlp.
    if playlist_id:
        return f"https://www.youtube.com/playlist?list={playlist_id}"
    return f"https://www.youtube.com/watch?v={video_id}"


def sanitize_filename(name: str) -> str:
    """Make a filename safe on Windows, macOS and Linux."""
    cleaned = re.sub(r"[\x00-\x1f\\/:*?\"<>|]", "", str(name))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:180] or "untitled"


def vtt_to_text(vtt_file: Path) -> str:
    text = []
    timestamp_pattern = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3}")
    with vtt_file.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            line = re.sub(r"<[^>]+>", "", line.strip())
            if not line or line.startswith(("WEBVTT", "Kind:", "Language:")) or timestamp_pattern.search(line):
                continue
            if line.isdigit():
                continue
            text.append(line)
    return " ".join(text)


def convert_all_vtt_to_txt(root: Path = OUTPUT_DIR) -> None:
    for vtt in root.rglob("*.vtt") if root.exists() else ():
        txt_path = vtt.with_suffix(".txt")
        if not txt_path.exists():
            txt_path.write_text(vtt_to_text(vtt), encoding="utf-8")


class PlaylistTranscriptDownloader:
    """Download selected playlist entries and report per-video progress."""

    def __init__(
        self,
        playlist_url: str,
        languages: Iterable[str] | None = None,
        transcript_type: str = "both",
        progress_callback: Callable[[dict], None] | None = None,
        cancel_event=None,
        selected_videos: list[dict] | None = None,
        settings: dict | None = None,
    ):
        self.playlist_url = validate_youtube_url(playlist_url)
        self.languages = [str(language).strip().lower() for language in (languages or ["en"]) if str(language).strip()][:10]
        self.transcript_type = transcript_type
        self.progress_callback = progress_callback or (lambda progress: None)
        self.cancel_event = cancel_event
        self.selected_videos = selected_videos
        self.settings = settings or {}

    def _check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise DownloadCancelled()

    def _progress_hook(self, data):
        self._check_cancelled()
        if data.get("status") not in {"downloading", "finished"}:
            return
        self.progress_callback({
            "phase": "file",
            "file_status": data["status"],
            "percent": data.get("_percent_str", "").strip(),
        })

    def _output_root(self) -> Path:
        root = Path(self.settings.get("output_folder") or OUTPUT_DIR)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _output_path(self, root: Path, playlist_title: str, index: int, title: str, ext: str, video_id: str = "") -> Path:
        folder = root / sanitize_filename(playlist_title)
        fmt = self.settings.get("filename_format", "index_title")
        stem = sanitize_filename(title)
        if fmt == "title":
            filename = stem
        elif fmt == "title_id":
            filename = f"{stem} [{sanitize_filename(video_id)}]"
        else:
            filename = f"{index:02d} - {stem}"
        return folder / f"{filename}.{ext}"

    def _available_path(self, path: Path) -> Path | None:
        handling = self.settings.get("duplicate_handling", "skip")
        if not path.exists():
            return path
        if handling == "skip":
            return None
        if handling == "overwrite":
            return path
        for number in range(2, 1000):
            candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
            if not candidate.exists():
                return candidate
        raise ValueError("Too many duplicate files.")

    def download(self):
        selected = self.selected_videos or []
        if not selected:
            # A flat extraction is cheap and gives callers a useful fallback.
            with YoutubeDL({"quiet": True, "skip_download": True, "extract_flat": True, "playlistend": 500}) as ydl:
                info = ydl.extract_info(self.playlist_url, download=False)
            selected = [
                {"id": entry.get("id"), "url": entry.get("url") or entry.get("webpage_url"), "title": entry.get("title") or entry.get("id"), "index": entry.get("playlist_index") or number}
                for number, entry in enumerate(info.get("entries") or [], 1) if entry
            ]
        selected = selected[:200]
        total = len(selected)
        playlist_title = self.settings.get("playlist_title") or "YouTube playlist"
        failures = []
        completed = 0
        self.progress_callback({"status": "downloading", "current": 0, "total": total, "title": "Preparing playlist", "failures": failures})
        root = self._output_root()
        for sequence, video in enumerate(selected, 1):
            self._check_cancelled()
            number = int(video.get("index") or sequence)
            title = str(video.get("title") or video.get("id") or f"Video {number}")
            url = video.get("url") or video.get("webpage_url")
            if not url:
                failures.append({"index": number, "id": video.get("id"), "title": title, "error": "Video URL is missing."})
                continue
            self.progress_callback({"status": "downloading", "current": completed, "total": total, "title": title, "video_index": number, "failures": failures})
            folder = root / sanitize_filename(playlist_title)
            folder.mkdir(parents=True, exist_ok=True)
            # A literal index in the template is stable even when extracting one
            # video at a time (yt-dlp otherwise has no playlist_index).
            fmt = self.settings.get("filename_format", "index_title")
            prefix = "" if fmt == "title" else f"{number:02d} - "
            if fmt == "title_id":
                prefix = ""
            outtmpl = str(folder / f"{prefix}%(title)s%(id)s.%(ext)s")
            before_captions = set(folder.glob("*.vtt"))
            options = {
                "skip_download": True,
                "subtitleslangs": self.languages,
                "subtitlesformat": "vtt",
                "writesubtitles": self.transcript_type in {"manual", "both"},
                "writeautomaticsub": self.transcript_type in {"automatic", "both"},
                "outtmpl": outtmpl,
                "windowsfilenames": True,
                "quiet": True,
                "noprogress": True,
                "progress_hooks": [self._progress_hook],
                "ignoreerrors": False,
                "overwrites": self.settings.get("duplicate_handling") == "overwrite",
            }
            try:
                with YoutubeDL(options) as ydl:
                    ydl.download([url])
                # yt-dlp appends the ID only when %(id)s is in the template;
                # rename caption files into the selected stable naming scheme.
                found_caption = False
                candidates = [path for path in folder.glob("*.vtt") if path not in before_captions]
                if not candidates and video.get("id"):
                    candidates = list(folder.glob(f"*{sanitize_filename(video['id'])}.vtt"))
                for source in candidates:
                    found_caption = True
                    desired = self._output_path(root, playlist_title, number, title, "vtt", str(video.get("id") or ""))
                    caption_format = self.settings.get("caption_format", "both")
                    # TXT-only jobs use the TXT destination for duplicate
                    # decisions; otherwise an existing TXT could be replaced.
                    duplicate_target = desired.with_suffix(".txt") if caption_format == "txt" else desired
                    target = self._available_path(duplicate_target)
                    if target is None:
                        source.unlink(missing_ok=True)
                        continue
                    if caption_format == "txt":
                        txt = target
                        txt.write_text(vtt_to_text(source), encoding="utf-8")
                        source.unlink(missing_ok=True)
                        continue
                    if source != target:
                        source.replace(target)
                    txt = target.with_suffix(".txt")
                    if caption_format == "both":
                        if self.settings.get("duplicate_handling") == "skip" and txt.exists() and txt != target:
                            pass
                        else:
                            txt.write_text(vtt_to_text(target), encoding="utf-8")
                    else:
                        txt.unlink(missing_ok=True)
                if found_caption:
                    completed += 1
                else:
                    failures.append({"index": number, "id": video.get("id"), "title": title, "error": "No captions were available."})
            except DownloadCancelled:
                raise
            except Exception as error:
                failures.append({"index": number, "id": video.get("id"), "title": title, "error": str(error)[:500]})
            self.progress_callback({"status": "downloading", "current": completed, "total": total, "title": title, "video_index": number, "failures": failures})
        self.progress_callback({"status": "complete", "current": completed, "total": total, "title": "Download complete", "failures": failures})
        return {"completed": completed, "total": total, "failures": failures}


if __name__ == "__main__":
    PlaylistTranscriptDownloader(
        "https://www.youtube.com/playlist?list=PLNPUF5QyWU8O0Wd8QDh9KaM1ggsxspJ31"
    ).download()
