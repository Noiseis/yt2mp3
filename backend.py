import os
import yt_dlp
import uuid
import json
import tempfile
import shutil
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app)

# --- NEW: Helper function to format bytes into KB, MB, etc. ---
def format_bytes(size_bytes):
    if size_bytes is None:
        return "N/A"
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 1)
    return f"{s}{size_name[i]}"

# --- Routes to serve the frontend for local testing ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)
# ------------------------------------


# --- API Endpoints ---
# --- UPDATED: get_info() now includes file size ---
@app.route('/get-info', methods=['POST'])
def get_info():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "URL is required"}), 400
    ydl_opts = {
        'quiet': True,
        'cookiefile': 'cookies.txt'  # Add this line to use the cookie file
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            audio_formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none' and f.get('abr'):
                    # Get filesize (it might be under 'filesize' or 'filesize_approx')
                    file_size = f.get('filesize') or f.get('filesize_approx')
                    
                    audio_formats.append({
                        'format_id': f.get('format_id'),
                        'quality': f"{round(f.get('abr'))}kbps",
                        'ext': f.get('ext'),
                        'size': format_bytes(file_size) # Add the formatted size
                    })

            return jsonify({
                "title": info.get('title', 'No Title'),
                "thumbnail": info.get('thumbnail', ''),
                "artist": info.get('uploader', 'Unknown Artist'),
                "audio_formats": audio_formats
            })
    except Exception as e:
        return jsonify({"error": "Failed to fetch video info", "details": str(e)}), 500

# --- The rest of the file is unchanged ---
@app.route('/download', methods=['POST'])
def download():
    # ... (This function is unchanged)
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    metadata = data.get('metadata', {})
    
    if not url or not format_id:
        return jsonify({"error": "URL and Format ID are required"}), 400

    temp_dir = tempfile.mkdtemp()
    
    file_id = str(uuid.uuid4())
    output_template = os.path.join(temp_dir, f"{file_id}.%(ext)s")

    ydl_opts = {
        'format': format_id,
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        mp3_filepath = os.path.join(temp_dir, f"{file_id}.mp3")
        
        response = send_file(
            mp3_filepath, 
            as_attachment=True, 
            download_name=f"{metadata.get('title', 'audio')}.mp3"
        )

        @response.call_on_close
        def cleanup():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temp directory: {e}")

        return response

    except Exception as e:
        shutil.rmtree(temp_dir)
        return jsonify({"error": "Download failed", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)