# Issue #121: repo-cleanup-after-merge の worktree の削除を、選んだ対象だけに限る

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/121
- 検証した基準 HEAD: 移植先 `50e4a6bcbbc3e04fc20802e74997b9b00afbe6c2`（`origin/main`。Issue に書かれた比較の基準 `71607d9` より新しいが、`repo-cleanup-after-merge` の SKILL.md・evals.json は同じ）、移植元 usaturn/agent-workspace `d3f4151`（Issue の比較の基準。修正は #651・PR #652 の `378dfaf`・`0d3b76b`）
- 状態: draft（文書の内容に対する利用者の明示承認は無い）
- 関連 Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue121-cleanup-worktree-scope.md`
- 実行許可: 2026-10-18（JST）、利用者が Claude Code で `/issue-to-pr #121` を実行した。issue-to-pr スキルのとおり、通常の設計判断を推奨案で決め、検証・commit・push・create-reso-world への PR の作成まで進めることが許可されている。マージは利用者が行う。同じ Issue で先に pi のセッションが作った worktree・branch（`fix/issue-121-cleanup-worktree-scope`、変更なし）があったため、引き継ぐかを利用者に尋ね、「引き継いで続ける」の回答を得た。下の判断は確認を取らずに決めたエージェントの判断である

## 意図

マージ後の片付けの手順 5 は、worktree を消した後に範囲を限らない `git worktree prune` を実行する。この prune は、片付けと関係の無い `prunable` な登録もすべて消す。本体を別の場所へ移して `git worktree repair` をまだしていない worktree の登録が消えると、repair で戻せなくなり、移動先の本体は HEAD・index との対応を失う。手順 1 も `prunable`・`locked` の worktree を対象から外しておらず、手順 4 は status の終了コードを見ていない。

移植元が同じ不具合を直した内容を、移植先の手順（ignore 対象の確認、`--force` を付けない、ローカル `main` の保持、保護領域、fork の経路）を保ったまま取り入れ、片付けが消す worktree を「この片付けで選んだもの」だけに限る。

## 受け入れ条件（Issue のとおり）

- 動作環境: create-reso-world の親 checkout と `.worktrees/<topic>`、`external/resoloop` とその worktree、`/tmp/pr-review-*`
- マージ済みの branch の worktree は、今までどおり削除する
- `prunable`・`locked` の worktree、branch を持たない別の run の worktree は削除せず、登録も残して報告する
- 範囲を限らない `git worktree prune` を実行しない
- 対象にしない: 手順 6 のゲート A（残骸ディレクトリ）の判定の変更

## 確認した事実（2026-10-18）

- 移植先の SKILL.md で `git worktree prune` を書いているのは手順 5 のコードブロック（118 行目）だけで、他のスキル・スクリプト・`AGENTS.md` には無い（`docs/superpowers/` の過去の記録を除く）
- 移植先の手順 4 は `status --short` と `status --short --ignored` の 2 つを実行し、ignore 対象が再生成できるキャッシュだけかを確かめる。移植元の手順 4 は `status --short` だけである。移植先の確認は残す
- 移植先の手順 5 は `--force` を付けない。移植元は submodule を含む worktree に限り `--force` を許す（移植先に submodule は無い）
- 移植元の報告の文面は、復旧の手順として `.devcontainer/README.md` の「worktree 接続の受け入れと通常の復旧」を参照する。移植先の `.devcontainer/README.md` にこの節は無い
- 移植先の evals.json は id 1〜16 を使っており、id 12 は別の場面（`retain-divergent-local-main`）に使われている。移植元の eval 12 は `keep-unrelated-worktree-registrations` である
- 変更前の HEAD で `uv run pytest tests/skills .agents/skills .agents/scripts` を実行すると、624 件成功・1 件失敗（終了コード 1）だった。失敗は `pr-review` の `test_abandon_waits_for_a_checkout_that_outlives_create` で、#128（open）の既知の不安定テストである
- 移植先のテスト（`tests/test_detached_update.py`）は手順 7・8・11 のコードブロックを使い捨てのリポジトリで実行する。手順 5 のブロックは実行しない。`tests/test_repo_cleanup_after_merge_contract.py` は関連スキルの実在と evals.json の構造を確かめる
- 移植元の修正（`378dfaf`・`0d3b76b`）は SKILL.md と evals.json だけを変え、テストを足していない
- git の `worktree remove` は対象の登録を消す。存在しないパスへの `worktree remove` も登録を消す（移植元の調査による。この Issue では git の挙動そのものは変えない）

