# Issue #154 review-verify の移植

- 文書管理・対象: `usaturn/create-reso-world`、Issue #154（親 #116）
- 基準 HEAD: `a024a22626d4ff6daa46e92aa7cb8aae081aa7ac`
- 状態: `completed`。前回のレビュー修正と、現行 HEAD `8ca547b4ab4c` に対する追加選別・マージ前の検証まで完了。内容承認の記録はなく、状態から承認を推測しない。
- 実行許可: 当初は引き継ぎに記録された `/skill:issue-to-pr #154` と `$superpowers:subagent-driven-development` により実装・公開を許可（マージを除く）。追加の `review-fix-planning #171` により、同スキルの完遂手順で選別・修正・検証・既存 PR への commit/push・状況投稿を行う。安全上の停止を報告した後、利用者が「再開してください」と明示したため、残る検証・自己レビュー・必要な修正・既存 PR への反映を再開した。内容承認と実行許可は区別する。
- 今回の実行許可: 利用者の `/skill:review-fix-planning #171` により、完遂の結論2（追加修正不要、検証・状況投稿・検証した head のマージ・関連 Issue 更新）まで許可されている。以下の「マージしない」は当初の実装・前回修正時の許可範囲であり、今回の最終判断は末尾の追加選別に記録する。
- Plan: `docs/superpowers/plans/2026-10-19-create-reso-world-issue154-review-verify.md`
- 参照: ボード Spec `2026-10-18-create-reso-world-issue116-review-automation-board-design.md` D-1〜D-24。移植元 `usaturn/agent-workspace@a47b2065fddad76b7475752fd0088af0733de204`。

## 意図と範囲

全レビュアーの候補をコミット済み HEAD と隔離した worktree で確認し、事実と未確認事項を `verified/` に残す。後続 #155/#156 が採否や修正を決めるための入力にする。確認担当は重大度・採否・修正設計・push 可否を決めない。

変更は `.agents/skills/review-verify/` と `.claude/skills/review-verify`、この Spec/Plan に限る。共有 helper、runner、雛形、他スキル、pi の設定は変更しない。文言照合テストや移植元固有の履歴は持ち込まない。

先行 #149/#152 は completed で close、PR #163/#164 は main に含まれる。指定 handoff の clean worktree と branch を再利用し、前セッションの予約解放を確認して新しい予約を取得した。前の pi の認証障害は現環境の通常委譲を妨げず、baseline 評価報告を回収した。

## インターフェース

### cycle

引数はレビューディレクトリの絶対パス、PR 番号、PR URL。親 checkout の `review_target.py review-dir ... --for-planning` を使い、既知でない対象には利用者が明示した絶対 `--code-root` を渡す。D-10 の `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<branch>/` を使い、旧配置は明示パスだけで読む。探索・clone はしない。resolver の実在する終了コードと対象制限に従う。

PR の head と base を固定し、各 Markdown と対応する構造化候補を照合する。JSON が不一致なら Markdown に戻り、parser が読めない範囲も手動で拾って coverage に残す。番号・URL の経路でも候補の `pr.repository` と `pr.number` を照合し、別 PR の候補は使わない。共有 helper は変更しない。

性質と位置が同じものだけ統合し、全出典・元の重大度を保持する。`confirmed` は挙動の実行証拠、静的主張ならコミット済み記述の根拠が必要。反証は `not_reproduced`、失敗・時間切れ・環境不足は `unverified` と `missing_checks`。別の入力、条件を述べた文書、PR 起因、未確認範囲も記録する。

出力は `review-findings/v2` の `verified/<HEAD先頭12文字>.json` と `.md`。形式は既存 `.agents/review-findings.md`、検査は既存 `review_findings.py` に従う。JSON は validate 成功後に置換する。票数を根拠にしない。

### fix_check

入口 JSON は厳密に次の 7 項目とする。

| 項目 | 値 |
| --- | --- |
| `repository` | from/to のある checkout の絶対パス |
| `from`, `to` | 実在するコミットの完全 SHA |
| `fix_ids` | 重複しない空でない参照の配列 |
| `fix_sections` | 採用変更と検証を含む Spec の Fix 節全文。空白のみを拒否 |
| `verified_file` | 入力となる確認済み一覧の絶対パス |
| `review_dir` | 保存先の絶対パス |

未入力の計画や未コミット内容は補わない。主張、全変更ファイル、文書候補の一覧を先に固定し、各件を証拠と照合する。未確認は coverage.remaining に残す。

`scripts/dispatch.py --request PATH --output-dir NEW_DIR [--template PATH] [--config PATH] [--assign ID|self]` と `accept --run-dir PATH` を移植する。設定の役割名は `fix-check`、出力 provenance の役割は `fix_check`。`workflows.fix.assignments.fix-check` の一次担当 1 件と明示 fallback のみ起動し、writes=false/result_shape=json を要求する。期限は最大1800秒、保存予約枠は300秒または期限の半分の短い方。

`self` は入力と prompt を返すだけで確認成功を表さない。外部結果は停止確認、登録済み checkout の監査、review_dir の起動前後の観測、payload/inventory の照合と helper の検査を通った場合だけ受け取る。入口リンク、監査不能、無断変更は拒否する。観測していない identity は unknown、指定モデルを実測モデルへ写さない。失敗を暗黙に self へ切り替えない。

