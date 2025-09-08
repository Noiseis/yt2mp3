import os
import yt_dlp
import uuid
import json
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

# Use a static folder relative to the script for Render
app = Flask(__name__, static_folder='static')
CORS(app)

DOWNLOAD_FOLDER = "/var/data/downloads" # A persistent directory on Render
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Serve the Frontend (for testing or combined deployment) ---
# Note: GitHub Pages will be our primary frontend host.
@app.route('/')
def index():
    # This will now serve from a 'static' subfolder
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)
# ------------------------------------

# --- API Endpoints ---
@app.route('/get-info', methods=['POST'])
def get_info():
    # This function is already production-ready and needs no changes
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "URL is required"}), 400
    ydl_opts = {'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_title = info.get('title', 'No Title')
            thumbnail_url = info.get('thumbnail', '')
            artist = info.get('uploader', 'Unknown Artist')
            audio_formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('abr'):
                    audio_formats.append({
                        'format_id': f.get('format_id'),
                        'quality': f"{round(f.get('abr'))}kbps",
                        'ext': f.get('ext')
                    })
            return jsonify({
                "title": video_title,
                "thumbnail": thumbnail_url,
                "artist": artist,
                "audio_formats": audio_formats
            })
    except Exception as e:
        return jsonify({"error": "Failed to fetch video info", "details": str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    # This function is already production-ready and needs no changes
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    metadata = data.get('metadata', {})
    if not url or not format_id:
        return jsonify({"error": "URL and Format ID are required"}), 400
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")
    ydl_opts = {
        'format': format_id,
        'outtmpl': output_template,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        mp3_filename = f"{file_id}.mp3"
        mp3_filepath = os.path.join(DOWNLOAD_FOLDER, mp3_filename)
        info_filepath = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.info.json")
        with open(info_filepath, 'w') as f:
            json.dump(metadata, f)
        return send_file(mp3_filepath, as_attachment=True, download_name=f"{metadata.get('title', 'audio')}.mp3")
    except Exception as e:
        return jsonify({"error": "Download failed", "details": str(e)}), 500

@app.route('/list-downloads', methods=['GET'])
def list_downloads():
    # This function is already production-ready and needs no changes
    downloads = []
    for filename in os.listdir(DOWNLOAD_FOLDER):
        if filename.endswith('.info.json'):
            file_id = filename.split('.')[0]
            mp3_file = f"{file_id}.mp3"
            if os.path.exists(os.path.join(DOWNLOAD_FOLDER, mp3_file)):
                with open(os.path.join(DOWNLOAD_FOLDER, filename), 'r') as f:
                    info = json.load(f)
                    info['mp3_file'] = mp3_file
                    downloads.append(info)
    return jsonify(downloads)

@app.route('/play/<filename>')
def play_file(filename):
    # This function is already production-ready and needs no changes
    return send_from_directory(DOWNLOAD_FOLDER, filename)

@app.route('/delete', methods=['POST'])
def delete_file():
    # This function is already production-ready and needs no changes
    filename = request.json.get('mp3_file')
    if not filename:
        return jsonify({"error": "Filename is required"}), 400
    try:
        file_id = filename.split('.')[0]
        mp3_path = os.path.join(DOWNLOAD_FOLDER, filename)
        info_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.info.json")
        if os.path.exists(mp3_path): os.remove(mp3_path)
        if os.path.exists(info_path): os.remove(info_path)
        return jsonify({"success": True, "message": f"{filename} deleted."})
    except Exception as e:
        return jsonify({"error": "Failed to delete file", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)