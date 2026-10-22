# Issue #235: tests/scripts のテストを、新しい採用基準で減らす

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/235（親 #228、ボード `test-reduction-board`、子のキー `script-tests`。先行 #229 は completed、PR #240 は `main` にマージ済み）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-23-create-reso-world-issue235-script-tests.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-235-script-tests`（branch `feat/issue-235-script-tests`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-23（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr #235 --merge
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #235`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う。Issue の「マージは利用者が行う（利用者が明示した指示がある場合を除く）」は、この `--merge` を明示の指示として扱う
  - 方針は #228 の「利用者の決定（2026-10-21）」と「削除と採用の基準」に従い、議論し直さない。ほかの判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`、`assign = {}`、`template = .devcontainer/agent-runner.toml`、`config = null`（いずれも既定の適用。利用者の指定は無い）。割り当ては、レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、修正（`implement`）が `claude-opus`、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。利用者の指定ではない）
- 予約: `refs/heads/agent-claims/issue-235` = `5573b7094d54b1ecee13a7cb0de0b6353f03bf6e`（https://github.com/usaturn/create-reso-world/issues/235#issuecomment-6345075530）
- 基準: `origin/main` の `481a047`

## 意図

`tests/scripts` のテスト（bash の `test-*.bash` と unittest の Python）を、`AGENTS.md` の「テストの採用基準」（#229、PR #240）の分類で 1 つずつ見直し、S（F∩S を含む）と D の代表だけにする。消すテストは、F・L・D の余りと、それだけが使っていた補助である。Meshy のテスト（`test_meshy.py`・`test_meshy_conversion.py`）は #103 が消すので扱わない。

## 範囲

- 変える: `tests/scripts/`（Meshy の 2 ファイルと `test-superpowers-python.bash` を除く）、この子の Spec・Plan
- 変えない: Issue の「変えないもの」のとおり。F∩S の値（ペルソナ節の SHA と `CLAUDE.md` の 1 行目、取り込んだ過去文書の SHA の一覧、gitignore の範囲）は変えていない
- `scripts/` のコードと文書の撤去は行わない（D-235-6）

## 計測（Issue の「検証」の計測コマンド）

| 指標 | 前（`481a047`） | 後 | 比 |
| --- | --- | --- | --- |
| Python のテスト（pytest の収集数） | 61 | 33 | 54% |
| bash のテスト（`tests/scripts/test-*.bash`） | 14 本 | 9 本 | 64% |
| 件数の合計 | 75 | 42 | 56% |
| 行数（`tests/scripts` の追跡ファイル。Meshy を除く） | 3,293 | 1,842 | 56% |

