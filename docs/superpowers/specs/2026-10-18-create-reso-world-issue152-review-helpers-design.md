# Issue #152: レビューの記録・候補・対象の共通 helper を取り入れる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/152（親 #116、ボード `review-automation-board`、子のキー `review-helpers`）
- 検証した基準 HEAD: 移植先 `3e3c1a3aacdda66678ba37da651e62e483cf06e4`（`origin/main`。Issue の基準 `84f417f` の後に #141・#159 などが入った版）、移植元 usaturn/agent-workspace `a47b2065fddad76b7475752fd0088af0733de204`（`main`、2026-10-17T19:08Z）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue152-review-helpers.md`
- 関連 Spec: `docs/superpowers/specs/2026-10-18-create-reso-world-issue116-review-automation-board-design.md`（D-1〜D-24。とくに D-5・D-8・D-10）
- 実行許可: 2026-10-18（UTC）、利用者が `/issue-to-pr #152` を実行した。issue-to-pr の規定により、通常の設計判断は推奨案で決め、Spec・Plan・実装・検証・commit・push・PR の作成（`main` 向け、`Closes #152`）まで続けることが許可されている。マージは含まない。下の判断は、確認を取らずに決めたエージェントの判断であり、利用者の承認ではない
- 予約: `refs/heads/agent-claims/issue-152`（SHA `f95534a69e34a80fb57d0ccbc06d2c8106048a45`、セッション `ef4e9e26-0d8d-4e71-8e2f-69bbec33d715`）

#116 の冒頭の「着手するエージェントへの注意（利用者決定: 2026-10-18）」に従う。この子に関係するのは次のとおり。

- `tools/workspace`・`projects.toml` は入れない。移植元の `projects.toml`・submodule・一時 clone に依存する箇所は、`scripts/superpowers_context.py` と `AGENTS.md` の「リポジトリ境界」に置き換える
- 移植先の review-fix-planning の判断基準・三択の結論・停止理由・マージ権限を変えない。この子は helper だけを入れ、スキルは変えない（スキルへの接続は #153〜#156）

## 意図

usaturn/agent-workspace の、複数モデルの PR レビューの自動化（#116）で、pr-review・review-verify・review-fix-planning・pr-review-fix-loop が共通に使う 3 つの helper と、その形式の文書を先に入れる。後続の子（#153 `pr-review-v2`、#154 `review-verify`、#155 `review-fix-roles`、#156 `fix-loop`）は、この子が決めるレビューディレクトリの規則と JSON の形を使う。

- `review_records.py`: PR の状況コメントに載せる判断の記録（review-records v1/v2）の検査・照合・集約・描画・取り出し
- `review_findings.py`: レビューの候補一覧・確認済みの一覧・工程の記録（review-findings v1/v2）の検査と集計
- `review_target.py`: PR とレビューディレクトリ、Git 操作の対象の checkout を決める

## 確認した事実（2026-10-18）

