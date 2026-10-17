# Issue #123: コミットしないファイルの置き場所（`agent_tmp.py`）・作業の安全規則・日本語表現の規則を取り入れる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/123（#124 を統合済み）
- 検証した基準 HEAD: 移植先 `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`）、移植元 usaturn/agent-workspace `d3f4151388d47a0dd80092de434ac786a204a783`（Issue で照合した版。2026-10-17 時点の `main` は `49c2e93`）
- 状態: draft（文書の内容に対する利用者の明示承認は無い）
- 関連 Plan: `docs/superpowers/plans/2026-10-17-create-reso-world-issue123-agent-tmp-safety-rules.md`
- 実行許可: 2026-10-17（JST）、利用者が「#123 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ」と指示した。推奨案での実装、隔離 worktree、commit、push、create-reso-world への PR の作成まで許可されている。マージは利用者が行う。下の判断は確認を取らずに決めたエージェントの判断である
- 追加の指示: 2026-10-17（JST）、PR #130 の作成後に利用者が「持ち越し候補について再調査し、本当に重要なことであれば Issue を作成せよ。採用しない場合は PR に採用しない理由を投稿すること」と指示した。D-5・D-9・D-12 と D-1 の表の確認用コピーの行は、この指示による再調査で改めた

## 意図

エージェントが作るスクラッチ・検証ログ・下書きが、`/tmp` 直下の固定名のファイルや worktree の中の未追跡ファイルとして残らないよう、用途ごとの置き場所を `AGENTS.md` に決め、セッションのディレクトリを作る `agent_tmp.py` を usaturn/agent-workspace から取り入れる。同じ PR で、削除・一時 HOME・編集前の確認の安全規則（旧 #124）と、日本語表現の規則 2 件（旧 #124）を足す。編集前の確認（追跡するファイルは worktree で編集する）と置き場所の表は、どちらも作業場所の扱いを決めるので、食い違わないよう 1 つの PR で書く。

## 確認した事実（2026-10-17）

- 移植元の `.agents/scripts/agent_tmp.py`（88 行）は標準ライブラリだけを使う。`root` は、スクリプト自身の置き場所から `git rev-parse --git-common-dir` で親の checkout（common dir が `.git` という名前のときの、その親）を求める。`mkdir <topic>` は topic を `[a-z0-9][a-z0-9._-]{0,63}` で検査し、`tmp/agents` の実体（symlink の先）が親の checkout の中にあって git に無視されることを確かめてから、`tempfile.mkdtemp` で `tmp/agents/<topic>.XXXXXX` を作る
- 移植元のテスト（`.agents/scripts/tests/test_agent_tmp.py`、167 行）は、submodule の検査にだけ `tools.test_support.repos.create_parent_repo`（agent-workspace の `public` submodule の構成）を使う。CLI のテスト 2 件は、実際の checkout の上でスクリプトを実行する
- 移植先の `.gitignore` は `tmp/`・`/.worktrees/`・`/external/`・`/worlds/`・`/reviews/`・`docs_draft/` を無視する。親の checkout の `tmp/` には、人が置いたファイルと、`tmp/superpowers-review/`・`tmp/docs_draft/claude_handoffs/` の既存の entry がある
- `scripts/superpowers_context.py` は `PARENT_ROOT` に、git dir と common dir が一致する（linked worktree ではない）create-reso-world の checkout を求める。`scripts/resoloop-meshy.sh` も、親の checkout を「スクリプトを含む checkout の common dir の親」として求める。`agent_tmp.py root` の結果はこれらと同じディレクトリになる
- 既存のスキルの一時ファイル: `pr-review` は `/tmp/pr-review-<PR>-<ランダム値>/`、`review-fix-planning` は `mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX"` を使い、どちらも一意のディレクトリの中に置く。`agent-handoff` は `tmp/docs_draft/claude_handoffs/`、`pr-review` のレビュー結果は `reviews/#<PR>-<branch>/`（resoloop の PR は `external/resoloop/reviews/`）。`repo-cleanup-after-merge` の手順 6 の例だけが `/tmp/gate-a.out`・`/tmp/gate-a.err` という固定名を使う
- `external/resoloop`（fork）の作業は、`docs/resoloop-fork-workflow.md` の手順で checkout 自身のブランチを切り替えて行い、worktree を使わない。`external/resoloop-meshy` の実装は、その checkout の `.worktrees/<topic>` で行う
- `CLAUDE.md` は 1 行目の `@AGENTS.md` で `AGENTS.md` を読み込み、「一時ファイル・ディレクトリの削除」の節（旧 #124 の 1 と同じ規則）を持つ。`.pi/APPEND_SYSTEM.md` に同じ規則は無い
- 移植先の追跡ファイル（`docs/` の過去の記録を除く）に、レビュー修正ループの「巡」「席」と「実行器」の使用は無い
- `tests/scripts/test-docs.bash --refs`（`test-instructions.bash` が `AGENTS.md`・`CLAUDE.md` に使う）は、backtick のパスのうち `<>` などのプレースホルダを含まないものの実在を確かめる
- #115 の Spec（`723bc6a`、draft）の D-5 は、ledger の置き場所を `PARENT_ROOT` の `tmp/agents/<topic>.XXXXXX/` とし、`agent_tmp.py` は持ち込まず `mkdir -p` と `mktemp -d` の 2 行で作る、としている。#115 のブランチは `pyproject.toml` の `testpaths` に `.agents/scripts` を足している

