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

テストを書くのは、下の S に当たる項目だけである。テストごとに、確かめる項目が壊れたときにエラーで気付けるかで、次のどれに当たるかを決める。

- F 固定値（書かない。F∩S を除く）: リポジトリの文書・設定・一覧の今の値を写して照合するテスト。文書の文言・見出し・節（削除した旧ファイル・旧文言が無いことを含む）、SKILL.md の本文と frontmatter、ランチャー・手順名・モデル・版・tier・mount・環境変数・ファイルの一覧、リポジトリのファイルのハッシュ、設定ファイルの値を写したもの、スクリプトを実行せずに本文の文字列だけで判定するものが当たる。コードに入力を与えて出力と比べる単体テストの期待値と、SKILL.md の手順を取り出して実際に実行するテストは F ではない
- F∩S（例外として使ってよく、消さない）: F のうち、壊れてもエラーにならない損害を防ぐ固定値。安全な操作範囲・権限・凍結した履歴・利用者所有部分を守る固定値が当たる。例: 削除の範囲、誤った対象を操作しないために禁止するパス、資格情報の送り先、権限を決める設定値（SKILL.md の frontmatter を含む）、指示ファイルの読み込み指定、mount・unset する環境変数・gitignore の範囲の一覧、利用者所有部分や凍結した履歴のハッシュ。防ぐ損害と理由をテストに書く
- L 気付ける（テストしない）: テストが無くても、壊れたときに普段の利用か既存の検査（ほかのテストは含めない。同じ守りの重なりは D）で、エラーや明らかな異常として現れる項目。例外・トレースバック、メッセージ付きの非 0 の終了、import・構文・解析のエラー、argparse、pydantic の検証、型検査・ruff、コマンドやファイルが見つからない、`scripts/check-layout.sh` の失敗、同じ流れの後段（次のツール、git、gh）が必ず失敗する、初回の利用で明らかに動かない、などで現れるものが当たる。ヘルプの文面、オプションの解析、エラーで止まる経路の終了コード、ファイルの存在・実行権限・symlink、誤った入力で例外を投げることだけを確かめるテストも L。ただし、拒否・停止・終了コードが壊れたときに、エラーにならずに S の損害（危険な操作が進む、失敗を成功と報告する、別の対象を選ぶ、記録を取り違える・上書きするなど）が残るものは S
- S 気付けない損害（書く）: 壊れてもエラーにならず、気付かないまま損害が残る項目。誤っているがもっともらしい結果（失敗を成功と報告する、別の PR・ブランチ・リポジトリ・base を選ぶ、未検証の状態をマージする、記録を失う・上書きする）、データの消失、誤った対象の削除・上書き・破壊的な git の操作、秘密情報の漏れ、危険な操作の拒否（パスの脱出、権限・サンドボックスの境界）、環境の隔離（`GIT_*`・`HOME`）、競合の防止が当たる。実際に起きた、気付けない不具合の再発防止も含む
- D 重複（代表の 1 件にする）: S のうち、同じ守りを別の組み合わせ・層・ファイルで確かめるテスト。同じ守りは代表の 1 件にし、組み合わせを網羅しない。同じ実体を複数のパス（symlink など）で確かめない。拒否を確かめるテストには、正しく通る例を少なくとも 1 件残す（何でも拒否する実装で通らないように）。守りは、それを実装しているモジュールのテストに置く
- superpowers の TDD でも、S に当たらない挙動のテストはコミットしない。確かめは、ツールの実行や一時的なテストで行う。一時的なテストの置き場所は「コミットしないファイルの置き場所」に従う
- テストを書かないときは、ツールの実行、静的解析・型検査、構造の検査（構文・参照先の実在）、`git diff` の確認で代え、結果を報告する
- Plan の各 Task に、テストの要否と理由を書く。不要なら、代わりの検証を検証手順にする
- レビューでは、追加・変更されたテストがこの基準に反していないか確かめる。守りの不足だけでなく、基準に反して足されたテスト（書きすぎ）も指摘する

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

- レビュー修正ループの `round` を「巡」、`seat` を「席」と訳さない。

  - 繰り返しの単位は「サイクル」、順番は「1 回目」「2 回目」、数は「サイクル数」「レビュー修正の回数」などと書く
  - レビューを担当するモデル・エージェントは「レビュアー」、その組み合わせは「レビュアーの構成」などと書く
  - 他のリポジトリの形式・記録に残る「巡」「席」は、引用するときだけ原文のまま書く