出力は `<to先頭12文字>.fix-check.json` と `.fix-check.md`、同 stem の `.statement-candidates.json`。accept は JSON 2件だけ保存し、要約は呼び出し側が書く。CLI は正常/self で0、実行失敗・受け取り拒否で1、設定・入力不備で2。accept の保存先欠落・dispatch.json 読み取り不備も2。

## 決定記録

| ID | 選択した案 | 検討した別案・理由 | 根拠と誤りの場合の影響 |
| --- | --- | --- | --- |
| D-1 | 移植元の dispatcher と振る舞いを保ち、環境依存箇所だけ変更 | 作り直しは監査・受け取り条件を失うおそれ | 利用者の移植指示。誤りなら互換性の修正が必要 |
| D-2 | 短い SKILL.md から cycle/fix_check の参照文書へ分ける | 全文一括は入口に無関係な情報が多い | skill-creator の段階的開示。誤りなら読み漏れを評価で検出し修正 |
| D-3 | root の uv 環境、既存 resolver、明示 checkout を使う | tools/devenv、Registry、clone は移植先の規約外 | #116 の利用者決定。別 owner 一律拒否など移植元の制限を持ち込まない |
| D-4 | fix workflow は利用者設定か一時 config で供給 | 共有雛形の追加は #155 の所有範囲 | #154 の変更範囲。未設定では入力・設定エラーにし、成功扱いしない |
| D-5 | upstream の Python 実行テストを選別移植し、無し/あり評価を別に行う | 文面一致テストでは行動を保証できない | AGENTS.md。baseline は採否と push 判断まで行い、専用 verdict/成果物形式を持たなかった |

## 検証と受け入れ

- 一意の fixture git repo と D-10 のレビューディレクトリから v2 の cycle JSON と要約を作り validate を通す。採否・重大度変更を出さない。
- 同じ pressure scenario をスキル無し/ありで比較する。未入力の Fix 節を補完せず、依存不足を unverified にし、不一致候補を黙って捨てず、push 判断を引き受けない。
- dispatcher を fake adapter で実行し、self/外部、完全入力、監査・停止確認、保存先変更、inventory、実測 identity、失敗を確認する。本物の CLI や資格情報を fixture にしない。
- `uv run pytest .agents/skills/review-verify`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`。スキル構文と参照先を検査する。
- push 前に親 checkout の秘密情報検査を実行し、その SHA を push。PR は同 branch から1件、main 向け。Actions は無効のため CI 確認不要。マージしない。

## 実行の証拠

実行許可の範囲で2 Taskを実装し、それぞれ独立レビューと1回の修正・差分再レビューを行った。旧配置への新規出力と、外部payloadの主要skill取り違えを修正した。cycle fixture、無し/あり判断評価、初回全体2000件、主要skill照合修正後の集中112件、Dev Container 33本、配置・構造の検査を実施。詳細と最終の回帰・公開結果は関連Planの実行記録に残す。当初の文書には内容承認がなくdraftを維持した。その後のレビュー修正と現在の状態は下記に区別して記録する。

最終コード `5d3dc18` では、固定済み入力PRと外部payloadのPRも保存前に照合する。全体2023件と集中131件が成功し、当初の独立レビューと修正差分再レビューでは未解決の指摘はなかった。その後の PR #171 のレビュー選別は以下に記録する。当初の公開先・所要時間・実行範囲はPlanの最終記録を参照する。

## PR #171 のレビュー選別と修正

対象 repository は `usaturn/create-reso-world`、PR #171、head branch は `feat/issue-154-review-verify`。入力は親 checkout の `reviews/usaturn/create-reso-world/#171-feat-issue-154-review-verify/` の4ファイルすべて。全ファイルの対象 HEAD は `513352e7825f8e2d07a2983c7ef3dd623a47d9c3`（冒頭の短縮表記を解決）で、現在の PR head と一致し、祖先確認も成功した。clean な既存 worktree `/workspaces/reso-world/.worktrees/issue-154-review-verify` を専用領域として再利用する。既存の本 Spec と Plan が Issue #154 の定義元であり、同テーマの文書を増やさず本 Spec を更新する。

### 全指摘の分類

区分は入力時点の分類。対応する4件（独立した修正は3件）、対応しない7件、解消済み0件。通常の指摘9件に加え、未確認候補・検証範囲の留保2件も落とさず記録する。

