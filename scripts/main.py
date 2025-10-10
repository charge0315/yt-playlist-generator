import os
import pickle
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 定数定義 ---

# YouTube APIにアクセスするためのスコープを定義します。
# このスコープは、ユーザーのYouTubeアカウントの読み取りおよび書き込み権限を要求します。
SCOPES = ['https://www.googleapis.com/auth/youtube']
# 使用するAPIの名前
API_SERVICE_NAME = 'youtube'
# 使用するAPIのバージョン
API_VERSION = 'v3'

# --- パス設定 ---

# このスクリプトファイル（main.py）が置かれているディレクトリの絶対パスを取得します。
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# SCRIPT_DIRの1つ上の階層をプロジェクトのルートディレクトリとして設定します。
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# OAuth 2.0クライアントID情報が記載されたJSONファイルへのパス
CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, 'client_secret.json')
# 認証後のアクセストークンを保存/読み込みするためのファイルパス
TOKEN_PICKLE_FILE = os.path.join(PROJECT_ROOT, 'token.pickle')


def get_authenticated_service():
    """
    Googleアカウントで認証を行い、YouTube APIと通信するためのサービスオブジェクトを生成して返します。
    初回実行時はブラウザが開き、認証とアクセス許可が求められます。
    2回目以降は保存された認証情報（token.pickle）を自動的に使用します。
    """
    creds = None
    # 保存された認証情報ファイルが存在する場合、それを読み込む
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)

    # 認証情報が存在しない、または無効な場合
    if not creds or not creds.valid:
        # 認証情報が期限切れの場合、リフレッシュトークンを使って更新する
        if creds and creds.expired and creds.refresh_token:
            print("認証情報の有効期限が切れています。更新します...")
            creds.refresh(Request())
        # 初回認証の場合
        else:
            # client_secret.jsonから認証フローを作成
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            # ローカルサーバーを起動し、ユーザーにブラウザで認証を行わせる
            creds = flow.run_local_server(port=0)
        # 新しい認証情報をファイルに保存する
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)

    # 認証済みのサービスオブジェクトを構築して返す
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def duration_to_seconds(duration):
    """
    YouTube APIから取得したISO 8601形式の動画時間（例: "PT1M30S"）を秒数（例: 90）に変換します。
    """
    # 正規表現で時間、分、秒を抽出
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    # 合計秒数を計算
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds


def get_my_subscriptions(youtube):
    """
    認証されたユーザーが登録しているすべてのチャンネルのリストを取得します。
    """
    print("登録チャンネルを取得しています...")
    subscriptions = []
    next_page_token = None
    # APIのページネーションをたどり、すべての登録チャンネルを取得
    while True:
        response = youtube.subscriptions().list(
            mine=True,
            part='snippet',
            maxResults=50, # 1回のリクエストで取得する最大件数
            pageToken=next_page_token
        ).execute()
        subscriptions.extend(response['items'])
        next_page_token = response.get('nextPageToken')
        # 次のページがなければループを終了
        if not next_page_token:
            break
    print(f"{len(subscriptions)}チャンネルの登録情報を取得しました。")
    return subscriptions


def create_playlist_for_recent_shorts(youtube, channel_id, channel_title):
    """
    指定された1つのチャンネルについて、直近のYouTube Shorts動画（61秒以下）を最大10件集め、
    新しい非公開再生リストを作成します。
    """
    try:
        # チャンネルIDから、そのチャンネルのアップロード動画がすべて含まれる再生リストのIDを取得
        channels_response = youtube.channels().list(
            id=channel_id,
            part='contentDetails'
        ).execute()
        if not channels_response['items']:
            print(f"エラー: チャンネルID {channel_id} が見つかりません。")
            return

        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # アップロード動画リストから、最新50件の動画IDを取得
        playlist_response = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part='contentDetails',
            maxResults=50
        ).execute()
        
        video_ids = [item['contentDetails']['videoId'] for item in playlist_response['items']]

        # 取得した動画IDリストを元に、各動画の詳細情報（特に動画時間）を取得
        videos_response = youtube.videos().list(
            id=','.join(video_ids),
            part='contentDetails'
        ).execute()

        # Shorts動画（61秒以下）をフィルタリングし、最新のものから最大10件のIDをリストに格納
        recent_shorts_ids = []
        for video in videos_response['items']:
            # 動画時間を秒に変換し、61秒以下か判定
            if duration_to_seconds(video['contentDetails']['duration']) <= 61:
                recent_shorts_ids.append(video['id'])
            # 10件集まったらループを抜ける
            if len(recent_shorts_ids) >= 10:
                break
        
        # Shorts動画が見つからなかった場合
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
                'privacyStatus': 'private' # 再生リストを非公開に設定
            }
        }
        playlist = youtube.playlists().insert(part='snippet,status', body=playlist_body).execute()
        new_playlist_id = playlist['id']

        # フィルタリングしたShorts動画を、新しく作成した再生リストに1件ずつ追加
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


# --- メイン処理 ---
if __name__ == '__main__':
    # 認証を行い、APIサービスオブジェクトを取得
    youtube = get_authenticated_service()
    # 登録チャンネルのリストを取得
    subscriptions = get_my_subscriptions(youtube)
    
    if not subscriptions:
        print("登録しているチャンネルがありません。")
    else:
        # 各登録チャンネルに対して、Shorts再生リスト作成処理を実行
        for sub in subscriptions:
            channel_id = sub['snippet']['resourceId']['channelId']
            channel_title = sub['snippet']['title']
            create_playlist_for_recent_shorts(youtube, channel_id, channel_title)
        print("\nすべての処理が完了しました。")