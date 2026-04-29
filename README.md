# YouTube Watch Later Sorter

Sort your YouTube Watch Later videos by duration (shortest → longest).

## How it works

YouTube's Data API does **not** expose the Watch Later (WL) playlist directly. This tool works around that limitation in two steps:

1. **Extract** video IDs from the Watch Later page using a browser console script.
2. **Sort** those videos by length and place them into a new (or existing) playlist via the YouTube Data API.

## Requirements

- Python 3.10+
- A Google Cloud project with the YouTube Data API v3 enabled
- An OAuth 2.0 Client ID (desktop application type)

## Setup

### 1. Clone & install

```bash
git clone github.com/Fluffy-Bunny-23/yt-wl-sorter.git
pip install -r requirements.txt
```

### 2. Get API credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or select an existing one).
3. Enable the **YouTube Data API v3**.
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**.
5. Choose **Desktop app**, give it a name, and download the JSON file.
6. Rename it to `client_secret.json` and place it in the project root.

### 3. Configure

Copy the template below into a `.env` file in the project root and adjust as needed:

```env
YOUTUBE_CLIENT_SECRET=client_secret.json
YOUTUBE_TOKEN_FILE=token.pickle
SOURCE_PLAYLIST=WL
SOURCE_VIDEO_IDS_FILE=watch_later_ids.txt
TARGET_PLAYLIST_NAME=Watch Later (Sorted by Length)
PLAYLIST_PRIVACY=private
YOUTUBE_OAUTH_HOST=127.0.0.1
YOUTUBE_OAUTH_PORT=8765
YOUTUBE_OAUTH_OPEN_BROWSER=false
```

| Variable | Default | Description |
|---|---|---|
| `YOUTUBE_CLIENT_SECRET` | `client_secret.json` | Path to your OAuth client secret JSON file |
| `YOUTUBE_TOKEN_FILE` | `token.pickle` | Where to cache the OAuth token (auto-generated after first login) |
| `SOURCE_PLAYLIST` | `WL` | Source playlist ID or URL. If using `SOURCE_VIDEO_IDS_FILE`, this is ignored |
| `SOURCE_VIDEO_IDS_FILE` | *(empty)* | Path to a text file with video IDs (one per line) — overrides `SOURCE_PLAYLIST` |
| `TARGET_PLAYLIST_NAME` | `Sorted Playlist` | Name of the output playlist (created if it doesn't exist) |
| `PLAYLIST_PRIVACY` | `private` | Privacy of the output playlist: `private`, `unlisted`, or `public` |
| `YOUTUBE_OAUTH_HOST` | `127.0.0.1` | Host for the local OAuth callback server |
| `YOUTUBE_OAUTH_PORT` | `8765` | Port for the local OAuth callback server |
| `YOUTUBE_OAUTH_OPEN_BROWSER` | `false` | Set to `true` to auto-open the browser during OAuth |

## Usage

### Step 1 — Extract Watch Later video IDs

YouTube's API doesn't let us read the Watch Later playlist directly, so we use a browser trick instead.

1. Open [youtube.com/playlist?list=WL](https://youtube.com/playlist?list=WL) and log in.
2. Open the **Developer Console** (F12 → Console).
3. Paste the contents of `extract_watch_later_ids.js` and press Enter.
4. The script will scroll through the page, collecting video IDs. Wait for it to finish.
5. Copy the printed IDs and save them into `watch_later_ids.txt` (one ID per line).

> **Tip:** If you have hundreds of videos, the script may take a minute or two to scroll through them all. Be patient!

### Step 2 — Sort and create the sorted playlist

```bash
python sort.py
```

The script will:

1. Launch a browser window asking you to log in to Google and grant access (one-time setup — the token is cached afterward).
2. Read video IDs from `watch_later_ids.txt` (or fetch them from `SOURCE_PLAYLIST` if the file option is not set).
3. Fetch durations from the YouTube API.
4. Sort videos by duration (shortest first).
5. Create (or reuse) a playlist named `Watch Later (Sorted by Length)`.
6. Clear the playlist and add videos in sorted order.

### Alternative: Use a regular playlist as source

If your videos are already in a normal (non-WL) YouTube playlist, you can skip the browser script. Just point `SOURCE_PLAYLIST` at the playlist ID or URL, leave `SOURCE_VIDEO_IDS_FILE` empty, and run `sort.py` directly.

## Files

| File | Purpose |
|---|---|
| `sort.py` | Main script — fetches durations, sorts, and creates the output playlist |
| `extract_watch_later_ids.js` | Browser console script to extract video IDs from the Watch Later page |
| `.env` | Configuration |
| `client_secret.json` | Your OAuth client secret (not committed to git) |
| `token.pickle` | Cached OAuth token (generated after first login, not committed) |
| `watch_later_ids.txt` | Video IDs extracted from the browser (not committed) |

This project was made by GPT-5.4 on Codex and the README was written by Kimi 2.6 Precision from CrofAI in Opencode.
