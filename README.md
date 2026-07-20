# TikTok → YouTube Shorts uploader

Download your own TikTok videos (watermark-free) and upload them to your
YouTube channel as Shorts — from the command line.

> Use this with **videos you own**. Re-uploading other people's content can
> violate copyright and both platforms' Terms of Service.

---

## What it does

1. Takes a TikTok URL (or a list of them).
2. Downloads the video with [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) —
   source quality, no watermark (this is the same clean result sites like
   ssstik.io give you, but done locally and reliably).
3. Uploads each video to your YouTube channel, tagged as a **Short**.

---

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. One-time YouTube setup

Uploading to YouTube requires a free Google API credential so the tool can
post **as you**. You do this once.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and
   create a project (or pick an existing one).
2. **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.
3. **APIs & Services → OAuth consent screen**:
   - User type: **External**.
   - Fill in the app name and your email.
   - Under **Test users**, add your own Google account (the one that owns your
     YouTube channel). While the app is in "testing" mode this is required.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**.
   - Download the JSON file, rename it to **`client_secret.json`**, and put it
     in this folder.

The first time you run an upload, a browser window opens asking you to sign in
and grant access. After that, a `token.json` is saved so you won't be asked
again.

> `client_secret.json` and `token.json` are secrets — they're already in
> `.gitignore` and must never be committed.

## 3. Run it

Download **and** upload one video (uploads as **private** by default so you can
review before publishing):

```bash
python tiktok_to_youtube.py "https://www.tiktok.com/@you/video/1234567890"
```

Several at once:

```bash
python tiktok_to_youtube.py URL1 URL2 URL3
```

From a file (one URL per line):

```bash
python tiktok_to_youtube.py --file links.txt
```

Just download, don't upload (no Google setup needed for this):

```bash
python tiktok_to_youtube.py URL --download-only
```

### Options

| Flag | What it does |
|------|--------------|
| `--privacy {private,unlisted,public}` | YouTube visibility. Default `private`. |
| `--download-only` | Only download from TikTok; skip YouTube. |
| `--no-shorts` | Upload as a regular video instead of a Short. |
| `--file links.txt` | Read URLs from a file, one per line. |

---

## Notes & limits

- **Quota:** The YouTube Data API gives each project ~10,000 units/day, and an
  upload costs ~1,600 units — so roughly **6 uploads per day** by default. You
  can request more from Google if you need it.
- **Shorts:** A video is treated as a Short when it's vertical and ≤ 3 minutes.
  The tool adds `#Shorts` to help YouTube classify it.
- **Start private.** The default privacy is `private` on purpose — download a
  batch, eyeball them on YouTube, then flip to public.