- 「実行器」のような、日本人の IT エンジニアが一般的に使わない直訳は避ける。文脈に応じて「ランナー」「実行ツール」「実行処理」などを使い、対象が明確な場合は具体的なツール名を使う。

## ファイルとドラフト

- `docs_draft/` はローカルの下書き置き場で、git では追跡しない。タスクで指定された場合だけ読む
- ユーザから作成を依頼された文書は、`docs_draft/` に Markdown で作成する
- リポジトリに残す文書は `docs/` に置く。設計仕様は `docs/superpowers/specs/`、実装計画は `docs/superpowers/plans/` に置く

### Spec・Plan の保存と公開

- どのリポジトリの作業でも、Spec・Plan の正本は `usaturn/create-reso-world` の `docs/superpowers/` に保存してコミットする。ResoLoop や無関係なリポジトリの作業でも、対象リポジトリには置かず、二重管理もしない。運用の要点は `docs/superpowers/README.md` にある
- スキル superpowers で作成する Spec・Plan は、作業時に必ず作成している worktree のブランチにコミットし、ユーザ確認用で main の `docs_draft/superpowers/specs/` `docs_draft/superpowers/plan/` にコピーする
- 作業先は 3 つを区別する。`PARENT_ROOT` はユーザが確認用ファイルを読む create-reso-world の親 checkout（`uv run --no-project python .agents/scripts/agent_tmp.py root` が出力するディレクトリ）、`DOC_ROOT` は正本をコミットする create-reso-world の checkout または worktree、`CODE_ROOT` はユーザの依頼または確認済みの引き継ぎで明示された、コード対象の checkout の絶対パスである。コード対象の cwd の `git rev-parse --show-toplevel` を、`DOC_ROOT` や `PARENT_ROOT` とみなさない
- 文書を create-reso-world に集めることは、他のリポジトリのコード変更・clone・push・PR 作成の許可ではない。対象 checkout の `AGENTS.md` 等も守る
- 正式な Spec・Plan は、承認前でも `draft` のまま `DOC_ROOT` の作業ブランチにコミットする。状態は `draft`・`approved`・`completed`・`superseded`・`cancelled` で書き、コミットしただけで `approved` にしない。完了した文書も削除しない
- 同じテーマのレビュー修正は既存の文書を更新し、過去の版は Git の履歴に残す。更新前には対象リポジトリ・Issue/PR・テーマ・正本のパスで現行の Spec/Plan を探し、複数の候補があって確定できないときは進めずに確認する。回ごとの新規文書（roundN）は既定で作らない。承認は内容のコミット SHA に結び付け、承認後の状態・記録追記だけの変更は再承認を求めない。実質的な設計・計画の変更は再承認を必要とする（記録した実行許可がその変更を明示的に含む場合を除く）。例外で進める場合は許可された変更内容を記録し、一般的な継続指示だけで変更の承認を推測しない
- ユーザに Spec・Plan の確認を依頼する前に、コミット済みの版を `scripts/superpowers-review-copy.sh` で `PARENT_ROOT` の `tmp/superpowers-review/` へコピーし、コピー先・文書のコミット SHA・正本のパスを示す。ファイル名は内容が分かる短い名前に `-spec.md` か `-plan.md` を付け、関連する Issue・PR があれば `<repo>-pr<N>-` のように番号を含める。番号を発明しない。コピーは既存の entry を決して差し替えない。正本が変わったら `...-r2-spec.md` のような別名で新しいコピーを公開し、旧コピーとユーザの注記は残す
- issue-to-pr スキルで進める作業は、ユーザに確認を求めないので確認用のコピーを作らない。Spec・Plan は `draft` のままコミットし、その作業の PR（他のリポジトリの作業では文書専用の PR）で公開する。ユーザの実行指示は実行許可として記録し、内容の承認（`approved`）にしない
- 公開: create-reso-world 自身の変更に伴う文書は、その作業の PR に含める。他のリポジトリの変更に伴う文書は、create-reso-world の文書用ブランチから、テーマごとに 1 つの文書専用 PR で公開する。コミット・push・PR 作成・マージは別の段階であり、ユーザまたは使っているワークフローの明示指示があるときだけ行う。ローカルのコミットだけのときは、報告と handoff に「公開未実施」と書く

### コミットしないファイルの置き場所

コミットしないファイルは、用途ごとに次の場所へ置く。表の相対パスは `PARENT_ROOT` が基準である。

