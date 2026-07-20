#!/usr/bin/env python3
"""
TikTok -> YouTube Shorts uploader.

Downloads your own TikTok videos (watermark-free, via yt-dlp) and uploads
them to your YouTube channel as Shorts.

Usage:
    python tiktok_to_youtube.py "https://www.tiktok.com/@you/video/123..."
    python tiktok_to_youtube.py URL1 URL2 URL3
    python tiktok_to_youtube.py --file links.txt
    python tiktok_to_youtube.py URL --privacy public
    python tiktok_to_youtube.py URL --download-only

See README.md for the one-time Google/YouTube setup.
"""

import argparse
import os
import sys

import yt_dlp

# --- YouTube API config -----------------------------------------------------
# Only pulled in when we actually upload, so --download-only works without
# any Google setup.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

DOWNLOAD_DIR = "downloads"


# --- Downloading ------------------------------------------------------------
def download_tiktok(url: str) -> dict:
    """Download a single TikTok. Returns dict with filepath, title, description."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    ydl_opts = {
        # Grab the best single mp4; TikTok's default is already watermark-free
        # from the source and yt-dlp does not add one.
        "format": "mp4/bestvideo+bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)

    # yt-dlp may remux to a different extension; find the real file.
    if not os.path.exists(filepath):
        base = os.path.splitext(filepath)[0]
        for ext in (".mp4", ".webm", ".mkv"):
            if os.path.exists(base + ext):
                filepath = base + ext
                break

    caption = (info.get("title") or info.get("description") or "").strip()
    return {
        "filepath": filepath,
        "title": caption or "TikTok video",
        "description": info.get("description", "") or caption,
        "uploader": info.get("uploader", ""),
    }


# --- YouTube auth + upload --------------------------------------------------
def get_youtube_service():
    """Authenticate (cached after first run) and return a YouTube API client."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, [YOUTUBE_UPLOAD_SCOPE])

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                sys.exit(
                    f"Missing {CLIENT_SECRETS_FILE}. See README.md for the one-time "
                    "Google Cloud / YouTube API setup."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, [YOUTUBE_UPLOAD_SCOPE]
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def build_shorts_metadata(video: dict, as_short: bool, privacy: str) -> dict:
    """Turn TikTok metadata into a YouTube upload body."""
    title = video["title"]
    description = video["description"]

    if as_short:
        # #Shorts in title/description is how YouTube classifies vertical uploads.
        if "#shorts" not in title.lower():
            title = f"{title} #Shorts"
        description = f"{description}\n\n#Shorts".strip()

    # YouTube titles cap at 100 chars.
    title = title[:100]

    return {
        "snippet": {
            "title": title or "Short",
            "description": description,
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }


def upload_to_youtube(youtube, video: dict, as_short: bool, privacy: str) -> str:
    """Upload a downloaded video. Returns the new YouTube video ID."""
    from googleapiclient.http import MediaFileUpload

    body = build_shorts_metadata(video, as_short, privacy)
    media = MediaFileUpload(video["filepath"], chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    upload {int(status.progress() * 100)}%")

    return response["id"]


# --- CLI --------------------------------------------------------------------
def collect_urls(args) -> list:
    urls = list(args.urls)
    if args.file:
        with open(args.file) as f:
            urls += [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return urls


def main():
    parser = argparse.ArgumentParser(
        description="Download your TikToks and upload them to YouTube as Shorts."
    )
    parser.add_argument("urls", nargs="*", help="One or more TikTok video URLs")
    parser.add_argument("--file", help="Text file with one TikTok URL per line")
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="YouTube privacy status (default: private, so you can review first)",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download from TikTok; skip the YouTube upload",
    )
    parser.add_argument(
        "--no-shorts",
        action="store_true",
        help="Upload as a regular video instead of tagging it as a Short",
    )
    args = parser.parse_args()

    urls = collect_urls(args)
    if not urls:
        parser.error("Give at least one TikTok URL, or use --file links.txt")

    youtube = None if args.download_only else get_youtube_service()

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")
        try:
            video = download_tiktok(url)
            print(f"    downloaded: {os.path.basename(video['filepath'])}")
            print(f"    title: {video['title']}")

            if args.download_only:
                continue

            video_id = upload_to_youtube(
                youtube, video, as_short=not args.no_shorts, privacy=args.privacy
            )
            print(f"    uploaded: https://youtube.com/watch?v={video_id} ({args.privacy})")
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)

    print("\nDone.")


if __name__ == "__main__":
    main()