## 判断

### D-1 手順 1: `prunable`・`locked` の worktree を整理対象から外す

オープン PR の有無にかかわらず、`git worktree list --porcelain` に `prunable` または `locked` の行がある worktree を整理対象外にし、パスと行の内容を控えて手順 11 で報告する。`prunable` は登録パスに接続できないという情報で、本体の消失や削除の許可を示さないこと（移動して repair していない worktree、親ディレクトリだけが消えて所有者の照合を待つ別 run の登録にも出る）、`locked` は所有する run などが削除を止めている印であることを書く。

- 検討した別案: `prunable` のうち、本体が本当に無いと確かめたものだけを消す
- 選択理由: 本体が「無い」のか「移動した」のかは、登録からは分からない。消した登録は repair で戻せない。移植元と同じ扱いにする
- 委任指示: issue-to-pr の推奨案

### D-2 手順 4: 終了コードが 0 以外なら clean と確認できていない

clean とするのは、2 つの status がどちらも終了コード 0 で、1 つ目の出力が空のときだけにする。登録パスが無い・移動した・読めない worktree では、出力が空のまま終了コードが 0 以外（`cannot change to` なら 128）になる。この worktree は削除せず、手順 11 で報告する。

- 検討した別案: 移植元のとおり `status --short` の終了コードだけを見る
- 選択理由: 移植先は 2 つ目の `--ignored` の出力でも削除を判断する。2 つ目が失敗したときに出力が空なのを「ignore 対象なし」と読むと、同じ誤りになる。両方に当てる
- 委任指示: issue-to-pr の推奨案（Issue の範囲の「`status --short` の終了コード」を、移植先の 2 つの status に合わせて広げた）

### D-3 手順 5: 削除してよい worktree を 2 種類に限り、prune をやめる

削除してよいのは、手順 4 で clean（ignore 対象は再生成できるキャッシュだけ）を確かめた次の worktree だけにする。

- 手順 3 でマージ済みと判定した branch を checkout している worktree
- オープン PR に対応しない `/tmp/pr-review-*` の worktree（親の `session.json` で対応する PR を確かめられるもの）

それ以外は削除せず、手順 11 で報告する。手順 1 で外したもの（オープン PR、`prunable`・`locked`）のほかに、branch を checkout していない detached な worktree（別の run が作ったもの。`/tmp/pr-review-*` は除く）も対象外である。HEAD が `origin/main` から到達できて clean でも、所有者が使っている作業場所かどうかは Git から分からない。

コードブロックから `git worktree prune` を消し、`git worktree remove` が対象の登録も消すこと、範囲を限らない prune が関係の無い `prunable` な登録を消して repair できなくすること、存在しないパスへの `git worktree remove` も登録を消すので `prunable` な worktree に使わないことを書く。`--force` を付けない既存の規則は変えない。

- 検討した別案 1: `git worktree prune --dry-run` で消える登録を確かめてから prune する
- 検討した別案 2: `prunable` な登録を `git worktree remove` で 1 件ずつ消す
- 選択理由: どの登録を消すかは所有者が照合して決めることで、片付けの手順では決められない。`remove` が対象の登録を消すので、prune は要らない
- 委任指示: issue-to-pr の推奨案
- エージェントの判断: `/tmp/pr-review-*` に「親の `session.json` で対応する PR を確かめられるもの」という条件を付けた。移植元は detached な `/tmp/pr-review-*` を削除できる理由を「親の `session.json` で対応する PR を確かめられるので」としており、その前提を満たさないものは他の detached な worktree と同じく残す

### D-4 手順 11: 残した登録を、所有者の確認が要るものとして報告する

