import time
import shutil
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
import os
import datetime as dt
import json
import youtube_handler
from dotenv import load_dotenv

load_dotenv()

# コメント先のチャンネルID
CHANNEL_ID = os.getenv('CHANNEL_ID')

# 監視対象の共有フォルダパス
SHARED_FOLDER_PATH = os.getenv('SHARED_FOLDER_PATH')

# ダウンロード先のフォルダパス
DOWNLOAD_FOLDER_PATH = os.getenv('DOWNLOAD_FOLDER_PATH')

# 監視対象のPCのIPアドレス
MONITORING_PC_IP = os.getenv('MONITORING_PC_IP')

# 転送元PCからクリップを削除するかどうか
DELETE_AFTER_TRANSFER = os.getenv('DELETE_AFTER_TRANSFER', 'False').lower() == 'true'

# 配信中のvideo_idリスト
live_streams = {}

class NewVideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.mp4'):
            self.download_file(event.src_path)

    def download_file(self, src_path):
        while True:
            try:
                
                file_name = os.path.basename(src_path)
                dest_path = os.path.join(DOWNLOAD_FOLDER_PATH, file_name)
                print(f"新しい動画ファイル検出: {file_name}")
                #shutil.copy2(src_path, dest_path)
                print(src_path)
                print(dest_path)
                command = f"rsync -avh '{src_path}' '{dest_path}'"
                os.system(command)
                # jsonファイルの存在確認と作成
                if not os.path.isfile("./metadata.json"):
                    dict = {}
                    with open("./metadata.json", 'w') as f:
                        json.dump(dict, f, indent=2)
                # jsonファイルの読み込み
                with open("./metadata.json") as f:
                    dict = json.load(f)
                # jsonファイルの更新
                dt_now_str = dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                dict[dest_path] = dt_now_str
                with open("./metadata.json", 'w') as f:
                    json.dump(dict, f, indent=2)
                print(f"ファイルをダウンロード: {dest_path}")
                if DELETE_AFTER_TRANSFER:
                    os.remove(src_path)
                print("コメントを配信辞書に登録します")
                # ここから配信辞書に登録
                youtube = youtube_handler.get_authenticated_service()
                video_id = youtube_handler.fetch_latest_live_video_id(youtube)
                if not video_id:
                    print("現在, ライブ配信はありません。")
                    break
                stream_start_time_jst = youtube_handler.fetch_stream_start_time(youtube, video_id)
                save_time = dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=9)))
                elapsed_time = save_time - stream_start_time_jst
                total_seconds = int(elapsed_time.total_seconds()) - 60 # 1分引く
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                timestamp = f"(プログラムによる自動コメント)\n{hours:02}:{minutes:02}:{seconds:02}\n"
                next_retry_time = dt.datetime.now() + dt.timedelta(minutes=10)
                if video_id not in live_streams: live_streams[video_id] = {"youtube": youtube, "comment": timestamp, "next_retry": next_retry_time, "reties": 0}
                else:
                    live_streams[video_id]["comment"] = live_streams[video_id]["comment"] + timestamp
                print("コメントを配信辞書に登録しました")
                break
            except Exception as e:
                print(f"ファイルのダウンロードに失敗: {e}")
                time.sleep(5)
                
def is_pc_online(ip):
    response = os.system(f"ping -c 1 {ip} > /dev/null")
    return response == 0

