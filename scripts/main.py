import os
import pickle
import re
import argparse
import time
import random
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


# --- 簡易ロギング ---
LOG_VERBOSE = False
LOG_QUIET = False

def _should_log():
    return not LOG_QUIET

def info(msg: str):
    if _should_log():
        print(msg)

def debug(msg: str):
    if LOG_VERBOSE and not LOG_QUIET:
        print(msg)

def warn(msg: str):
    if _should_log():
        print(msg)


# --- リトライ付きAPI実行ヘルパー ---
def execute_with_retry(callable_execute, *, max_attempts: int = 3, base_delay: float = 1.0):
    """
    callable_execute: () -> Any を実行し、HttpError等で失敗した場合は指数バックオフで最大 max_attempts 回まで再試行。
    戻り値: callable_execute の戻り値
    失敗時は最後の例外を送出
    """
    attempt = 0
    while True:
        try:
            return callable_execute()
        except HttpError as e:
            attempt += 1
            # 429/5xx/403（quota）などでの再試行に備える
            if attempt >= max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            warn(f"一時的なエラーのため再試行します（{attempt}/{max_attempts-1}）: {e}")
            time.sleep(delay)
        except Exception as e:
            # 予期しない例外は再試行せずに投げる
            raise


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
    info("登録チャンネルを取得しています...")
    subscriptions = []
    next_page_token = None
    # APIのページネーションをたどり、すべての登録チャンネルを取得
    while True:
        response = execute_with_retry(lambda: youtube.subscriptions().list(
            mine=True,
            part='snippet',
            maxResults=50, # 1回のリクエストで取得する最大件数
            pageToken=next_page_token
        ).execute())
        subscriptions.extend(response['items'])
        next_page_token = response.get('nextPageToken')
        # 次のページがなければループを終了
        if not next_page_token:
            break
    info(f"{len(subscriptions)}チャンネルの登録情報を取得しました。")
    return subscriptions


def find_my_playlist_by_title(youtube, title):
    """
    自分のアカウントに存在するプレイリストの中から、タイトル一致のものを検索して返します。
    見つからない場合は None。
    """
    next_page_token = None
    while True:
        resp = execute_with_retry(lambda: youtube.playlists().list(
            mine=True,
            part='snippet',
            maxResults=50,
            pageToken=next_page_token
        ).execute())
        for item in resp.get('items', []):
            if item['snippet'].get('title') == title:
                return item
        next_page_token = resp.get('nextPageToken')
        if not next_page_token:
            break
    return None


def list_playlist_items(youtube, playlist_id):
    """
    指定プレイリスト内の項目を一覧取得する。
    戻り値: [(playlistItemId, videoId, position), ...]
    """
    results = []
    next_page_token = None
    while True:
        resp = execute_with_retry(lambda: youtube.playlistItems().list(
            playlistId=playlist_id,
            part='snippet,contentDetails',
            maxResults=50,
            pageToken=next_page_token
        ).execute())
        for it in resp.get('items', []):
            results.append((
                it['id'],
                it['contentDetails']['videoId'],
                it['snippet'].get('position', 0)
            ))
        next_page_token = resp.get('nextPageToken')
        if not next_page_token:
            break
    return results