| ID | 入力・内容 | 分類 | 現行 HEAD で確認した根拠・判断 |
| --- | --- | --- | --- |
| S-L1 | SWE-2-Max L-1: 不正 batch / I/O 例外の traceback | 対応しない | 不正batchや通常ファイルの保存先はKeyError/FileExistsErrorで停止し成果物を公開しないことを再現。書込途中のI/O失敗は別で、sidecarだけ置換され得る既存の制限を文書が明示している。診断形式の改善は採用しない |
| S-I1 | SWE-2-Max I-1: 保存先祖先の symlink | 対応する（F1、G-M1 と同原因） | `check_review_directories` は末端2階層のみ。親リンクがある正常 payload で accept が成功し、リンク先に JSON 2件を書いた。意図した保存先外への操作に当たる（a） |
| C-L1 | claude L-1: base の FETCH_HEAD 依存 | 対応する（F3） | 同じ checkout の fetch が間に入ると merge-base が PR head 自身になった。並行レビューの実在する利用で base と PR 起因の判定が誤る（a/b） |
| C-I1 | claude I-1: 保存先リンク拒否の分類が ValueError | 対応しない | リンク拒否は動作し、起動も書き込みもしない。failure_category の戻り値が型名だけになることを再現。診断の具体性のみ |
| C-I2 | claude I-2: D-10 と verified.pr の照合を dispatcher でも行うか | 対応しない | fix-check.md:19 が resolve 結果と入力 review_dir の一致を起動前に確認する責務を呼び出し側へ明記。dispatcher に別のパスを直接渡せば保存するが、明記された入力条件に反する場合の検査追加は設計の是非 |
| D-L1 | DeepSeek L-1: verified/ 作成時点の記載漏れ | 対応しない | dispatch 後に verified/ を作ると拒否するが、作らなければ accept 自身が作成して成功することを対照実行。既存の全エントリ固定の仕様と整合し、記載手順の実行に作成操作を足す必要はない |
| D-I1 | DeepSeek I-1: verified が通常ファイルのとき traceback | 対応しない | S-L1 と同じ。実行で FileExistsError と全既存エントリの不変を確認。通常ファイルを保存ディレクトリとして使う異常構成の診断形式のみ |
| G-M1 | gpt M-1: 起動後の保存先親リンクへの差し替え | 対応する（F1） | 正常 dispatch 後に reviews を rename し元の名前を symlink 化。snapshot は等しいのに accept が成功し、移動先に JSON 2件を書いた。事前確認だけでは防げない誤対象操作（a） |
| G-M2 | gpt M-2: 評価 fixture の Git 環境変数継承 | 対応する（F2） | 別の fake repository の index を GIT_INDEX_FILE で渡し文書の Python block 全体を実行。終了1でも index が変わり README.md/checkbox.py が追加された。手順実行で他 repository を変更する（a） |
| C-U1 | claude 未確認候補: 将来の loop/ 書き込みと snapshot | 対応しない | 現行 HEAD に #156 の loop 実装は無い。fix-check.md は全エントリ固定を明記。後続接続時に書き込み時点を決める設計事項で、この PR の現行挙動の欠陥ではない |
| S-U1 | SWE 未確認範囲: 実 AI CLI の E2E | 対応しない | 未実施であり成功としない。PR 自体が対象外と明記し fake adapter で subprocess/runner/保存を検証する受け入れ範囲。特定 CLI の不具合の根拠ではない |

確認は元 HEAD の隔離 worktree と一意の `/tmp/review-fix-planning.XXXXXX/` 内の fake repository/adapter で行い、9つの再現・対照が 2.47 秒ですべて期待どおりだった。変更ファイル10件の全文・関連 helper の fetch/resolve、v2検査、runner呼び出しとテストを本体と読み取り専用調査担当で確認。再現用 worktree と親領域は選別後に削除した。他の作業中 worktree の未コミット内容は参照しない。

### 守る条件と影響経路

| Fix / 守る条件 | 経路 | 判定 | 確かめる方法 |
| --- | --- | --- | --- |
| F1: 保存先本体・verified とその祖先にリンクがあれば、外部起動や成果物保存を行わない | dispatch の check_review_directories → snapshot_review | 修正する | 親リンクの深さを変えた単一異常の負例、起動なし・管理する全状態不変を比較 |
| F1 | 停止確認後の review_changes → snapshot_review | 修正する | 起動後に親リンクへ置換し、監査が無変更を返さないことを確認。停止未確認時の読取禁止は既存テストで保持 |
| F1 | accept の snapshot・保存直前 | 修正する | 正常 payload、同一内容のリンク先で拒否し、リンク先・過去成果物・run/設定/認証・一時生成物を含む状態不変を比較 |
| F1 | 直接 review_dir/verified リンク、通常の保存成功 | 既存の拒否・正常挙動を保つ | 既存131件と追加回帰テスト。保存先の同一性も観測し、同内容の別ディレクトリへの置換を無変更と扱わない |
| F1 | cycle の手動保存 | 既に満たす | SKILL.md と cycle.md が親リンクを含む事前確認を要求。dispatcher に共通ガードを設けるが sandbox は保証しない |
| F2: fixture の全 subprocess は利用者の Git 対象・設定・hook 環境を継承せず、一意の fixture 領域だけを変更する | validation.md の env → init/add/commit/rev-parse/show/worktree/helper 全呼出し | 修正する | 別 fake repository を指す GIT_INDEX_FILE 等を一度に1つ渡し、HEAD・index・内容・mode・リンク・設定・hook呼出しの前後比較 |
| F2 | test_dispatch.py の isolated_git_environment | 既に満たす | GIT_* / BASH_ENV / ENV を除去し HOME/XDG と Git設定を分離している。既存テストを実行 |
| F3: cycle の base は同時 fetch の対象に左右されず固定する | cycle.md の base取得 → BASE → v2.base / pr_relation | 修正する | 一意の ref に --no-write-fetch-head で取得、SHA固定後に別fetchを挟み期待するmerge-baseと比較。手順文書のため文言照合テストは追加しない |
| F3 | review_target.fetch_pull_head | 既に満たす | 専用PR refと --no-write-fetch-head を実装。関連処理を精読 |

