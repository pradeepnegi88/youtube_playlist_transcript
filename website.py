"""Small local HTTP application for the transcript library and job queue."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
import json
import os
import queue
import re
import sqlite3
import threading
import time
import uuid

from yt_dlp import YoutubeDL
from main import (
    DownloadCancelled,
    PlaylistTranscriptDownloader,
    sanitize_filename,
    validate_youtube_url,
)

ROOT = Path(__file__).parent.resolve()
TRANSCRIPT_ROOTS = [ROOT / "transcripts", ROOT / "Learn German in Hindi"]
PORT = int(os.environ.get("PORT", "8000"))
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "https://youtube-playlist-transcript-sitt.vercel.app")
DB_PATH = ROOT / "jobs.sqlite3"
MAX_BODY = 128 * 1024
MAX_ENTRIES = 200
MAX_QUEUE = 20
JOB_QUEUE = queue.Queue(MAX_QUEUE)
STOP_EVENTS = {}
DB_LOCK = threading.RLock()


def db():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL,
                current INTEGER DEFAULT 0, total INTEGER DEFAULT 0, title TEXT,
                failures TEXT NOT NULL DEFAULT '[]', error TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            )"""
        )
        connection.commit()


def update_job(job_id, **values):
    if not values:
        return
    values["updated_at"] = time.time()
    assignments = ", ".join(f"{key} = ?" for key in values)
    with DB_LOCK, db() as connection:
        connection.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", (*values.values(), job_id))
        connection.commit()


def get_job(job_id):
    with DB_LOCK, db() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["payload"] = json.loads(result.pop("payload"))
    result["failures"] = json.loads(result["failures"] or "[]")
    result.pop("cancel_requested", None)
    return result


def title_from_filename(filename: str) -> str:
    title = re.sub(r"^\d+\s*-\s*", "", filename)
    return re.sub(r"\.(?:en|hi)\.txt$", "", title).strip()


def track_name(path: Path) -> str:
    if path.parent == ROOT / "Learn German in Hindi":
        return "Learn German in Hindi"
    return path.parent.name


def catalog() -> list[dict]:
    items = []
    for root in TRANSCRIPT_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.txt")):
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            items.append({"id": relative, "title": title_from_filename(path.name), "track": track_name(path),
                          "path": relative, "words": len(text.split()), "preview": " ".join(text.split())[:180]})
    return items


def preview_playlist(url: str) -> dict:
    safe_url = validate_youtube_url(url, require_playlist=True)
    options = {"quiet": True, "skip_download": True, "extract_flat": True, "playlistend": MAX_ENTRIES}
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(safe_url, download=False)
    videos = []
    for index, entry in enumerate(info.get("entries") or [], 1):
        if not entry:
            continue
        video_id = str(entry.get("id") or "")
        videos.append({"index": entry.get("playlist_index") or index, "id": video_id,
                       "title": entry.get("title") or video_id,
                       "duration": entry.get("duration"), "url": entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
                       "thumbnail": entry.get("thumbnail")})
    return {"title": info.get("title") or "YouTube playlist", "channel": info.get("channel") or info.get("uploader"),
            "count": len(videos), "videos": videos}