- 移植元の 3 つの helper は標準ライブラリだけで書かれている。`review_findings.py` は同じディレクトリの `review_records.py` を `importlib` で読み、`review_target.py` は `agent_tmp.py` を読む。移植先の `agent_tmp.py` は同じ `resolve_main_root`・`AgentTmpError` を持つ
- 移植元の `review_records.py`・`review_findings.py` とそのテスト（411 件）を、移植先の Python 3.14.4・pytest でそのまま実行して全て通った（使い捨てのディレクトリで確認）
- 移植先の `pyproject.toml` は `requires-python = ">=3.12"`（`>=3.14` に上げるのは #149 の担当。#116 の D-7）。3 つの helper とテストのうち、3.12 の文法で読めないのは `review_target.py` の括弧の無い `except FileNotFoundError, NotADirectoryError:` の 1 か所だけ
- 移植元の `review_target.py` は、Git 操作の対象を「親の checkout か、登録済みの submodule の checkout。無ければ一時 clone」で決め、`clone` サブコマンドを持つ。旧配置として、親と submodule の `reviews/#<N>-*` を明示したパスでだけ読む。`--for-planning` は PR の owner を `usaturn` に限る（移植元 #483 の利用者決定）
- 移植先の `scripts/superpowers_context.py` の `resolve_context("review-workspace", ...)` は、create-reso-world を親の checkout、usaturn/resoloop・orange3134/resoloop を `external/resoloop`（origin が fork、upstream が上流）に固定し、それ以外は明示した `CODE_ROOT` の remote 1 件との一致で扱う。`CODE_ROOT` は main checkout に限る。返す `base_remote` は PR を取得する remote（上流の PR は `upstream`）
- 移植先の pr-review（#146、PR #160 で `main` に入った）は、保存先を checkout ごとの `reviews/<owner>/<repo>/#<PR>-<branch>/`（owner/repo は小文字）にし、PR head を `refs/pr-review/repos/<owner>/<repo>/<PR>` に固定する。旧形式は各 checkout の `reviews/#<PR>-*`
- 移植先の review-fix-planning は、既知の経路（create-reso-world・usaturn/resoloop・orange3134/resoloop）と、明示した `CODE_ROOT` の PR を扱う。`external/resoloop/reviews/` の旧形式のディレクトリは fork と上流のどちらの PR か分からないので、PR の URL が無ければ推測せずに止まる（ディレクトリ名との一致で絞らない）
- 移植元の `review-records.md` は、「巡（round）」「席（seat）」を多く使う（114 か所と 24 か所。helper とテストのコメントにも 25 か所）。`review-findings.md` は使わず、同じ単位を「サイクル」「レビュアー」と書いている。移植先の `AGENTS.md` の「日本語表現」は、round を「巡」、seat を「席」と訳さないと定めている。出力の形式（JSON のキー・マーカー）には「巡」「席」は含まれない
- 移植元の文書と helper の `#494` などの番号は、改名前の usaturn/maatlog-poc（現 usaturn/agent-workspace）の Issue を指す。移植先でそのまま書くと create-reso-world の Issue を指してしまう

## 判断

### 範囲

- **D-1 変えるファイル**: Issue の「変えてよいもの」のうち、3 つの helper・3 つのテスト・2 つの文書を足す。`scripts/superpowers_context.py` には関数を足さない（D-4。既存の公開関数で足りるため）。したがって `tests/scripts/test_superpowers_context.py` も変えない
  - 検討した別案: `superpowers_context.py` に `review_target.py` 用の関数（既知の経路の一覧を返すなど）を足す。`resolve_context` が経路の決定と拒否を全て持っていて、呼ぶだけで済むので採らない。経路の規則を 2 か所に持たないためでもある
- **D-2 変えないもの**: Issue の「変えないもの」のとおり。`docs/maatlog-poc-porting.md` の 152 行目（`.agents/review-records.md`・`.agents/scripts/**` を「対象外」とした #17 の記録）は、この子の範囲に無いので変えない。PR と #116 で調整役に伝える

### `review_records.py`・`review_findings.py`

- **D-3 形式と挙動は移植元のまま**: 関数・CLI・JSON の形（キー、値、マーカー、`review-records` のブロック）、エラーの文言、終了コードを変えない（#116 の「共有インターフェースと担当」の「移植元の名前と形は、移植のために変えない」）。変えるのは次だけ
  - コメント・docstring・`--help` の文言の「巡」「席」を、`AGENTS.md` の「日本語表現」に合わせて書き換える（D-13）
  - 改名前のリポジトリの Issue 番号（`#494` など）を `usaturn/agent-workspace#494` の形にする
  - 検討した別案: 文言も移植元のまま写し、移植元との差分を小さく保つ。移植先の規則（`AGENTS.md`）に反するので採らない

### `review_target.py`

- **D-4 Git 操作の対象（`target_root`）**: 移植元の「親の checkout・submodule・一時 clone」を、`superpowers_context.resolve_context("review-workspace", parent_root=..., code_root=..., repo=<PR のリポジトリ>)` に置き換える。返る `code_root` を `target_root`、`base_remote` を新しい項目 `base_remote` として JSON に出す
  - create-reso-world の PR は親の checkout、usaturn/resoloop・orange3134/resoloop の PR は `external/resoloop`（`base_remote` はそれぞれ `origin`・`upstream`）。それ以外は `--code-root <絶対パス>` で明示した main checkout（remote 1 件が PR のリポジトリと一致すること）
  - checkout が決まらないとき（`external/resoloop` が無い・remote が違う、それ以外のリポジトリで `--code-root` が無い・一致しない、既知の経路と食い違う `--code-root`）は、`superpowers_context.py` の理由を添えて終了コード 7 で止まる。clone しない、checkout を探さない
  - `superpowers_context.py` は、`review_target.py` と同じ checkout の `scripts/superpowers_context.py` を `importlib` で読む（helper とその規則の版をそろえる）
  - 検討した別案: 移植元のとおり、checkout が無ければ `target_root: null` を返して呼び出し側に任せる。Issue の制約（「checkout が決まらなければ `CODE_ROOT` の明示を求めて止まる」）と、移植先の pr-review・review-fix-planning の「推測せず停止」に合わないので採らない