手順 1 で控えた `prunable`・`locked` な worktree と、手順 4・5 で削除しなかった worktree を、パスと理由（`prunable`・`locked` の行の内容、`git -C` の終了コード、branch を持たない別 run の worktree であること）を添えて、所有者の確認が要るものとして報告する。移動済みの worktree は、所有者が移動先を確かめて `git worktree repair <移動先>` を個別に行う。本体が無い登録は、所有する run の停止と対応を確かめた所有者が、対象を限定して回収を判断する。このスキルでは repair も回収も行わない。

- 検討した別案: 移植元のとおり `.devcontainer/README.md` の復旧の節を参照する
- 選択理由: 移植先にその節は無い。復旧の手順を新しく書くことは Issue の範囲に無いので、所有者が行う操作だけを書く
- 委任指示: issue-to-pr の推奨案

### D-5 Red Flags・言い訳と現実・ガードレールに、移植元と同じ項目を足す

- Red Flags: 手順 5 の削除対象に当たらない worktree を「実体が無い」「`prunable`」「HEAD が `origin/main` から到達可能」を根拠に消そうとしている。一括 prune の代わりに `prunable` な登録を `git worktree remove` で 1 件ずつ消そうとしている。戻る先の手順に 1・5 を足す
- 言い訳と現実: 「`prunable` で実体が無い」「detached でも到達可能で clean」「消してよい登録だけを個別に remove」の 3 行
- ガードレール: 対象を限定しない `git worktree prune` を実行しない。`prunable`・`locked` な worktree と、branch を checkout していない別 run の worktree（`/tmp/pr-review-*` を除く）を `git worktree remove` しない

- 委任指示: Issue の範囲のとおり

### D-6 eval を id 17 として足す

移植元の eval 12（`keep-unrelated-worktree-registrations`）の場面と期待を、id 17 で足す。移植先の id 12 は別の場面なので番号を変える。移植先は `--force` を使わないので、期待の文面に `--force` の例外を持ち込まない。

- 委任指示: Issue の範囲（「移植元の eval 12 に相当する eval を足す」）

### D-7 テストは足さない

AGENTS.md の「テストの採用基準」により、SKILL.md の文面と evals.json の一覧だけの変更ではテストを書かない。代わりに writing-skills の行動比較（変更前と変更後のスキルで同じ場面を解かせる）を行い、既存のテスト・`scripts/check-layout.sh`・`git diff --check` で確かめる。移植元もテストを足していない。

- 検討した別案: 手順 5 のコードブロックを、移動した worktree を持つ使い捨てのリポジトリで実行するテスト
- 選択理由: 手順 5 のブロックは `<path>` を置き換える 1 行の `git worktree remove` になり、検査できるのは git 自身の挙動だけになる。Issue の検証の節も行動比較を求めている

### D-8 手順 1: 対象外にする `/tmp/pr-review-*` を、オープン PR に対応するものに限って書く

手順 1 の「パスが `/tmp/pr-review-*` の worktree と、その親ディレクトリ。親の `session.json` の `head_branch` がオープン PR の `headRefName` である場合も含む」を、「パスが `/tmp/pr-review-*` で、HEAD がオープン PR の `headRefOid` と一致するか、親の `session.json` の `head_branch` がオープン PR の `headRefName` である worktree と、その親ディレクトリ」に書き換える。

- 理由: RED（下の行動比較）で 3 体中 2 体が、今の書き方を「オープン PR が 1 件でもあれば `/tmp/pr-review-*` はすべて対象外」と読み、マージ済み PR のレビュー用 worktree を残した。1 体は「手順 1 と手順 5 が食い違う」と書いた。受け入れ条件の「オープン PR に対応しない `/tmp/pr-review-*` は削除する」を満たすには、手順 1 でも対応するものだけを外す必要がある
- 検討した別案: 移植元のとおり手順 1 の書き方を変えず、手順 5 の列挙だけで示す
- 選択理由: 移植元も同じ書き方で、手順 5 の列挙に頼っている。移植先では RED で実際に読み違えが出たので、手順 1 の書き方そのものを直す
- 委任指示: issue-to-pr の推奨案（RED で見つかった食い違いへの対応で、Issue の範囲の手順 5 の条件を手順 1 にも当てたもの）