def worker():
    while True:
        job_id = JOB_QUEUE.get()
        if job_id is None:
            JOB_QUEUE.task_done()
            return
        job = get_job(job_id)
        if not job:
            JOB_QUEUE.task_done()
            continue
        payload = job["payload"]
        update_job(job_id, status="downloading", error=None)
        try:
            def progress(event):
                failures = event.get("failures", job.get("failures", []))
                update_job(job_id, current=event.get("current", 0), total=event.get("total", 0),
                           title=event.get("title", "Working"), failures=json.dumps(failures, ensure_ascii=False))

            downloader = PlaylistTranscriptDownloader(
                payload["playlist_url"], payload.get("languages", ["en"]), payload.get("transcript_type", "both"),
                progress_callback=progress, cancel_event=STOP_EVENTS[job_id],
                selected_videos=payload.get("videos"), settings=payload.get("settings", {}),
            )
            result = downloader.download()
            if STOP_EVENTS[job_id].is_set():
                update_job(job_id, status="cancelled", title="Download cancelled",
                           failures=json.dumps(result.get("failures", []), ensure_ascii=False))
            else:
                update_job(job_id, status="complete" if not result["failures"] else "complete_with_errors",
                           title="Download complete", current=result["completed"], total=result["total"],
                           failures=json.dumps(result["failures"], ensure_ascii=False))
        except DownloadCancelled:
            update_job(job_id, status="cancelled", title="Download cancelled")
        except Exception as error:
            update_job(job_id, status="error", error=str(error)[:500], title="Download failed")
        finally:
            STOP_EVENTS.pop(job_id, None)
            JOB_QUEUE.task_done()


