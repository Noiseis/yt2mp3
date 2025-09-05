import os
import uuid
import subprocess
import sys
from flask import Flask, request, send_file, jsonify
import yt_dlp

# Auto-install missing dependencies (only useful for local runs)
def install(package, pip_name=None):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name or package])

install("flask")
install("yt_dlp", "yt-dlp")

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return {"message": "Backend is running 🚀"}

@app.route("/download", methods=["POST"])
def download_audio():
    url = request.json.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

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
    }

    try:
        # Download and convert
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        mp3_file = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp3")

        # Send file, then cleanup after sending
        response = send_file(mp3_file, as_attachment=True, download_name="audio.mp3")

        @response.call_on_close
        def cleanup():
            try:
                os.remove(mp3_file)
            except Exception as e:
                print(f"Cleanup error: {e}")

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