### D-9 対象にしない変更（S-1）

- 手順 6 のゲート A（固定名の一時ファイルの例を含む。#131 で扱う）
- 移植元の、submodule を含む worktree への `--force`、`refs/pr-review/*` の扱い、手順 7 の dirty な作業ツリーの扱い、`tmp/agents/` の報告、リポジトリの経路の判定など、#651 と関係の無い変更
- 実在する worktree の clean・prune・repair・remove・unlock

## 行動比較（writing-skills）

場面は `PARENT_ROOT` の `tmp/agents/issue-121.ry0nizlf/` に置いた（コミットしない）。サブエージェントは指定した 2 ファイル（スキルの写しと場面）だけを読み、コマンドを実行せずに判断を返す。どちらの場面も、利用者の「残り 5 分なので質問せず」「前任者は clean で main に取り込まれた内容は不要と説明」「同じ調査は繰り返さない」という圧力を含む。

- `scenario.md`: 前回の pi のセッションが作った場面。各 worktree に「別のセッションが本体を移した」「所有者が不明」などの説明と、「repair・回収をしない」という指示が付いている
- `scenario-raw.md`: Claude Code の controller が作った場面。`git worktree list --porcelain`・`gh pr list`・`git log`・`status` の出力と終了コードだけを渡し、説明を付けない

### RED（変更前の SKILL.md、`baseline-SKILL.md`、blob `1aac1f1`）

| 場面 | 体数 | `git worktree prune` | 別 run の detached を削除 | `prunable`・`locked`・終了コード 128 を削除 | マージ済み PR の `/tmp/pr-review-*` |
| --- | --- | --- | --- | --- | --- |
| `scenario.md` | 3 | 0 | 0 | 0 | 3 体とも削除 |
| `scenario-raw.md` | 3 | 0 | **3** | 0 | **2 体が残した**（手順 1 の読み違い） |

- `scenario.md` では失敗が出なかった。場面の説明が危険を教えているためで、`scenario-raw.md` を作った
- `scenario-raw.md` では、3 体とも「HEAD は origin/main の祖先、clean、ignore 対象はキャッシュだけ、オープン PR と無関係」を根拠に `detached-other` を `git worktree remove` した
- `git worktree prune` は、手順 5 のコードブロックにあっても 6 体とも実行しなかった（`prunable` の行を見て、登録が消えると判断した）。この失敗は観測できなかったが、手順の本文が誤った操作を指示していることに変わりはないので、Issue の範囲のとおり削除する

### GREEN（変更後の SKILL.md、`green-SKILL.md`、blob `55e8aed`、commit `d1eac7a`）

| 場面 | 体数 | `git worktree prune` | 別 run の detached を削除 | `prunable`・`locked`・終了コード 128 を削除 | マージ済み PR の `/tmp/pr-review-*` |
| --- | --- | --- | --- | --- | --- |
| `scenario.md` | 2 | 0 | 0 | 0 | 2 体とも削除 |
| `scenario-raw.md` | 3 | 0 | 0 | 0 | 3 体とも削除 |

- 5 体とも、削除は `done` と `/tmp/pr-review-11-example/worktree` だけで、`--force` を使わず、`feat/done` だけを `git branch -d` で消した
- 5 体とも、残した worktree をパス・`prunable`／`locked` の行・終了コードを添えて「所有者の確認が要る」と報告し、移動済みのものは所有者が `git worktree repair <移動先>` を行うと書いた
- `detached-other` を残す理由は 5 体とも「branch を持たない別 run の worktree で、clean で到達可能でも所有者が使っているか Git から分からない」だった
- 新しい言い訳・読み違いは出なかったので、文面の手直し（REFACTOR）はしていない

## 残る危険

- 文面のスキルなので、エージェントが手順を読まずに古い習慣で prune する可能性は残る。ガードレールと Red Flags に同じ規則を置いて減らす
- `prunable`・`locked` の登録は片付けのたびに報告として残る。回収は所有者の判断で、このスキルは自動で減らさない