| 用途 | 置き場所 |
| --- | --- |
| セッション後も参照し得るスクラッチ・検証ログ・下書き | `tmp/agents/<topic>.XXXXXX/`（`uv run --no-project python .agents/scripts/agent_tmp.py mkdir <topic>` で作る。`<topic>` は `issue-123` のような英小文字の短い名前） |
| superpowers の subagent-driven-development・executing-plans の作業領域（ledger・Task の brief・報告・review package） | `tmp/agents/<topic>.XXXXXX/sdd/<plan>/`（使い方は「SDD 実行運用」） |
| エージェント間の引き継ぎ | `tmp/docs_draft/claude_handoffs/`（agent-handoff スキル） |
| Spec・Plan の確認用コピー | `tmp/superpowers-review/`（`scripts/superpowers-review-copy.sh`）と、`docs_draft/superpowers/specs/`・`docs_draft/superpowers/plan/`（「Spec・Plan の保存と公開」のとおり両方に置く）。正式な Spec・Plan は今までどおり `DOC_ROOT` の `docs/superpowers/` にコミットする |
| ユーザから作成を依頼された文書 | `docs_draft/` |
| PR レビュー結果 | `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<branch>/`（全リポジトリ共通。PR base 側の owner/repo を小文字にし、保存先は `.agents/scripts/review_target.py` が決める。旧配置は移さず、読む側が明示パスで指定したときだけ使う） |
| 使い捨ての git worktree とその作業領域 | `/tmp` の一意のディレクトリ（pr-review の `/tmp/pr-review-*`、review-fix-planning の `mktemp -d`） |
| 消えても困らない中間出力 | `/tmp` に `mktemp -d` で作るディレクトリ、Claude Code の scratchpad |

- worktree（`.worktrees/<topic>`、`external/resoloop-meshy/.worktrees/<topic>`、レビュー用の使い捨ての worktree）の中に、コミットしないファイルを作らない。worktree を消すと失われ、repo-cleanup-after-merge が判定できずに止まる。テストやビルドが作る、再生成できるキャッシュ（`.venv/`・`__pycache__/` など）は除く
- `/tmp` 直下に固定名のファイルを作らない。`/tmp` を使うときも `mktemp -d` で一意のディレクトリを作り、その中に置く
- `tmp/agents/` のセッションディレクトリは、作ったスキル（スキルを使わないときは作ったエージェント）自身が不要と確かめた時点で消す。消せなかったものは最終報告に完全パスを書く
- `tmp/agents/` 以外の `tmp/`（人が置いたファイルを含む）は、表の用途で書き足すほかは触らない
- ワールドのプロジェクトの中に置く作業物（プロジェクトの `tmp/` のバックアップなど）は、今までどおりプロジェクトの `AGENTS.md` に従い、この表の対象にしない

## 作業の安全

### 編集前の確認

- 編集の前に `git status --porcelain` と `git worktree list` を確認する
- create-reso-world で追跡するファイルは、親の checkout（`PARENT_ROOT`。`origin/main` の detached HEAD）では編集しない。最新の `origin/main` から作った `.worktrees/<topic>` の worktree で編集する
- 他のリポジトリの追跡ファイルは、「リポジトリ境界」の作業ルートと手順書（`docs/resoloop-fork-workflow.md`・`docs/resoloop-meshy-workflow.md`）に従って編集する
- 次は追跡するファイルの編集に当たらないので、今までどおり親の checkout で行う
  - ワールドのプロジェクト（`worlds/<name>/` と従来位置の 4 つ。git の追跡対象外）の作業。「プロジェクト運用」のとおり、プロジェクトのディレクトリを cwd にし、branch・worktree を求めない
  - 「コミットしないファイルの置き場所」の表にある場所への書き込み

### 削除

rm / rmdir の削除対象にシェル変数を使う場合は、各変数に `${VAR:?}` 形式の空値ガードを付け、パス全体を引用する（例: `rm -rf -- "${T:?}/${n:?}"`）。サブエージェントが実行するコマンドにも適用する。

### 一時 HOME