「後」は、PR 修正ループのサイクル 1（D-235-9）で 7 場面を戻した commit（`8476840`）の後に、同じコマンドで測った（`33 tests collected`、`ls` が 9、`wc -l` が 1842）。戻す前（`d0ef1f5`）は 1786 行だった。

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-235-1 | 分類の単位は、bash は場面（`# N.` の見出し）、Python は関数、parametrize・ループは群とする。残すテストは、守りごとの代表の 1 件にする | ループの全ての値を残す | #228 の「迷うもの」「D」に従う。ループは値を減らすだけで件数は変わらないが、行数が減る | #228 の決定 1・6 |
| D-235-2 | check-layout.sh・new-world.sh・resoloop-fork.sh が「拒否する」テストは、拒否が壊れると S の損害（誤ったレイアウトの通過、利用者のファイルの上書き、別の checkout への push）が残るので L ではなく S とする | 終了コードの検査は全て L | `AGENTS.md` の L のただし書き | `AGENTS.md` の基準 |
| D-235-3 | `test-blender-system-python.bash` は L として消す。PATH の除去・`VIRTUAL_ENV` の解除・引数の保持が壊れると、Blender が NumPy を import できない例外（#60）か、起動の失敗として現れる。`exec` なので終了コードは変わらない | 迷いとして残す | #229 の申し送り（この子の手がかりは L）。気付ける経路が具体的にある | 迷いは無い |
| D-235-4 | `test_superpowers_lifecycle.py` の `test_continuation_gates_keep_unapproved_or_unauthorized_resumes_blocked` は、F∩S の候補だが決められないので「迷い」として残す。`test_handoff_schema_separates_approval_current_authority_and_publication` は schema の定義の文言を写した F として消す | 2 件とも残す。2 件とも消す | 受け取り側が再開するか決める表の「blocked」の行は、変わると未承認の実装が進む（権限を決める値）。定義の一覧は変わっても気付ける（schema を読む側が欠けた項目に気付く） | `integration` の一覧で先頭に並べる |
| D-235-5 | 消したテストだけが使っていた `tests/scripts/lib/path.bash` を消す。`path_without` を使っていた場面は、全て L として消えた | 残す | 使う側がいなくなった。#228 の「消したテストだけが使っていた補助は一緒に消す」 | — |
| D-235-6 | `scripts/` のコードの撤去（#228 の決定 5）は行わない | 旧形式の経路を探して撤去する | Issue の手がかりに撤去の候補が挙がっておらず、`git grep` による呼び出し元の確認を行っていない。確かめられないものは撤去しない（#228 の「撤去」） | — |
| D-235-7 | `test-scan-before-push.bash` は、検出の経路と fail-closed のうち、緩める経路ごと（インライン allow・色付き diff・textconv・`.gitattributes`・作業ツリーと環境変数の設定・base の設定の取得）を別の守りとして全て残す。D とするのは、同じ allowlist の狭さを確かめる無作為な値の 5 件のうち 2 件（区切り無し、GitHub の token）と、`--base` の remote 名の誤り・usage・未知の引数だけ | 緩める経路も代表に絞る | 緩める経路は実装が別なので、1 つが壊れても別のテストは通る（D の「同じ守り」ではない） | — |
| D-235-9 | D（同じ守り）に当たるのは、同じ実装（同じ関数・同じ分岐）の値違いだけにする。別の関数・別の分岐は、同じ性質（symlink の先に書かない、リンクの行き先、指示ファイルの読み込み）を守っていても別の守りなので、代表を残す。レビューの指摘（サイクル 1、4 人）で、旧場面 24・30・34 の symlink・25・37b・37c・fork の旧場面 21・26 の origin への push の確認を、D・F・L としていたのを S に直し、7 場面を戻した | 同じ性質は 1 件にまとめる | D-235-7 で緩める経路を経路ごとに残した基準と、#228 の決定 6（数を合わせるために S のテストを消さない）に合わせる。表の旧 38 の記載漏れも直した | レビューの指摘 |
| D-235-8 | 残した守りのうち、重さが高く代表に絞ったものは、使い捨てのコピーで守る処理を壊し、残したテストが失敗することを 1 回ずつ確かめた（下の「変異の確認」） | 確認しない | Issue の受け入れ | Issue の受け入れ |

## 棚卸しの表

分類は F・F∩S・L・S・D・撤去・迷い。重さ（S）は高・中・低（#228 の「守りの重さ」）。「新」は、今の場面の番号。

### bash

| ファイル・場面（前の番号） | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `test-agent-config.bash` | S（高） | 共有する MCP 設定の header に鍵の直書きが入る。private の CI と gitleaks は停止していて、この検査だけが直書きのコミットを止める | 残す |
| `test-blender-system-python.bash` | L | D-235-3 | 消す |
| `test-ci.bash`（`ci.yml` の gitleaks ジョブ、版の一致） | F | ワークフローと `install_gitleaks.bash` の値の写し。private の CI は止めていてジョブは実行されない | 消す |
| `test-ci.bash`（`.gitleaks.toml` の allowlist の正規表現） | F・D | 設定の値を写して照合している。allowlist が秘密情報を除外しない確認は `test-scan-before-push.bash` が実際の gitleaks で行う（下の `leak_with_repo_config`） | 消す |
| `test-docs.bash`・`test-instructions.bash` の参照実在の検査 | L・F | 参照先のファイルの存在は構造の検査（`AGENTS.md`「テストを書かないとき」）。文書の本文の写しでもある | 消す |
| `test-file-modes.bash` | L | 実行権限は、実行したときに「Permission denied」として現れる | 消す |
| `test-gitignore.bash` の 3 つの一覧 | F∩S | gitignore の範囲。Issue の「変えないもの」。値は変えていない | 残す |
| `test-gitignore.bash` の 4 つ目（追跡中かつ ignore の組が 0 件） | D | `scripts/check-layout.sh` の `tracked but ignored` と同じ守り（`test-check-layout.bash` の新 4 が確かめる） | 消す |
| `test-instructions.bash`（`CLAUDE.md` の 1 行目、ペルソナ節の SHA） | F∩S | 指示ファイルの読み込み指定と利用者所有部分のハッシュ。Issue の「変えないもの」 | 残す |
| `test-superpowers-review-copy.bash` | L | `exec uv run` のラッパーの起動の確認だけ。壊れれば起動の失敗として現れる。拒否・非置換・競合は Python のテストが確かめる | 消す |
| `test-superpowers-python.bash` | — | `integration` の担当 | 変えない |
| `test-resoloop-meshy.bash` の 3（clone・2 回目の確認）、6（origin 違い・無しで何も変えない）、7（外側のリポジトリの remote を見ない） | S（中） | 別のリポジトリの checkout を、自分の checkout として扱う（別のリポジトリを選ぶ）。clone の処理は `resoloop-fork.sh` と同じなので代表の 3 件にする | 残す（新 1〜3） |
| `test-resoloop-meshy.bash` の 1・2・4・8 | L | usage・status の表示・clone の失敗の終了コードとメッセージ | 消す |
| `test-resoloop-meshy.bash` の 5 | D | URL の末尾の `/`・`.git` の正規化。誤れば clone 済みを不一致と誤判定して止まるだけ（気付ける）で、`resoloop-fork.sh` と同じ | 消す |
| `test-resoloop-meshy.bash` の 9 | L | worktree の中へ clone しても、次の利用で checkout が見つからず気付ける。作り直せる | 消す |

