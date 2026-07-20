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
import json
import os
import re
import sys

import yt_dlp

# --- YouTube API config -----------------------------------------------------
# Only pulled in when we actually upload, so --download-only works without
# any Google setup.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

DOWNLOAD_DIR = "downloads"

# Remembers which TikToks have already been uploaded, so re-runs skip them.
UPLOADED_FILE = "uploaded.json"


# --- Upload history (duplicate prevention) ----------------------------------
def load_uploaded() -> dict:
    """Load the {tiktok_id: youtube_id} record of past uploads."""
    try:
        with open(UPLOADED_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_uploaded(record: dict) -> None:
    with open(UPLOADED_FILE, "w") as f:
        json.dump(record, f, indent=2)


def extract_tiktok_id(url: str):
    """Pull the numeric video id out of a TikTok URL, or None."""
    m = re.search(r"/video/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"(\d{6,})", url)  # fallback for other URL shapes
    return m.group(1) if m else None


# --- Downloading ------------------------------------------------------------
def _cookie_opts(cookies_browser):
    """yt-dlp options for borrowing login cookies from a local browser.

    TikTok often refuses to list/serve videos to anonymous requests; using the
    cookies from a browser where you're logged in gets past that.
    """
    if cookies_browser:
        return {"cookiesfrombrowser": (cookies_browser, None, None, None)}
    return {}


def download_tiktok(url: str, cookies_browser=None) -> dict:
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
        **_cookie_opts(cookies_browser),
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
        "id": str(info.get("id", "")),
        "filepath": filepath,
        "title": caption or "TikTok video",
        "description": info.get("description", "") or caption,
        "uploader": info.get("uploader", ""),
    }


def is_profile_url(url: str) -> bool:
    """True for a profile/channel URL (a whole account) vs a single video."""
    return "/@" in url and "/video/" not in url


def expand_profile(url: str, cookies_browser=None) -> list:
    """Given a TikTok profile URL, return every video URL on that account."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",  # list entries without downloading
        "skip_download": True,
        **_cookie_opts(cookies_browser),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries") or []
    uploader = info.get("uploader", "")
    urls = []
    for e in entries:
        if not e:
            continue
        u = e.get("url") or e.get("webpage_url")
        if u and u.startswith("http"):
            urls.append(u)
        elif e.get("id"):
            who = e.get("uploader") or uploader
            urls.append(f"https://www.tiktok.com/@{who}/video/{e['id']}")
    return urls


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

    # Scheduled/unattended runs set this so we never hang waiting on a browser.
    noninteractive = os.environ.get("TIKTOK_NONINTERACTIVE") == "1"

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.exceptions import RefreshError

            try:
                creds.refresh(Request())
            except RefreshError:
                if noninteractive:
                    sys.exit(
                        "YouTube login expired and can't refresh unattended.\n"
                        "This usually means your Google OAuth app is still in "
                        "'Testing' mode (those logins expire every 7 days).\n"
                        "Fix: publish the app to Production (see README, "
                        "'Keeping the daily job logged in'), then run the tool "
                        "once by hand to sign in again."
                    )
                creds = None  # fall through to interactive sign-in below
        if not creds or not creds.valid:
            if noninteractive:
                sys.exit(
                    "YouTube sign-in required but running unattended. Run the "
                    "tool once by hand (or open the app) to sign in first."
                )
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


def _strip_hashtags(text: str) -> str:
    """Remove #hashtag tokens from a caption, leaving any real words behind."""
    words = [w for w in text.split() if not w.startswith("#")]
    return " ".join(words).strip()


def build_shorts_metadata(
    video: dict, as_short: bool, privacy: str, hashtags: str = None
) -> dict:
    """Turn TikTok metadata into a YouTube upload body."""
    title = video["title"]
    description = video["description"]

    if hashtags:
        # Replace the TikTok hashtags with the user's own set. Keep any
        # non-hashtag caption text (usually there's none), then append.
        base_title = _strip_hashtags(title)
        base_desc = _strip_hashtags(description)
        title = f"{base_title} {hashtags}".strip()
        description = f"{base_desc}\n\n{hashtags}".strip()

    if as_short:
        # #Shorts in title/description is how YouTube classifies vertical uploads.
        if "#shorts" not in title.lower():
            title = f"{title} #Shorts"
        if "#shorts" not in description.lower():
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


def upload_to_youtube(
    youtube, video: dict, as_short: bool, privacy: str, hashtags: str = None
) -> str:
    """Upload a downloaded video. Returns the new YouTube video ID."""
    from googleapiclient.http import MediaFileUpload

    body = build_shorts_metadata(video, as_short, privacy, hashtags)
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


# --- Core job (shared by the CLI and the GUI) -------------------------------
def expand_urls(raw_urls, cookies_browser=None) -> list:
    """Expand any profile URLs in the list into their individual video URLs."""
    urls = []
    for url in raw_urls:
        if is_profile_url(url):
            print(f"Fetching all videos from profile: {url}")
            try:
                found = expand_profile(url, cookies_browser)
            except Exception as e:
                print(f"  Could not list this profile: {e}", file=sys.stderr)
                if not cookies_browser:
                    print(
                        "  TikTok often hides an account's video list from logged-out\n"
                        "  requests. Try adding your browser cookies (chrome/edge/...).",
                        file=sys.stderr,
                    )
                continue
            print(f"  found {len(found)} videos")
            urls += found
        else:
            urls.append(url)
    return urls


def run_job(
    raw_urls,
    *,
    privacy="private",
    download_only=False,
    as_short=True,
    cookies_browser=None,
    hashtags=None,
    limit=None,
    skip=0,
    force=False,
    should_stop=None,
):
    """Download and upload a batch of TikToks. Prints progress via print().

    Videos already recorded in uploaded.json are skipped automatically (unless
    `force` is True), so re-runs never create duplicates. `should_stop` is an
    optional callable returning True to abort early (used by the GUI's Stop
    button).
    """
    urls = expand_urls(raw_urls, cookies_browser)

    uploaded = load_uploaded()
    if not force and uploaded:
        before = len(urls)
        urls = [u for u in urls if extract_tiktok_id(u) not in uploaded]
        already = before - len(urls)
        if already:
            print(f"Skipping {already} video(s) already uploaded previously.")

    # skip/limit apply to what's LEFT, so "do 6" means 6 *new* videos.
    if skip:
        urls = urls[skip:]
    if limit is not None:
        urls = urls[:limit]

    if not urls:
        print("Nothing new to process.")
        return

    print(f"\nProcessing {len(urls)} video(s).")
    youtube = None if download_only else get_youtube_service()

    for i, url in enumerate(urls, 1):
        if should_stop and should_stop():
            print("\nStopped by user.")
            return
        print(f"\n[{i}/{len(urls)}] {url}")
        try:
            video = download_tiktok(url, cookies_browser)
            print(f"    downloaded: {os.path.basename(video['filepath'])}")
            print(f"    title: {video['title']}")

            if download_only:
                continue

            video_id = upload_to_youtube(
                youtube, video, as_short=as_short, privacy=privacy, hashtags=hashtags
            )
            print(f"    uploaded: https://youtube.com/watch?v={video_id} ({privacy})")

            # Record it so future runs skip this video.
            key = video.get("id") or extract_tiktok_id(url)
            if key:
                uploaded[key] = video_id
                save_uploaded(uploaded)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)

    print("\nDone.")