def sync_playlist_items(youtube, playlist_id, target_video_ids, dry_run: bool = False):
    """
    既存プレイリストの内容を target_video_ids に同期します。
    - 足りない動画は追加
    - 余分な動画は削除
    並び順の完全一致までは行わず、最小限の変更に留めます。
    """
    current = list_playlist_items(youtube, playlist_id)
    current_video_ids = [v for _, v, _ in current]
    id_to_item = {v: pid for (pid, v, _) in current}

    to_add = [v for v in target_video_ids if v not in current_video_ids]
    to_remove = [v for v in current_video_ids if v not in target_video_ids]

    if dry_run:
        info(f"  [DRY-RUN] 追加予定: {len(to_add)}件, 削除予定: {len(to_remove)}件")
    else:
        # 追加
        for video_id in to_add:
            playlist_item_body = {
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
            execute_with_retry(lambda: youtube.playlistItems().insert(part='snippet', body=playlist_item_body).execute())

        # 削除
        for video_id in to_remove:
            pid = id_to_item.get(video_id)
            if pid:
                execute_with_retry(lambda: youtube.playlistItems().delete(id=pid).execute())

    return len(to_add), len(to_remove)


def fetch_recent_shorts(youtube, uploads_playlist_id: str, limit: int):
    """
    アップロードプレイリストから最新のShorts（<=61秒）を、最新順で最大 limit 件取得。
    playlistItems の順序（新しい順）を基準にして順序を維持します。
    戻り値: [videoId, ...]
    """
    # 最新50件の動画IDを playlistItems の順序で取得
    resp = execute_with_retry(lambda: youtube.playlistItems().list(
        playlistId=uploads_playlist_id,
        part='contentDetails',
        maxResults=50
    ).execute())
    ordered_ids = [item['contentDetails']['videoId'] for item in resp.get('items', [])]
    if not ordered_ids:
        return []

    # 動画詳細（duration）を取得し、duration<=61 のものを順序を保って抽出
    videos_resp = execute_with_retry(lambda: youtube.videos().list(
        id=','.join(ordered_ids),
        part='contentDetails'
    ).execute())
    id_to_duration = {v['id']: v['contentDetails']['duration'] for v in videos_resp.get('items', [])}

    recent_shorts_ids = []
    for vid in ordered_ids:
        dur = id_to_duration.get(vid)
        if not dur:
            continue
        if duration_to_seconds(dur) <= 61:
            recent_shorts_ids.append(vid)
        if len(recent_shorts_ids) >= limit:
            break
    return recent_shorts_ids


def reorder_playlist_to_match(youtube, playlist_id: str, target_video_ids, dry_run: bool = False):
    """
    既存アイテムの position を target_video_ids の順序に合わせて並び替える。
    更新した件数を返す。
    注意: YouTube API の仕様上、update時は snippet に playlistId/position を含める必要があります。
    """
    items = list_playlist_items(youtube, playlist_id)
    # videoId -> (playlistItemId, current_pos)
    video_to_item = {v: (pid, pos) for (pid, v, pos) in items}
    updated = 0
    for idx, vid in enumerate(target_video_ids):
        if vid in video_to_item:
            pid, cur_pos = video_to_item[vid]
            if cur_pos != idx:
                if dry_run:
                    updated += 1
                else:
                    body = {
                        'id': pid,
                        'snippet': {
                            'playlistId': playlist_id,
                            'position': idx,
                        }
                    }
                    try:
                        execute_with_retry(lambda: youtube.playlistItems().update(part='snippet', body=body).execute())
                        updated += 1
                    except HttpError as e:
                        warn(f"並び替えに失敗しました（videoId={vid} → pos={idx}）: {e}")
    return updated


def create_playlist_for_recent_shorts(youtube, channel_id, channel_title, update_mode=False, per_channel_limit: int = 10, dry_run: bool = False):
    """
    指定された1つのチャンネルについて、直近のYouTube Shorts動画（61秒以下）を最大10件集め、
    新しい非公開再生リストを作成します。
    """
    try:
        # チャンネルIDから、そのチャンネルのアップロード動画がすべて含まれる再生リストのIDを取得
        channels_response = execute_with_retry(lambda: youtube.channels().list(
            id=channel_id,
            part='contentDetails'
        ).execute())
        if not channels_response['items']:
            print(f"エラー: チャンネルID {channel_id} が見つかりません。")
            return

        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # アップロード動画リストから、最新50件の動画IDを取得
        # 最新Shortsを上限 per_channel_limit まで取得（最新順）
        recent_shorts_ids = fetch_recent_shorts(youtube, uploads_playlist_id, per_channel_limit)
        
        # Shorts動画が見つからなかった場合
        if not recent_shorts_ids:
            info(f"- {channel_title}: 直近のShorts動画が見つかりませんでした。")
            return

        playlist_title = f"{channel_title} - 最新Shorts"

        if update_mode:
            # 既存プレイリストがあれば同期、なければ作成
            existing = find_my_playlist_by_title(youtube, playlist_title)
            if existing:
                pid = existing['id']
                add_cnt, del_cnt = sync_playlist_items(youtube, pid, recent_shorts_ids, dry_run=dry_run)
                # 並び順を同期（最新順）
                reord = reorder_playlist_to_match(youtube, pid, recent_shorts_ids, dry_run=dry_run)
                suffix = "（ドライラン）" if dry_run else ""
                info(f"- {channel_title}: 既存プレイリストを更新{suffix}（追加 {add_cnt} / 削除 {del_cnt} / 並び替え {reord}）。")
            else:
                if dry_run:
                    info(f"- {channel_title}: 既存なし → [DRY-RUN] 作成予定（{len(recent_shorts_ids)}件）。")
                else:
                    info(f"- {channel_title}: 既存なし → 作成します（{len(recent_shorts_ids)}件）。")
                    playlist_body = {
                        'snippet': {
                            'title': playlist_title,
                            'description': f'{channel_title}の直近のShorts動画を集めた再生リストです。'
                        },
                        'status': {
                            'privacyStatus': 'private'
                        }
                    }
                    playlist = execute_with_retry(lambda: youtube.playlists().insert(part='snippet,status', body=playlist_body).execute())
                    new_playlist_id = playlist['id']
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
                        execute_with_retry(lambda: youtube.playlistItems().insert(part='snippet', body=playlist_item_body).execute())
                    info(f"  -> 再生リスト '{playlist_title}' を作成しました。")
        else:
            if dry_run:
                info(f"- {channel_title}: [DRY-RUN] {len(recent_shorts_ids)}件のShorts動画で再生リストを作成予定。")
            else:
                info(f"- {channel_title}: {len(recent_shorts_ids)}件のShorts動画で再生リストを作成します。")
                playlist_body = {
                    'snippet': {
                        'title': playlist_title,
                        'description': f'{channel_title}の直近のShorts動画を集めた再生リストです。'
                    },
                    'status': {
                        'privacyStatus': 'private' # 再生リストを非公開に設定
                    }
                }
                playlist = execute_with_retry(lambda: youtube.playlists().insert(part='snippet,status', body=playlist_body).execute())
                new_playlist_id = playlist['id']
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
                    execute_with_retry(lambda: youtube.playlistItems().insert(part='snippet', body=playlist_item_body).execute())
                info(f"  -> 再生リスト '{playlist_title}' を作成しました。")

    except HttpError as e:
        warn(f"エラーが発生しました ({channel_title}): {e}")


# --- メイン処理 ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YouTube Shorts プレイリスト自動生成/更新スクリプト')
    parser.add_argument('--update', action='store_true', help='既存プレイリストがあれば更新（なければ作成）するモード')
    parser.add_argument('--limit', type=int, default=10, help='1チャンネルあたりのShorts上限（デフォルト: 10）')
    parser.add_argument('--dry-run', action='store_true', help='書き込み操作を行わず、実行計画のみ表示する')
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument('--verbose', action='store_true', help='詳細ログを出力')
    verbosity.add_argument('--quiet', action='store_true', help='必要最低限の出力のみ')
    args = parser.parse_args()

    # ログ設定
    LOG_VERBOSE = bool(args.verbose)
    LOG_QUIET = bool(args.quiet)

    # 認証を行い、APIサービスオブジェクトを取得
    youtube = get_authenticated_service()
    # 登録チャンネルのリストを取得
    subscriptions = get_my_subscriptions(youtube)

    if not subscriptions:
        info("登録しているチャンネルがありません。")
    else:
        # 各登録チャンネルに対して、Shorts再生リスト作成/更新処理を実行
        for sub in subscriptions:
            channel_id = sub['snippet']['resourceId']['channelId']
            channel_title = sub['snippet']['title']
            create_playlist_for_recent_shorts(youtube, channel_id, channel_title, update_mode=args.update, per_channel_limit=args.limit, dry_run=args.dry_run)
        info("\nすべての処理が完了しました。")