- **D-5 一時 clone を持ち込まない**: `clone` サブコマンド・`clone_repository`・`CloneTarget` は持ち込まない（Issue の制約）。`fetch_pull_head` は、後続の pr-review（#153）が既存の checkout で PR head を固定するのに使うので、移植先の規則に合わせて残す
  - 署名は `fetch_pull_head(checkout, repository, number, head_sha, *, remote)`。ref は移植先の pr-review（#146）と同じ `refs/pr-review/repos/<owner>/<repo の小文字>/<N>`、取得元は D-4 の `base_remote`。fork と上流の同じ番号の PR が、同じ checkout で互いの ref を上書きしない
  - 失敗の終了コードは移植元の 12 のまま。名前は `EXIT_CLONE` から `EXIT_FETCH` にする（clone をしないため）
- **D-6 レビューディレクトリの規則（#116 の D-10）**: 新しい配置は `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<head ブランチを変換した名前>/`。`<owner>/<repo>` は PR が存在する側（base）のリポジトリを小文字にしたもの。head ブランチの変換は移植元と移植先の pr-review で同じ規則（`/`・Windows で使えない文字・制御文字を `-` に、末尾の空白と `.` を落とす）
  - 小文字にするのは、移植先の pr-review（#146）と `superpowers_context.py` が小文字で扱うため（移植元は GitHub の正式名の大小のまま）。今の対象リポジトリは全て小文字なので、移植元の配置とも一致する
  - fork と上流の同じ番号の PR は、`<owner>/<repo>` が違うので別のディレクトリになる
- **D-7 旧配置は明示したパスでだけ読む**: 番号・URL からは新しい配置（`PARENT_ROOT/reviews/<owner>/<repo>/` の直下の `#<N>-*`）だけを見る。見つからないときは、移植元と同じく、旧配置にある同じ番号のディレクトリをエラーの文に並べる（選ばない）。明示したパスは次の順で PR を決める
  1. `PARENT_ROOT/reviews/<owner>/<repo>/#<N>-*`: パスの `<owner>/<repo>`
  2. `PARENT_ROOT/reviews/#<N>-*`（移植先の旧形式）: 親の origin（create-reso-world）
  3. `<checkout>/reviews/<owner>/<repo>/#<N>-*`（#146 の checkout ごとの配置。例 `external/resoloop/reviews/usaturn/resoloop/#11-*`）: パスの `<owner>/<repo>`。`<checkout>` が Git の checkout のルートで、その remote に `<owner>/<repo>` があること
  4. `<checkout>/reviews/#<N>-*`（各 checkout の旧形式）: `<checkout>` の remote の GitHub のリポジトリが 1 つだけならそれ。`external/resoloop` のように複数（fork と上流）なら、どちらの PR か決められないので終了コード 11 で止まる。ディレクトリ名との一致で絞らない（移植先の review-fix-planning の規則と同じ）
  5. どれでもないとき: 移植元と同じく `findings/*.json` の `pr`。無ければ終了コード 11
  - 1〜4 で決めたときも、`findings/` があれば移植元と同じく食い違いを確かめる。GitHub に照会した PR の head ブランチとディレクトリ名が一致しなければ止まる（移植元と同じ）
  - 検討した別案: 4 の複数のときに、fork と上流の両方に照会し、ディレクトリ名と head ブランチが一致する 1 件に絞る。移植先の review-fix-planning が「ディレクトリ名との一致で候補を 1 件に絞らない」と決めているので採らない。旧形式のディレクトリは、`reviews/<owner>/<repo>/` の下へ移せば 1 か 3 で読める
