# CLAUDE.md

## リポジトリ概要

[resoloop](https://github.com/orange3134/resoloop) と Blender で resonite 上に 3D モデルやワールドを作成する開発環境

## 基本方針

- ユーザの指示が曖昧な場合は AskUserQuestion を使う
- 複雑なモデルを作る時や、計画や設計が必要な変更は、方針を決めてから実装する
- Python を使う時は uv 必須であり python3 コマンドを使わないこと

## 日本語表現

コードレビューや説明、PR や Issue への起票では、不自然な直訳表現を避け、日本人エンジニアに一般的な表現を使うこと。

- `contract` を「契約」と訳さず、文脈に応じて「仕様」「API仕様」「インターフェース仕様」「既存の挙動」などと表現する。
- `atomic` / `atomically` を「原子的」「原子的に」と訳さず、文脈に応じて「アトミック」「一括で」「途中状態を残さず」「不可分な操作として」などと表現する。
- 単なる言い換えではなく、可能な限り具体的に何が保証されるか、何が問題になるかを説明する。
- `product` / `production` を機械的に「製品」と訳さない。「製品」「製品実装」は原則として使用せず、文脈に応じて自然な日本語に言い換えること。

  - 「製品」→「システム」「アプリケーション」「機能」「実装」「対象」など
  - 「製品実装」→「実装作業」「本実装」「機能実装」など

- 作業終了を表す際に「着地」「着地完了」は使用しない。

  - 文脈に応じて「完了」「作業完了」「対応完了」「実装完了」「修正完了」を使用する。

## ファイルとドラフト

- `docs_draft/` は、タスクで指定された場合だけ読む
- ユーザから作成を依頼された文書は、`docs_draft/` に reStructuredText で作成する

## 開発と検証

- リポジトリ内の Python ツールは `uv` で実行する
- Gitleaks は `.devcontainer/install_beforehand.bash` と同じ approved pin を使う。Dev Container では再導入しない

## エージェント運用

- 長時間コマンド、検証、バックグラウンド処理、サブエージェントの完了・生存・進捗を監視するときは `monitoring-long-tasks` を使う。監視手順はスキルが正本であり、各ランタイムでどのツールを使うかは `.agents/monitoring-runtimes.md` を参照する

### SDD 実行運用

- Plan に contingency 節を設ける。最初の RED で実環境の出力形式や API 挙動が前提と異なる場合は、仕様の意味を保つ最小限の修正を ledger に記録して継続する。仕様の意味を変える場合だけ Ruling を求める
- 開発中は変更に関連するテストと静的チェック（ruff / pyright）を実行する。最終 Task では、環境変更は親 worktree の `./scripts/ci/verify-devenv.sh`、アプリ変更は公開側 worktree の `./scripts/ci/verify.sh <profile>` を1回実行する。アプリの profile は上記の差分基準で選ぶ
- 実装サブエージェントはテスト、lint、回帰を同期実行し、完了を待ってからターンを終える。`monitoring-long-tasks` の監視ルールは controller が長時間タスクを監視するためのものであり、実装サブエージェント内部の待ちをバックグラウンド化する根拠にしない
- controller は `monitoring-long-tasks` の終了条件が成立するまでターンを保持し、stall ポーリングを担当する。完了通知は harness の終了コード付きプロセス終了通知を指し、成果物やサブエージェントの結果通知とは区別する。これは対象停止の判定材料であり、対象の実行中にターンを終える根拠にしない。ただし事前宣言した読み取り専用の PR レビュー委譲の期限・無進捗打ち切りに限り、停止確認不能のときは委譲対象・停止状態・残存パスを報告してターンを終えてよい。`TaskOutput(block=true)` の raw dump は読まず、途中経過は出力ファイルを必要な範囲だけ読む
- 各担当は着手から成果提出までの所要時間と主要 Task 別の内訳を作業報告に記録する

## 環境

Windows 11 の WSL2（Gentoo Linux）上で Docker を動かし、Ubuntu 26.04 LTS の Dev Container を使用する。

## 最新ドキュメントの取得

- ライブラリ、フレームワーク、SDK、API、CLI、クラウドサービスの仕様は Context7 で確認する。リファクタリング、ビジネスロジック、コードレビューには使わない
- ユーザが `/org/project` 形式の ID を示していない場合は、`npx ctx7@latest library <name> "<query>"` で ID を解決してから、`npx ctx7@latest docs <id> "<query>"` を実行する
- ユーザの質問を具体的な query にし、機密情報を含めない。1件につき3回までとし、指定バージョンがある場合は返された version ID を使う
- quota error の場合はその旨を伝え、`npx ctx7@latest login` または `CONTEXT7_API_KEY` を案内する。黙って別情報へ切り替えない