#### test-check-layout.bash（53 場面）

| 前の番号 | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| 1 | S（通る例） | 何でも拒否する実装で通らないための、問題の無いリポジトリの通過 | 残す（新 1） |
| 2・9・10 | S（高） | 追跡禁止ファイル（私的なデータ）を、非 ASCII のディレクトリの中でも、サブディレクトリを `--root` にしても見逃さない。見逃すとコミットされ、気付かない | 統合して残す（新 2） |
| 3 | S（中） | 行き先の無い追跡 symlink。使うまで気付かないスキルの欠落 | 残す（新 3） |
| 4 | S（中） | 追跡中なのに ignore の対象。clone で記録が失われる | 残す（新 4） |
| 13・14・15・16 | S（中） | スキルのリンクの不一致（欠落・実ディレクトリのコピーが元と食い違う・行き先違い）。エージェントが古い、または無いスキルを静かに使う | 残す（新 5） |
| 17・37a | L | 対応するスキルの無いリンクは、読み込んでも見つからないだけで損害にならない | 消す |
| 34 | D | 15 と同じ非 symlink の検査（同じ関数・同じ枝） | 消す |
| 21・23 | S（中） | 標準レイアウトのプロジェクトの通過と、手で編集した同梱スキル（`SKILL_SYNC_CONFLICT`）の検出。更新で編集が失われる | 残す（新 6） |
| 24・28・29 | S（中） | プロジェクトのレイアウトの逸脱（必須ファイルの欠落・symlink の行き先・スキルのリンクの欠落）を通さない | 残す（新 7） |
| 25 | S（中）・F∩S | プロジェクトの `CLAUDE.md` が `@AGENTS.md` を読み込まない（指示ファイルの読み込み指定）。通すと、プロジェクトの規約と安全ルールを読まないまま作業が進む（D-235-9） | 残す（新 7 の `p-claude`） |
| 37b・37c | S（中） | プロジェクト側のスキルのリンク（`check_local_skill_links`。ルート側の `check_skill_links` とは別の関数）の行き先違いと実ディレクトリ。通すと、古い、または別のスキルを静かに使う（D-235-9） | 残す（新 7 の `p-target`・`p-realdir`） |
| 41a | S（中） | 追跡解除した従来位置のプロジェクトを検出して通過する（検出しないと検査されない） | 残す（新 8） |
| 42a・42b | S（高） | 作業領域の下の追跡ファイル（ワールドの作業物）の再混入。`git add -f` でも検出する | 残す（新 9） |
| 43 の通過、48 の前半 | S（中） | mount のソースと `initialize.bash` の食い違いを検出し、一致なら通過する | 残す（新 10） |
| 50 の前半 | S（中） | 設定が無ければ assets も標準ワールドとして失敗する（欠落を自動分類で隠さない）。明示された設定では通過する | 残す（新 11） |
| 52 の 3 件の誤った設定、正しい設定 | S（中） | 壊れた設定・収集できないパスを暗黙に無視せず失敗する（検査されないプロジェクトが残らない） | 残す（新 12） |
| 5・7・8 | L | 引数・`--root` の誤りは終了コード 64 とメッセージで止まる | 消す |
| 6 | D | mounts の通過は新 10、リポジトリ自身の通過は `README.md` の「テスト」の入口（`scripts/check-layout.sh`）が確かめる | 消す |
| 11・20・31・32・33・40・41c・42 の clone | L | 誤って失敗する側の検査（誤検知）。失敗は気付ける | 消す |
| 12・22・23 の warn・35・36・42c・43 の skip・45・46・47・48 の後半・49・52 の jq・symlink・ディレクトリ・53 | L | メッセージ・表示順・skip の表示・終了コード・見つからないファイル・壊れたオブジェクトのエラー（いずれもメッセージ付きの非 0 の終了） | 消す |
| 18 | F | 削除した旧ファイル（`.devin/skills`）が無いこと | 消す |
| 19 | L | 0 バイトのスキルのファイルは、初回の利用で明らかに動かない | 消す |
| 26・27・38 | F | `AGENTS.md` の節の見出し・`.resoloop/.gitignore` の行・`CLAUDE.md` の末尾の空行の写し | 消す |
| 30・39・41b | D | 28・24 と同じ検査（symlink の行き先と必須ファイルは、同じ分岐に値だけが違う） | 消す |
| 50 の後半、51 | D | 設定の仕組みは 50 の前半と 52 が確かめる。items の値の検査は設定値の写し | 消す |