## 判断

### D-1 置き場所の表と規則

`AGENTS.md` の「ファイルとドラフト」に「コミットしないファイルの置き場所」の小節を足す。表の相対パスは `PARENT_ROOT` を基準にする。

| 用途 | 置き場所 |
| --- | --- |
| セッション後も参照し得るスクラッチ・検証ログ・下書き | `tmp/agents/<topic>.XXXXXX/`（`agent_tmp.py mkdir <topic>` で作る） |
| エージェント間の引き継ぎ | `tmp/docs_draft/claude_handoffs/`（agent-handoff） |
| Spec・Plan の確認用コピー | `tmp/superpowers-review/`（`scripts/superpowers-review-copy.sh`）と、`docs_draft/superpowers/specs/`・`docs_draft/superpowers/plan/`（「Spec・Plan の保存と公開」のとおり両方に置く）。正式な Spec・Plan は今までどおり `DOC_ROOT` の `docs/superpowers/` にコミットする |
| ユーザから作成を依頼された文書 | `docs_draft/` |
| PR レビュー結果 | `reviews/#<PR>-<branch>/`（保存先は pr-review のヘルパーが決める。resoloop の PR は `external/resoloop/reviews/`、その他のリポジトリは `CODE_ROOT` の `reviews/`） |
| 使い捨ての git worktree とその作業領域 | `/tmp` の一意のディレクトリ（pr-review の `/tmp/pr-review-*`、review-fix-planning の `mktemp -d`） |
| 消えても困らない中間出力 | `/tmp` の `mktemp -d` のディレクトリ、Claude Code の scratchpad |

規則（Issue の範囲 1 のとおり）:

- worktree（`.worktrees/<topic>`、`external/resoloop-meshy/.worktrees/<topic>`、レビュー用の使い捨ての worktree）の中に、コミットしないファイルを作らない。worktree を消すと失われ、`repo-cleanup-after-merge` が判定できずに止まるため。テストやビルドが作る、再生成できるキャッシュ（`.venv/`・`__pycache__/` など）は除く。`repo-cleanup-after-merge` が削除してよいと判定する種類で、`uv run` を worktree で使えなくしないため
- `/tmp` 直下に固定名のファイルを作らない。`/tmp` を使うときも `mktemp -d` で一意のディレクトリを作り、その中に置く
- `tmp/agents/` のセッションディレクトリは、作ったスキル（スキルを使わないときは作ったエージェント）自身が不要と確かめた時点で消す。消せなかったものは最終報告に完全パスを書く
- `tmp/agents/` 以外の `tmp/`（人が置いたファイルを含む）は、表の用途で書き足すほかは触らない
- ワールドのプロジェクトの中に置く作業物（プロジェクトの `tmp/` のバックアップなど）は、今までどおりプロジェクトの `AGENTS.md` に従い、この表の対象にしない。ワールドの作業の流れは変えない（Issue の「対象にしない」）