### 方針・再発の確認

- F1 は祖先を含む同じガードを dispatch・snapshot・accept で使用し、保存直前にも確認する。snapshot に保存先ディレクトリの同一性を含め、同じ内容の別実体への差し替えも拒否する。単に呼び出し側の事前確認へ戻す案は、起動後の変更を見逃すため不採用。全ファイル操作を sandbox 化する案はこの PR の観測・受け取りという保証を越えるため採らない。検査と実際の書き込みの間に行われる悪意ある同時変更を防ぐ sandbox ではないことを維持する。
- F2 は既存テストの隔離方針に合わせ、env を生成する1か所で全 subprocess に適用する。個々の git コマンドの `-C` 追加だけでは環境指定が優先されるため不採用。文書内コードを実行する回帰テストは追加するが文言は検査しない。
- F3 はセッション固有 ref を一時領域から命名し、取得直後に SHA へ解決して以後は SHA を使う。共有 remote-tracking ref だけに頼る案では同一 base の更新と競合し得るため採らない。用済みの専用 ref を削除する。文書手順は実Gitのローカルremoteで検証し、文書本文を固定するテストは作らない。
- 以前の修正 `9bb52c2` は旧配置への出力、`1a2ce01` は主要skill、`5d3dc18` は PR の照合。F1 のガードは `4f83ddc` の追加時から変わっておらず、F2/F3 も以前のレビュー修正で触っていない。同じ条件の2回目・修正が生んだ回帰には当たらない。自己レビューで再発した場合は設計の見直しへ切り替える。

### 自己レビューでの再発と守る条件の設計（F1 / SR-C1）

3観点の自己レビューを1回実施した。反証担当が、inventory再生成・文書検証の間にリンクではない別rootへ置換すると、保存直前のリンクガードだけでは保存を拒否できないと指摘した。controllerは検査段階2箇所×変更2種類（root複製、既存成果物の更新）の4ケースで accept が終了0となり既存成果物を置換する誤動作を再現した（4 failed、既存リンク対照2 passed、2.02秒）。実在する同じPRの並行更新・ディレクトリ移動で到達する誤対象操作であり SR-C1 を「対応する（a）」とした。この回に直したF1の検査漏れなので、きっかけ3「自己レビューでの再発」に当たる。自己レビュー後の修正は再レビューしない。

**守る条件:** dispatchで観測した保存先本体の同一性と配下の状態を、停止確認後の受領処理開始時と、inventory/文書検査をすべて終えた保存直前の両方で確認する。リンク・監査不能・rootのdev/ino変更・エントリの追加削除/種類/mode/内容/リンク先変更があれば、一時出力も作らず拒否する。他者の変更を復元・削除せず、その時点の全管理状態を残す。正常・拒否・未停止・入力不備の順序を崩さない。最終の観測より後の悪意ある競合はsandboxの保証外だが、最終の観測より前に完了した変更をこの例外へ含めない。

以前の修正で不足した理由は、初回検査はsnapshot全体なのに最終検査だけリンク判定という別の条件になっていたこと。`4f83ddc`以来のsnapshotの仕組みへ今回追加したroot同一性も、最終段階には適用されていなかった。したがって最終段階へroot条件だけを足す点の修正は選ばない。

| 経路・停止位置 | 変更前の挙動 | 判定 | 確かめるassertion |
| --- | --- | --- | --- |
| dispatch起動前: check_review_directories / snapshot_review | 祖先リンクを拒否し、rootと配下の状態を固定 | 既に満たす | 単一リンク異常でadapter未起動、tmp_path全体のパス/bytes/mode/リンク不変 |
| dispatchの停止未確認 | 保存先を再読取しない | 既に満たす | snapshot呼出しが起動前の1回のみ、review_changes=null |
| dispatchの停止確認後 | snapshotがリンク・root同一性・配下全体を観測 | 既に満たす | 起動中の親差替えを無変更とせず、accept拒否時も管理状態不変 |
| accept: check_batch / request・snapshotの入力検査 | 未停止・不正入力を保存先再検査より先に拒否 | 既に満たす | 既存の未停止・不正入力テスト、成果物なし |
| accept: inventory検査より前 | 全snapshot照合、その後別のリンク検査 | 共通処理へ集約 | require_unchanged_reviewによる全比較、異常前後の管理状態一致 |
| accept: inventory再生成中・文書検証中に変更 | 最後はリンクのみ。通常root差替えや他者の成果物更新を許す | 修正する | 両検査段階×祖先リンク/root差替え/成果物更新の6負例すべて拒否、注入直後と拒否後の全管理状態一致 |
| accept: 全検査後から最初のmkdir前 | リンクガードのみ | 共通処理へ集約 | 起動時snapshotと照合する同じrequire_unchanged_reviewを呼び、削除対照で6負例がすべて失敗 |
| accept: mkdir/mkdtemp/JSON2件書込/sidecar置換/本体置換/cleanup | 最終検査後にのみ実行、2件同時の一括置換は保証しない | 挙動を保つ | 正常保存と既存成果物の正常置換を既存テストで検査。I/O障害でsidecarだけ置換され得る既存の制限は維持 |
| 最終観測後の悪意ある同時変更 | sandboxではなく防止を保証しない | 対象外 | 文書とPR説明で保証境界を明記 |

