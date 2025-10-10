# YouTube Shorts プレイリスト自動生成スクリプト

自分が登録しているYouTubeチャンネルの最新ショート動画を自動で検出し、チャンネルごとに再生リストを自動生成するPythonスクリプトです。

## 主な機能

- 登録している全チャンネルを自動で取得
- 各チャンネルの最新動画からショート動画（61秒以下）を検出
- チャンネルごとに最新ショート動画（最大10件）をまとめた再生リストを非公開で作成
- Google OAuth認証情報を自動で管理（初回認証後は自動ログイン）

## 必要なもの

- Python 3.x

## セットアップ方法

1. **リポジトリをクローン**
   ```bash
   git clone https://github.com/charge0315/youtube-playlist-generator.git
   cd youtube-playlist-generator
   ```

2. **仮想環境の作成と有効化**
   ```bash
   # 仮想環境を作成
   python -m venv .venv
   
   # 仮想環境を有効化
   # Windowsの場合
   .venv\Scripts\activate
   # macOS / Linux の場合
   # source .venv/bin/activate
   ```

3. **依存ライブラリのインストール**
   ```bash
   pip install -r requirements.txt
   ```

## 事前準備：Google APIキーの取得

このスクリプトを実行するには、GoogleのOAuth 2.0クライアントIDが必要です。

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセスし、新しいプロジェクトを作成します。
2. 「APIとサービス」 > 「ライブラリ」に移動し、**YouTube Data API v3**を検索して有効にします。
3. 「APIとサービス」 > 「認証情報」に移動し、「認証情報を作成」 > 「OAuthクライアントID」を選択します。
4. アプリケーションの種類で「デスクトップアプリ」を選択し、適当な名前をつけます。
5. 作成後、JSONファイルをダウンロードし、ファイル名を`client_secret.json`に変更します。
6. `client_secret.json`を、このプロジェクトのルートディレクトリ（`.gitignore`や`requirements.txt`がある場所）に配置します。

## 実行方法

プロジェクトのルートディレクトリで、以下のコマンドを実行します。

```bash
python scripts/main.py
```

初回実行時、ブラウザが自動的に開き、Googleアカウントでのログインと、YouTubeアカウントへのアクセス許可を求める画面が表示されます。画面の指示に従って認証を完了してください。

2回目以降は、保存された認証情報を使って自動で処理が開始されます。
