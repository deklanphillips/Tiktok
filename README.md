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

## 3. Run it — the app (recommended)

Just **double-click `Start.bat`** (or run `python gui.py`). Everything is in one
window with three tabs — no editing `.bat` or `.txt` files:

- **Settings** — your profile URL, hashtags, privacy, and how many per day.
  Saved automatically; used by both manual and automatic runs.
- **Upload** — hit **Start** to run a batch right now and watch the progress.
- **Automation** — one button to turn the **daily auto-upload** on/off, pick the
  time, run a batch now, and read the daily log.

**First-time order:** open **Settings**, fill in your profile + hashtags, click
**Save settings**. Then use **Upload** or **Automation**.

The top-right **⟳ Update app** button pulls the latest version and offers to
relaunch — so after the first setup you never need the terminal again.

The daily automation is free and within YouTube's rules — it's just your PC
running the official uploader on a schedule (your PC must be on and awake at the
chosen time). See **"Keeping the daily job logged in"** below so it doesn't stop
after a week.

## 3b. Run it — the command line (optional)

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

Open the app → **Automation** tab:

1. Make sure you've signed in once (run a batch from the **Upload** tab).
2. Set the time and click **Turn ON daily upload**.

That's it — every day at that time your PC uploads the next batch of new videos
and skips everything already done. Read results in the **Daily log** box, or
click **Turn OFF** to stop. It's free (official API, within the daily quota) and
ToS-friendly — just you on a schedule. Your PC must be on and awake at the time.

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

## Auto-publish on a schedule (e.g. 3 Shorts/day)

Instead of leaving uploads private for you to publish by hand, let **YouTube**
publish them for you at set times — even when your PC is off.

In the app: **Settings** tab → tick **"Auto-publish uploads on a schedule"** and
set your times (e.g. `09:00`, `14:00`, `19:00`) → **Save**. Now every upload is
stamped with the next open slot: 9 AM, 2 PM, 7 PM, then the next day, and so on.

Upload 21 videos and you've got a **week of 3-per-day** auto-posting. Combine it
with the daily automation to keep feeding the queue: the tool uploads a batch
(within quota), and YouTube trickles them out at your chosen times.

- The slot cursor is remembered in `schedule.json`, so slots never collide
  across runs.
- Command line: `--schedule "09:00,14:00,19:00"`.
- Scheduled videos sit as **private** until their time, then go **public**
  automatically.

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
