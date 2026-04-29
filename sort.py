import os
import pickle
import re
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# =========================
# LOAD ENV
# =========================
load_dotenv()

CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "token.pickle")
SOURCE_PLAYLIST = os.getenv("SOURCE_PLAYLIST", "WL")
SOURCE_VIDEO_IDS_FILE = os.getenv("SOURCE_VIDEO_IDS_FILE")
TARGET_PLAYLIST_NAME = os.getenv("TARGET_PLAYLIST_NAME", "Sorted Playlist")
PLAYLIST_PRIVACY = os.getenv("PLAYLIST_PRIVACY", "private")
OAUTH_HOST = os.getenv("YOUTUBE_OAUTH_HOST", "127.0.0.1")
OAUTH_PORT = int(os.getenv("YOUTUBE_OAUTH_PORT", "8765"))
OAUTH_OPEN_BROWSER = os.getenv("YOUTUBE_OAUTH_OPEN_BROWSER", "false").lower() == "true"

SCOPES = ["https://www.googleapis.com/auth/youtube"]

ISO8601_DURATION_RE = re.compile(
    r"^P"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)


def parse_duration_seconds(duration_iso):
    match = ISO8601_DURATION_RE.fullmatch(duration_iso)
    if not match:
        raise ValueError(f"Unsupported ISO-8601 duration: {duration_iso}")

    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return (((days * 24) + hours) * 60 + minutes) * 60 + seconds


def normalize_playlist_id(value):
    if not value:
        raise ValueError("SOURCE_PLAYLIST is empty")

    if "youtube.com" in value or "youtu.be" in value:
        parsed = urlparse(value)
        playlist_id = parse_qs(parsed.query).get("list", [None])[0]
        if playlist_id:
            return playlist_id
        raise ValueError(f"Could not extract playlist ID from URL: {value}")

    return value


def normalize_video_id(value):
    value = value.strip()
    if not value:
        return None

    if "youtube.com" in value or "youtu.be" in value:
        parsed = urlparse(value)
        if parsed.netloc == "youtu.be":
            return parsed.path.lstrip("/") or None
        return parse_qs(parsed.query).get("v", [None])[0]

    return value


def load_video_ids_from_file(path):
    with open(path, "r", encoding="utf-8") as handle:
        raw_lines = handle.readlines()

    video_ids = []
    seen = set()
    for raw_line in raw_lines:
        video_id = normalize_video_id(raw_line)
        if video_id and video_id not in seen:
            seen.add(video_id)
            video_ids.append(video_id)

    if not video_ids:
        raise RuntimeError(f"No video IDs found in {path}")

    return video_ids


def validate_playlist_items(source_playlist, video_ids):
    if video_ids:
        return

    if source_playlist == "WL":
        raise RuntimeError(
            "SOURCE_PLAYLIST=WL returned 0 videos. Watch Later is not exposed as a "
            "normal playlist by the YouTube Data API. Use a real playlist ID or "
            "playlist URL instead."
        )

    raise RuntimeError(
        f"Source playlist '{source_playlist}' returned 0 videos. Check that the "
        "playlist ID is correct and that the authenticated account can read it."
    )

# =========================
# AUTH
# =========================
def get_authenticated_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET, SCOPES
        )
        print(
            "Starting OAuth callback server at "
            f"http://{OAUTH_HOST}:{OAUTH_PORT}/"
        )
        print(
            "If you're connected over SSH, forward the port from your host with:"
        )
        print(
            f"  ssh -L {OAUTH_PORT}:127.0.0.1:{OAUTH_PORT} <vm-host>"
        )
        creds = flow.run_local_server(
            host=OAUTH_HOST,
            port=OAUTH_PORT,
            open_browser=OAUTH_OPEN_BROWSER
        )

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


# =========================
# FETCH PLAYLIST ITEMS
# =========================
def get_all_playlist_items(youtube, playlist_id):
    items = []
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=50
    )

    while request:
        response = request.execute()
        items.extend(response["items"])
        request = youtube.playlistItems().list_next(request, response)

    return items


def find_playlist_by_title(youtube, title):
    request = youtube.playlists().list(
        part="snippet",
        mine=True,
        maxResults=50
    )

    while request:
        response = request.execute()
        for item in response["items"]:
            if item["snippet"]["title"] == title:
                return item["id"]
        request = youtube.playlists().list_next(request, response)

    return None


# =========================
# GET VIDEO DURATIONS
# =========================
def get_video_durations(youtube, video_ids):
    durations = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        request = youtube.videos().list(
            part="contentDetails",
            id=",".join(batch)
        )
        response = request.execute()

        for item in response["items"]:
            duration_iso = item["contentDetails"]["duration"]
            duration_seconds = parse_duration_seconds(duration_iso)
            durations[item["id"]] = duration_seconds

    return durations


# =========================
# CREATE PLAYLIST
# =========================
def create_playlist(youtube, title, privacy):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": "Sorted automatically by duration (shortest → longest)"
            },
            "status": {
                "privacyStatus": privacy
            }
        }
    )
    response = request.execute()
    return response["id"]


def get_or_create_playlist(youtube, title, privacy):
    existing_playlist_id = find_playlist_by_title(youtube, title)
    if existing_playlist_id:
        print(f"Using existing playlist: {existing_playlist_id}")
        return existing_playlist_id

    print("Creating new playlist...")
    return create_playlist(youtube, title, privacy)


def clear_playlist(youtube, playlist_id):
    items = get_all_playlist_items(youtube, playlist_id)
    if not items:
        return

    print(f"Clearing {len(items)} existing videos from target playlist...")
    for item in items:
        youtube.playlistItems().delete(id=item["id"]).execute()


# =========================
# ADD VIDEOS TO PLAYLIST
# =========================
def add_videos_to_playlist(youtube, playlist_id, video_ids):
    for i, vid in enumerate(video_ids):
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": vid
                    },
                    "position": i
                }
            }
        ).execute()


# =========================
# MAIN
# =========================
def main():
    youtube = get_authenticated_service()
    if SOURCE_VIDEO_IDS_FILE:
        print(f"Loading video IDs from {SOURCE_VIDEO_IDS_FILE}...")
        video_ids = load_video_ids_from_file(SOURCE_VIDEO_IDS_FILE)
    else:
        source_playlist = normalize_playlist_id(SOURCE_PLAYLIST)

        print("Fetching playlist videos...")
        items = get_all_playlist_items(youtube, source_playlist)

        video_ids = [
            item["contentDetails"]["videoId"]
            for item in items
        ]
        validate_playlist_items(source_playlist, video_ids)

    print(f"Found {len(video_ids)} videos")

    print("Fetching durations...")
    durations = get_video_durations(youtube, video_ids)

    print("Sorting...")
    sorted_videos = sorted(video_ids, key=lambda vid: durations.get(vid, 0))

    playlist_id = get_or_create_playlist(
        youtube,
        TARGET_PLAYLIST_NAME,
        PLAYLIST_PRIVACY
    )
    clear_playlist(youtube, playlist_id)

    print("Adding videos in sorted order...")
    add_videos_to_playlist(youtube, playlist_id, sorted_videos)

    print("Done!")
    print(f"New playlist ID: {playlist_id}")


if __name__ == "__main__":
    main()
