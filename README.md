# Times Bot

このリポジトリは Discord の新規参加者ごとに `times-<name>` チャンネルを自動作成し、退室時にアーカイブへ移動する Bot です。

## 機能
- サーバー参加時に `times-ユーザー名` のテキストチャンネルを作成
- 退室時に timesチャンネルをアーカイブ用カテゴリへ移動
- 既存チャンネルがアーカイブにある場合は復帰
- `times-` チャンネルのみ並び順をアルファベットで整列

## 事前準備
1. Discord Developer Portal でアプリ/ボットを作成
2. Bot Token を取得（後述の `.env` に設定）
3. サーバーに Bot を招待（必要権限: チャンネル管理、チャンネル作成、メッセージ送信 など）
4. Privileged Intents を有効化（以下の二つ）
   - `Server Members Intent`
   - `Message Content Intent`

## インストール
[Poetry](https://python-poetry.org/) を使用します。
```bash
poetry install
```

## 使い方
1. `.env.example` をコピーして `.env` を作成し、`DISCORD_BOT_TOKEN` に Bot Token を設定（`.env` は Git にコミットしないこと）
2. Bot を起動
```bash
poetry run python times.py
```
3. Discord 上でカテゴリIDを指定してセットアップ
```text
!setup active <category_id>
!setup archive <category_id>
```
- `active` : 参加者の `times-` チャンネルを作成するカテゴリ
- `archive`: 退室者のチャンネルを移動するカテゴリ

`settings.json` に設定が保存されます。再起動後も保持されます。

## 動作概要
- 参加時: `times-<username>` を作成。既存チャンネルがアーカイブにある場合は `active` へ戻します。
- 退室時: 該当チャンネルを `archive` カテゴリへ移動します。

## 注意点
- ユーザー名を小文字化し、空白/記号を削除してチャンネル名を生成します。
- `times-` 以外のチャンネルは並び替え対象になりません。
- `settings.json` が壊れている場合は空設定として起動します。

## ファイル構成
- `times.py` : Bot 本体
- `.env` : Bot Token（`.env.example` をコピーして作成）
- `settings.json` : 設定保存（自動生成）
