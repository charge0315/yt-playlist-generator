## YouTube ショート動画プレイリスト生成ツール

このプロジェクトは、登録しているチャンネルから YouTube ショート動画のプレイリストを自動生成する Python スクリプトです。

### プロジェクト概要

主要なロジックは `scripts/main.py` に含まれています。このスクリプトは YouTube Data API v3 を使用して以下の処理を行います:
1.  登録しているすべてのチャンネルを取得します。
2.  各チャンネルについて、61秒未満のショート動画である最近の動画を検索します。
3.  各チャンネルの最新ショート動画を含む新しい非公開プレイリストを作成します。

認証は Google OAuth 2.0 を介して処理されます。スクリプトの初回実行時には、認証のためにブラウザが開きます。その後の実行では、保存された `token.pickle` ファイルが使用されます。

### 主要ファイル

-   `scripts/main.py`: アプリケーションのメインエントリーポイントであり、中心的なロジックです。
-   `requirements.txt`: Python の依存関係をリストアップしています。
-   `setup.ps1` / `setup.sh`: Windows および Unix ライクなシステム向けのセットアップスクリプトで、仮想環境の作成と依存関係のインストールを行います。
-   `client_secret.json`: **(必須、リポジトリには含まれません)** Google OAuth 2.0 のクライアントシークレットファイルです。Google Cloud Console から取得し、プロジェクトのルートに配置する必要があります。
-   `token.pickle`: **(生成される)** 認証成功後にユーザーのアクセスおよびリフレッシュトークンを保存します。

### 開発ワークフロー

**1. セットアップ**

スクリプトを実行する前に、環境をセットアップする必要があります。

Windows (PowerShell) の場合:
```powershell
pwsh -ExecutionPolicy Bypass -File .\setup.ps1
```

macOS / Linux の場合:
```bash
bash ./setup.sh
```

これらのスクリプトは `.venv/` に Python 仮想環境を作成し、`requirements.txt` から必要なパッケージをインストールします。

**2. スクリプトの実行**

セットアップ後、メインスクリプトを実行します:
```bash
# Windows の場合
.venv\Scripts\activate
python scripts/main.py

# macOS / Linux の場合
source .venv/bin/activate
python scripts/main.py
```

**3. ドライラン**

実際にプレイリストを作成または変更せずにスクリプトが何を行うかを確認するには、`--dry-run` フラグを使用します。これはテストやデバッグに便利です。
```bash
python scripts/main.py --dry-run
```

### プロジェクト固有の規約

-   スクリプトは簡易的なロギング実装を使用しています。出力には `info()`、`debug()`、`warn()` 関数を使用してください。
-   YouTube API への API 呼び出しは、`scripts/main.py` の `execute_with_retry` ヘルパー関数でラップされており、指数バックオフを用いて一時的なネットワークエラーを処理します。新しい API 呼び出しを追加する際は、堅牢性を確保するためにこのヘルパーを使用してください。
