# YouTube Downloader

<p align="center"><img src="assets/icon.png" width="120" alt="App icon"></p>

A simple app to download YouTube videos, whole playlists, or just the audio (MP3) to your computer.

**No coding. No terminal. No installing anything else.** Download it, open it, paste a link, click Download.

---

## Step 1: Download the app

Go to the **[Releases page](../../releases/latest)** and download the file for your computer:

| Your computer | Download this file |
|---|---|
| Windows | `YouTube-Downloader-Windows.zip` |
| Mac (Apple chip: M1, M2, M3 or newer) | `YouTube-Downloader-Mac.zip` |
| Linux | `YouTube-Downloader-Linux.tar.gz` |

## Step 2: Open it

### Windows
1. Right-click the zip file and choose **Extract All**.
2. Open the extracted folder and double-click **YouTube Downloader**.
3. If Windows shows a blue "Windows protected your PC" window, click **More info**, then **Run anyway**.
   This happens because the app is free and not signed with a paid certificate. It is safe, and the full source code is in this repository.

### Mac
1. Double-click the zip file, then drag **YouTube Downloader** into your Applications folder.
2. The first time, **right-click** the app and choose **Open**, then click **Open** again.
   If it still refuses: open **System Settings > Privacy & Security**, scroll down and click **Open Anyway**.

### Linux
1. Right-click the file and choose **Extract Here**.
2. Open the extracted folder. Right-click **YouTube Downloader**, open **Properties > Permissions**, and tick **Allow executing file as program** (the wording differs between systems).
3. Double-click **YouTube Downloader**. If it asks, choose **Run**.

## Step 3: Use it

1. Copy a YouTube link from your browser and click **Paste** in the app.
2. Choose **Video** or **Audio only (MP3)**, and **Just this one video** or **The whole playlist**.
3. Click **Download**.
4. When it says *Finished*, click **Open folder** to see your files.

By default files are saved in `Downloads/YouTube Videos`. You can pick another folder with **Choose...**.

---

## Something went wrong?

| Problem | What to do |
|---|---|
| Error 403, or "Sign in to confirm you're not a bot" | Under **Extra options**, set **Use my browser login** to the browser you use (make sure you are logged in to YouTube there), then try again. |
| Age-restricted or members-only video | Same fix: choose your browser under **Use my browser login**. |
| It worked before but suddenly stopped | YouTube changes often. Download the **newest version** from the [Releases page](../../releases/latest). |
| Nothing happens when I click Download | Check that the link starts with `https://` and that you are online. |

Still stuck? [Open an issue](../../issues) and copy the red/error text from the app's message box.

---

## For developers

Run from source (Python 3.9+ with Tk):

```bash
pip install -r requirements.txt
python app/yt_downloader.py
```

The packaged apps are built automatically by GitHub Actions (`.github/workflows/build.yml`) with PyInstaller. They bundle [yt-dlp](https://github.com/yt-dlp/yt-dlp), ffmpeg (via `imageio-ffmpeg`) and [Deno](https://deno.com) (YouTube needs a JavaScript runtime).

To publish a new version:

```bash
git tag v1.0.1
git push origin v1.0.1
```

After a few minutes the three downloads appear on the Releases page.

---

## Please read

- Only download videos you have the right to download (your own videos, Creative Commons, or where the owner allows it). You are responsible for how you use this app and for following the laws of your country and YouTube's Terms of Service.
- This project is not affiliated with or endorsed by YouTube or Google.

## Credits

Built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg](https://ffmpeg.org) and [Deno](https://deno.com). Released under the [MIT License](LICENSE).