比較した案: (1)最終リンクガードへinode判定だけ足す案は同じ保存先の成果物更新を取りこぼすため不採用。(2)同じ全snapshot照合を `require_unchanged_review` へまとめ、acceptの検査前後から呼ぶ案を採用。(3)PRの保証を起動後の通常root変更を許すものへ狭める案は、並行作業の成果物を無断で置換するので不採用。別PRへの分割は行わない。

全PR担当・検出力担当は致命的な追加指摘なし。ただし旧snapshot形式の未受領runの案内を両担当が推奨したため、SR-P1/SR-T1をそれぞれ「対応しない」と記録する（既知制約の説明改善のみ）。旧runの再dispatchが必要なことは既知の実在する制約なので、本SpecとPR説明の既知制限へ記録し、互換補完や新しい文言テストは作らない。

集計: 元入力は対応する4 / 対応しない7 / 解消済み0、自己レビューは対応する1 / 対応しない2 / 解消済み0、合計は対応する5 / 対応しない9 / 解消済み0。独立した修正は引き続きF1/F2/F3の3件。最初の2つのレビュー委譲はscope/template・diff不足でNEEDS_CONTEXTとなり、コードレビューは未着手だったためレビュー回数に数えない。実際に3観点の読取りを行ったのはその後の1回だけ。

### 実行・検証のタスク

- [x] 入力4件・HEAD・context・clean worktree・全指摘と全変更内容の確認、隔離再現と片付け。
- [x] 分類・影響経路・方針決定、既存 Spec の選択と更新。
- [x] F1: 拒否時の全状態比較を実行する回帰を先にREDとし、祖先ガードとroot同一性を実装。自己レビューの再発には共通の全snapshot照合で対応した。安全条件・誤動作の再発防止として実行テストが必要。
- [x] F2: 文書コードを敵対的Git環境で実行する回帰を先にREDとし、全subprocessの環境を隔離。利用者所有repositoryと設定を守るため実行テストが必要。文言は照合しない。
- [x] F3: 文書のfetch手順を修正し、実Gitの競合fetchと2種類の失敗・後片付けを実行。文言固定テストは不要。
- [x] ガードを1つずつ外した最終版の隔離対照で9パターン・延べ40負例がすべて失敗することを確認し、worktreeと親領域を削除。
- [x] 最後の修正後に関連テスト153件、指定スキル検証774件、Dev Container33本、配置・構造・参照・差分検査。
- [x] 反証・PR全体・検出力の3観点を1回だけ自己レビューし、全指摘を判定。SR-C1の修正後は再検証のみで再レビューしない。
- [x] 結果・件数・保証・既知制限を確定し、completedとした。以降はcontext/APIの再確認、1回のcommit、秘密情報検査付きpush、状況コメントを実行する。公開操作の結果は本SpecではなくPRコメントと完了報告へ記録する。

### 最終の検証結果

| 検証 | 結果 |
| --- | --- |
| F1 初回の実行回帰 | 7件の期待したREDを観測し、修正後のdispatcher138件成功 |
| F2 文書のPython block全体実行 | 修正前は汚染10件失敗・clean対照1件成功、修正後は11件すべて成功 |
| SR-C1 検査中の差替え・更新 | controllerが4 failed / 2 passedのREDを観測。共通処理へ修正後は6 passed / 136 deselected、1.87秒 |
| 最後の修正後のreview-verify全件 | `uv run pytest .agents/skills/review-verify -q`: 153 passed、34.63秒 |
| 最後の修正後の指定スキル検証 | `uv run pytest tests/skills .agents/skills -q`: **774 passed、228.63秒** |
| 最後の修正後の環境検証 | `bash .devcontainer/run-tests.bash`: **33本PASS**。`bash scripts/check-layout.sh`: PASS |
| F3の実Git | 競合fetchでも固定baseを返して終了0、存在しないbase・無効headは終了1/1。全ケースで専用refと一時領域を削除 |
| 構造・静的検査 | dispatcherとテスト4ファイルのAST、evals JSON、15参照先と相対symlink、差分空白検査に成功 |
| skill-efficiency-check | 構造上の問題0件。既存の複数行descriptionを2文字と認識して警告1件を出す。実際のfrontmatter/packagingは指定スキル検証で成功。警告回避のための文言変更はしない |

最終の安全境界の対照は、修正済み内容を元HEADの別の隔離worktreeへ写し、ガード1箇所ずつを無効にして実行した。祖先6/6、snapshot4/4、保存直前の共通照合6/6、root同一性3/3、監査例外処理2/2、Git選択環境5/5、shell起動環境2/2、HOME/XDG設定2/2、共通環境分離全体10/10の期待した失敗を観測した（合計40、pytestのsetup errorは0）。正常版では同じ負例を含む153件・774件が成功。Git global-configは環境除去と設定上書きの二重防御なので、片方だけの無効化で常に失敗するとは主張しない。初回の対照でshell負例の-k指定を誤り1件しか選ばなかったため修正し、global-configの冗長性も確認して最終の集合を確定した。無条件に再試行して成功を集めたものではない。

