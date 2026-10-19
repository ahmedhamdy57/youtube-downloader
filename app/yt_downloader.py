#!/usr/bin/env python3
"""YouTube Downloader - a simple window around yt-dlp.

Works as a normal Python script, and as a packaged app (PyInstaller) that
already contains yt-dlp, ffmpeg and Deno, so users install nothing.
"""
import os
import sys
import queue
import threading
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, scrolledtext

import yt_dlp
from yt_dlp.utils import DownloadCancelled

APP_NAME = "YouTube Downloader"
DEFAULT_FOLDER = str(Path.home() / "Downloads" / "YouTube Videos")


def bundle_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def setup_path():
    """Make the bundled Deno (needed by YouTube) visible to yt-dlp."""
    parts = [bundle_dir(), str(Path.home() / ".deno" / "bin"), os.environ.get("PATH", "")]
    os.environ["PATH"] = os.pathsep.join(parts)


def ffmpeg_path():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None  # fall back to a system ffmpeg if there is one


def open_folder(path):
    os.makedirs(path, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa
        return
    env = dict(os.environ)
    orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
    if orig is not None:
        env["LD_LIBRARY_PATH"] = orig
    else:
        env.pop("LD_LIBRARY_PATH", None)
    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path], env=env)


def friendly_hint(msg):
    m = msg.lower()
    if "sign in" in m or "403" in m or "bot" in m or "age" in m and "restrict" in m:
        return "Tip: set 'Use my browser login' to the browser where you are logged in to YouTube, then try again."
    if "private" in m or "members" in m:
        return "Tip: this video is private or members-only. Choose your browser under 'Use my browser login'."
    if "unsupported url" in m or "is not a valid url" in m:
        return "Tip: check the link. It should start with https://"
    if "unable to download" in m or "getaddrinfo" in m or "network" in m:
        return "Tip: check your internet connection."
    if "ffmpeg" in m:
        return "Tip: ffmpeg problem. Please download the newest version of this app."
    return ""