永続シェルで `export HOME=...` しない。一時 HOME が要る検証は `env HOME="$tmpdir" ...` のワンショットに限る。HOME を差し替えたままにすると、後続の `gh`・`git` が別の HOME を見て未認証になる。

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
| 採用済み `external-tools.toml` の通常ツール | 台帳の `path`（常設親 `PARENT_ROOT` 基準） | 共通 resolver で repository・common-dir・remote と実送信先を照合する。レビューと cleanup は常設 checkout、実装と review-fix は同 common-dir の名前付き branch の明示 linked worktree。手順は `docs/external-tools-workflow.md`。不在・不一致・候補複数では停止し、別 clone や親へ切り替えない |
| それ以外（未登録 repo） | ユーザの依頼または確認済みの引き継ぎで明示された checkout の絶対パス（`CODE_ROOT`） | その checkout 自身のルートであり、remote のうち 1 つだけが対象の owner/repo と一致すること。この経路を持つのは `pr-review`（レビュー）と `review-fix-planning`（修正計画と、その PR の承認済み実装修正）で、既存の承認済み PR 修正経路は維持する。一般的な外部コード実装は非対応であり、実行経路が未定義の外部実装の handoff は blocked（not ready）として記録する。remote が無いローカル専用の checkout との PR 連携は非対応のため扱えない（明示指示があっても resolver は remote 0 件で停止する）。明示が無い・一致しない・候補が複数ある場合は推測せず停止する。checkout の探索・clone はしない |

通常ツールの一覧はスキルへ転記せず台帳で管理し、検証コマンド・編集範囲・実行条件は対象 repo の `AGENTS.md` と `README.md` を読む。運用台帳は検証済み常設親の detached HEAD の blob（ローカル `origin/main` の祖先）だけから読む。候補の parse・feature branch・親の未コミット変更を採用にしない。台帳の無い旧親は既存経路だけを保持し、壊れた台帳は空として扱わない。

登録は「この機構が扱える対象」を定義するだけであり、repo 作成・clone・実装・push・PR・マージ・release・実機操作の許可ではない。各依頼・workflow で別に確認する。通常ツールは `managed-tool-v1`（手動マージ）とし、既存 parent / fork のマージ経路へ追加しない。未登録 repo の明示 `CODE_ROOT` による PR review-fix の例外は、新規実装・任意 setup/release への許可に広げない。

## push の前の秘密情報の検査

「リポジトリ境界」のリポジトリへ commit を push する前に、まだ push していない commit を Gitleaks で検査し、検査した commit をそのまま push する。

- 検査は `bash scripts/scan-before-push.sh [-C <checkout>] [--base <remote>/<branch>]`。base の既定は `origin/main` で、PR の base が別ならそれを渡す。成功すると、検査した commit の SHA だけを標準出力に出す
- push は `SHA="$(bash scripts/scan-before-push.sh -C <checkout>)" && [ -n "$SHA" ] && git -C <checkout> push <remote> "${SHA:?}:refs/heads/<branch>"` の形にする（zsh は `$SHA:r` を修飾子として展開するので、`${SHA:?}` と波括弧で書く）。SHA が空だと refspec が branch の削除になるので、呼び出しを分けるときも `:?` を外さない。検査の後に変わった HEAD を push しない
- 検出や失敗で止まったら push しない。誤検出でも `.gitleaksignore`、inline の `gitleaks:allow`、作業ツリーの `.gitleaks.toml` で回避しない（検査はどれも使わない）
- 検出が次の 3 つをすべて満たすときは、その行を足した commit を直し、検証と検査をやり直して続けてよい
  - その commit は、この作業で作り、まだどこにも push していない（`git branch -r --contains <commit>` が空）
  - 値が秘密情報でないと確かめられる: この作業で書いたテスト用の偽の値・例か、名前から作った識別子であり、環境変数・認証情報のファイル・コマンドやツールの出力・利用者や Issue の文から写した値ではない
  - その commit は、レビューを保存した commit（review-fix-planning の自己レビューが `<model>-commit-<SHA>.md` に記録した commit）でも、その祖先でもない。書き換えると、保存したレビューの commit が PR の履歴から外れ、次のサイクルの祖先の確認で止まる
- 直すときは、その行を足した commit そのものを書き換える。上に commit を足しても、検査は範囲のすべての commit を見るので通らない。テスト用の偽の値は実行時に組み立てる（`"_".join(...)` で連結する、`tests/scripts/test-scan-before-push.bash` のトークンのように `sha256sum` から作る）。文書では値を省くか `<16 進 8 桁>` のように置き換え、分割・符号化した形でも書き残さない。報告に、検出した rule・file・commit と直し方を書く（値は書かない）
- それ以外の検出は直さず、直した後も検出が残るときはそれ以上直さずに、利用者に報告する。push 済みの commit は書き換えない（force push しない）。除外が必要なら、base の `.gitleaks.toml` を先に変える
- gitleaks が無い・版が違うときも止まる。`bash .devcontainer/install_gitleaks.bash` で導入する
- 対象にしない: 公開済みの commit だけを送る push（`scripts/resoloop-fork.sh sync`、claim ref の作成、ブランチの削除）