# --- CLI --------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Download your TikToks and upload them to YouTube as Shorts."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="TikTok video URLs, or a profile URL (e.g. https://www.tiktok.com/@you) "
        "to pull every video from that account",
    )
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
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Use login cookies from a local browser (chrome, edge, firefox, "
        "brave, ...) so TikTok will list/serve your videos",
    )
    parser.add_argument(
        "--hashtags",
        metavar='"#a #b #c"',
        help="Replace each TikTok's hashtags with your own set on YouTube, "
        'e.g. --hashtags "#gta #memes #funny"',
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Only process the first N videos (handy for testing, or for "
        "staying under YouTube's daily upload quota)",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        metavar="N",
        help="Skip the first N of the remaining (not-yet-uploaded) videos",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-upload even videos already recorded in uploaded.json "
        "(by default those are skipped to avoid duplicates)",
    )
    args = parser.parse_args()

    raw = list(args.urls)
    if args.file:
        with open(args.file) as f:
            raw += [line.strip() for line in f if line.strip() and not line.startswith("#")]
    if not raw:
        parser.error("Give at least one TikTok URL, or use --file links.txt")

    run_job(
        raw,
        privacy=args.privacy,
        download_only=args.download_only,
        as_short=not args.no_shorts,
        cookies_browser=args.cookies_from_browser,
        hashtags=args.hashtags,
        limit=args.limit,
        skip=args.skip,
        force=args.force,
    )


if __name__ == "__main__":
    main()
