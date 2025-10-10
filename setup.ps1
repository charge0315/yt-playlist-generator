<#
 .SYNOPSIS
  youtube-playlist-generator の実行環境をセットアップします（Windows/PowerShell）。

 .DESCRIPTION
  - Python の検出（py / python）
  - 仮想環境 .venv の作成（既存があれば再利用。-Recreate で再作成）
  - 依存パッケージのインストール（pip をアップグレード）
  - 必須ファイル client_secret.json の存在チェック
  - 最後に次のステップを案内（-Run で scripts/main.py を実行）

 .PARAMETER Recreate
  既存の .venv を削除してから再作成します。

 .PARAMETER Run
  セットアップ完了後に scripts/main.py を実行します（初回はブラウザで認証が開きます）。

 .EXAMPLE
  pwsh -ExecutionPolicy Bypass -File .\setup.ps1

 .EXAMPLE
  pwsh -ExecutionPolicy Bypass -File .\setup.ps1 -Recreate -Run
#>

[CmdletBinding()] Param(
    [switch]$Recreate,
    [switch]$Run
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERR]  $msg" -ForegroundColor Red }

try {
    # スクリプトのルート（リポジトリのルート）
    $RepoRoot = $PSScriptRoot
    Set-Location $RepoRoot
    Write-Info "Repository root: $RepoRoot"

    # Python 実行コマンドの検出
    $pythonExe = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3 --version | Out-Null
            $pythonExe = @('py','-3')
            Write-Ok "Using Python via 'py -3'"
        } catch {
            & py --version | Out-Null
            $pythonExe = @('py')
            Write-Ok "Using Python via 'py'"
        }
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python --version | Out-Null
        $pythonExe = @('python')
        Write-Ok "Using Python via 'python'"
    } else {
        throw "Python が見つかりませんでした。Microsoft Store などから Python 3.x をインストールしてください。"
    }

    # .venv 作成/再作成
    $venvPath = Join-Path $RepoRoot '.venv'
    if (Test-Path $venvPath) {
        if ($Recreate) {
            Write-Warn ".venv を削除して再作成します (-Recreate)。"
            Remove-Item -Recurse -Force $venvPath
        } else {
            Write-Info ".venv が既に存在します。再利用します。(-Recreate で再作成)"
        }
    }

    if (-not (Test-Path $venvPath)) {
        Write-Info ".venv を作成しています…"
        & $pythonExe[0] $pythonExe[1..($pythonExe.Length-1)] -m venv .venv
        Write-Ok ".venv を作成しました。"
    }

    # 仮想環境の Python
    $venvPython = Join-Path $venvPath 'Scripts/python.exe'
    if (-not (Test-Path $venvPython)) {
        throw "仮想環境の Python が見つかりませんでした: $venvPython"
    }

    # pip アップグレードと依存インストール
    Write-Info "pip / setuptools / wheel をアップグレードしています…"
    & $venvPython -m pip install --upgrade pip setuptools wheel | Out-Host
    Write-Ok "pip / setuptools / wheel をアップグレードしました。"

    $reqFile = Join-Path $RepoRoot 'requirements.txt'
    if (Test-Path $reqFile) {
        Write-Info "requirements.txt をインストールしています…"
        & $venvPython -m pip install -r $reqFile | Out-Host
        Write-Ok "依存関係をインストールしました。"
    } else {
        Write-Warn "requirements.txt が見つかりません。スキップします。"
    }

    # 簡易インポート検証
    Write-Info "インポート検証を実行しています…"
    $code = @"
import importlib, sys
mods = ['googleapiclient', 'google_auth_oauthlib']
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        missing.append(f"{m}: {e}")
if missing:
    print('MISSING:', '; '.join(missing))
    sys.exit(2)
print('IMPORTS_OK')
"@
    & $venvPython -c $code
    if ($LASTEXITCODE -ne 0) { throw "必要な Python モジュールのインポートに失敗しました。" }
    Write-Ok "必要なモジュールのインポートに成功しました。"

    # 認証ファイルの存在チェック
    $clientSecret = Join-Path $RepoRoot 'client_secret.json'
    if (-not (Test-Path $clientSecret)) {
        Write-Warn "client_secret.json がありません。README の手順に従って Google Cloud Console からダウンロードし、プロジェクト直下に配置してください。"
    } else {
        Write-Ok "client_secret.json を検出しました。"
    }

    # 次のステップ
    Write-Host ""; Write-Ok "セットアップが完了しました。"; Write-Host ""
    Write-Host "次のコマンドで実行できます:" -ForegroundColor Cyan
    Write-Host "  .\\.venv\\Scripts\\python scripts\\main.py" -ForegroundColor White
    Write-Host "（初回はブラウザで Google 認証が開きます）" -ForegroundColor DarkGray

    if ($Run) {
        Write-Info "scripts/main.py を起動します (-Run)。"
        & $venvPython (Join-Path $RepoRoot 'scripts/main.py')
    }

    exit 0
}
catch {
    Write-Err $_
    exit 1
}