#### test-new-world.bash（47 場面）

| 前の番号 | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| 1 | S（高） | 不正な名前（`../x`・`x/y` などのパスの脱出）で何も作らない | 残す（新 1） |
| 2 | S（通る例） | 新規作成が通ること。通る例が無いと、何でも拒否する実装で通る | 残す（新 2。リンクの行き先・`pyproject.toml` の中身の検査は L として消した） |
| 3 | S（高） | 既存のプロジェクトを `--apply` 無しで上書きしない | 残す（新 3） |
| 4 | S（中） | `--apply` の繰り返しで何も変わらない | 残す（新 4） |
| 16 | S（中） | 前提（ルートの `.pi`）が無ければ、`resoloop init` を呼ばず何も作らない（途中状態を残さない）。15・28・45 は同じ守りなので D | 残す（新 5） |
| 36 | S（高） | `worlds/<name>` とルート直下 `<name>` の両方があれば対象が決められず、何も変更しない（別の対象を選ばない） | 残す（新 6） |
| 37 | S（高） | 欠落・null の設定だけを補い、他の JSON の値と mode を保つ | 残す（新 7） |
| 39 | S（高） | 利用者が書いた `blenderExecutable`（カスタム・古い絶対パス・空文字）を上書きしない。40 は同じ守りなので D | 残す（新 8） |
| 41 | S（高） | JSON の構文・値型の競合は、追加や `+x` を含め何も変更しない。9 件の値のうち 3 件を代表にする | 残す（新 9） |
| 42 | S（高） | JSON が symlink（実体・壊れたリンク）でも、リンク先へ書かない。ディレクトリは D | 残す（新 10） |
| 43 | S（高） | 利用者の wrapper（symlink・内容違い）を上書きせず、リンク先も変えない。4 つの種類のうち 2 つを代表にする | 残す（新 11） |
| 44 | S（高） | 別の競合があれば、wrapper の mode と JSON も変えない（競合の検査の前に chmod や JSON の編集をしない）。解消すれば `+x` になる | 残す（新 12）。6・7・8・22・23・25・26・27 は同じ「競合なら無変更」なので D |
| 24 | S（高） | `AGENTS.md` が symlink でも、リンク先（利用者のファイル）へ追記しない（`new-world.sh` の `AGENTS.md` の枝。D-235-9） | 残す（新 13） |
| 30 | S（高） | 途中のディレクトリ（`.claude`）がディレクトリへの symlink でも、リンク先にも手元にも書かない（`parent_ok` の枝。D-235-9） | 残す（新 14） |
| 34 の symlink | S（高） | ルートの `worlds/` が symlink なら、`resoloop` を呼ばず、リンク先に何も作らない（`worlds/` の検査。通常ファイルの `worlds/` は L。D-235-9） | 残す（新 15） |
| 38 | D | 設定済みの wrapper の値のとき JSON を整形し直さずバイト列も保持する。利用者の指定の保持は新 7・8 が確かめ、整形が変わっても作業の結果は変わらない | 消す |
| 5・9・10・14・17・18・31・32・33・46 | L | 終了コードとメッセージで止まる（引数・resoloop・uv・jq の不在、init の失敗） | 消す |
| 11・12・13・20・21・29・35・35b・47 | L | `uv sync` の呼び出し・`cache/` の追記・SKILL.md の無いディレクトリ・名前の特殊文字・従来位置のリンク。誤れば `check-layout.sh`（symlink の行き先・欠落）か Blender の例外として現れる | 消す |
| 19・34 の通常ファイル・45 | D・L | 19 は 36 と同じ対象の曖昧さ。34 の通常ファイルの `worlds/` は、リンクが解決できず `check-layout.sh` が失敗する。45 は 5 と同じ前提の欠落 | 消す |

