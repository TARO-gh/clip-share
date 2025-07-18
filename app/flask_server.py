# flask_server.py
from flask import Flask, send_from_directory, render_template_string
import os
import json
import datetime as dt
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)

DOWNLOAD_FOLDER_PATH = os.getenv('DOWNLOAD_FOLDER_PATH')
METADATA_FILE = os.getenv('METADATA_FILE')

@app.route('/')
def index():
    # replayフォルダ内の.mp4ファイル一覧取得
    files = [f for f in os.listdir(DOWNLOAD_FOLDER_PATH) if f.endswith('.mp4')]
    files.sort(reverse=True)

    # メタデータ読み込み
    if os.path.isfile(METADATA_FILE):
        with open(METADATA_FILE) as f:
            metadata = json.load(f)
    else:
        metadata = {}

    # 日付ごとにファイルをまとめる
    grouped_files = defaultdict(list)
    for file in files:
        file_path = os.path.join(DOWNLOAD_FOLDER_PATH, file)
        save_time_str = metadata.get(file_path)

        if save_time_str:
            save_dt = dt.datetime.strptime(save_time_str, "%Y-%m-%d_%H-%M-%S")
            date_str = save_dt.strftime("%Y-%m-%d")
        else:
            date_str = "Unknown"

        grouped_files[date_str].append(file)

    grouped_files = dict(sorted(grouped_files.items(), reverse=True))

    # HTMLテンプレート
    html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>動画一覧（日付別）</title>
        <style>
            body { background-color: #000; color: #fff; font-family: Arial, sans-serif; margin: 40px; }
            .date-header { margin-top: 40px; font-size: 24px; font-weight: bold; }
            .video-container { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 10px; }
            .video-item { width: 320px; position: relative; }
            video { width: 100%; border-radius: 10px; box-shadow: 2px 2px 8px rgba(255,255,255,0.3); cursor: pointer; }
            p { text-align: center; margin-top: 5px; font-size: 14px; color: #ccc; }

            /* ポップアップ用 */
            #popup {
                display: none;
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 1000;
                background-color: #111;
                padding: 10px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(255,255,255,0.5);
            }
            #popup video {
                width: 640px;
            }
            #overlay {
                display: none;
                position: fixed;
                top: 0; left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.6);
                z-index: 999;
            }
        </style>
    </head>
    <body>
        <h1>保存された動画（日付ごと）</h1>
        <div id="overlay" onclick="closePopup()"></div>
        <div id="popup">
            <video id="popup-video" controls preload="metadata">
                <source id="popup-source" src="" type="video/mp4">
                あなたのブラウザは video タグに対応していません。
            </video>
        </div>

        {% for date, file_list in grouped_files.items() %}
            <div class="date-header">{{ date }}</div>
            <div class="video-container">
                {% for file in file_list %}
                    <div class="video-item">
                        <video onclick="showPopup('{{ url_for('serve_file', filename=file) }}')" preload="metadata">
                            <source src="{{ url_for('serve_file', filename=file) }}" type="video/mp4">
                        </video>
                        <p>{{ file }}</p>
                    </div>
                {% endfor %}
            </div>
        {% endfor %}

        <script>
            function showPopup(videoUrl) {
                document.getElementById('popup-source').src = videoUrl;
                document.getElementById('popup-video').load();
                document.getElementById('overlay').style.display = 'block';
                document.getElementById('popup').style.display = 'block';
            }
            function closePopup() {
                document.getElementById('popup').style.display = 'none';
                document.getElementById('overlay').style.display = 'none';
                document.getElementById('popup-video').pause();
            }
        </script>
    </body>
    </html>
    """

    return render_template_string(html, grouped_files=grouped_files)

@app.route('/replay/<path:filename>')
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER_PATH, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=60000, debug=True)
