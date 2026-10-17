# create-reso-world 共通規約

このリポジトリで作業するコーディングエージェント（Claude Code、Codex、pi、Cursor、Devin）の共通規約。Claude Code 固有の注意は `CLAUDE.md`、pi 固有の注意は `.pi/APPEND_SYSTEM.md` にある。ワールドのプロジェクトでは、この規約に加えてプロジェクト直下の `AGENTS.md` が適用される。
本文に書くパスは、プロジェクトを cwd にしている場合も含めて、特記が無ければリポジトリのルート基準である。

## リポジトリ概要

[resoloop](https://github.com/orange3134/resoloop) と Blender で Resonite 上に 3D モデルやワールドを作成する開発環境。Dev Container の定義と共通の規約・スキル・雛形を管理する。ワールドのプロジェクトはローカルの作業物で git の追跡対象外であり、`worlds/` の直下に作る（issue #57）。追跡解除した従来位置の `MyResoniteProject/`、`akichi/`、`slum02/`、`slum03/` もローカルの作業物として残る。resoloop のプラグイン（Meshy 用の usaturn/resoloop-meshy）は、別のリポジトリとして `external/resoloop-meshy` に checkout して開発する（「リポジトリ境界」）。

## 基本方針

- ユーザの指示が曖昧な場合は、作業を始める前にユーザに質問する
- 複雑なモデルを作る時や、計画や設計が必要な変更は、方針を決めてから実装する
- Python を使う時は uv 必須であり python3 コマンドを使わないこと。リポジトリ内の Python ツールも `uv` で実行する
- 例外として、Dev Container のブートストラップ（`.devcontainer/` 配下）と zsh ヘルパーは uv の導入前にも動く必要があるため、python3 を使ってよい
- ローカルは常に origin/main(origin/HEAD) に保つこと(ローカルの main は作らない)

## テストの採用基準

テストは、コードを実行して確かめる挙動があるときだけ書く。superpowers の TDD でも、守る挙動が無い変更ではテストを作らずに進める。

- 書く: コードを実行してロジック・分岐・安全条件・入出力の解析を確かめる場合、実際に起きた不具合の再発を防ぐ場合
- 書かない: 文書・SKILL.md の文面・設定値・一覧・雛形だけの変更
- 作らない型:
  1. 文書の文言を `in`／`not in` などで照合する
  2. 削除した旧ファイル・旧文言が無いことだけを確かめる
  3. ランチャー一覧・手順名・版・モデル名など、運用で変わる値をテストに写す
  4. スクリプトを実行せず、本文の文字列一致だけで判定する
  5. 同じ実体を複数のパス（symlink など）で検査する。pydantic・Pyright・ruff など他の仕組みが保証することを再検査する
- 安全な操作範囲・権限・凍結した履歴・利用者所有部分を守るための固定値は使ってよい。防ぐ誤りと理由をテストに書く
- テストを書かないときは、ツールの実行、静的解析・型検査、構造の検査（構文・参照先の実在）、`git diff` の確認で代え、結果を報告する
- Plan の各 Task に、テストの要否と理由を書く。不要なら、代わりの検証を検証手順にする
- レビューでは、追加・変更されたテストがこの基準に反していないか確かめる

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

- 「正本」は使用しない。「採用条件は `page-types.md` にのみ定義する」のようにファイル名と関係を具体的に書く。
   抽象語が必要な場合は、仕様・ルールを定義するファイルを文脈に応じて「定義元」「正式版」「基準となる文書・設定」「正式な保存先」「一元管理する場所」「〜を基準とする」など、日本人エンジニアに自然で分かりやすい表現に言い換えること。
   単純な置換ではなく、何を基準にするのかが伝わる文章にする。

## ファイルとドラフト

- `docs_draft/` はローカルの下書き置き場で、git では追跡しない。タスクで指定された場合だけ読む
- ユーザから作成を依頼された文書は、`docs_draft/` に Markdown で作成する
- リポジトリに残す文書は `docs/` に置く。設計仕様は `docs/superpowers/specs/`、実装計画は `docs/superpowers/plans/` に置く

### Spec・Plan の保存と公開

- どのリポジトリの作業でも、Spec・Plan の正本は `usaturn/create-reso-world` の `docs/superpowers/` に保存してコミットする。ResoLoop や無関係なリポジトリの作業でも、対象リポジトリには置かず、二重管理もしない。運用の要点は `docs/superpowers/README.md` にある
- スキル superpowers で作成する Spec・Plan は、作業時に必ず作成している worktree のブランチにコミットし、ユーザ確認用で main の `docs_draft/superpowers/specs/` `docs_draft/superpowers/plan/` にコピーする
- 作業先は 3 つを区別する。`PARENT_ROOT` はユーザが確認用ファイルを読む create-reso-world の親 checkout、`DOC_ROOT` は正本をコミットする create-reso-world の checkout または worktree、`CODE_ROOT` はユーザの依頼または確認済みの引き継ぎで明示された、コード対象の checkout の絶対パスである。コード対象の cwd の `git rev-parse --show-toplevel` を、`DOC_ROOT` や `PARENT_ROOT` とみなさない
- 文書を create-reso-world に集めることは、他のリポジトリのコード変更・clone・push・PR 作成の許可ではない。対象 checkout の `AGENTS.md` 等も守る
- 正式な Spec・Plan は、承認前でも `draft` のまま `DOC_ROOT` の作業ブランチにコミットする。状態は `draft`・`approved`・`completed`・`superseded`・`cancelled` で書き、コミットしただけで `approved` にしない。完了した文書も削除しない
- 同じテーマのレビュー修正は既存の文書を更新し、過去の版は Git の履歴に残す。更新前には対象リポジトリ・Issue/PR・テーマ・正本のパスで現行の Spec/Plan を探し、複数の候補があって確定できないときは進めずに確認する。回ごとの新規文書（roundN）は既定で作らない。承認は内容のコミット SHA に結び付け、承認後の状態・記録追記だけの変更は再承認を求めない。実質的な設計・計画の変更は再承認を必要とする（記録した実行許可がその変更を明示的に含む場合を除く）。例外で進める場合は許可された変更内容を記録し、一般的な継続指示だけで変更の承認を推測しない
- ユーザに Spec・Plan の確認を依頼する前に、コミット済みの版を `scripts/superpowers-review-copy.sh` で `PARENT_ROOT` の `tmp/superpowers-review/` へコピーし、コピー先・文書のコミット SHA・正本のパスを示す。ファイル名は内容が分かる短い名前に `-spec.md` か `-plan.md` を付け、関連する Issue・PR があれば `<repo>-pr<N>-` のように番号を含める。番号を発明しない。コピーは既存の entry を決して差し替えない。正本が変わったら `...-r2-spec.md` のような別名で新しいコピーを公開し、旧コピーとユーザの注記は残す
- 公開: create-reso-world 自身の変更に伴う文書は、その作業の PR に含める。他のリポジトリの変更に伴う文書は、create-reso-world の文書用ブランチから、テーマごとに 1 つの文書専用 PR で公開する。コミット・push・PR 作成・マージは別の段階であり、ユーザまたは使っているワークフローの明示指示があるときだけ行う。ローカルのコミットだけのときは、報告と handoff に「公開未実施」と書く

## プロジェクト運用

- ワールドの作業は、そのプロジェクトのディレクトリ（例: `worlds/slum02/`）を cwd にしてエージェントを起動する。プロジェクト固有の規約と安全ルールは、プロジェクト直下の `AGENTS.md` にある
- 新しいプロジェクトは `scripts/new-world.sh <name>` で作る（`worlds/<name>/` に作られ、git の追跡対象外）。既存プロジェクトの雛形の不足分は `scripts/new-world.sh --apply <name>` で補う（`worlds/<name>/` と従来位置の `MyResoniteProject/`・`akichi/`・`slum02/`・`slum03/` の両方に使える）
- プロジェクトは git の追跡対象外なので、ワールド作業に branch・commit・PR は要求しない。`git clean -fdx` はローカルプロジェクトをまとめて削除するので使わない
- 各プロジェクトのテストは、そのプロジェクトのディレクトリで `uv run pytest` を実行する
- resoloop 同梱のスキル（`resonite-*`）が導入済みの resoloop と一致しているかは、プロジェクトのディレクトリで `resoloop skills sync --check` を実行して確かめる。更新は差分を確認してから `resoloop skills sync --update` で行う
- リポジトリ全体の配置は `scripts/check-layout.sh` で検査する

## リポジトリ境界

作業や PR の対象リポジトリごとに、作業ルートと確認事項を次のとおりとする。

| PR や作業対象の owner/repo | 作業ルート | 確認事項 |
| --- | --- | --- |
| usaturn/create-reso-world（このリポジトリの origin） | `git rev-parse --show-toplevel` | `origin` の URL が一致すること |
| usaturn/resoloop または orange3134/resoloop | `<toplevel>/external/resoloop` | `origin` が usaturn/resoloop、`upstream` が orange3134/resoloop であること。checkout が無ければ `scripts/resoloop-fork.sh clone` を案内して停止する |
| usaturn/resoloop-meshy | `<PARENT_ROOT>/external/resoloop-meshy` | `origin` が usaturn/resoloop-meshy であること。checkout が無ければ `bash scripts/resoloop-meshy.sh clone` を案内して停止する。実装は作業ルートの `.worktrees/<topic>` の worktree で行う。`pr-review`・`review-fix-planning` には作業ルートを `CODE_ROOT` として明示する。手順は `docs/resoloop-meshy-workflow.md` |
| それ以外 | ユーザの依頼または確認済みの引き継ぎで明示された checkout の絶対パス（`CODE_ROOT`） | その checkout 自身のルートであり、remote のうち 1 つだけが対象の owner/repo と一致すること。この経路を持つのは `pr-review`（レビュー）と `review-fix-planning`（修正計画と、その PR の承認済み実装修正）で、既存の承認済み PR 修正経路は維持する。一般的な外部コード実装は非対応であり、実行経路が未定義の外部実装の handoff は blocked（not ready）として記録する。remote が無いローカル専用の checkout との PR 連携は非対応のため扱えない（明示指示があっても resolver は remote 0 件で停止する）。明示が無い・一致しない・候補が複数ある場合は推測せず停止する。checkout の探索・clone はしない |

## GitHub Actions

- 料金の問題でプライベートの usaturn/create-reso-world の CI は使わず停止しているため、CI の確認は不要。パブリックの CI は停止していない為、確認すること
- テストを作っても CI（GitHub Actions のワークフローなど）は作らない。テストはローカルで実行し、結果を報告する。新しいリポジトリを作ったら、その場で Actions を無効にする（`gh api -X PUT repos/<owner>/<repo>/actions/permissions -F enabled=false`）

## ResoLoop の版管理

- ResoLoop は常に NuGet の最新の公開版を使い、版を固定しない。postCreate が `.devcontainer/install_resoloop.bash` で最新を導入する。rebuild せずに最新へ上げるときも同じスクリプトを実行する。使っている版は `resoloop --version` で確かめる
- 上流に未取り込みの修正を一時的に使うときは、`scripts/resoloop-fork.sh install <fork のブランチかコミット>` で fork のビルドを導入する。次の rebuild か `bash .devcontainer/install_resoloop.bash` で最新の公開版に戻る。fork の取得・ビルド・導入の手順は `docs/resoloop-fork-workflow.md` に従う
- 版が上がると同梱スキル（`resonite-*`）にも更新が出る。postCreate と `scripts/check-layout.sh` は更新の有無を表示するだけなので、「プロジェクト運用」のとおり差分を確認してから `--update` する

## エージェント運用

- 長時間コマンド、検証、バックグラウンド処理、サブエージェントの完了・生存・進捗を監視するときは monitoring-long-tasks スキルを使う。監視手順はスキルが正本であり、各ランタイムでどのツールを使うかはリポジトリルートの `.agents/monitoring-runtimes.md` を参照する（プロジェクトを cwd にしている場合も、パスはリポジトリルート基準）

### SDD 実行運用

- Plan に「実行予算」の節を設け、Issue 全体の能動時間の予算、phase の目安、worker の期限・予約枠・無進捗の打ち切り、失敗の種類ごとの再試行の上限、checkpoint の時点、縮小・切り出し・方法変更の候補を書く。適用範囲、時間の数え方、ledger の置き場所と片付け、checkpoint での判断は `.agents/execution-budget.md` に従う
- 実装サブエージェントはテスト、lint、回帰を同期実行し、完了を待ってからターンを終える。monitoring-long-tasks の監視ルールは controller が長時間タスクを監視するためのものであり、実装サブエージェント内部の待ちをバックグラウンド化する根拠にしない
- controller は monitoring-long-tasks の終了条件が成立するまでターンを保持し、stall ポーリングを担当する。完了通知は harness の終了コード付きプロセス終了通知を指し、成果物やサブエージェントの結果通知とは区別する。これは対象停止の判定材料であり、対象の実行中にターンを終える根拠にしない。ただし monitoring-long-tasks の「事前宣言した打ち切り」の対象に限り、宣言した条件で止めてよく、停止確認不能のときは対象・停止状態・残存パスを報告してターンを終えてよい
- 各担当は着手から成果提出までの所要時間と主要 Task 別の内訳を作業報告に記録する

## 環境

Windows 11 の WSL2（Gentoo Linux）上で Docker を動かし、Ubuntu 26.04 LTS の Dev Container を使用する。

## 最新ドキュメントの取得

- ライブラリ、フレームワーク、SDK、API、CLI、クラウドサービスの仕様は Context7 で確認する。手順は find-docs スキルを正本とする
- 問い合わせは 1 件につき 3 回までとする