#### test-resoloop-fork.bash（28 場面）

| 前の番号 | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| 3 | S（通る例） | clone が通り、2 回目は確かめるだけ | 残す（新 1） |
| 4 の前半・25 | S（高） | 他の remote を持つ checkout を受け付けず、sync は fetch も push もしない（別のリポジトリへの push）。24 は URL の正規化で D | 残す（新 2） |
| 5 | S（中） | 外側のリポジトリの remote を見て clone 済みと誤判定しない | 残す（新 3） |
| 7・8（ローカルのブランチ、`HEAD`）・27 | S（中） | origin のブランチを使い、同じ名前の古いローカルのブランチを選ばず、`origin/HEAD` を origin のブランチとして扱わず、後から push された先端も fetch してから取り出す（別のコミットを選ばない） | 残す（新 4） |
| 9・14 の後半 | S（高） | 未コミットの変更があれば checkout も build も拒否し、HEAD を動かさない（変更の消失、版の取り違え） | 残す（新 5） |
| 11 | S（通る例） | sync が上流の main を fast-forward する | 残す（新 6） |
| 12 | S（高） | fork の main が上流から分岐していれば push しない | 残す（新 7） |
| 21・26 の後半 | S（高） | main に未コミットの変更があれば、ローカル main を動かさない。上流に無いコミットを持つローカル main も動かさない。どちらも止まる前に origin の main を上流の先端へ進める（確認は D-235-9 で戻した） | 残す（新 8） |
| 17・20 | S（中） | install が導入した版と `resoloop --version` を照合し、違えば成功と報告しない（失敗を成功と報告しない） | 残す（新 9） |
| 8（SHA・`upstream/main`・解決できない名前） | L | 解決できなければメッセージ付きのエラーで止まる。解決できる場合は git の解決そのもの | 消す |
| 1・2・6・10・13・15・16・18・22・23・28・19・14 の前半 | L | usage・status の表示・SDK の不在・build と test の呼び出しの引数・版の組み立て（導入時の照合が見つける）・tool の失敗の終了コード・導入済みの版のときの再 build の省略 | 消す |
| 26 の前半 | D | main の fast-forward は 11 と同じ | 消す |

#### test-scan-before-push.bash（17 リポジトリ）

| 場面 | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| 未 push の commit・マージ commit だけに足した値、インライン allow、色付き diff、textconv、`.gitattributes`、作業ツリーと環境変数の緩い設定、base に設定が無いときの作業ツリーの設定 | S（高） | 秘密情報が push される。緩める経路ごとに実装が別（D-235-7） | 残す |
| リポジトリの `.gitleaks.toml` での無作為な値 3 件（識別子に似た値・語と 8 桁の数字・接頭辞付き） | S（高） | allowlist が秘密情報を除外しない。`test-ci.bash` を消したので、ここが allowlist の狭さを確かめる。区切り無しの値と GitHub の token は、同じ allowlist の別の値なので D | 残す（3 件）。2 件は消す |
| 空の `.gitleaksignore`、壊れた base の設定、壊れたオブジェクト、octopus マージ、存在しない base、版の違う gitleaks、失敗する gitleaks | S（高） | 検査できないのに成功と報告する（fail-closed）。gitleaks は git が失敗しても 0 で「no leaks」と出す | 残す |
| 秘密情報の無い commit とマージ commit の通過（検査した SHA を出す） | S（通る例） | 何でも拒否する実装で通らない | 残す |
| 壊れた `.gitleaksignore` の symlink、`--base` の remote 名の誤り・usage・未知の引数 | D・L | 空の `.gitleaksignore` と同じ守り、引数のエラー（終了コード 2） | 消す |
| base で公開済みの値を取り込んだマージの通過、base の allowlist が効くこと、識別子の通過、`-C` のサブディレクトリ | L | 誤って止まる側の検査（止まれば気付く）。検査した SHA の表示は最後の通る例が確かめる | 消す |

