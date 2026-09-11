# Archive Transcript Library

A local web application for downloading, organizing, and reading YouTube playlist transcripts.

## Project guidance

- [CLAUDE.md](CLAUDE.md): AI coding assistant guidance
- [AGENTS.md](AGENTS.md): automated agent instructions
- [CONTRIBUTING.md](CONTRIBUTING.md): contribution workflow
- [TESTING.md](TESTING.md): testing standards
- [SECURITY.md](SECURITY.md): security practices
- [DEPLOYMENT.md](DEPLOYMENT.md): deployment checklist

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

### Automatic Vercel deployment

The [Vercel GitHub Actions workflow](.github/workflows/vercel-deploy.yml) deploys the frontend automatically whenever code is pushed to `main`. It can also be started manually from the GitHub Actions tab.

Add these repository secrets in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `VERCEL_TOKEN` | A Vercel personal access token |
| `VERCEL_ORG_ID` | The Vercel team or account ID |
| `VERCEL_PROJECT_ID` | The Vercel project ID |

You can find the project and organization IDs in the Vercel project settings or by running:

```bash
vercel link
cat .vercel/project.json
```

To make downloads work from the Vercel deployment, host `website.py` and its worker on Render, Railway, Fly.io, or a VPS, then update the API requests in [app.js](app.js) to use that backend URL and configure CORS.

### Deploy the Python backend to Render

The repository includes [render.yaml](render.yaml). In Render, choose **New → Blueprint** and connect this repository. Render will create the Python web service using the included build and start commands.

After deployment, copy the Render service URL, for example:

```text
https://archive-transcript-api.onrender.com
```

Set that URL in the `window.ARCHIVE_API_URL` block in both [index.html](index.html) and [download.html](download.html), then push to `main`:

```html
<script>
  window.ARCHIVE_API_URL = "https://archive-transcript-api.onrender.com";
</script>
```

The Render free service may sleep when idle and can take approximately one minute to wake up. Its local SQLite database and transcript files are not durable across restarts; use persistent storage for production data.

The frontend reads the optional `window.ARCHIVE_API_URL` value as the backend base URL. For example, add this before `app.js` in both HTML pages:

```html
<script>
  window.ARCHIVE_API_URL = "https://your-python-backend.example.com";
</script>
<script src="/app.js"></script>
```

Without this backend URL, the Vercel deployment is frontend-only and playlist preview/download requests cannot work.

For public deployment, use a host that supports long-running Python processes or a VPS. A typical architecture is:

```text
Frontend        Vercel or a static host
Python worker   Render, Railway, Fly.io, or a VPS
Database        Managed PostgreSQL or SQLite on a persistent disk
File storage    Object storage or a persistent volume
```

Serverless-only hosting is not recommended for the downloader because playlist downloads can run longer than a serverless function timeout and local files are not persistent there.

## Vercel Analytics

The static pages load Vercel Web Analytics through `@vercel/analytics`. The bundle is generated during the Vercel build:

```bash
npm install
npm run build
```

After deployment, enable **Web Analytics** in the Vercel project dashboard. Analytics data is collected from the deployed Vercel domain, not from `localhost`.

## Project structure

```text
index.html       Transcript library page
download.html    Playlist downloader page
app.js           Browser behavior and API integration
styles.css       Shared application styling
analytics.js     Vercel Analytics entrypoint
package.json     Frontend dependencies and build script
website.py       HTTP server, API, SQLite jobs, and worker queue
main.py          YouTube transcript downloader
transcripts/     Downloaded transcript library
```
