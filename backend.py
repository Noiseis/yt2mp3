import os
import sys
import subprocess
import uuid

# ---------- Auto Install Dependencies ----------
def install(package, pip_name=None):
    """Try importing a package, if missing install it via pip."""
    try:
        __import__(package)
    except ImportError:
        print(f"📦 Installing missing package: {pip_name or package} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name or package])

# Ensure required libraries
install("flask")
install("yt_dlp", "yt-dlp")

# ---------- Imports after ensuring install ----------
from flask import Flask, request, send_file
import yt_dlp

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ---------- Routes ----------
@app.route("/")
def home():
    return {"message": "Backend is running 🚀"}

@app.route("/download", methods=["POST"])
def download_audio():
    """Download YouTube video audio as MP3 and return as file."""
    url = request.json.get("url")
    if not url:
        return {"error": "No URL provided"}, 400

    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "noplaylist": False
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        mp3_file = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp3")
        return send_file(mp3_file, as_attachment=True, download_name="audio.mp3")

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
