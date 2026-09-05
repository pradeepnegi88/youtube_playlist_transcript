# Archive Transcript Library

A local web application for downloading, organizing, and reading YouTube playlist transcripts.

## Features

- Preview a YouTube playlist before downloading
- Select individual videos
- Download manual captions, automatic captions, or both
- Choose transcript languages such as `en` or `hi`
- Save VTT, TXT, or both formats
- Configure filenames and duplicate handling
- Track download progress in the browser
- Cancel downloads and retry failed videos
- Persistent download jobs using SQLite
- Search and filter the transcript library
- Read transcripts with:
  - Table of contents
  - Reading time
  - Font size controls
  - Light/dark theme
  - Search highlighting
  - Copy and download actions

## Requirements

- Python 3.10+
- `pip`
- Internet access for YouTube metadata and captions

## Setup

Install the Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Start the web application:

```bash
python3 website.py
```

Open the application:

```text
http://localhost:8000
```

## Pages

### Transcript library

```text
http://localhost:8000/
```

Browse, search, filter, and read downloaded transcripts.

### Playlist downloader

```text
http://localhost:8000/download.html
```

Paste a YouTube playlist URL, preview its videos, choose the videos to download, and configure the download settings.

## Download settings

- **Languages:** comma-separated language codes, for example `en, hi`
- **Caption source:** manual, automatic, or both
- **Output folder:** must remain inside the project directory
- **File types:** VTT, TXT, or VTT + TXT
- **Filename format:** indexed title, title, or title with video ID
- **Duplicates:** skip, overwrite, or rename

Downloaded files are stored under the selected output folder, grouped by playlist name.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/preview` | Fetch playlist metadata and videos |
| `POST` | `/api/download` | Create a background download job |
| `GET` | `/api/download/status/<job-id>` | Read job progress |
| `POST` | `/api/download/<job-id>/cancel` | Cancel a running job |
| `POST` | `/api/download/<job-id>/retry` | Retry failed videos |
| `GET` | `/api/catalog` | List available TXT transcripts |
| `GET` | `/api/transcript/<path>` | Read a transcript |

Download jobs are persisted in `jobs.sqlite3`. This file is generated at runtime and should not be committed.

## Command-line downloader

The downloader can also be used directly from Python:

```bash
python3 main.py
```

The reusable `PlaylistTranscriptDownloader` class is defined in [main.py](main.py).

## Deployment notes

This application is designed first for local use. The downloader uses `yt-dlp`, background workers, SQLite, and local transcript files.

### Deploy the frontend to Vercel

The repository includes [vercel.json](vercel.json) for deploying the static frontend:

```bash
npm install -g vercel
vercel
```

Vercel will serve the library and downloader pages, but it will not run the Python `yt-dlp` worker or provide the local transcript files. Without a hosted API, the deployed UI will show a connection message instead of transcript data.

To make downloads work from the Vercel deployment, host `website.py` and its worker on Render, Railway, Fly.io, or a VPS, then update the API requests in [app.js](app.js) to use that backend URL and configure CORS.

For public deployment, use a host that supports long-running Python processes or a VPS. A typical architecture is:

```text
Frontend        Vercel or a static host
Python worker   Render, Railway, Fly.io, or a VPS
Database        Managed PostgreSQL or SQLite on a persistent disk
File storage    Object storage or a persistent volume
```

Serverless-only hosting is not recommended for the downloader because playlist downloads can run longer than a serverless function timeout and local files are not persistent there.

## Project structure

```text
index.html       Transcript library page
download.html    Playlist downloader page
app.js           Browser behavior and API integration
styles.css       Shared application styling
website.py       HTTP server, API, SQLite jobs, and worker queue
main.py          YouTube transcript downloader
transcripts/     Downloaded transcript library
```