### D-2 `agent_tmp.py` は判定のロジックを変えずに移植する

`.agents/scripts/agent_tmp.py` に置く。変えるのは次だけにする。

- docstring・コメント: 「Issue #333」を `usaturn/agent-workspace#333` にし、`create-reso-world#123` で移植したことを書く。移植先の Issue 番号と取り違えないため。`public/` submodule・リリース worktree の例を、移植先の例（`.worktrees/<topic>` の worktree、`external/resoloop-meshy`・ワールドを cwd にした呼び出し）に置き換える
- 識別子（`resolve_main_root` など）・エラーメッセージ・CLI の引数は変えない。submodule の checkout（common dir が `.git` でない）を拒否する検査も残す。移植先に submodule は無いが、親を決められないときに推測で書き込まないための安全条件であり、外す理由が無い

実行のコマンドは `uv run --no-project python .agents/scripts/agent_tmp.py root|mkdir <topic>` とする（パスは `AGENTS.md` の冒頭のとおりリポジトリのルート基準）。`--no-project` にするのは、ワールドなど別の `pyproject.toml` を持つ cwd から呼んでも、その project を同期しないため。

### D-3 `root` の結果は `PARENT_ROOT` と同じものとして扱う

「Spec・Plan の保存と公開」の `PARENT_ROOT` の定義に、`agent_tmp.py root` が出力するディレクトリであることを書き足す。create-reso-world の checkout は submodule を持たないので、「common dir の親」は `superpowers_context.py` が求める main checkout と一致する（確認した事実）。`PARENT_ROOT` を受け取る `superpowers_context.py`・`superpowers-review-copy.sh` の検証（origin の照合など）は今までどおり行われ、`agent_tmp.py` 側には足さない。

### D-4 テストは create-reso-world の形の fixture で書き直す

`.agents/scripts/tests/test_agent_tmp.py` に置く。`AGENTS.md` の「テストの採用基準」の「コードを実行してロジック・分岐・安全条件・入出力の解析を確かめる場合」に当たる。

- 判定関数の単体テスト（main・サブディレクトリ・linked worktree からの解決、非 git の拒否、一意のディレクトリ、版の形の topic、不正な topic、無視されない `tmp`、外を指す symlink、追跡するディレクトリを指す symlink）は移植元のまま持ち込む
- submodule の拒否のテストは、`create_parent_repo` の代わりに、ローカルの repository を `git submodule add` した最小の親をテストの中で作る
- CLI のテストは、実際の checkout ではなく create-reso-world の形の fixture で実行する。fixture は、ローカルの bare の origin、その clone の親の checkout（`origin/main` の detached HEAD、ローカルの `main` 無し）、実際の `.gitignore` の写し、`.agents/scripts/agent_tmp.py` の写し（コミット済み）、`.worktrees/<topic>` の worktree、別の repository として clone した `external/resoloop-meshy` とその `.worktrees/<topic>`、自分の `.git` を持つ `worlds/<name>` で作る
  - `root`: 親の checkout の写しと worktree の写しのそれぞれを、親・worktree・`external/resoloop-meshy`・その worktree・ワールド・ワールドのサブディレクトリ・リポジトリの外の各 cwd から実行し、どれも親の checkout を出力することを確かめる
  - `mkdir`: worktree の写しを `external/resoloop-meshy` の worktree から実行し、親の checkout の `tmp/agents/<topic>.XXXXXX` が 0700 で作られること、親と worktree の `git status --porcelain` が空のままであることを確かめる
  - 不正な topic: 終了コード 1、stdout が空、stderr が `agent_tmp: ` で始まり、`tmp/agents` を作らないことを確かめる