失敗時の比較は、テスト対象のsnapshot実装を流用しないlstat/bytes/readlinkによる独立観測で、tmp_path/偽host配下の全パスの有無・種類・mode・bytes・リンク先を比較した。旧成果物2件、別名へ移動した保存先、参照先、repositoryのHEAD/ref/index/追跡・staged内容、run成果物、偽HOME/config、hook/署名コマンドのmarkerを含む。期待値は異常を入れた直後・処理呼出し前の状態から取り、拒否後の状態と比較する。入力異常・無断変更の拒否を、書込途中のI/O障害の復元保証とは混同しない。

再開後の最初の指定スキル検証では、変更外の `monitoring-long-tasks/tests/test_task_watch_process.py::test_undeclared_stop_never_signals` の時間依存assertionが1件失敗した（769 passed）。同一ソースのbase `b5dc45af02606acdf52c75a8a66d004f97d1b4bc` と修正側の単体再実行は各1 passed。その後の全指定検証は自己レビュー前770 passed、最後の修正後774 passedで成功した。このPRでは当該監視コード・テストを変更していない。自己レビュー前の全体2041 passedは履歴として保持するが、最後の修正後に全体を再実行した結果としては扱わない。

### 結論と残る保証境界

**結論1: 修正して既存PRへpushする。** F1/F2/F3と自己レビューのSR-C1を修正し、最後の修正後の規定検証を完了した。分類は合計で対応する5 / 対応しない9 / 解消済み0、独立したFixは3件。反証・PR全体・検出力の3観点レビューは1回のみで、SR-C1の修正は再レビューしていない。形式・診断だけの指摘へ追加実装を広げていない。

旧snapshot形式（rootのdev/inoなし）でdispatch済み・未受領のrunは新helperで再dispatchが必要。D-10/PRの対応確認は文書化済みの呼び出し側の責務。dispatch後は受領まで保存先へ新しいエントリ・要約等を書かず、作成が必要なら起動前に行うかacceptへ任せる。snapshotは観測であってsandboxではなく、最終検査後の悪意ある同時変更・変更の巻戻し・JSON2件同時の一括置換は保証しない。実AI CLIのE2Eは未実施で成功としない。これらの実在する制約はPR説明にも記録する。

### 中断・再開と所要時間

初回は実装担当が環境確認で資格情報相当の値をツール出力へ誤表示したと報告したため、安全の失敗として公開前に停止し、未コミットの実装とSpecを保全した。値は文書・handoffへ転記せず再収集もしない。外部公開や実サービスでの利用は報告されていないが、harnessの当該出力には残る。利用者へ必要な確認・更新を案内した後、「再開してください」と明示されたため残作業を再開した。資格情報の更新作業を代行・検証したとは主張しない。再開後の担当には環境の一括列挙を禁止し、新たな同種の事故は報告されていない。

レビュー修正の着手は2026-10-18T18:11頃UTC、初回の停止記録と引き継ぎは18:38頃、再開は18:44頃、最終検証と記録確定は19:31頃。能動時間は計約74分（初回約27分＋再開後約47分、利用者待ち約6分を除外）。主な内訳は初期照合・再現・方針約8分、初回実装担当約14分、安全停止と引き継ぎ約5分、再開の照合・対照と初期検証約20分、3観点レビューと起動条件の調整約12分、再発の再現・設計見直しと修正約8分、最終回帰と記録約7分。並行した最後のスキル・環境検証は約5分54秒で、合算しない。既存worktreeは借用したものなのでこの作業の片付け対象にしない。初回の引き継ぎは親checkoutの `tmp/docs_draft/claude_handoffs/20261018T1835-pr171-review-fix-safety-stop.handoff.md` と対のJSONに残し、完了報告で状態を更新する。

## 現行 HEAD 8ca547b の追加選別（2026-10-18）

### 対象と実行許可

対象は `usaturn/create-reso-world` PR #171、`feat/issue-154-review-verify`、検証 HEAD は `8ca547b4ab4c5556216bf1640468a537e9c9c44d`。利用者が `review-fix-planning` と `#171` を指定したため、承認待ちの計画ではなく完遂として実行する。本 Spec が同じテーマの現行文書であり、新規 Spec/Plan は作らない。

入力は `/workspaces/reso-world/reviews/usaturn/create-reso-world/#171-feat-issue-154-review-verify/` の全5ファイル。SWE-2-Max.md、claude-opus-5-5.md、gpt-6.1-sol.md、opencode-go-deepseek-v4.1-flash.md の対象 HEAD は `8ca547b4ab4c`、commandcode-deepseek-deepseek-v4.1-flash.md は `513352e7825f`。両 SHA とも検証 HEAD の祖先であることを確認した。4ファイルの以前のレビュー履歴も読み、元の指摘と更新後の判定を区別した。

親 checkout と同じ Git repository に属する既存の `/workspaces/reso-world/.worktrees/issue-154-review-verify` は clean、HEAD 一致を確認して借用した。共通 context に `PARENT_ROOT`・`CODE_ROOT`・`DOC_ROOT`・文書/head branch と head repository を明示した。2件の読み取り専用調査と本体で変更12ファイルの全文、関連 resolver/schema/runner とテストを確認した。子はテストを実行せず、挙動の根拠は本体が固定 HEAD の隔離 worktree で実行した。別の作業中 worktree の内容は読んでいない。