### Python

#### test_superpowers_context.py（35 件 → 21 件）

| テスト | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `parent_origin_rejection_does_not_disclose_url_credentials`、`push_url_rejection_does_not_disclose_credentials...`、`repository_input_errors_do_not_echo_credentials...` | S（高） | 拒否のメッセージに URL の資格情報が出ない（秘密情報の漏れ） | 残す |
| `document_origin_rejection_does_not_disclose_url_credentials` | D | `_require_origin` を PARENT_ROOT と共有する（`superpowers_context.py:143`）。同じ関数のラベル違い | 消す |
| `external_cwd_cannot_become_implicit_parent`、`explicit_parent_supports_external_cwd_but_code_stays_explicit`、`empty_roots_are_omitted_not_external_defaults` | S（高） | 別のリポジトリの cwd を PARENT_ROOT に選ばない。通る例を含む | 残す |
| `missing_unsupported_or_foreign_parent_origin_has_actionable_error`、`linked_parent_requires_explicit_main_parent`、`explicit_roots_must_be_absolute_checkout_roots` | S（中） | 別のリポジトリ・worktree・checkout の外を root に選ばない。値の組み合わせを代表の数件にした | 残す |
| `external_remote_selection_requires_exactly_one_name`、`known_routes_select_base_and_reject_conflicting_explicit_root`、`fork_requires_both_expected_remotes` | S（高） | base の remote を 1 つに決め、既知のリポジトリの経路を別の checkout にすり替えない | 残す |
| `workspace_rejects_linked_code_but_fix_accepts_verified_worktrees`、`fix_rejects_known_worktree_effective_fetch_rewrites_without_disclosing_urls`、`fix_accepts_known_worktree_same_repository_transport_rewrites`、`fix_rejects_same_url_clone_and_its_linked_worktree_for_known_routes`、`document_main_and_linked_roots_verify_requested_branch` | S（高） | worktree の実効の fetch URL の書き換えや同じ URL の clone を、既知の checkout と誤認しない。経路と URL の値を代表にした。通る例を含む | 残す |
| `base_and_head_remote_are_independent_and_head_branch_must_match`、`head_remote_rejects_matching_first_pushurl_with_wrong_later_destination`、`head_remote_rejects_mixed_fetch_url_fallback_destinations` | S（高） | push 先の remote を 1 つに決め、後ろの push URL や fetch URL の fallback の誤った宛先を見逃さない（誤った対象への push）。通る例を含む | 残す |
| `invalid_repository_inputs_fail_clearly` | S（中） | 他のホスト（`github.com.evil`）を GitHub と誤認しない。3 件を代表にした | 残す |
| `missing_required_inputs_exit_64...`、`known_fork_prerequisite_defects_exit_65...`、`supplied_invalid_roots_and_candidate_mismatches_still_exit_66`、`malformed_operation_syntax_keeps_argparse_exit_2` | L | 終了コードとメッセージで止まる（argparse・必須入力の不足）。拒否の守りは上の S が確かめる | 消す |
| `parent_main_can_be_inferred_from_its_subdirectory`、`github_remote_formats_and_pr_url_normalize`、`head_remote_accepts_fetch_base_and_effective_push_head_split`、`head_remote_preserves_no_pushurl_fallback`、`head_remote_accepts_multiple_push_urls_only_when_all_target_head`、`head_remote_uses_effective_push_instead_of_rewrite` | L | 正しい入力を誤って拒否する側の検査（拒否すれば気付く）。通る例は上の S が含む | 消す |
| `head_remote_rejects_wrong_single_pushurl...`、`head_remote_requires_one_effective_push_candidate_name`、`copy_only_validates_document_and_parent_not_code_cwd` | D | later_destination（push URL の検査）、`external_remote_selection`（1 つに決める）、`external_cwd`（cwd を選ばない）と同じ守り | 消す |

#### test_superpowers_review_copy.py（23 件 → 10 件）