- `.gitignore` は実際のファイルを写す。実際の無視の規則の上で `mkdir` が動くことを確かめるためで、値の写しのテストではない（`.gitignore` から `tmp/` の無視が外れると、`mkdir` のテストが失敗して気付ける）

### D-5 テストの範囲

- `pyproject.toml` の `testpaths` に `.agents/scripts` を足す。#115 のブランチと同じ行の同じ変更にし、後からマージする側で衝突しないようにする
- `README.md` の「テスト」の節と `.github/workflows/ci.yml` の `skill-tests` のコマンドにも `.agents/scripts` を足す（CI は止めているが記載をそろえる。#115 の Spec の D-4 と同じ）
- `.devcontainer/README.md` の「テストの実行」のコマンドにも `.agents/scripts` を足す。この節は「CI も同じコマンドを実行する」と書いており、ci.yml を変えると食い違うため。#114 のブランチが `.devcontainer/README.md` で変えるのはツールの表だけで、この行とは重ならない（当初は #114 との衝突を理由に変えないとしたが、再調査で理由が成り立たないと分かった）

### D-6 作業の安全規則

`AGENTS.md` に「作業の安全」の節を新しく作り、「ファイルとドラフト」の次（「プロジェクト運用」の前）に置く。

- **編集前の確認:** `git status --porcelain` と `git worktree list` を確認する。create-reso-world で追跡するファイルは、親の checkout（`origin/main` の detached HEAD）では編集せず、最新の `origin/main` から作った `.worktrees/<topic>` の worktree で編集する。他のリポジトリの追跡ファイルは「リポジトリ境界」の作業ルートと手順書（`docs/resoloop-fork-workflow.md`・`docs/resoloop-meshy-workflow.md`）に従う。`external/resoloop` は fork の手順のとおり checkout のブランチで作業するので、worktree の規則をそちらに広げない
- 次は「追跡するファイルの編集」に当たらず、今までどおり親の checkout で行う: ワールドのプロジェクト（`worlds/<name>/` と従来位置の 4 つ。git の追跡対象外）の作業、「コミットしないファイルの置き場所」の表にある場所への書き込み。Issue の「Spec で決めること」の書き分けをこの箇条で示す。「プロジェクト運用」の「ワールドの作業は、そのプロジェクトのディレクトリを cwd にして起動する」「branch・commit・PR は要求しない」と食い違わない
- **削除:** `rm`・`rmdir` の対象にシェル変数を使うときは、各変数に `${VAR:?}` の空値ガードを付け、パス全体を引用する（例: `rm -rf -- "${T:?}/${n:?}"`）。サブエージェントが実行するコマンドにも適用する。既存のスクリプトの一括の書き直しはしない（Issue の「対象にしない」）
- **一時 HOME:** 永続シェルで `export HOME=...` しない。一時 HOME が要る検証は `env HOME="$tmpdir" ...` のワンショットに限る。後続の `gh`・`git` が別の HOME を見て未認証になるため（`pr-review` の手順 3 と同じ理由）。テストのスクリプトの中で HOME を差し替えるのは、そのプロセスの中だけなので対象にしない

### D-7 `CLAUDE.md` の重複を消す

`CLAUDE.md` の「一時ファイル・ディレクトリの削除」の節を消す。`CLAUDE.md` は `@AGENTS.md` で同じ規則を読み込むので、Claude Code への効果は変わらない。規則を `AGENTS.md` の 1 か所で管理し、Codex・pi・Cursor・Devin にも同じ規則を適用する。

### D-8 日本語表現

「日本語表現」の節に 2 件を足す。

