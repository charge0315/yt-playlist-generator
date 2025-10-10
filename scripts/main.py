import os
import pickle
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# スコープの定義 (YouTubeアカウントの読み書き)
SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# このスクリプトがあるディレクトリの絶対パスを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# １つ上の階層のプロジェクトルートを取得
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, 'client_secret.json')
TOKEN_PICKLE_FILE = os.path.join(PROJECT_ROOT, 'token.pickle')


def get_authenticated_service():
    """
    認証を行い、YouTube APIサービスオブジェクトを返す
    """
    creds = None
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("認証情報の有効期限が切れています。更新します...")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0) # 修正点
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def duration_to_seconds(duration):
    """
    ISO 8601形式の動画時間を秒に変換する
    """
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds

def get_my_subscriptions(youtube):
    """
    認証ユーザーの登録チャンネルリストを取得する
    """
    print("登録チャンネルを取得しています...")
    subscriptions = []
    next_page_token = None
    while True:
        response = youtube.subscriptions().list(
            mine=True,
            part='snippet',
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        subscriptions.extend(response['items'])
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break
    print(f"{len(subscriptions)}チャンネルの登録情報を取得しました。")
    return subscriptions

def create_playlist_for_recent_shorts(youtube, channel_id, channel_title):
    """
    特定のチャンネルの最新Shorts10件で再生リストを作成する
    """
    try:
        # チャンネルのアップロード動画リストIDを取得
        channels_response = youtube.channels().list(
            id=channel_id,
            part='contentDetails'
        ).execute()
        if not channels_response['items']:
            print(f"エラー: チャンネルID {channel_id} が見つかりません。")
            return

        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # アップロードリストから最新50件の動画を取得
        playlist_response = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part='contentDetails',
            maxResults=50 # 最新の投稿を取得するため、50件で十分と仮定
        ).execute()
        
        video_ids = [item['contentDetails']['videoId'] for item in playlist_response['items']]

        # 動画の詳細情報を取得
        videos_response = youtube.videos().list(
            id=','.join(video_ids),
            part='contentDetails'
        ).execute()

        # Shorts動画（61秒以下）をフィルタリングし、最新10件を取得
        recent_shorts_ids = []
        for video in videos_response['items']:
            if duration_to_seconds(video['contentDetails']['duration']) <= 61:
                recent_shorts_ids.append(video['id'])
            if len(recent_shorts_ids) >= 10:
                break
        
        if not recent_shorts_ids:
            print(f"- {channel_title}: 直近のShorts動画が見つかりませんでした。")
            return

        print(f"- {channel_title}: {len(recent_shorts_ids)}件のShorts動画で再生リストを作成します。")

        # 新しい再生リストを作成
        playlist_title = f"{channel_title} - 最新Shorts"
        playlist_body = {
            'snippet': {
                'title': playlist_title,
                'description': f'{channel_title}の直近のShorts動画を集めた再生リストです。'
            },
            'status': {
                'privacyStatus': 'private'
            }
        }
        playlist = youtube.playlists().insert(part='snippet,status', body=playlist_body).execute()
        new_playlist_id = playlist['id']

        # 動画を再生リストに追加
        for video_id in recent_shorts_ids:
            playlist_item_body = {
                'snippet': {
                    'playlistId': new_playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
            youtube.playlistItems().insert(part='snippet', body=playlist_item_body).execute()
        
        print(f"  -> 再生リスト '{playlist_title}' を作成しました。")

    except HttpError as e:
        print(f"エラーが発生しました ({channel_title}): {e}")


if __name__ == '__main__':
    youtube = get_authenticated_service()
    subscriptions = get_my_subscriptions(youtube)
    
    if not subscriptions:
        print("登録しているチャンネルがありません。")
    else:
        for sub in subscriptions:
            channel_id = sub['snippet']['resourceId']['channelId']
            channel_title = sub['snippet']['title']
            create_playlist_for_recent_shorts(youtube, channel_id, channel_title)
        print("\nすべての処理が完了しました。")