### 今回の全指摘と分類

**解消済み4 / 対応する0 / 対応しない11、合計15件。** 通常の指摘13件に未確認候補2件を加えた数。レビュー側の Resolved 表記ではなく、現在の挙動で分類する。以下は今回の入力だけの集計で、前回の14件の履歴を合算しない。

| ID | 出典・内容 | 分類 | 現行 HEAD の根拠・判断 |
| --- | --- | --- | --- |
| S-L1 | SWE L-1: 不正 batch / 公開時 OSError の traceback | 対応しない | `dispatch.py:437,455,537-546,558-561`。不正 batch は CLI の終了1・KeyError、全既存状態不変を再現。I/O途中でsidecarだけ置換される可能性は既知の非保証。通常の生成済みbatchの主要処理は止まらず、診断形式や既知のI/O制限を拡張しない |
| S-I1 | SWE I-1: 保存先祖先のリンク未検査 | 解消済み | `8ca547b` の `dispatch.py:205-214` は全祖先を検査。acceptの検査前後も同じsnapshot照合。実行回帰を含む774件成功 |
| S-U1 | SWE 未確認候補: 同内容の配下ディレクトリ差替え・マウント点 | 対応しない | `dispatch.py:226-229` はroot以外のdev/inoを保証しない。同じlexical path・種類・mode・内容なら通常の書込先は変わらない。特権によるmount変更まで阻止するsandboxは保証外で、サポート経路での誤対象操作の根拠ではない |
| C-L2 | claude L-2: review_dir欠落でdispatch成功・accept不能 | 対応しない | 不在rootでdispatchは0/success/変更なし、acceptは2、後からmkdirしても1を再現。rootを起動前に準備し再dispatchすると正常保存。未準備の初回移行先で1回の外部実行をやり直す制約で、誤った一覧の公開・既存データ破損はなく、準備済み保存先の主要経路は動作する。事前拒否を増やす仕様変更は採らず、PRに条件と回避手順を記録する |
| C-I1 | claude I-1: リンク拒否の分類がValueErrorのみ | 対応しない | リンク入口で終了2、adapter未起動、管理状態不変、stderrがValueErrorになることを再現。拒否は動作し、診断の具体性だけの問題 |
| C-L1 | claude L-1: base取得のFETCH_HEAD依存 | 解消済み | `8ca547b` の `cycle.md:48-67` は専用refと完全SHAを使用。bash/zshで競合fetch後も正しいbase、失敗2種と全後片付けを実行確認 |
| C-I2 | claude I-2: D-10/PR照合をdispatcher自身も行うか | 対応しない | `fix-check.md:19` がresolve結果との照合を呼出側の責務と明記し、実装は変わっていない。レビュー側は設計確定としてResolvedだが、同じ入力をdispatcher単体へ渡す挙動の消滅ではないため設計の是非として分類 |
| C-U1 | claude 未確認候補: 将来のloop/書込とsnapshotの衝突 | 対応しない | 起動後のloop/state.json追加はaccept終了1、全状態不変を再現。全エントリ固定は明記済み。検証HEADに#156のloop実装はなく、後続の書込順の設計事項。無変更として誤受領しない |
| D-L1 | commandcode L-1: 保存先の起動前作成手順なし | 対応しない | root欠落部分はC-L2と同じ制約。rootがあればverified/はaccept自身が作って正常終了する。rootとverified/を混同せず、必要なroot準備は起動前、追加作成した後は再dispatchという回避手順をPRに記録 |
| D-I1 | commandcode I-1: verifiedが通常ファイルだとtraceback | 対応しない | 正常payloadでCLI終了1・FileExistsErrorを再現。通常ファイルを含む全既存状態が不変。出力ディレクトリとして不適切な保存先の診断形式のみ |
| G-M1 | gpt M-1: 保存先親リンクへの起動後差替え | 解消済み | `8ca547b` の `dispatch.py:205-214,511,535` は起動前・停止後・受領検査前後に同じ全snapshot条件を適用。祖先差替え・同内容別root・検査中更新の実行回帰成功 |
| G-M2 | gpt M-2: 評価fixtureのGit環境継承 | 解消済み | `8ca547b` の `validation.md:61-72` が全subprocessの環境を分離。コード全体を実行し偽hostの状態を比べる11件を含む774件成功 |
| O-L1 | opencode L-1: allowed-tools省略 | 対応しない | SKILL frontmatterはname/descriptionだけ。通常Claude起動時の許可確認が増えるメタデータの問題で、権限の無断拡張や主要処理の誤動作ではない。文書・スキルの任意メタデータを固定するテストは追加しない |
| O-I1 | opencode I-1: CLAIMS_JSONは本文でなくパス | 対応しない | `review_findings.py` の--claimsはPathで、直前の文書はclaims.jsonを説明。本文を渡すと終了66・出力なし、ファイルパスでは成功する対照を再現。変数名の明確さの改善で、記載例自体が本文値を指定しているわけではない |
| O-I2 | opencode I-2: Spec completed / Plan draft | 対応しない | 文書の状態メタデータの不揃いで機能・安全に影響しない。Planは内容未承認のdraftを維持した理由も末尾に記録。今回のSpecのcompletedも承認と区別する |

