import os
import datetime as dt
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = os.getenv('TOKEN_FILE')
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def get_authenticated_service():
    """認証して、YouTube APIサービスオブジェクトを返す"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        else:
            print("エラー: 有効な認証情報がありません。先にauthorize.pyを実行してください。")
            return None
    return build('youtube', 'v3', credentials=creds)

def fetch_latest_live_video_id(youtube):
    print(f"あなたのチャンネルからライブ配信を検索中...")
    try:
        # 1. 自分の配信を全部取得（ステータス情報も一緒に）
        response = youtube.liveBroadcasts().list(
            part='id,snippet,status', # statusも取得する
            mine=True 
        ).execute() # 消費クォーター1?

        # 2. 取得したリストの中から、配信中のものを探す
        for broadcast in response['items']:
            if broadcast['status']['lifeCycleStatus'] == 'live':
                video_id = broadcast['id']
                print(f"ライブ配信を発見しました。ビデオID: {video_id}")
                return video_id # 見つかったら、そのIDを返して終了
        
        # ループを抜けても見つからなかった場合
        print("現在、このチャンネルでライブ配信は見つかりません。")
        return None

    except HttpError as e:
        print(f"YouTube APIエラー（動画ID検索）: {e}")
        return None

def fetch_stream_start_time(youtube, video_id):
    """配信の開始時刻（JST）を取得する"""
    if not video_id: return None
    try:
        response = youtube.videos().list(
            part='liveStreamingDetails',
            id=video_id
        ).execute() # 消費クォーター1?
        if response['items'] and 'actualStartTime' in response['items'][0]['liveStreamingDetails']:
            start_time_str = response['items'][0]['liveStreamingDetails']['actualStartTime']
            start_time_utc = dt.datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
            return start_time_utc.astimezone(dt.timezone(dt.timedelta(hours=9)))
        return None
    except HttpError as e:
        print(f"YouTube APIエラー（開始時刻取得）: {e}")
        return None

def post_youtube_comment(youtube, video_id, text):
    """YouTubeにコメントを投稿する"""
    try:
        request_body = {
            'snippet': {
                'videoId': video_id,
                'topLevelComment': {'snippet': {'textOriginal': text}}
            }
        }
        # ↓消費クォーター50?
        youtube.commentThreads().insert(part='snippet', body=request_body).execute()
        print(f"コメント投稿成功: '{text}'")
    except HttpError as e:
        print(f"コメント投稿エラー: {e}")
        raise e
    
def get_broadcast_status(youtube, video_id):
    """指定されたビデオIDの配信ステータスを取得する"""
    try:
        response = youtube.liveBroadcasts().list(
            part='id,snippet,status', # statusも取得する
            mine=True # 念のため自分の動画に絞る
        ).execute() # 消費クォーター1?
        # 取得したリストの中から、指定されたビデオIDを探す
        for broadcast in response['items']:
            if broadcast['id'] == video_id:
                # ステータスを返す
                print(f"ビデオID: {video_id} のステータス: {broadcast['status']['lifeCycleStatus']}")
                return broadcast['status']['lifeCycleStatus']
        return None # 動画が見つからない場合
    except HttpError as e:
        print(f"ステータス取得エラー: {e}")
        return 'error' # エラーが起きたことを示す