## GitHub Actions

- usaturn/create-reso-world は公開リポジトリだが、GitHub Actions は無効（`enabled=false`）のままにし、CI の確認は不要。同じ検査をローカルで実行するので、有効にしても時間がかかるだけである。プライベートで開発したい場合もあるので、CI は基本的に無効にする。`.github/workflows/ci.yml` は残してあるが動かない
- Actions が有効な公開リポジトリ（usaturn/resoloop など）の作業では、CI を確認する
- 登録済み通常ツールの CI は採用済み台帳の `ci` と実状態を controller が読取照合する。`disabled` は Actions permissions の `enabled=false`、`required` は実際の PR checks の成功を確認する。不一致・不在・取得失敗は停止する。registry/check のローカル成功をネットワーク確認済みと表示せず、未知 repo の CI を免除しない。詳細は `docs/external-tools-workflow.md`。
- テストを作っても CI（GitHub Actions のワークフローなど）は作らない。テストはローカルで実行し、結果を報告する。新しいリポジトリを作ったら、その場で Actions を無効にする（`gh api -X PUT repos/<owner>/<repo>/actions/permissions -F enabled=false`）

## ResoLoop の版管理

- ResoLoop は常に NuGet の最新の公開版を使い、版を固定しない。postCreate が `.devcontainer/install_resoloop.bash` で最新を導入する。rebuild せずに最新へ上げるときも同じスクリプトを実行する。使っている版は `resoloop --version` で確かめる
- 上流に未取り込みの修正を一時的に使うときは、`scripts/resoloop-fork.sh install <fork のブランチかコミット>` で fork のビルドを導入する。次の rebuild か `bash .devcontainer/install_resoloop.bash` で最新の公開版に戻る。fork の取得・ビルド・導入の手順は `docs/resoloop-fork-workflow.md` に従う
- 版が上がると同梱スキル（`resonite-*`）にも更新が出る。postCreate と `scripts/check-layout.sh` は更新の有無を表示するだけなので、「プロジェクト運用」のとおり差分を確認してから `--update` する

## エージェント運用

- 長時間コマンド、検証、バックグラウンド処理、サブエージェントの完了・生存・進捗を監視するときは monitoring-long-tasks スキルを使う。監視手順はスキルが正本であり、各ランタイムでどのツールを使うかはリポジトリルートの `.agents/monitoring-runtimes.md` を参照する（プロジェクトを cwd にしている場合も、パスはリポジトリルート基準）
- 別のエージェント（モデル）を非対話で起動して結果を回収するときは、リポジトリのルートを cwd にして agent-runner（`uv run --project "$PARENT_ROOT" --locked python -m tools.agent_runner`）を使う。仕様は `tools/agent_runner/interfaces.rst`、待ち方と停止の確かめ方は `.agents/monitoring-runtimes.md` の「agent-runner の同期実行と停止確認」にある。runner の担当（`AGENT_RUNNER_DEPTH=1`）の中から runner を起動しない（runner が `nested_invocation` で拒否する）。#150・#151 で adapter が入るまでは、どの runtime も `unsupported` を返すので、それまでは各スキルの従来の起動方法を使う
- 本物の担当（モデル）を起動する確認は費用がかかるので、Issue・Plan に書いた回数と対象に限る。テストは偽の adapter・偽の CLI だけを使う

### SDD 実行運用

この節では controller（司令塔）・ledger（進捗記録）・brief（依頼書）という用語を使う。

