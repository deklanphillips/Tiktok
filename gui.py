#!/usr/bin/env python3
"""
Desktop app for the TikTok -> YouTube Shorts uploader.

Double-click this file (or run `python gui.py`) to get a window with fields
and a Start button instead of typing commands. It uses the exact same engine
as tiktok_to_youtube.py under the hood.
"""

import queue
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

import tiktok_to_youtube as engine

# Your default hashtags — edit this line to change what's pre-filled.
DEFAULT_HASHTAGS = "#gtastorymode #gta #memes #gtav #funny #gtamemes #gta6"


class _QueueWriter:
    """A file-like object that shoves written text onto a queue (thread-safe)."""

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

        root.title("TikTok → YouTube Uploader")
        root.geometry("720x620")
        root.minsize(620, 520)

        pad = {"padx": 10, "pady": 5}
        form = ttk.Frame(root)
        form.pack(fill="x", **pad)
        form.columnconfigure(1, weight=1)

        # --- TikTok URL / profile ---
        ttk.Label(form, text="TikTok profile or video URL:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.url_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.url_var).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=4
        )

        # --- Hashtags ---
        ttk.Label(form, text="Hashtags (YouTube):").grid(row=1, column=0, sticky="w", pady=4)
        self.tags_var = tk.StringVar(value=DEFAULT_HASHTAGS)
        ttk.Entry(form, textvariable=self.tags_var).grid(
            row=1, column=1, columnspan=3, sticky="ew", pady=4
        )

        # --- Privacy / Skip / Limit ---
        ttk.Label(form, text="Privacy:").grid(row=2, column=0, sticky="w", pady=4)
        self.privacy_var = tk.StringVar(value="private")
        ttk.Combobox(
            form,
            textvariable=self.privacy_var,
            values=["private", "unlisted", "public"],
            state="readonly",
            width=12,
        ).grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Skip first:").grid(row=3, column=0, sticky="w", pady=4)
        self.skip_var = tk.StringVar(value="0")
        ttk.Spinbox(form, from_=0, to=100000, textvariable=self.skip_var, width=10).grid(
            row=3, column=1, sticky="w", pady=4
        )

        ttk.Label(form, text="How many (blank = all):").grid(
            row=3, column=2, sticky="e", pady=4
        )
        self.limit_var = tk.StringVar(value="6")
        ttk.Spinbox(form, from_=0, to=100000, textvariable=self.limit_var, width=10).grid(
            row=3, column=3, sticky="w", pady=4
        )

        # --- Cookies browser ---
        ttk.Label(form, text="Browser cookies (if needed):").grid(
            row=4, column=0, sticky="w", pady=4
        )
        self.cookies_var = tk.StringVar(value="")
        ttk.Combobox(
            form,
            textvariable=self.cookies_var,
            values=["", "chrome", "edge", "firefox", "brave"],
            state="readonly",
            width=12,
        ).grid(row=4, column=1, sticky="w", pady=4)

        # --- Checkboxes ---
        self.shorts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Upload as Shorts", variable=self.shorts_var).grid(
            row=5, column=1, sticky="w", pady=4
        )
        self.download_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form, text="Download only (no YouTube)", variable=self.download_only_var
        ).grid(row=5, column=2, columnspan=2, sticky="w", pady=4)

        self.force_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form,
            text="Re-upload duplicates (ignore history)",
            variable=self.force_var,
        ).grid(row=6, column=1, columnspan=3, sticky="w", pady=4)

        # --- Buttons ---
        btns = ttk.Frame(root)
        btns.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btns, text="Start", command=self.on_start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(
            btns, text="Stop", command=self.on_stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=6)

        # --- Log output ---
        ttk.Label(root, text="Progress:").pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(root, height=16, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.root.after(100, self._drain_log)

    # --- logging plumbing ---
    def _append(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain_log(self):
        try:
            while True:
                self._append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log)

    # --- controls ---
    def on_stop(self):
        self.stop_flag = True
        self._append("\nStopping after the current video...\n")

    def on_start(self):
        if self.worker and self.worker.is_alive():
            return
        url = self.url_var.get().strip()
        if not url:
            self._append("Please paste a TikTok profile or video URL first.\n")
            return

        # Parse numeric fields.
        def _int_or(default, s):
            s = s.strip()
            return int(s) if s.isdigit() else default

        skip = _int_or(0, self.skip_var.get())
        limit_raw = self.limit_var.get().strip()
        limit = int(limit_raw) if limit_raw.isdigit() and int(limit_raw) > 0 else None

        params = dict(
            raw_urls=[url],
            privacy=self.privacy_var.get(),
            download_only=self.download_only_var.get(),
            as_short=self.shorts_var.get(),
            cookies_browser=self.cookies_var.get() or None,
            hashtags=self.tags_var.get().strip() or None,
            limit=limit,
            skip=skip,
            force=self.force_var.get(),
            should_stop=lambda: self.stop_flag,
        )

        self.stop_flag = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._append("=" * 50 + "\nStarting...\n")

        self.worker = threading.Thread(target=self._run, args=(params,), daemon=True)
        self.worker.start()

    def _run(self, params):
        # Redirect the engine's print() output into our log queue.
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = _QueueWriter(self.log_queue)
        try:
            engine.run_job(**params)
        except Exception as e:
            print(f"\nERROR: {e}")
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            self.root.after(0, self._on_done)

    def _on_done(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
