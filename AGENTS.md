# create-reso-world 共通規約

このリポジトリで作業するコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin、dsh）の共通規約。Claude Code 固有の注意は `CLAUDE.md`、pi 固有の注意は `.pi/APPEND_SYSTEM.md` にある。ワールドのプロジェクトでは、この規約に加えてプロジェクト直下の `AGENTS.md` が適用される。

## リポジトリ概要

[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite 上に 3D モデルやワールドを作成する開発環境。Dev Container の定義と、ワールドのプロジェクト（`MyResoniteProject/`、`akichi/`、`slum02/`）を同じリポジトリで管理する。

## 基本方針

- ユーザの指示が曖昧な場合は、作業を始める前にユーザに質問する
- 複雑なモデルを作る時や、計画や設計が必要な変更は、方針を決めてから実装する
- Python を使う時は uv 必須であり python3 コマンドを使わないこと。リポジトリ内の Python ツールも `uv` で実行する
- 例外として、Dev Container のブートストラップ（`.devcontainer/` 配下）と zsh ヘルパーは uv の導入前にも動く必要があるため、python3 を使ってよい

## resoloop 注意

- 後から人間がインスペクターで触りやすいように、オブジェクトごとに、1つのメッシュにする
- タスク開始前に、タスクの内容を確認し、長大なタスクであった場合は分割して実装する
- 長時間タスクは同一セッションを使いまわすと Context Rot が起こるので、区切りのいいところで agent-handoff スキルを使って引き継ぐ

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

- `docs_draft/` はローカルの下書き置き場で、git では追跡しない。タスクで指定された場合だけ読む
- ユーザから作成を依頼された文書は、`docs_draft/` に Markdown で作成する
- リポジトリに残す文書は `docs/` に置く。設計仕様は `docs/superpowers/specs/`、実装計画は `docs/superpowers/plans/` に置く

## プロジェクト運用

- ワールドの作業は、そのプロジェクトのディレクトリ（例: `slum02/`）を cwd にしてエージェントを起動する。プロジェクト固有の規約と安全ルールは、プロジェクト直下の `AGENTS.md` にある
- 新しいプロジェクトは `scripts/new-world.sh <name>` で作る。既存プロジェクトの雛形の不足分は `scripts/new-world.sh --apply <name>` で補う
- 各プロジェクトのテストは、そのプロジェクトのディレクトリで `uv run pytest` を実行する
- resoloop 同梱のスキル（`resonite-*`）が導入済みの resoloop と一致しているかは、プロジェクトのディレクトリで `resoloop skills sync --check` を実行して確かめる。更新は差分を確認してから `resoloop skills sync --update` で行う
- リポジトリ全体の配置は `scripts/check-layout.sh` で検査する

## リポジトリ境界

作業や PR の対象リポジトリごとに、作業ルートと確認事項を次のとおりとする。

| PR や作業対象の owner/repo | 作業ルート | 確認事項 |
| --- | --- | --- |
| usaturn/create-reso-world（このリポジトリの origin） | `git rev-parse --show-toplevel` | `origin` の URL が一致すること |
| usaturn/resoloop または orange3134/resoloop | `<toplevel>/external/resoloop` | `origin` が usaturn/resoloop、`upstream` が orange3134/resoloop であること。checkout が無ければ `scripts/resoloop-fork.sh clone` を案内して停止する |
| それ以外 | 推測せず停止する | — |

## ResoLoop の版管理

- 導入する ResoLoop の版は `.devcontainer/resoloop.lock` を正とする。既定は fork モードで、Blender 5 の UV 修正を含むビルドを使う
- 版を変えるときはロックファイルを明示的に更新してコミットする。`dotnet tool update` などで手元の導入だけを変えない
- fork の取得・ビルド・導入は `scripts/resoloop-fork.sh` で行い、手順は `docs/resoloop-fork-workflow.md` に従う

## エージェント運用

- 長時間コマンド、検証、バックグラウンド処理、サブエージェントの完了・生存・進捗を監視するときは monitoring-long-tasks スキルを使う。監視手順はスキルが正本であり、各ランタイムでどのツールを使うかはリポジトリルートの `.agents/monitoring-runtimes.md` を参照する（プロジェクトを cwd にしている場合も、パスはリポジトリルート基準）

### SDD 実行運用

- 実装サブエージェントはテスト、lint、回帰を同期実行し、完了を待ってからターンを終える。monitoring-long-tasks の監視ルールは controller が長時間タスクを監視するためのものであり、実装サブエージェント内部の待ちをバックグラウンド化する根拠にしない
- controller は monitoring-long-tasks の終了条件が成立するまでターンを保持し、stall ポーリングを担当する。完了通知は harness の終了コード付きプロセス終了通知を指し、成果物やサブエージェントの結果通知とは区別する。これは対象停止の判定材料であり、対象の実行中にターンを終える根拠にしない。ただし事前宣言した読み取り専用の PR レビュー委譲の期限・無進捗打ち切りに限り、停止確認不能のときは委譲対象・停止状態・残存パスを報告してターンを終えてよい
- 各担当は着手から成果提出までの所要時間と主要 Task 別の内訳を作業報告に記録する

## 環境

Windows 11 の WSL2（Gentoo Linux）上で Docker を動かし、Ubuntu 26.04 LTS の Dev Container を使用する。

## 最新ドキュメントの取得

- ライブラリ、フレームワーク、SDK、API、CLI、クラウドサービスの仕様は Context7 で確認する。手順は find-docs スキルを正本とする
- 問い合わせは 1 件につき 3 回までとする