独立した指摘でないテスト提案は上の該当IDに含む。opencodeの補足にあるdispatch記録の不備・snapshot型の直接固定テストの不足も確認したが、実害の欠陥ではないため追加しない。実AI CLIのE2E・特権mount操作は受け入れの範囲外であり、実行成功とみなさない。前回の停止記録にある資格情報は再収集していない。

### 方針・再発の確認

**結論2: 追加修正不要として、最終の状況コメント後に検証したheadをマージする。** 対応する項目は0件なので、修正対象の影響経路表・設計見直し・ガード削除対照・修正後の自己レビューは今回不要。子による調査は選別前の読取りで、修正後の自己レビューではない。前回F1/F2/F3/SR-C1の解消を現行コードと実行回帰で確認した。C-L2はroot準備に関する別の入力条件であり、前回の保存先同一性ガードの再発ではない。

比較した案は、(1)入力存在ガード・診断形式・任意メタデータを追加する、(2)採用基準どおり追加実装をせず、実在する制約を条件・回避手順付きでPR説明へ残す、の2つ。主要な正常経路とfail-closedの境界が維持され、追加対象が致命的条件を満たさないため(2)を選ぶ。旧配置から初めてD-10へ出力する際は、PR照合・リンク/書込可否の確認後、dispatch前にD-10のrootを準備する。verified/の作成はacceptへ任せられる。起動後にroot等を作った場合は新たにdispatchする。

### 今回実行した検証と結果

| 対象 | 検証 | 結果 |
| --- | --- | --- |
| 固定HEADの隔離worktree | 一時probe6件: 欠落root→dispatch/accept→mkdir後拒否→準備後成功、不正batch、通常ファイルverified、リンクの診断・未起動、claims本文/パスの対照、loop書込後拒否 | 6 passed / 2.45秒。拒否時はtmp_path配下の全パス・種類・mode・bytes・リンクを処理前後で比較 |
| 固定HEADのbase手順 | 文書のBASEスニペットを抽出し、ローカルGit remoteでbash/zsh各3ケース。専用fetch直後に別fetchでFETCH_HEADを上書き | 計6ケース成功。正常は期待base・終了0、無いbase/無効headは終了1。全ケースで専用ref・一時領域なし |
| PRのcleanな専用worktree | `uv run --locked python -B -m pytest tests/skills .agents/skills -q` | 774 passed / 226.85秒 |
| 同上 | `bash .devcontainer/run-tests.bash` / `bash scripts/check-layout.sh` | 33本PASS / PASS、終了0 |
| head＋現行baseの一時merge | base `b5dc45af02606acdf52c75a8a66d004f97d1b4bc` は分岐点 `a024a22626d4ff6daa46e92aa7cb8aae081aa7ac` より先。隔離worktreeで `git merge --no-commit --no-ff <base>` | 競合なし。このmergeはpushしない |
| 一時merge状態 | 同じ指定pytest・Dev Container・配置検査 | 774 passed / 228.42秒、33本PASS、配置PASS、すべて終了0 |
| 固定HEADの構造 | Python4ファイルAST、評価JSON、15ローカル参照先、相対symlink、`git diff --check origin/main...HEAD` | PASS |

新しい永続テストは作らない。今回はコード・挙動・設定を変えず、記録だけの更新であるため、実行probe・既存テスト・構造検査・差分確認を根拠とする。リポジトリ全体の追加一括pytestや関係のないワールドは実行しない。privateのcreate-reso-worldはActions無効のためCI確認は不要。PRはopen・非draftで、許可されたマージ対象であることをAPIで確認した。

再現用のGit worktreeを登録から外してから親の一意な一時領域を削除した。借用した専用worktreeは削除しない。公開直前にAPI/contextを再確認し、検証HEADを親とする本Specだけの1コミットを秘密情報検査付きでfast-forward pushする。検証中にheadが変わればマージせず停止する。push・コメント・merge・Issue更新の結果は、本Specへ追記コミットせずPR状況コメントと完了報告へ記録する。

### 今回のタスクと所要時間

- [x] 5入力・両世代HEAD・context・cleanな既存専用worktree・変更全文を確認。
- [x] 全指摘と関連処理を調査、隔離probeと既存回帰で分類。テスト追加は不要（記録のみ）。
- [x] 追加修正0件の方針を確定、PRに残す制約と回避方法を整理。
- [x] PR headと最新baseの一時mergeで同じ規定検証を完了、再現領域を片付け。
- [x] 同じテーマの本Specを更新しcompleted、件数・保証・根拠を確定。
- [ ] 公開直前のHEAD/context確認、本Specだけのcommit・検査付きpush、最終状況コメント、head一致条件付きmerge、関連Issue更新（外部操作の結果は状況コメントと完了報告へ）。

着手は2026-10-18T20:03:22Z。20:28頃まで約25分。主要内訳は照合・全入力読取り約3分、独立調査・本体確認約5分、再現と方針・base probe約6分、head/baseの並列検証約9分31秒（20:17:16〜20:26:47）、構造検査・片付け約1分。子に時計がないため子の推測時間は採用しない。以後の記録・公開の時間を含む最終の所要時間は完了報告に記す。