- **D-8 `--for-planning` で範囲を狭めない**: 移植元の owner の制限（`PLANNING_OWNERS = {"usaturn"}`、終了コード 10）は持ち込まない。移植先の review-fix-planning は既知の経路と明示した `CODE_ROOT` の PR を扱っていて（上流の orange3134/resoloop を含む）、owner で止めると停止理由が増え、#116 の注意書き（停止理由を変えない）に反する。範囲は D-4 の経路で決まるので、`resolve` と `review-dir` で同じになる。Issue の「対象にする PR の範囲を広げない」は D-4（clone をしない）で満たす
  - `--for-planning` は、移植元の呼び出し（review-verify・review-fix-planning の `review-dir "$ARG" --for-planning`）がそのまま動くように受け付け、範囲は変えない。ヘルプにそう書く
  - 検討した別案: (a) 移植元のとおり `usaturn` に限り、上流の `orange3134/resoloop` だけ加える。移植先で `CODE_ROOT` を明示した他の owner の PR が止まるようになるので採らない。(b) `--for-planning` を削る。移植元の呼び出しが引数の誤りで止まり、後続の子が呼び出しを書き換える手間が増えるだけなので採らない
- **D-9 CLI と JSON**: `resolve <PR> [--code-root <絶対パス>]` と `review-dir <PR|パス> [--for-planning] [--code-root <絶対パス>]`。成功時の JSON は移植元の項目（`parent_root`・`repository`・`number`・`url`・`head_ref`・`head_sha`・`head_repository`・`base_ref`・`state`・`clone_url`・`review_dir`・`target_root`）に `base_remote` を足したもの。`target_root` は常に文字列（null にならない）。`clone_url` は PR の base のリポジトリの URL で、移植元と同じく出す（後続の pr-review が checkout からの clone の remote に使う）
  - 終了コード: 0 成功、2 引数の誤り、3 PR が存在しない、4 リポジトリが存在しないかアクセス権が無い、5 認証・権限の問題、6 通信・API の失敗、7 親の main checkout・origin、または Git 操作の対象の checkout を使えない、8 PR はあるが保存済みのレビューが無い、9 候補が複数、11 パスから PR を決められない・食い違う、12 fetch の失敗。10 は使わない（D-8）。値は移植元と同じ
  - 番号（`3`・`#3`）は親の origin（create-reso-world）の PR。ほかのリポジトリの PR は URL で指定する（移植元と同じ）
- **D-10 Python の版**: 括弧の無い `except A, B:` を `except (A, B):` にする。`pyproject.toml` は #149 の担当で、今は `>=3.12` なので、この子の helper は 3.12 の文法に収める

### テスト

- **D-11 テストの範囲**: `AGENTS.md` の「テストの採用基準」に従う
  - `test_review_records.py`・`test_review_findings.py` は移植元のまま写す。文書の記入例を helper に通すテスト（記入例が検査・読み取り・描画で使えること）はコードを実行するので残す。ただし `test_format_document_examples_are_valid` の「記入例の種類の集合が決まった 6 つと一致する」の assertion は、文書の節構成を固定値で検査するので外し、記入例が 1 つ以上あって全て検査を通ることだけを確かめる
  - `test_review_target.py` は、移植元の `create_parent_repo`（`tools.test_support.repos`）の代わりに、実際の Git の checkout（親: origin が create-reso-world で `/reviews/`・`/external/` を無視、`external/resoloop`: origin が fork・upstream が上流、`--code-root` 用の別の checkout）を作る fixture で作り直す（#116 の D-8）。GitHub への照会は移植元の `FakeGh`（`gh api -i` の応答を返す偽物）で置き換え、`fetch_pull_head` はローカルの bare remote で確かめる。Git の設定は `GIT_CONFIG_NOSYSTEM=1`・`GIT_CONFIG_GLOBAL=/dev/null` で利用者の設定から切り離す
  - 写さないテスト: 一時 clone（`clone_repository`・`CloneTarget`）、submodule、owner の制限。D-4・D-5・D-8 で持ち込まない機能のため
  - 足すテスト（移植先の規則の挙動）: 既知の経路と `base_remote`、fork と上流の同じ番号の PR が別のディレクトリと別の ref になること、checkout が無いときに clone せず終了コード 7 で止まること、`--code-root` の受け付けと拒否、D-7 の 2〜4 の旧配置、`--for-planning` で他の owner の PR が止まらないこと