| テスト | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `distinct_concurrent_copies_leave_exactly_one_winner` | S（高） | 同時に別の内容を公開しても、一方が他方を上書きしない（記録を上書きしない） | 残す |
| `user_annotation_written_before_a_paused_publish_survives` | S（高） | 公開の直前に利用者が書いた注記を失わない | 残す |
| `destination_changed_into_a_symlink_before_publish_does_not_follow` | S（高） | 公開の直前に symlink に差し替えられても、リンク先（確認用コピーの外）へ書かない | 残す |
| `injected_link_failure_never_replaces_an_existing_destination` | S（高） | リンクの失敗時に、既存の entry を別の方法（rename・copy）で差し替えない | 残す |
| `creates_exact_committed_bytes_and_reports_metadata` | S（通る例） | コミット済みの版と同じ内容を作る（利用者が別の版を読まない） | 残す |
| `uncommitted_worktree_or_index_changes_are_rejected` | S（中） | 未コミットの版をコピーして、確認した版と食い違わない | 残す |
| `wrong_kind_suffix_or_uncommitted_path_is_rejected` | S（高）・L | `--name` のパスの脱出と、`--path` の範囲外を拒否する。種類・拡張子・未コミットのパスの拒否はメッセージ付きの非 0 の終了（L） | 3 件に絞って残す（`name_and_path_outside_the_review_layout_are_rejected`） |
| `existing_destination_kinds_are_never_replaced` | S（高） | symlink・ディレクトリ・FIFO・注記付きの既存の entry を差し替えない | 残す |
| `empty_required_roots_are_rejected_before_context_fallback` | S（高） | 空の root が cwd の fallback で公開される（別の対象を選ぶ）。2 つの root の組み合わせは D | 1 つ目のループだけ残す |
| `destination_must_be_ignored_and_inside_the_parent_checkout` | S（高） | ignore されていない場所や、symlink で親の checkout の外へ公開しない | 残す |
| `concurrent_identical_copies_report_created_and_unchanged`、`repeated_identical_copy_is_unchanged`、`pre_existing_identical_regular_file_is_unchanged` | L | `created`・`unchanged` の表示。内容が同じなので損害は無い | 消す |
| `destination_changed_into_a_directory_before_publish_fails`、`injected_link_failure_fails_closed_without_residue` | D | symlink の差し替え・既存の entry の非置換と同じ守り（ディレクトリへの `os.link` はエラーで止まる） | 消す |
| `old_committed_version_versus_new_dirty_source_is_rejected`、`new_versioned_name_leaves_the_old_copy_untouched`、`committed_plan_copies_with_exact_bytes_full_sha_and_kind_flow` | D | 未コミットの拒否・既存の非置換・正確な内容と同じ守り（spec と plan の種類の違いだけ） | 消す |
| `non_regular_committed_entry_is_rejected`、`commit_that_is_not_a_commit_is_rejected`、`replace_from_is_rejected_before_any_mutation`、`usage_errors_exit_2` | L | メッセージ付きの非 0 の終了・argparse の拒否 | 消す |
| `context_rejections_keep_shared_module_messages_and_change_nothing` | D | `test_superpowers_context.py` が同じ守り（origin・絶対パス・main checkout）を確かめる。守りを実装している側に残す | 消す |

#### test_superpowers_lifecycle.py（3 件 → 2 件）

| テスト | 分類 | 理由・防ぐ損害（重さ） | 扱い |
| --- | --- | --- | --- |
| `imported_documents_are_unchanged_since_import` | F∩S | 取り込んだ過去文書の SHA（凍結した履歴）。Issue の「変えないもの」。値は変えていない | 残す |
| `continuation_gates_keep_unapproved_or_unauthorized_resumes_blocked` | 迷い（F∩S の候補） | D-235-4。変わると、未承認・無許可の再開が「ready」になる | 残す |
| `handoff_schema_separates_approval_current_authority_and_publication` | F | schema の定義の項目名の写し（D-235-4） | 消す |

### 補助・fixture

| 対象 | 分類 | 扱い |
| --- | --- | --- |
| `tests/scripts/lib/path.bash` | 撤去（消したテストだけが使っていた補助） | 消す（D-235-5） |
| `tests/scripts/fixtures/superpowers-imported-documents.sha256.json` | F∩S | 残す（変えない） |

## 変異の確認（D-235-8）

守る処理を使い捨てのコピー（`mktemp -d` で作り、追跡するファイルだけを写した。実際のリポジトリには手を加えていない）で壊し、残したテストが失敗することを確かめた。

