#!/usr/bin/env python3
"""
All-in-one desktop app for the TikTok -> YouTube uploader.

Double-click Start.bat (or run `python gui.py`). Everything lives here:
  * Upload tab      - run a batch now, watch progress
  * Automation tab  - turn the daily auto-upload on/off, see the log
  * Settings tab    - your profile, hashtags, privacy (saved automatically)

No more editing .bat or .txt files by hand.
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import tiktok_to_youtube as engine

TASK_NAME = "TikTokToYouTube"
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "tiktok_to_youtube.py")
LOG_FILE = os.path.join(HERE, "daily_log.txt")


class _QueueWriter:
    """File-like object that pushes writes onto a queue (thread-safe)."""

    def __init__(self, q):
        self.q = q

    def write(self, text):
        if text:
            self.q.put(text)

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.log_queue = queue.Queue()
        self.worker = None
        self.stop_flag = False
        self.settings = engine.load_settings()

        root.title("TikTok → YouTube Uploader")
        root.geometry("760x660")
        root.minsize(680, 560)

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self._build_upload_tab(nb)
        self._build_automation_tab(nb)
        self._build_settings_tab(nb)

        self.root.after(100, self._drain_log)
        self.refresh_task_status()

    # ------------------------------------------------------------------ UPLOAD
    def _build_upload_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Upload  ")

        form = ttk.Frame(tab)
        form.pack(fill="x", padx=10, pady=8)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="TikTok profile or video URL:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.url_var = tk.StringVar(value=self.settings.get("profile", ""))
        ttk.Entry(form, textvariable=self.url_var).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=4
        )

        ttk.Label(form, text="How many now:").grid(row=1, column=0, sticky="w", pady=4)
        self.limit_var = tk.StringVar(value=str(self.settings.get("daily_count", 6)))
        ttk.Spinbox(form, from_=1, to=100000, textvariable=self.limit_var, width=10).grid(
            row=1, column=1, sticky="w", pady=4
        )

        self.download_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form, text="Download only (no YouTube)", variable=self.download_only_var
        ).grid(row=1, column=2, columnspan=2, sticky="w", pady=4)

        self.force_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form, text="Re-upload duplicates (ignore history)", variable=self.force_var
        ).grid(row=2, column=1, columnspan=3, sticky="w", pady=4)

        btns = ttk.Frame(tab)
        btns.pack(fill="x", padx=10)
        self.start_btn = ttk.Button(btns, text="Start upload", command=self.on_start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(btns, text="Stop", command=self.on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        ttk.Label(tab, text="Progress:").pack(anchor="w", padx=10, pady=(8, 0))
        self.log = scrolledtext.ScrolledText(tab, height=16, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # -------------------------------------------------------------- AUTOMATION
    def _build_automation_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Automation  ")

        info = ttk.Label(
            tab,
            wraplength=680,
            justify="left",
            text=(
                "Let Windows upload for you automatically. Each day at the time "
                "below it uploads the next batch of NEW videos (skipping anything "
                "already done). Free and within YouTube's rules — it's just you on "
                "a schedule.\n\nYour PC needs to be on and awake at that time."
            ),
        )
        info.pack(anchor="w", padx=12, pady=(12, 8))

        row = ttk.Frame(tab)
        row.pack(anchor="w", padx=12, pady=4)
        ttk.Label(row, text="Run daily at:").pack(side="left")
        self.time_var = tk.StringVar(value=self.settings.get("schedule_time", "09:00"))
        ttk.Entry(row, textvariable=self.time_var, width=8).pack(side="left", padx=6)
        ttk.Label(row, text="(24-hour, e.g. 09:00 or 18:30)").pack(side="left")

        row2 = ttk.Frame(tab)
        row2.pack(anchor="w", padx=12, pady=8)
        ttk.Button(row2, text="Turn ON daily upload", command=self.enable_task).pack(
            side="left"
        )
        ttk.Button(row2, text="Turn OFF", command=self.disable_task).pack(
            side="left", padx=6
        )
        ttk.Button(row2, text="Run daily batch now", command=self.run_daily_now).pack(
            side="left", padx=6
        )

        self.status_var = tk.StringVar(value="Status: checking...")
        ttk.Label(tab, textvariable=self.status_var, font=("", 10, "bold")).pack(
            anchor="w", padx=12, pady=(4, 8)
        )

        logrow = ttk.Frame(tab)
        logrow.pack(anchor="w", padx=12)
        ttk.Label(logrow, text="Daily log:").pack(side="left")
        ttk.Button(logrow, text="Refresh", command=self.load_daily_log).pack(
            side="left", padx=6
        )
        ttk.Button(logrow, text="Open log file", command=self.open_log_file).pack(
            side="left"
        )

        self.daily_log = scrolledtext.ScrolledText(
            tab, height=12, state="disabled", wrap="word"
        )
        self.daily_log.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.load_daily_log()

    # ---------------------------------------------------------------- SETTINGS
    def _build_settings_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  Settings  ")

        form = ttk.Frame(tab)
        form.pack(fill="x", padx=12, pady=12)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Your TikTok profile URL:").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self.set_profile = tk.StringVar(value=self.settings.get("profile", ""))
        ttk.Entry(form, textvariable=self.set_profile).grid(
            row=0, column=1, sticky="ew", pady=6
        )

        ttk.Label(form, text="Hashtags for YouTube:").grid(
            row=1, column=0, sticky="w", pady=6
        )
        self.set_tags = tk.StringVar(value=self.settings.get("hashtags", ""))
        ttk.Entry(form, textvariable=self.set_tags).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(form, text="Privacy:").grid(row=2, column=0, sticky="w", pady=6)
        self.set_privacy = tk.StringVar(value=self.settings.get("privacy", "private"))
        ttk.Combobox(
            form,
            textvariable=self.set_privacy,
            values=["private", "unlisted", "public"],
            state="readonly",
            width=14,
        ).grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Videos per day:").grid(row=3, column=0, sticky="w", pady=6)
        self.set_count = tk.StringVar(value=str(self.settings.get("daily_count", 6)))
        ttk.Spinbox(form, from_=1, to=100000, textvariable=self.set_count, width=10).grid(
            row=3, column=1, sticky="w", pady=6
        )

        ttk.Label(form, text="Browser cookies (if TikTok blocks listing):").grid(
            row=4, column=0, sticky="w", pady=6
        )
        self.set_cookies = tk.StringVar(value=self.settings.get("cookies_browser", ""))
        ttk.Combobox(
            form,
            textvariable=self.set_cookies,
            values=["", "chrome", "edge", "firefox", "brave"],
            state="readonly",
            width=14,
        ).grid(row=4, column=1, sticky="w", pady=6)

        self.set_shorts = tk.BooleanVar(value=self.settings.get("as_short", True))
        ttk.Checkbutton(form, text="Upload as Shorts", variable=self.set_shorts).grid(
            row=5, column=1, sticky="w", pady=6
        )

        ttk.Button(tab, text="Save settings", command=self.save_settings_clicked).pack(
            anchor="w", padx=12
        )
        self.save_note = tk.StringVar(value="")
        ttk.Label(tab, textvariable=self.save_note, foreground="green").pack(
            anchor="w", padx=12, pady=6
        )

    # --------------------------------------------------------------- settings
    def _collect_settings(self):
        def _int(s, d):
            s = str(s).strip()
            return int(s) if s.isdigit() and int(s) > 0 else d

        return {
            "profile": self.set_profile.get().strip(),
            "hashtags": self.set_tags.get().strip(),
            "privacy": self.set_privacy.get(),
            "daily_count": _int(self.set_count.get(), 6),
            "as_short": self.set_shorts.get(),
            "cookies_browser": self.set_cookies.get(),
            "schedule_time": self.time_var.get().strip() or "09:00",
        }

    def save_settings_clicked(self):
        self.settings = self._collect_settings()
        engine.save_settings(self.settings)
        # keep the Upload tab in sync
        self.url_var.set(self.settings["profile"])
        self.limit_var.set(str(self.settings["daily_count"]))
        self.save_note.set("Saved ✓")
        self.root.after(2500, lambda: self.save_note.set(""))

    # --------------------------------------------------------------- logging
    def _append(self, widget, text):
        widget.configure(state="normal")
        widget.insert("end", text)
        widget.see("end")
        widget.configure(state="disabled")

    def _drain_log(self):
        try:
            while True:
                self._append(self.log, self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log)

    def load_daily_log(self):
        self.daily_log.configure(state="normal")
        self.daily_log.delete("1.0", "end")
        try:
            with open(LOG_FILE, encoding="utf-8") as f:
                self.daily_log.insert("end", f.read())
            self.daily_log.see("end")
        except FileNotFoundError:
            self.daily_log.insert("end", "(no runs yet)")
        self.daily_log.configure(state="disabled")

    def open_log_file(self):
        if os.path.exists(LOG_FILE):
            try:
                os.startfile(LOG_FILE)  # Windows
            except AttributeError:
                subprocess.Popen(["xdg-open", LOG_FILE])
        else:
            messagebox.showinfo("Daily log", "No runs yet — nothing to show.")

    # ------------------------------------------------------------ run a batch
    def on_stop(self):
        self.stop_flag = True
        self._append(self.log, "\nStopping after the current video...\n")

    def on_start(self):
        if self.worker and self.worker.is_alive():
            return
        url = self.url_var.get().strip()
        if not url:
            self._append(self.log, "Please enter a TikTok profile or video URL.\n")
            return

        limit_raw = self.limit_var.get().strip()
        limit = int(limit_raw) if limit_raw.isdigit() and int(limit_raw) > 0 else None

        params = dict(
            raw_urls=[url],
            privacy=self.settings.get("privacy", "private"),
            download_only=self.download_only_var.get(),
            as_short=self.settings.get("as_short", True),
            cookies_browser=self.settings.get("cookies_browser") or None,
            hashtags=(self.settings.get("hashtags") or "").strip() or None,
            limit=limit,
            skip=0,
            force=self.force_var.get(),
            should_stop=lambda: self.stop_flag,
        )

        self.stop_flag = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._append(self.log, "=" * 50 + "\nStarting...\n")
        self.worker = threading.Thread(target=self._run, args=(params,), daemon=True)
        self.worker.start()

    def _run(self, params):
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = _QueueWriter(self.log_queue)
        try:
            engine.run_job(**params)
        except Exception as e:
            print(f"\nERROR: {e}")
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            self.root.after(0, self._run_done)

    def _run_done(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    # ------------------------------------------------ Windows scheduled task
    def _schtasks(self, args):
        """Run schtasks and return (ok, output). No-op-ish off Windows."""
        try:
            out = subprocess.run(
                ["schtasks"] + args,
                capture_output=True,
                text=True,
            )
            return out.returncode == 0, (out.stdout + out.stderr).strip()
        except FileNotFoundError:
            return False, "schtasks not found (this feature needs Windows)."

    def refresh_task_status(self):
        ok, _ = self._schtasks(["/Query", "/TN", TASK_NAME])
        if ok:
            self.status_var.set(
                f"Status: ON — runs daily at {self.settings.get('schedule_time', '09:00')}"
            )
        else:
            self.status_var.set("Status: OFF — daily upload is not scheduled")

    def enable_task(self):
        # Save first so the daily run uses current settings.
        self.save_settings_clicked()
        t = self.settings["schedule_time"]
        cmd = f'"{sys.executable}" "{SCRIPT}" --daily'
        ok, msg = self._schtasks(
            ["/Create", "/SC", "DAILY", "/TN", TASK_NAME, "/TR", cmd, "/ST", t, "/F"]
        )
        if ok:
            messagebox.showinfo(
                "Automation ON",
                f"Daily upload scheduled for {t} every day.\n\n"
                "Your PC must be on and awake at that time.",
            )
        else:
            messagebox.showerror("Could not schedule", msg or "Unknown error.")
        self.refresh_task_status()

    def disable_task(self):
        ok, msg = self._schtasks(["/Delete", "/TN", TASK_NAME, "/F"])
        if ok:
            messagebox.showinfo("Automation OFF", "Daily upload turned off.")
        else:
            messagebox.showinfo("Automation", msg or "Nothing to turn off.")
        self.refresh_task_status()

    def run_daily_now(self):
        """Trigger one unattended-style batch immediately, in the background."""
        self.save_settings_clicked()
        subprocess.Popen([sys.executable, SCRIPT, "--daily"], cwd=HERE)
        messagebox.showinfo(
            "Running",
            "Started a batch in the background. Click 'Refresh' under Daily log "
            "in a minute to see the results.",
        )


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