class QLogger:
    def __init__(self, q):
        self.q = q

    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.q.put(("line", msg))

    def info(self, msg):
        self.q.put(("line", msg))

    def warning(self, msg):
        self.q.put(("line", "Warning: " + msg))

    def error(self, msg):
        self.q.put(("line", "Error: " + msg))
        hint = friendly_hint(msg)
        if hint:
            self.q.put(("line", hint))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  (yt-dlp {yt_dlp.version.__version__})")
        self.geometry("720x640")
        self.minsize(620, 560)
        self.q = queue.Queue()
        self.cancel = threading.Event()
        self.running = False

        self.url = tk.StringVar()
        self.kind = tk.StringVar(value="video")
        self.scope = tk.StringVar(value="single")
        self.quality = tk.StringVar(value="720p")
        self.browser = tk.StringVar(value="None")
        self.folder = tk.StringVar(value=DEFAULT_FOLDER)
        self.items = tk.StringVar()
        self.ignore = tk.BooleanVar(value=True)

        self.build_ui()
        self.after(100, self.poll)

    # ---------------- layout ----------------
    def build_ui(self):
        f = ttk.Frame(self, padding=14)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        pad = {"padx": 6, "pady": 5}

        ttk.Label(f, text="1. Paste the YouTube link").grid(row=0, column=0, columnspan=4, sticky="w", **pad)
        e = ttk.Entry(f, textvariable=self.url)
        e.grid(row=1, column=0, columnspan=3, sticky="ew", **pad)
        e.focus()
        ttk.Button(f, text="Paste", command=self.paste).grid(row=1, column=3, **pad)

        ttk.Label(f, text="2. Choose what you want").grid(row=2, column=0, columnspan=4, sticky="w", **pad)
        row = ttk.Frame(f)
        row.grid(row=3, column=0, columnspan=4, sticky="w", **pad)
        for text, var, val in [("Video", self.kind, "video"), ("Audio only (MP3)", self.kind, "audio")]:
            ttk.Radiobutton(row, text=text, variable=var, value=val, command=self.refresh).pack(side="left", padx=(0, 14))
        row2 = ttk.Frame(f)
        row2.grid(row=4, column=0, columnspan=4, sticky="w", **pad)
        for text, val in [("Just this one video", "single"), ("The whole playlist", "playlist")]:
            ttk.Radiobutton(row2, text=text, variable=self.scope, value=val, command=self.refresh).pack(side="left", padx=(0, 14))

        ttk.Label(f, text="Video quality").grid(row=5, column=0, sticky="w", **pad)
        self.qbox = ttk.Combobox(f, textvariable=self.quality, state="readonly", width=12,
                                 values=["480p", "720p", "1080p", "Best"])
        self.qbox.grid(row=5, column=1, sticky="w", **pad)

        ttk.Label(f, text="3. Where to save").grid(row=6, column=0, columnspan=4, sticky="w", **pad)
        ttk.Entry(f, textvariable=self.folder).grid(row=7, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Button(f, text="Choose...", command=self.browse).grid(row=7, column=3, **pad)

        adv = ttk.LabelFrame(f, text="Extra options (you can ignore these)", padding=8)
        adv.grid(row=8, column=0, columnspan=4, sticky="ew", padx=6, pady=8)
        adv.columnconfigure(1, weight=1)
        browsers = ["None", "firefox", "chrome", "edge", "brave"] + (["safari"] if sys.platform == "darwin" else [])
        ttk.Label(adv, text="Use my browser login").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(adv, textvariable=self.browser, state="readonly", width=12, values=browsers).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(adv, text="Only needed if a download fails or the video is age-restricted.").grid(row=1, column=0, columnspan=3, sticky="w")
        ttk.Label(adv, text="Playlist items").grid(row=2, column=0, sticky="w", pady=(8, 3))
        self.items_entry = ttk.Entry(adv, textvariable=self.items, width=14)
        self.items_entry.grid(row=2, column=1, sticky="w", padx=6, pady=(8, 3))
        ttk.Label(adv, text="Example: 1-5. Leave empty for all.").grid(row=2, column=2, sticky="w")
        ttk.Checkbutton(adv, text="Skip videos that are not available and keep going",
                        variable=self.ignore).grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))

        bar = ttk.Frame(f)
        bar.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(4, 4))
        self.btn_go = ttk.Button(bar, text="Download", command=self.start)
        self.btn_go.pack(side="left", padx=6, ipadx=18, ipady=4)
        self.btn_stop = ttk.Button(bar, text="Stop", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6, ipady=4)
        ttk.Button(bar, text="Open folder", command=self.show_folder).pack(side="left", padx=6, ipady=4)

        self.pbar = ttk.Progressbar(f, maximum=100)
        self.pbar.grid(row=10, column=0, columnspan=4, sticky="ew", padx=6, pady=(6, 2))
        self.status = ttk.Label(f, text="Ready")
        self.status.grid(row=11, column=0, columnspan=4, sticky="w", padx=6)

        self.log = scrolledtext.ScrolledText(f, height=8, state="disabled", wrap="word")
        self.log.grid(row=12, column=0, columnspan=4, sticky="nsew", padx=6, pady=(6, 0))
        f.rowconfigure(12, weight=1)
        self.refresh()

    # ---------------- helpers ----------------
    def refresh(self):
        self.qbox.configure(state="disabled" if self.kind.get() == "audio" else "readonly")
        self.items_entry.configure(state="normal" if self.scope.get() == "playlist" else "disabled")

    def paste(self):
        try:
            self.url.set(self.clipboard_get().strip())
        except tk.TclError:
            pass

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.folder.get() or DEFAULT_FOLDER)
        if d:
            self.folder.set(d)

    def show_folder(self):
        open_folder(os.path.expanduser(self.folder.get().strip() or DEFAULT_FOLDER))

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_busy(self, on):
        self.running = on
        self.btn_go.configure(state="disabled" if on else "normal")
        self.btn_stop.configure(state="normal" if on else "disabled")

    # ---------------- downloading ----------------
    def make_options(self, folder):
        playlist = self.scope.get() == "playlist"
        tmpl = "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s" if playlist else "%(title)s.%(ext)s"

        def hook(d):
            if self.cancel.is_set():
                raise DownloadCancelled("Stopped")
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                pct = d["downloaded_bytes"] / total * 100 if total else 0
                info = d.get("info_dict") or {}
                idx, n = info.get("playlist_index"), info.get("n_entries")
                label = f"Video {idx} of {n}:  " if idx and n else ""
                speed = (d.get("_speed_str") or "").strip()
                eta = (d.get("_eta_str") or "").strip()
                self.q.put(("progress", (pct, f"{label}{pct:.0f}%   {speed}   time left {eta}")))
            elif d["status"] == "finished":
                self.q.put(("line", "Downloaded: " + os.path.basename(d.get("filename", ""))))

        opts = {
            "outtmpl": os.path.join(folder, tmpl),
            "noplaylist": not playlist,
            "ignoreerrors": "only_download" if self.ignore.get() else False,
            "progress_hooks": [hook],
            "logger": QLogger(self.q),
            "noprogress": True,
        }
        ff = ffmpeg_path()
        if ff:
            opts["ffmpeg_location"] = ff
        if self.kind.get() == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        else:
            q = self.quality.get()
            if q == "Best":
                opts["format"] = "bv*+ba/b"
            else:
                h = q.rstrip("p")
                opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]"
            opts["merge_output_format"] = "mp4"
        if playlist and self.items.get().strip():
            opts["playlist_items"] = self.items.get().strip()
        if self.browser.get() != "None":
            opts["cookiesfrombrowser"] = (self.browser.get(),)
        return opts

    def start(self):
        url = self.url.get().strip()
        if not url.startswith("http"):
            messagebox.showwarning(APP_NAME, "Please paste a YouTube link first.\nIt should start with https://")
            return
        folder = os.path.expanduser(self.folder.get().strip() or DEFAULT_FOLDER)
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Cannot use that folder:\n{e}")
            return
        self.cancel.clear()
        self.pbar["value"] = 0
        self.status.configure(text="Starting...")
        self.write("Starting download...")
        self.set_busy(True)
        opts = self.make_options(folder)
        threading.Thread(target=self.worker, args=(opts, url), daemon=True).start()

    def worker(self, opts, url):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                code = ydl.download([url])
            self.q.put(("done", code))
        except DownloadCancelled:
            self.q.put(("cancelled", None))
        except Exception as e:  # noqa
            msg = str(e)
            self.q.put(("line", "Error: " + msg))
            hint = friendly_hint(msg)
            if hint:
                self.q.put(("line", hint))
            self.q.put(("done", 1))

    def stop(self):
        self.cancel.set()
        self.status.configure(text="Stopping...")

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "line":
                    self.write(val)
                elif kind == "progress":
                    self.pbar["value"] = val[0]
                    self.status.configure(text=val[1])
                elif kind == "cancelled":
                    self.set_busy(False)
                    self.status.configure(text="Stopped")
                    self.write("Stopped.")
                elif kind == "done":
                    self.set_busy(False)
                    if val == 0:
                        self.pbar["value"] = 100
                        self.status.configure(text="Finished! Click 'Open folder' to see your files.")
                        self.write("All done.")
                    else:
                        self.status.configure(text="Something went wrong. See the messages below.")
        except queue.Empty:
            pass
        self.after(100, self.poll)


if __name__ == "__main__":
    setup_path()
    App().mainloop()