| 変異 | 守り | 失敗したテスト |
| --- | --- | --- |
| `check-layout.sh` の追跡禁止ファイルの検査から `git ls-files -z` の `-z` を外す | 追跡禁止ファイル（非 ASCII のディレクトリ）の見逃し | `test-check-layout.bash` の新 2 |
| `new-world.sh` が symlink の `.resoloop.json` を通常のファイルとして書く | symlink の先に書かない | `test-new-world.bash` の新 10 |
| 競合の検査の前に wrapper を `chmod +x` する | 競合なら無変更 | 新 9（新 12 も同じ守り） |
| 内容の違うファイルの競合を無視する | 利用者の wrapper の上書き | 新 11 |
| `resoloop-fork.sh` の remote の検査を外す（`require_remotes`） | 他人の checkout の拒否 | 新 2（clone） |
| `do_sync` の remote の検査だけを外す | 別のリポジトリへの push | 新 2（sync） |
| 分岐した `origin/main` の拒否を外す | 分岐した main への push | 新 7 |
| 未コミットの変更の拒否を外す | 変更の消失 | 新 5 |
| `.gitleaks.toml` の識別子の allowlist で、名前の塊の英字と数字の混在を許す | 無作為な値の除外 | `test-scan-before-push.bash`（識別子に似た値） |
| 同じ allowlist で `key()` の接頭辞の要求を外す | 語と 8 桁の数字の除外 | `test-scan-before-push.bash`（語と 8 桁の数字） |
| `select_push_remote` が最初の push URL だけを見る | 後ろの宛先の見逃し | `test_superpowers_context.py` の `later_destination` ほか 5 件 |
| `superpowers_review_copy.py` が内容の違う既存のファイルを受け入れる | 利用者の注記の上書き | `test_superpowers_review_copy.py` 3 件 |
| 同じファイルが symlink を辿る（`O_NOFOLLOW` を外す） | symlink の先への書き込み | 同 2 件 |
| 〔サイクル 1〕`new-world.sh` の `AGENTS.md` の symlink の枝を外す | `AGENTS.md` の symlink の先への追記 | `test-new-world.bash` の新 13 |
| 〔サイクル 1〕`parent_ok` の `-L` の判定を外す | 途中のディレクトリの symlink の先への書き込み | 新 14 |
| 〔サイクル 1〕`worlds/` の symlink の検査を外す | `worlds/` の symlink の先への作成 | 新 15 |
| 〔サイクル 1〕`check-layout.sh` が `CLAUDE.md` の内容を比べない | 指示ファイルの読み込み漏れ | `test-check-layout.bash` の新 7 の `p-claude` |
| 〔サイクル 1〕`check_local_skill_links` が行き先を確かめない | プロジェクト側のスキルのリンクの行き先違い | 同 `p-target` |
| 〔サイクル 1〕同じ関数が実ディレクトリを受け入れる | プロジェクト側のスキルのリンクの実ディレクトリ | 同 `p-realdir` |
| 〔サイクル 1〕`do_sync` が main を checkout 中は origin へ push しない | main 上の sync の push | `test-resoloop-fork.bash` の新 8（2 つの確認） |

## 申し送り（この子の範囲外）

- `.gitleaks.toml` の冒頭のコメントと 2 つ目の allowlist の description、`.devcontainer/install_gitleaks.bash:4` のコメント、`tests/scripts/test_meshy.py:20` のコメントが、消した `test-ci.bash` を参照している。いずれもこの子の範囲外（`.devcontainer` は #234、Meshy は #103、`.gitleaks.toml` はどの子の担当でもない）。2 つ目の allowlist（過去の文書に残る偽のトークンの除外）は、履歴を書き換えない限り残す必要があるので、値は変えない。コメントの更新は #228 の調整役に任せる
- `.agents/skills/review-fix-planning/SKILL.md:364`・`evals/evals.json` が `tests/scripts/test-check-layout.bash` を例に挙げている。ファイルは残っているので変更は要らない

## 受け入れ条件との対応

| Issue の受け入れ | 状態 |
| --- | --- |
| Spec に棚卸しの表がある | 上の「棚卸しの表」 |
| F・L・D の余り・撤去した経路のテストと、それだけが使っていた補助が消えている | 消した（D-235-5、棚卸しの表の「消す」） |
| 重さが高の守りで代表に絞ったものを、壊した使い捨てのコピーで確かめる | 「変異の確認」。13 件と、サイクル 1 で戻した 7 件の合計 20 件とも、残したテストが失敗した |
| 残したテストが通る | Plan の「検証の記録」 |
| 件数・行数の前後を測り、Spec とこの Issue に書く | 上の「計測」。Issue には PR のマージ後に書く |