def start_workers():
    init_db()
    # Jobs survive a process restart.  A job that was running during the
    # restart is safe to resume because each caption is written atomically.
    with DB_LOCK, db() as connection:
        connection.execute("UPDATE jobs SET status='queued', updated_at=? WHERE status IN ('downloading','cancelling')", (time.time(),))
        pending = [row["id"] for row in connection.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created_at")]
        connection.commit()
    for _ in range(2):
        threading.Thread(target=worker, daemon=True, name="transcript-worker").start()
    for job_id in pending[:MAX_QUEUE]:
        STOP_EVENTS[job_id] = threading.Event()
        try:
            JOB_QUEUE.put_nowait(job_id)
        except queue.Full:
            break


class TranscriptHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def read_payload(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            raise ValueError("Request is too large.")
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/catalog":
            self.send_json(catalog()); return
        if parsed.path.startswith("/api/transcript/"):
            relative = unquote(parsed.path.removeprefix("/api/transcript/"))
            requested = (ROOT / relative).resolve()
            allowed = any(root.resolve() in requested.parents for root in TRANSCRIPT_ROOTS)
            if not allowed or requested.suffix != ".txt" or not requested.is_file():
                self.send_error(404, "Transcript not found"); return
            self.send_json({"title": title_from_filename(requested.name), "track": track_name(requested),
                            "content": requested.read_text(encoding="utf-8", errors="replace")}); return
        match = re.fullmatch(r"/api/download/status/([a-f0-9]{32})", parsed.path)
        if match:
            job = get_job(match.group(1))
            if not job:
                self.send_error(404, "Download job not found")
            else:
                self.send_json(job)
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self.read_payload()
            if parsed.path == "/api/preview":
                self.send_json(preview_playlist(payload.get("playlist_url", ""))); return
            if parsed.path == "/api/download":
                self.create_download(payload); return
            match = re.fullmatch(r"/api/download/([a-f0-9]{32})/(cancel|retry)", parsed.path)
            if match:
                self.change_job(match.group(1), match.group(2), payload); return
            self.send_error(404, "Endpoint not found")
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, status=400)
        except Exception as error:
            self.send_json({"error": str(error)[:500]}, status=502)

    def create_download(self, payload):
        playlist_url = validate_youtube_url(payload.get("playlist_url", ""), require_playlist=False)
        languages = payload.get("languages", "en")
        if isinstance(languages, str):
            languages = [item.strip().lower() for item in languages.split(",") if item.strip()]
        if not languages or len(languages) > 10 or any(not re.fullmatch(r"[a-z]{2,8}(?:-[A-Z]{2})?", item) for item in languages):
            raise ValueError("Use up to ten valid language codes.")
        transcript_type = payload.get("transcript_type", "both")
        if transcript_type not in {"manual", "automatic", "both"}:
            raise ValueError("Choose a valid caption source.")
        videos = payload.get("videos") or []
        if len(videos) > MAX_ENTRIES:
            raise ValueError(f"Select no more than {MAX_ENTRIES} videos.")
        normalized_videos = []
        for video in videos:
            if not isinstance(video, dict):
                raise ValueError("Invalid video selection.")
            video = dict(video)
            video["url"] = validate_youtube_url(video.get("url", ""))
            if video.get("id") and not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", str(video["id"])):
                raise ValueError("Invalid video selection.")
            video["title"] = str(video.get("title") or video.get("id") or "Video")[:300]
            normalized_videos.append(video)
        videos = normalized_videos
        settings = payload.get("settings") or {}
        if not isinstance(settings, dict) or len(str(settings.get("output_folder", ""))) > 200:
            raise ValueError("Download settings are too large.")
        settings["caption_format"] = settings.get("caption_format", "both")
        settings["filename_format"] = settings.get("filename_format", "index_title")
        settings["duplicate_handling"] = settings.get("duplicate_handling", "skip")
        if settings["caption_format"] not in {"vtt", "txt", "both"} or settings["filename_format"] not in {"index_title", "title", "title_id"} or settings["duplicate_handling"] not in {"skip", "overwrite", "rename"}:
            raise ValueError("Invalid download settings.")
        output = Path(settings.get("output_folder") or "transcripts")
        if output.is_absolute() or ".." in output.parts:
            raise ValueError("Output folder must be inside this application.")
        resolved_output = (ROOT / output).resolve()
        if ROOT != resolved_output and ROOT not in resolved_output.parents:
            raise ValueError("Output folder must be inside this application.")
        settings["output_folder"] = str(resolved_output)
        if not videos:
            # The API remains useful for callers that skip the preview step;
            # persist the expanded list so failed entries can still be retried.
            preview = preview_playlist(playlist_url)
            videos = preview["videos"]
            settings["playlist_title"] = settings.get("playlist_title") or preview["title"]
        if len(videos) == 0:
            raise ValueError("The playlist contains no selectable videos.")
        job_id = uuid.uuid4().hex
        now = time.time()
        job_payload = {"playlist_url": playlist_url, "languages": languages, "transcript_type": transcript_type,
                       "videos": videos, "settings": settings}
        with DB_LOCK, db() as connection:
            connection.execute("INSERT INTO jobs(id,payload,status,title,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                               (job_id, json.dumps(job_payload, ensure_ascii=False), "queued", "Waiting for worker", now, now))
            connection.commit()
        if JOB_QUEUE.full():
            update_job(job_id, status="error", error="The download queue is full.")
            raise ValueError("The download queue is full.")
        STOP_EVENTS[job_id] = threading.Event()
        JOB_QUEUE.put_nowait(job_id)
        self.send_json({"id": job_id, "status": "queued"})

    def change_job(self, job_id, action, payload):
        job = get_job(job_id)
        if not job:
            self.send_json({"error": "Download job not found."}, 404); return
        if action == "cancel":
            STOP_EVENTS.setdefault(job_id, threading.Event()).set()
            update_job(job_id, status="cancelling", title="Cancelling download")
            self.send_json({"ok": True}); return
        if job["status"] not in {"complete_with_errors", "error", "cancelled"}:
            raise ValueError("Only failed or cancelled jobs can be retried.")
        failed = job["failures"]
        wanted = payload.get("video_ids") if isinstance(payload, dict) else None
        if wanted:
            failed = [item for item in failed if item.get("id") in wanted]
        videos = [item for item in job["payload"].get("videos", []) if any(item.get("id") == failure.get("id") for failure in failed)]
        job["payload"]["videos"] = videos
        now = time.time()
        with DB_LOCK, db() as connection:
            connection.execute("UPDATE jobs SET payload=?,status='queued',error=NULL,failures='[]',current=0,total=?,updated_at=? WHERE id=?",
                               (json.dumps(job["payload"], ensure_ascii=False), len(videos), now, job_id)); connection.commit()
        STOP_EVENTS[job_id] = threading.Event(); JOB_QUEUE.put_nowait(job_id)
        self.send_json({"ok": True, "id": job_id})


start_workers()

if __name__ == "__main__":
    print(f"Transcript library running at http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), TranscriptHandler).serve_forever()
