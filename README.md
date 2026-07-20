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

## 3. Run it — the easy way (desktop app)

Prefer a window with buttons instead of typing commands? Just **double-click
`Start.bat`** (or run `python gui.py`).

You get a small app where you paste your TikTok profile URL, your hashtags are
pre-filled, and you pick privacy / how many to do — then hit **Start** and
watch the progress. It uses the same engine as the command line below.

> Editing the pre-filled hashtags: open `gui.py` and change the
> `DEFAULT_HASHTAGS` line near the top.

## 3b. Run it — the command line

### Pull your whole profile at once

Give it your profile URL and it downloads **every** video on the account, then
uploads them all as private Shorts (keeping each TikTok's original hashtags):

```bash
python tiktok_to_youtube.py "https://www.tiktok.com/@yourusername"
```

They land on YouTube as **private**, so you can then open **YouTube Studio →
Content**, and set a publish date/time on each one to **schedule** them.

### One or a few videos

Download **and** upload a single video:

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
| `--hashtags "#a #b #c"` | Replace each TikTok's hashtags with your own set. |
| `--limit N` | Only process the first N videos (testing / daily quota). |
| `--skip N` | Skip the first N videos (with `--limit`, do the next batch). |
| `--force` | Re-upload even videos already in `uploaded.json`. |
| `--download-only` | Only download from TikTok; skip YouTube. |
| `--no-shorts` | Upload as a regular video instead of a Short. |
| `--cookies-from-browser BROWSER` | Borrow TikTok login cookies from a browser. |
| `--file links.txt` | Read URLs from a file, one per line. |

**Custom hashtags example:**

```bash
python tiktok_to_youtube.py "https://www.tiktok.com/@you" \
  --hashtags "#gtastorymode #gta #memes #gtav #funny #gtamemes #gta6"
```

---

## Troubleshooting

**"This account does not have any videos posted" (but it clearly does):**
TikTok often refuses to list an account's videos for logged-out requests. Fix
it by borrowing the login cookies from a browser you're signed into TikTok on:

```bash
python tiktok_to_youtube.py "https://www.tiktok.com/@you" --cookies-from-browser chrome
```

Replace `chrome` with `edge`, `firefox`, `brave`, etc. Close the browser first
if it complains that the cookie database is locked. This flag also helps if
individual video downloads get rejected.

## Fully automatic daily uploads (free, ToS-friendly)

Let Windows run the uploader for you once a day — 6 new videos each day, using
the official API, at no extra cost. This is just you on a schedule; it doesn't
violate YouTube's terms.

**Set it up (once):**

1. Run the tool by hand once first (open the app or run a command) so you're
   signed in and it works.
2. Open `daily_upload.bat` in Notepad and check the `PROFILE` and `HASHTAGS`
   lines near the top are right. Change the time in `setup_daily_task.bat` if
   you don't want 9:00 AM.
3. Double-click **`setup_daily_task.bat`**.

That's it — every day at 9 AM it uploads the next 6 new videos and skips
everything already done. Output is logged to `daily_log.txt`. To stop it, run
**`remove_daily_task.bat`**.

### Keeping the daily job logged in (important)

While your Google OAuth app is in **"Testing"** mode, its logins **expire every
7 days** — which would quietly break the daily job after a week. To make it
last, publish the app:

- Google Cloud Console → **APIs & Services → OAuth consent screen** →
  **Publish app** → confirm.

You do **not** need Google's full verification for your own use — you may see an
"unverified app" notice, which is fine for a personal tool. After publishing,
run the tool by hand once more to refresh the login, and the daily job will
keep working indefinitely.

## No duplicates

Every successful upload is recorded in **`uploaded.json`** (TikTok video id →
YouTube video id). On any later run, videos already in that file are skipped
automatically — so you can safely point the tool at your whole profile every
day and it will only ever upload the *new* ones. `--limit`/`--skip` apply to
what's left after that filtering, so "do 6" always means 6 fresh videos.

- Want to redo one anyway? Use `--force` (CLI) or the **"Re-upload
  duplicates"** checkbox (app).
- `uploaded.json` lives in the project folder and is git-ignored (it's your
  personal history). Delete it to start fresh; back it up to keep your history.

## Notes & limits

- **Quota — important for a full profile:** The YouTube Data API gives each
  project ~10,000 units/day, and an upload costs ~1,600 units — so roughly
  **6 uploads per day** by default. If your profile has more than ~6 videos,
  the run will upload the first batch and then start reporting a
  `quotaExceeded` error on the rest. Just re-run the same command the next day
  (already-uploaded ones are skipped only if you remove them from your list),
  or request a quota increase from Google to do them all at once.
- **Hashtags:** Each video keeps the original hashtags from its TikTok caption,
  with `#Shorts` added on.
- **Shorts:** A video is treated as a Short when it's vertical and ≤ 3 minutes.
  The tool adds `#Shorts` to help YouTube classify it.
- **Start private.** The default privacy is `private` on purpose — download a
  batch, eyeball them on YouTube, then flip to public.