def start_monitoring():
    event_handler = NewVideoHandler()
    observer = PollingObserver()
    observer.schedule(event_handler, SHARED_FOLDER_PATH, recursive=False)
    observer.start()
    # jsonファイルの存在確認と作成
    if not os.path.isfile("./metadata.json"):
        dict = {}
        with open("./metadata.json", 'w') as f:
            json.dump(dict, f, indent=2)
    print(f"監視開始: {SHARED_FOLDER_PATH}")

    while True:
        try:
            time.sleep(5)
            if not is_pc_online(MONITORING_PC_IP):
                raise ConnectionError("切断されました。")
            dt_now = dt.datetime.now()
            file_name_list = os.listdir(DOWNLOAD_FOLDER_PATH)
            file_name_list = [f for f in file_name_list if not f.startswith('.')]
            # jsonファイルの読み込み
            with open("./metadata.json") as f:
                dict = json.load(f)
            #print(file_name_list)
            for idx, file_name in enumerate(file_name_list):
                file_path = os.path.join(DOWNLOAD_FOLDER_PATH, file_name)
                metadata_str = dict[file_path]
                metadata_dt = dt.datetime.strptime(metadata_str, '%Y-%m-%d_%H-%M-%S')
                if dt_now - metadata_dt >= dt.timedelta(weeks=4): 
                    os.remove(file_path)
                    del dict[file_path]
                    with open("./metadata.json", 'w') as f:
                        json.dump(dict, f, indent=2)

            # コメント投稿
            if live_streams:
                for key in list(live_streams):
                    if dt_now < live_streams[key]["next_retry"]:
                        #print(f"次の投稿まで待機: {live_streams[key]['next_retry']} (ビデオID: {key})")
                        continue
                    print(f"配信が終了したか確認します (ビデオID: {key})")
                    try:
                        status = youtube_handler.get_broadcast_status(live_streams[key]["youtube"], key)
                        if status == 'live':
                            print(f"配信中です．10分後にリトライします．: {key}")
                            live_streams[key]["next_retry"] = dt_now + dt.timedelta(minutes=10)  # 10分後に再試行
                            live_streams[key]["reties"] += 1
                            if live_streams[key]["reties"] > 60: # 10時間以上再試行している場合
                                print(f"再試行回数が60回を超えました。次の配信のコメントを破棄します: {key}")
                                del live_streams[key]
                                continue
                            continue
                        elif status == 'complete':
                            print(f"配信の終了を確認しました: {key}")
                            youtube_handler.post_youtube_comment(live_streams[key]["youtube"], key, live_streams[key]["comment"])
                            print(f"コメントを投稿しました (ビデオID: {key})")
                            del live_streams[key]  # コメント投稿後は削除
                            continue
                        else:
                            print(f"配信の状態が不明です．10分後にリトライします．: {status} (ビデオID: {key})")
                            live_streams[key]["next_retry"] = dt_now + dt.timedelta(minutes=10)
                            live_streams[key]["reties"] += 1
                            if live_streams[key]["reties"] > 60: # 10時間以上再試行している場合
                                print(f"再試行回数が60回を超えました。次の配信のコメントを破棄します: {key}")
                                del live_streams[key]
                                continue
                            continue
                    except Exception as e:
                        print(f"コメントの投稿に失敗: {e}")
                        live_streams[key]["next_retry"] = dt_now + dt.timedelta(minutes=10)
                        live_streams[key]["reties"] += 1
                        if live_streams[key]["reties"] > 60: # 10時間以上再試行している場合
                            print(f"再試行回数が60回を超えました。次の配信のコメントを破棄します: {key}")
                            del live_streams[key]
                            continue
                        continue

        except KeyboardInterrupt:
            observer.stop()
            print("監視停止")
            break
        except ConnectionError:
            print(f"エラーが発生しました: ConnectionError")
            print(observer.is_alive())
            observer.stop()
            observer.join()
            print("再接続を試みます...")
            
            while True:
                try:
                    time.sleep(30)  # 30秒待機
                    observer = PollingObserver()
                    observer.schedule(event_handler, SHARED_FOLDER_PATH, recursive=False)
                    observer.start()
                    print(f"再接続成功: {SHARED_FOLDER_PATH}")
                    break
                except Exception as re:
                    
                    print(f"再接続失敗")
            

    observer.join()

if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_FOLDER_PATH):
        os.makedirs(DOWNLOAD_FOLDER_PATH)
        print(f"ダウンロードフォルダを作成: {DOWNLOAD_FOLDER_PATH}")
    if os.path.exists(DOWNLOAD_FOLDER_PATH):
        start_monitoring()
    