- レビュー修正ループの `round` を「巡」、`seat` を「席」と訳さない。繰り返しの単位は「サイクル」、順番は「1 回目」「2 回目」、数は「サイクル数」「レビュー修正の回数」、担当するモデル・エージェントは「レビュアー」、その組み合わせは「レビュアーの構成」などと書く。移植先にはこれらの語を使う形式・テストが無いので、移植元の「既存の形式・テストに残る語」の箇条は、「外部のリポジトリの形式・記録を引用するときだけ原文のまま書く」にする
- 「実行器」のような、日本人の IT エンジニアが一般的に使わない直訳を避ける。文脈に応じて「ランナー」「実行ツール」「実行処理」などを使い、対象が明確なら具体的なツール名を使う

### D-9 既存のスキルの一時ファイルは移さない

- `pr-review`・`review-fix-planning` は、すでに表の「使い捨ての git worktree とその作業領域」の置き方（`/tmp` の一意のディレクトリ）に当たるので、移さない。`agent-handoff`・`superpowers-review-copy.sh`・`pr-review` の保存先も表のとおりで変えない
- `repo-cleanup-after-merge` の手順 6 の `/tmp/gate-a.out`・`/tmp/gate-a.err` は、D-1 の「固定名を作らない」に反する。直すのはスキルの手順の変更なので、この PR では変えず、#131 で扱う。判定の 2 つの出力を並行するセッションが上書きすると、照合していない残骸を消すおそれがある

### D-10 #115 との関係

- #115 の D-5 の置き場所（`PARENT_ROOT` の `tmp/agents/<topic>.XXXXXX/`）は、D-1 の表と `agent_tmp.py mkdir` が作る場所・名前の形と同じで、食い違いは無い。#115 が入口を `agent_tmp.py mkdir` に変えるかは、#115 の側で決める。この PR では #115 のファイルに触れない
- `testpaths` の変更は D-5 のとおり #115 と同じ行にする

### D-11 PR と Issue

PR の本文は `Closes #123` にする。受け入れ基準は、テストと文書の読み合わせで確かめられ、rebuild を要しない。

### D-12 superpowers の SDD の作業領域

superpowers の subagent-driven-development・executing-plans のスクリプトは、作業領域を worktree の中の `.superpowers/sdd/` に作り、場所を変える手段が無い。D-1 の「worktree の中にコミットしないファイルを作らない」と食い違い、repo-cleanup-after-merge は `.superpowers/` がある worktree を消さずに止まる（2026-10-17 の時点で親 checkout と 4 つの worktree に残っている）。扱いは #132 で決める。この PR の作業では、ledger を scratchpad に置いた

## 受け入れ基準との対応

| 受け入れ基準 | 確かめ方 |
| --- | --- |
| どこから呼んでも `agent_tmp.py root` が親の checkout を返す（親 checkout、`.worktrees/<topic>`、`external/resoloop-meshy` とその worktree、ワールド） | D-4 の fixture の `root` のテスト |
| `mkdir <topic>` が `tmp/agents/<topic>.XXXXXX` を作る。topic の形が不正なら何も作らずに止まる | D-4 の `mkdir`・不正な topic のテストと、移植元の単体テスト |
| 追跡するファイルの編集が worktree で行われる | D-6 の規則。この作業自体を `.worktrees/issue-123-agent-tmp-safety-rules` で行う |
| 新しく書く削除のコマンドに空値ガードが付く | D-6 の規則。この PR のテストの片付けは pytest の `tmp_path` を使い、シェルの `rm` を書かない |
| 2 の 3 の規則がワールドを cwd にした作業を止めない | D-6 の書き分けの箇条を「プロジェクト運用」と読み合わせる（Plan の Task 3） |

## 範囲外

- 既存の `tmp/` の中身の片付け、ワールドのプロジェクトでの作業の流れの変更、既存のスクリプトの `rm` の一括の書き直し（Issue の「対象にしない」）
- 静的 lint の自動修正、「検証前のルート確認」「環境側の検証」（Issue の「持ち込まないもの」）
- `repo-cleanup-after-merge` の固定名の修正（D-9。#131）
- superpowers の SDD の作業領域の扱い（D-12。#132）
- #115 のファイル（D-10）