- Plan に「実行予算」の節を設け、Issue 全体の能動時間の予算、phase の目安、worker の期限・予約枠・無進捗の打ち切り、失敗の種類ごとの再試行の上限、checkpoint の時点、縮小・切り出し・方法変更の候補を書く。適用範囲、時間の数え方、ledger の置き場所と片付け、checkpoint での判断は `.agents/execution-budget.md` に従う
- superpowers の subagent-driven-development・executing-plans の作業領域は、スキルの言う `.superpowers/sdd/<plan>/` ではなく、実行予算の ledger と同じセッションディレクトリの `sdd/<plan>/`（`tmp/agents/<topic>.XXXXXX/sdd/<plan>/`。`<plan>` は Plan のファイル名から `.md` を除いた名前）にし、最初に `mkdir -p` で作る。`sdd-workspace`・`task-start`・`task-done` は作業領域を worktree に作るので使わない。`task-brief` は 3 つ目、`review-package` は 4 つ目の引数に、作業領域の下のスクリプトの既定の名前（`task-<N>-brief.md`・`review-<base7>..<head7>.diff`）を渡す。BASE は Task の開始時に `git rev-parse HEAD` で控える。ledger（`progress.md`）の完了の行は手で書き、SDD は Task のレビューが clean か、上限で残りを parked にしたときにスキルの書式で、executing-plans は Task のテストが通ったときだけ `task-done` と同じ書式で書く
- 実装サブエージェントはテスト、lint、回帰を同期実行し、完了を待ってからターンを終える。monitoring-long-tasks の監視ルールは controller が長時間タスクを監視するためのものであり、実装サブエージェント内部の待ちをバックグラウンド化する根拠にしない
- controller は monitoring-long-tasks の終了条件が成立するまでターンを保持し、stall ポーリングを担当する。完了通知は harness の終了コード付きプロセス終了通知を指し、成果物やサブエージェントの結果通知とは区別する。これは対象停止の判定材料であり、対象の実行中にターンを終える根拠にしない。ただし monitoring-long-tasks の「事前宣言した打ち切り」の対象に限り、宣言した条件で止めてよく、停止確認不能のときは対象・停止状態・残存パスを報告してターンを終えてよい
- 各担当は着手から成果提出までの所要時間と主要 Task 別の内訳を作業報告に記録する

以下の追加規則は Claude Code・pi の subagent-driven-development・executing-plans で新しく作成する Plan に適用する。既存の Spec・Plan には遡及適用せず、review-fix-planning の指摘の採否基準も変更しない。

- Plan に「contingency（代替策）」節を設け、失敗・行き詰まり時の代替策と切り替える条件を記す。最初の RED で実出力・API の前提が異なると判明した場合は、仕様の意味を保つ最小修正を ledger に残して継続する。意味が変わる場合は利用者の裁定を待つ。実行予算の縮小・切り出し・方法変更と整合させ、既存の停止条件・安全境界を維持する
- Plan に「受け入れ基準」節を設け、動作環境、実入力、防御範囲の 3 点を記す。実入力は対象に応じて複数行・非 ASCII 等の実際の形を示し、防御範囲は対象条件と対象外の反例・設定を明記する。テストの要否は「テストの採用基準」に従い、実行して確かめられる S の条件は実装前にテスト化する。テストが不要な場合は代わりの検証を書く
- controller は同じ受け入れ基準の本文を実装担当・タスクレビュー担当双方の brief に写す。レビュー担当にだけ全 Plan・Spec を追加資料として渡してはならない。指定文言は文字列の一致だけでなく実入力・実出力との意味を照合し、指摘された文言自体の妥当性もレビュー対象にする。意味を保つ表記の差は Plan の条件に照らして判断する
- 範囲外または Plan と矛盾するレビュー指摘は、controller が修正前に採用・不採用・保留を裁定し、理由とともに ledger に記録する。指摘に合わせてレビュー後に採否基準を変更しない
- 採用したレビュー指摘は原文のまま修正担当へ渡し、controller は要約・言い換え・修正手段の指定を書き足さない。裁定理由・採否は原文と分けて記してよいが、その補足にも修正手段の指定を加えない
- レビュアーを複数置く場合は、指摘箇所ごとではなく、入力→保存→検証の一連の流れを通して追う担当に分ける。最終全体レビューでの追加実行は、具体的な不具合の疑いに対する絞ったテスト・最小再現に限る。pi のレビュー子は読み取り専用を保ち、必要なテスト・再現は controller が同期実行して結果をレビュー担当に返す
- 新しい Plan は、受け入れ基準・防御範囲・動作環境の 3 点を明示して実行前にユーザへ提示し、確認を得る。一般的な連続実行指示では提示・確認を省略しない。issue-to-pr で着手した run に限り、同スキルに従って省略する。この場合も「Spec・Plan の保存と公開」に従って draft のままコミットし、実行許可と内容の承認を区別する

## 環境

Windows 11 の WSL2（Gentoo Linux）上で Docker を動かし、Ubuntu 26.04 LTS の Dev Container を使用する。

## 最新ドキュメントの取得

- ライブラリ、フレームワーク、SDK、API、CLI、クラウドサービスの仕様は、find-docs スキルの手順で Context7 CLI（`ctx7`）を使って確認する。npx・Context7 の MCP Server・Pi の Context7 拡張に切り替えない
- 問い合わせは 1 件につき 3 回までとする