- **D-12 受け入れの確かめ方**（Issue の「受け入れ」）
  - 移植したテストが通る: `uv run pytest .agents/scripts tests/scripts/test_superpowers_context.py`
  - fork と上流の同じ番号の PR が別のレビューディレクトリになる: `test_review_target.py`（D-11）
  - 旧配置は明示したパスでだけ受け付け、番号・URL からは探さない: `test_review_target.py`（番号では旧配置を選ばずにエラーの文に並べるだけ、パスでは受け付ける）
  - checkout の無いリポジトリで clone せずに止まる: `test_review_target.py`（終了コード 7、clone 先も ref も作られない）
  - 判断の記録が無い PR の集約が、空の結果・終了コード 0: `test_review_records.py` の `test_fold_without_records_is_empty`・`test_cli_fold_accepts_a_pull_request_without_comments`（移植元のまま）

### 文書

- **D-13 `.agents/review-records.md`・`.agents/review-findings.md`**: 形式（JSON・マーカー・ブロック・コマンドの引数）と記入例の構造は移植元のまま。次を移植先に合わせる
  - 用語: `AGENTS.md` のとおり、「巡（round）」は「サイクル（round）」（「1 巡目」は「1 回目」、「各巡」は「各サイクル」）、「席（seat）」は「レビュアー（seat）」、「席構成」は「レビュアーの構成」にする。移植元の `review-findings.md` も、同じ単位を既に「サイクル」と書いている。PR 修正ループ（loop）が run の中で数える番号は、この形式のサイクルの番号（`round`）と別のものなので、「loop のサイクル番号」と書き分ける
  - 改名前のリポジトリ（usaturn/maatlog-poc、現 usaturn/agent-workspace）の Issue 番号は `usaturn/agent-workspace#N` にする。記入例の架空の PR（#900）のリポジトリは `usaturn/create-reso-world` にする
  - 置き場所の説明は D-6・D-7 に合わせる（親の main checkout の `reviews/<owner>/<repo>/`、旧配置、`public/` などの移植元の構成を外す）
  - 移植先にまだ無いもの（`tools/agent_runner/`、pr-review の `review_run.py`、review-verify、pr-review-fix-loop など）を指す箇所は、どの子で入るか（#149・#153〜#156）を添えて残す。移植元にだけあり、持ち込まないもの（`tools/review_triage`、`tools/herdr_pr_review` など）を指す箇所は外すか、移植元のものと分かる書き方にする
  - 検討した別案: 文書を移植元のまま写し、注記を足すだけにする。移植先の読者（後続の子と利用者）が、存在しない構成や別リポジトリの Issue を移植先のものと取り違えるので採らない

### 実行方式

- **D-14 inline（`superpowers:executing-plans`）で実装する**: 作業の大半は、移植元のファイルをこのセッションに読み込んだうえでの写しと、文書の用語の書き換えである。`review_target.py` の適応はこの Spec の判断（D-4〜D-8）に強く依存する。子に渡すと、移植元と判断の文脈を全て渡し直すことになる。最後にブランチ全体のレビューを、新しいサブエージェントで 1 回行う
  - 検討した別案: `superpowers:subagent-driven-development` で Task ごとに担当とレビュアーを起動する。Task は独立しているが、文脈の受け渡しの量に対して得るものが小さいので採らない

## 範囲外

- スキル（pr-review・review-verify・review-fix-planning・pr-review-fix-loop）への接続（#153〜#156）
- `AGENTS.md` の「PR レビュー結果」の行と、pr-review の保存先の切り替え（#153。#116 の D-10・D-17）
- `pyproject.toml`・`README.md` の「テスト」の変更（#149）
- `docs/maatlog-poc-porting.md` の更新（D-2）

## 実装者に任せること

- 文書の用語の書き換えで、文脈に応じた言い回し（「回」「レビュアー」の使い分け）
- `review_target.py` の関数の分け方（D-4〜D-8 の挙動と CLI・JSON・終了コードを満たす範囲）
- テストの fixture の書き方
