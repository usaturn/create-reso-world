# PR #16 文書ライフサイクルの根本修正設計・対応計画

- 日付: 2026-10-04 JST
- 状態: completed（提示内容の承認と実行許可に基づく実装・レビュー・受入検証が完了。証跡は10節。PRのマージ状態とは別）
- 内容承認・実行許可の指示: 本書提示後のユーザ指示「進めてください。プランを作成したら、そのまま実装を開始してください」。今回はhandoffを指定した「作業を続行して」により再開
- 承認内容の文書コミット: `79330776e52a4b077c8a596b035ab8f48a242123`（提示・承認された内容を変更せず保存した初版。後続の状態記録とは別）
- 詳細Plan: `docs/superpowers/plans/2026-10-04-pr16-document-lifecycle-root-cause.md`。作成直後の実行は明示指示済み。未提示のPlan本文をユーザがレビュー承認したとは記録しない
- brainstorming 経路: architectural
- 文書管理・変更対象: `usaturn/create-reso-world`
- 対象 PR: https://github.com/usaturn/create-reso-world/pull/16
- 反映先: 既存 `docs/superpowers-document-lifecycle`。main・別の修正用PRへ実装を反映しない
- 検証 HEAD: `b441c3b79b91f2945e60f9b948fd52dd77fcb02f`
- base: `9699e94a56798a5d148d464825b57e426c155695`
- 入力: `reviews/#16-docs-superpowers-document-lifecycle/` の全5ファイル
- 調査報告: `docs_draft/2026-10-04-create-reso-world-pr16-root-cause-investigation.md`（ローカル専用）
- 本書の保存状態: 正本と実装修正は既存PR #16へ公開済み。検証した公開版は `0f6ff4619e32dbf27b6204e2a7e010498c319b8c`。この完了記録を含む最終復元版と公開確認はPRコメント・handoffに記録する
- 関連する既存設計: `docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md`

## 1. 意図と成功条件

レビュー指摘をもう一度選別して少数の箇所だけ直すのではなく、修正のたびに隣接経路の欠落が出る原因を除去する。文書保存の目的は維持し、対象repo、作業checkout、文書版、実行許可、公開結果を混同しない運用にする。

「今後の指摘がゼロになる」とは保証しない。完了とは、既知の再現ケースが解消し、仕様と許可範囲が一致し、経路横断の検証が通り、既知の非対応事項を解消済みと誤表示しないことを指す。

調査時は設計までで停止した。その後の明示承認により詳細Planを作成し、既存PRの隔離worktreeで実装を開始する。以下は承認済みの設計と受入条件であり、実施結果はPlanと完了記録で区別する。

## 2. 根本原因

### 2.1 安全条件が分岐ごとに後付けされている

`20db57f` は外部 `CODE_ROOT` のlinked拒否、`333f4fb` は同一repoの `TOPLEVEL` のlinked拒否、`530cfab` はforkのlinked拒否・zsh・SSH URLを追加した。同じ「fetch前にhelperの要件を満たす」という条件を、独立した分岐へ逐次追加している。

現行resolverはcwdのoriginを文書管理repoの固定識別子ではなく分岐の基準に使う。そのため外部cwdではCODE_ROOTの明示・remote件数検査を迂回する。URL正規化もresolverとcopy helperで二重化されている。

根拠: `.agents/skills/pr-review/SKILL.md:105–181`、`scripts/superpowers-review-copy.sh:21–58`。

### 2.2 コピーの保護は事前検査であって公開時の保証ではない

コピー先を検査してから `mv -f` するので、検査後の他コピー・編集を置換する。公開後のcmpは、その時点で自分が書いた内容を確かめるだけで、直前に消した内容を検出しない。既存テストの成功はこの競合を否定しない。

根拠: `scripts/superpowers-review-copy.sh:94–116`。今回、同時コピー・実行中編集・コピー先の種別変更を固定順序で再現した。

### 2.3 仕様、許可範囲、状態の記録が別々に更新されている

AGENTSは任意CODE_ROOTの経路を2スキルに限定するが、運用SpecとIssue計画は外部実装まで一般化する。remoteなしの例外も実行できない。文書の承認をSHAへ結び付ける規約に対し、このPR自身の初期Spec/Planは包括実行指示を `approved` と記録している。

「同テーマは既存文書更新」という方針に対し、review-fix-planningは既存正本の選択手順がなく日付入りの新規命名を指定する。実装済みPlanは `approved`・未チェック43件のまま。

根拠: `AGENTS.md:48–51,70`、運用Spec §3.1・§4・§5・§11、Plan `:6,777–779`、`review-fix-planning/SKILL.md:62–74,184`、`planning-parallel-issues/SKILL.md:14`。

### 2.4 検証単位が利用者の経路と一致していない

resolverの実行テストは有効だが、fixtureの親originは常に正しい。linked/fork/shell/URLの交差条件はレビュー後に増えている。他3スキルの今回追加テストは主に語句・フィールドの存在確認であり、文書作成から承認、実装、公開、handoffでの復元までを通した証拠ではない。

根拠: `pr-review/tests/test_pr_review_skill_contract.py:108–174,395–639`、`review-fix-planning/tests/test_review_fix_planning_skill_contract.py:159–234`、`agent-handoff/tests/test_agent_handoff_skill_contract.py:228–243`。

### 2.5 過去の非対応裁定が設計の再検討を固定的に除外していた

既存の分類は限定された依頼の範囲を守るうえでは合理的だった。しかし、R3–R7・R10などを毎回対象外にし、新しい局所不具合だけを扱う方法では、今回の「根本計画」という目的を満たさない。今回は安全境界を維持したまま、矛盾の解消とコピー方式の変更を明示的な設計提案として再検討する。過去の実装許可がこの再設計にも及ぶとは扱わない。

## 3. 全既存論点の分類

固定HEADでの分類は **解消済み7 / 対応する8 / 判断保留0 / 対応しない2**。IDは既存のR1–R17を維持する。「対応する」は承認後の計画であり、修正済みではない。

以下の `pr-review` / `review-fix-planning` は `.agents/skills/<name>/SKILL.md`。行番号は検証HEAD基準。

| ID | レビュー出典 | 論点 | 分類・根拠 | 修正方針・検証 |
| --- | --- | --- | --- | --- |
| R1 | Claude 解消L-1、DeepSeek 解消L-2 | linked CODE_ROOTを通す | 解消済み。`20db57f`、pr-review:151–155。現行テスト成功 | main checkout要件を維持し、共通resolverへ移す際も拒否テストを残す |
| R2 | Codex 解消M-3 | 別DOC_ROOTで作成・commit先不一致 | 解消済み。`ab28ff5`、review-fix-planning:57,62–64,183。別DOC_ROOTの新規・更新・親未変更を今回再実行 | 書込・commit・blob取得の全操作をDOC_ROOTへ限定する統合テストを維持 |
| R3 | DeepSeek L-1、Claude L-2の一部 | remoteなしを扱うという文書と実装の不一致 | 対応する(b)。AGENTS:70、運用Spec:66,253と、remote0件を66で拒否する実測の不一致 | remoteなしのPR連携は非対応と揃える。0件拒否と全文書の整合を検証 |
| R4 | Claude L-2本体 | 2スキル限定と外部実装の広い想定 | 対応する(b)。AGENTS:70とplanning SKILL:14・運用Spec:47–70で実行可能範囲が一致しない | 許可範囲を拡張せず、外部実装計画は実行経路未定義のblockerを持つ。ready判定とhandoffを確認 |
| R5 | Codex M-1 | コピー同時実行・実行中編集の上書き | 対応する(a)。copy helper:94–116。2ケースを今回再現、A/Bとも0でも内容消失 | 既存entryを置換しない公開方式へ変更。バリア制御で同時実行・編集・種別変更を検証 |
| R6 | Codex M-2 | 外部cwdをTOPLEVEL/helper元に採用 | 対応する(b)。AGENTS:48のroot分離とresolver:118–134,181が不一致。外部cwd3条件で正常値を返しhelper不在を確認 | 親cwd前提を実行時に照合し、不適切な親をfetch前に拒否。自動探索・外部cwdの自動対応はしない |
| R7 | DeepSeek I-1 | 古いPlanの手順を現行として読める | 対応する(b)。Plan:777–779と現行review-fix-planning:62–64が異なる。Planのapproved表示に現行手順への参照がない | Plan本文全体は同期せず、冒頭を完了記録・再実行禁止・現行手順への参照にする。R10と同じ作業単位で対応 |
| R8 | Claude・DeepSeek 未検証候補 | 相対allowed-toolsと別DOC_ROOT | 対応しない。Claude Codeでの誤動作未実証。確認プロンプトの発生だけで安全性不具合とはしない | 許可パターンを推測で拡張しない。対象ランタイムの運用受入で実際の動作を記録する |
| R9 | DeepSeek 解消L-3 | linked TOPLEVELをfetch後に拒否 | 解消済み。`333f4fb`、pr-review:124–132、現行テスト成功 | 全既知経路の共通事前条件として維持 |
| R10 | Claude I-1 | 内容承認・実行許可・完了状態の混同 | 対応する(b)。README:18,23、運用Spec:4,263、Plan:6と未チェック43件を照合 | 内容承認と実行指示を別記録にし、事実からcompleted/履歴を補正。新しい承認を捏造しない |
| R11 | Claude 解消M-1 | zshでremoteが空 | 解消済み。`530cfab`、pr-review:157–171。bash/zsh・nounsetケースを現行96テスト内で実行 | shell別ロジックをなくし、呼出し結果の空値拒否を維持 |
| R12 | DeepSeek 解消L-4 | fork経路のlinked cwdがclone案内 | 解消済み。`530cfab`、pr-review:124–144。両ownerテスト成功 | linked検査をfork lookupの前に共通適用 |
| R13 | DeepSeek 解消I-2 | ssh://を解釈しない | 解消済み。`530cfab`。resolver・copy helper双方のURLテスト成功 | URL照合の実装を共有し、HTTPS/SCP/SSHの成功と不一致拒否を維持 |
| R14 | SWE L-1 | 親origin欠落で有効CODE_ROOTにも裸の終了1 | 対応する(a:エラー経路の診断)。pr-review:119–122。originなしはgitエラーのみ、解釈不能URLではstderr空の終了1を今回再現 | 無効な親を許可するのではなく、共通preflightで理由付き66を返す。正常stdout・fetch・helper実行がないことを検証 |
| R15 | DeepSeek I-3 | 既存更新方針と回別文書の増殖 | 対応する(b)。AGENTS:50・README:9とreview-fix-planning:184の新規命名誘因、既存3回分文書を照合 | 同テーマの正本選択を先に行う。独立した再設計だけ別Specを許し、既存3回分は履歴として保持 |
| R16 | DeepSeek I-4 | PR説明の検証結果が古い | 解消済み。`b441c3b`と現在のPR API本文が初回失敗・現行成功を分離。現在HEADのCIは全SUCCESS | 検証HEAD・日付・今回実施/履歴結果を区別する報告を維持 |
| R17 | DeepSeek 未検証候補 | PARENT_ROOT選定手順の不足 | 対応しない（独立した誤動作としては未実証）。helperはorigin/main checkoutを照合する | R6の共通context設計で明示・選定規則も定まるが、誤選定バグを修正したとは主張しない |

Test suggestionsは独立した不具合として数えない。初回SpecのF9（tmp自体のsymlink検査追加）は現行5レビューの独立findingではなく補強提案。本計画のコピー安全マトリクスには含めるが、既知不具合の件数へ加えない。履歴文書全文未読というレビューcoverageの限界も不具合件数へ加えない。

## 4. 代替案と推奨案

| 案 | 内容 | 評価 |
| --- | --- | --- |
| A: 局所修正の継続 | 分岐を追加、copyをflockで直列化、文書へ注意書きを追加 | スクリプト間の競合は減るがロックに従わない編集を保護できず、分岐・仕様の重複も残る。非推奨 |
| B: 最小の構造改善 | 共通のroot/identity照合、非置換コピー、状態と権限の分離、経路横断の検証 | **推奨**。既存の安全境界を維持し、今回の原因を4つの責務へ分けて直す |
| C: 汎用ワークフロー基盤 | 任意cwd/remoteなし/外部実装まで解放し、文書台帳・状態管理エンジンを新設 | 許可範囲と実装量が大きく増える。PR #16の安定化には過剰。別途設計が必要 |

## 5. 推奨設計

### 5.1 ルートとrepo識別を一度だけ照合する

小さな共通PythonモジュールとCLIを `scripts/superpowers_context.py` に置く。Pythonはuvで実行し、新しい依存は追加しない。CLIはJSONを返し、shellコードやeval用代入を生成しない。shellからはjqで必要フィールドだけ取得する。

責務は、パス・repo URL・checkout種別・remote選定の**読み取り専用照合**だけ。fetch、clone、worktree作成、commit、push、文書状態の自動変更はしない。

入力: 操作種別（review-workspace / review-fix / review-copy）、PRの固定識別子、親/文書/コードroot、必要な文書ブランチ。成功時は照合済みroot、repo、選定remote、branch/HEADを返す。入力不足64、既知forkの不備65、パス・identity・候補不一致66を理由付きで返す。失敗時は正常結果のstdoutを出さない。copyラッパーの従来の引数2・拒否1は維持し、内部診断をstderrへ伝える。

不変条件:

1. helperの配置元は検証済みcreate-reso-world。任意のcwdのoriginとPRが一致するだけでは採用しない。
2. `PARENT_ROOT` は明示されたmain checkout。省略時はcreate-reso-worldのmain checkout内のcwdからだけ確定できる。linked・外部cwdでは推測せず拒否する。複数cloneを検索しない。
3. `DOC_ROOT` はcreate-reso-worldの明示checkout/worktree。書く前に対象文書ブランチを確認する。CODE_ROOTから導出しない。
4. pr-reviewの作業元CODE_ROOTはmain checkout。review-fixの実装用checkout/worktreeとは操作種別を分け、linked拒否を全操作へ一律に広げない。
5. 既知のfork/upstream経路と、その他repoの一致remote1件を区別する。明示CODE_ROOTが既知経路と矛盾すれば拒否する。
6. 取得remoteはbase repo、push remoteはAPIで確認したhead repoを別々に照合する。fetch用remoteをpush先へ流用しない。新たなpush機能は作らず、既存手順が同じ照合関数を使う。
7. 全root照合とlinked検査はfetch・helper・文書書込より前。URL照合とcheckout種別判定をSKILL内で再実装しない。

pr-reviewとreview-fix-planningの説明はこのCLIの利用へ寄せる。copy helperは同モジュールのroot/URL照合を使う。操作別の制約は共通関数の引数で明示し、制約差を消さない。

### 5.2 確認用コピーは既存entryを置換しない

固定名を比較して上書きする設計を廃止する。正本が変わったら `...-r2-spec.md`、`...-r3-spec.md` のように別名へ公開する。短い名前・repo/PR番号・直下配置・完全なSHAを別途提示する既存方針は維持する。SHAや追加ディレクトリを一律にパスへ足さない。

- `--name` は維持。同一内容の通常ファイルがあれば書かずに `unchanged`。
- 既存の異なる内容、ユーザ編集、symlink、directory、特殊ファイルは変更せず拒否する。
- `--replace-from` は安全でない置換を実行せず、移行案内付き引数エラーとする。現行の全呼出し元を同時に新手順へ更新する。過去Plan内の旧呼出しは履歴であり、現行手順ではないと冒頭に明示する。
- 完成した一時ファイルを、**既存entryがあれば失敗する公開操作**で公開する。例として同ディレクトリ内の通常ファイルを `os.link` で公開し、一時名だけを除去する方式を採る。`mv -f`、directory内へ移動する操作、既存entryの削除、上書きモードへのfallbackは使わない。
- 同名異内容の2プロセスでは一方だけ成功。他方は内容不一致で失敗し、勝者の内容を残す。同名同内容は成功/unchangedを許す。
- 新しい版の公開は旧コピーに触らないため、旧コピーへの編集と競合しない。最新を指す可変symlinkや自動番号採番も作らない。
- 一時ファイルの権限と全内容を公開前に確定し、公開後にファイルを追記・chmodしない。公開後の検証失敗を理由に第三者が変更したファイルを削除・巻き戻ししない。

保証範囲は、通常の同時helper実行と、既存コピーへのユーザ編集をhelperが消さないこと。ユーザが公開後の新コピーを書き換えることまで禁止・防止する保証ではない。悪意ある親ディレクトリの並行差し替え、突然の電源断までの耐久性を今回の範囲へ含めない。静的なsymlink/範囲外解決拒否は維持する。

### 5.3 文書保存とコード実行許可を分離する

Spec/Planの保存先は対象repoにかかわらずcreate-reso-worldのまま。任意repoのPRレビューと、そのPRのreview-fix-planningの承認済み実装修正の既存経路は維持する。

一般的な外部実装を新規に許可しない。remoteなしのPR連携は非対応と明記する。Issue計画でその他repoを対象とする資料を保存できても、実装経路が未定義ならblockerを明記し、実行可能なhandoff・子Issueのready状態として扱わない。確認済みhandoffがあるだけで許可経路が増えることはない。

運用Spec §3.1・§10、AGENTS境界表、planning-parallel-issues、agent-handoffをこの区別に揃える。任意repo実装を正式に開く設計は本PRと分ける。

### 5.4 内容承認、実行指示、完了を別の事実として記録する

文書の状態enumは増やさない。一方、状態だけから内容承認や実行許可を推測しない。

- 内容承認: 確認したrepo相対pathと文書commit、承認の根拠を記録。包括的な「推奨案で最後まで実行」の指示は内容承認とは別の実行許可として記録する。
- 実装開始時: Spec/Planのそれぞれについて承認済み版と現在の設計内容、継続指示、handoffの対象外、コードHEAD/反映先を確認する。completed/superseded/cancelledのPlanを通常の再開経路で実行しない。
- 承認後の記録追記commit: 承認済みSHAを追記前の版として保持する。現在HEADと承認SHAが異なるだけで再承認を要求しない。設計内容・範囲・検証条件が変われば再承認する。Markdown全体の一致ではなく内容変更の有無を確認する手順とする。
- 実装後: 実装・検証の結果からcompletedを記録する。completedはmergedやpublishedを意味しない。コードと文書のSHA、push/PRの状態を別に報告する。
- 失敗/途中停止: 状態と公開未実施を正確に残す。ローカルcommitだけでは第三者が復元できるとは言わない。
- handoff: `document_commit` は復元版、承認されたSpec/Planのcommitは別の任意フィールドで保持する。既存schema v2の欠落フィールドを承認済みと解釈しない。新たな永続台帳・汎用状態管理エンジンは作らない。

このPRの運用Spec、初回修正Spec、Planは、実施・検証済みの事実と、個別内容承認を確認できない事実の両方を記録する。過去の承認を捏造せず、確認できた包括指示を実行許可として残す。43チェック項目を一括で実行済みに変えず、冒頭に完了結果と旧手順が履歴であることを明記する。

### 5.5 正本を選んでから更新する

対象repo・PR・テーマから既存Specを先に探す。既存が1件ならその正本を更新、複数なら関連文書の後継指定/明示pathで確定し、確定できなければ停止する。日付入りの命名は新しい独立テーマにのみ適用する。

PR #16の通常のレビュー修正記録は既存round3ファイルへ集約する。既存の初回/round2は履歴として残し、現在の記録へ参照を追加する。本文の全履歴や取り込み22件を統合・移動・リネームしない。

本書はコピーAPIと共通resolverの責務を変更する独立した再設計フェーズのSpecであり、単なるround5の選別記録ではない。この設計へのフィードバックは本書を更新し、回別Specを新規作成しない。

## 6. 承認後の対応順序

同じworktreeを複数担当が同時に編集しない。次の段階ごとに実装担当1名、読み取り専用の確認担当を割り当てる。局所的な新しいfindingの発見ではなく、同じ受入マトリクスへの適合を確認する。

| 段階 | 対象ファイル | 内容 | 完了証拠 |
| --- | --- | --- | --- |
| T1: 仕様を確定 | AGENTS、docs/superpowers/README、運用Spec、4スキルの関連節を照合 | 許可境界、操作別root制約、非置換コピー、承認/実行/完了、正本更新の決定表を作る。実行に影響する本文の編集はT2のRED確認後、T3–T5で行う | 各仕様の正本と利用箇所を列挙した整合表。本書の内容承認 |
| T2: 失敗を固定 | `tests/scripts/test_superpowers_context.py`（新規）、`tests/scripts/test-superpowers-review-copy.bash`、既存resolverテスト | R5/R6/R14の再現を先にRED化。旧linked/remote/shell/SSH拒否・成功を移植 | 期待した原因で失敗したログ。テストのstdout/exitの期待値を緩めない |
| T3: 共通照合 | `scripts/superpowers_context.py`（新規）、pr-review/review-fix-planningとテスト、copy helper | Markdown内の分岐ロジックを共通の読み取り専用CLIへ移す。操作別linked要件とhead/baseの区別を残す | 正常/異常root×repo×remote×shellのマトリクスGREEN。拒否時にGit ref/status不変 |
| T4: 非置換公開 | `scripts/superpowers-review-copy.sh`、必要なら小さなPython公開関数、コピーのbash/pytestテスト、全現行呼出し元 | 新規entryのみ公開。r2等へ新版を提示し、replace-fromを安全に拒否 | 競合・編集中コピー・directory/symlinkの固定順序テストGREEN。失敗後に他者の内容とentry一覧が不変 |
| T5: 運用と履歴 | review-fix-planning、agent-handoffとschema、planning-parallel-issuesとsession-workflow、該当3文書の冒頭、round3記録 | 共通手順の利用、再開ゲート、blocked/ready、承認SHAの区別、旧手順の履歴表示。必要なevalを更新 | 文書commit→コピー→新版→承認記録→handoff復元のfixture受入。外部実装未許可がreadyにならない |
| T6: 統合検証 | `.devcontainer/run-tests.bash`の既存発見規則、CIの既存スキル検査 | 新規テストがCIで実際に収集・実行されることを確認。必要な組込だけ変更 | 下記の個別・全体検証成功、決定表全セルの証拠。固定HEADでの運用受入 |
| T7: 反映 | 既存PR #16、既存round3記録 | 並行更新確認、最新コードHEADの検証結果と設計結果を記録し、既存headへcommit/push。最終コメントは1回でまとめる | push後のremote/PR HEAD一致、PR説明とstatus commentの整合。マージは別途指示 |

詳細Plan作成時に新規Pythonテストの収集経路を確定する。既存bashテストから呼ぶか、run-testsの既存実行規則へ加える。ファイルを置いただけでCI対象になったと扱わない。

## 7. 検証マトリクス

### 7.1 context/remote/checkout

| 軸 | 必須ケース |
| --- | --- |
| 操作 | review-workspace / review-fix / review-copy。共通判定を使ってもlinked可否は操作別 |
| 対象 | create-reso-world、ResoLoop fork、upstream、その他repo |
| 親 | 正しいmain、linked、外部cwd、originなし、異なるrepo、解釈不能URL、明示親とcwd不一致 |
| コードroot | 正しいmain、linked、相対、サブディレクトリ、不存在、既知経路と矛盾、親外・空白を含むpath |
| remote | 0/1/2件一致、origin以外の一致、base/head不一致、push先候補不定 |
| URL/shell | HTTPS/SCP/ssh://（.git有無）、誤host/repo。bash、zsh既定/nounset |

全組合せを無制限に増やすのではなく、各不変条件を全対象経路に適用するケースと、今回露呈した交差条件をパラメータ化する。例: linked親×両ResoLoop owner、無効な親origin×有効CODE_ROOT、外部cwd×CODE_ROOT未指定/明示/remote2件。

失敗では、終了コード、理由、正常stdoutなし、fetch/helper未到達、ref/index/status不変を確認。後続処理未到達はstdout空だけで推定せず、Git操作の監視fixtureで副作用の不在を確認する。

### 7.2 コピー

通常作成、同内容再実行、異内容・編集・symlink・directory・特殊ファイル、tmp自体のsymlink、ignore外、正本dirty/staged、別DOC_ROOT、同名同内容/異内容同時公開、旧コピー編集中の新版公開、公開直前のentry種別変更、公開失敗・検証失敗・一時ファイルcleanupを確認する。SpecとPlanを両方扱う。

競合はpipe/FIFOバリアで固定し、sleepでたまたま当たることを合格条件にしない。既存entryの内容だけでなく、entry一覧・inode/mtimeなどから「書かなかった」ことも確認する。

### 7.3 文書とhandoff

1. 親mainと別DOC_ROOTで文書commit→閲覧copy。コード側checkoutと親の正本文書は未変更。
2. 文書更新→別名copy。旧コピーと注記が残り、新copyは提示commitのblobと一致。
3. 内容承認の版が一致する場合、不一致で実質変更がある場合、記録追記だけの場合を手順とevalで区別。
4. completed/superseded/cancelledのPlanから新規実装へ進まない。
5. 外部PRの取得先baseとpush先head、文書側の公開先を区別。文書PRなし・文書push失敗は公開未実施。
6. 公開アーティファクト/許可された復元手段から新しい空領域に正本を復元しhashを照合。閲覧copyや元ホストの絶対pathで代用しない。
7. 一般外部実装の許可経路なし、文書情報欠落の旧handoffは、ready/承認済みと推測しない。

pytestのfixtureが通っても、自然言語スキルをLLMが正しく実行することの完全な証明にはならない。標準経路1件について、使用ランタイムで操作痕跡付きの運用受入を行う。R8はここで許可照合の観測だけを記録し、未検証候補を実証済みとしない。

### 7.4 実装時の必須コマンド

```bash
bash tests/scripts/test-superpowers-review-copy.bash
bash tests/scripts/test-docs.bash
bash tests/scripts/test-gitignore.bash
bash tests/scripts/test-instructions.bash
uv run pytest .agents/skills/pr-review .agents/skills/review-fix-planning \
  .agents/skills/agent-handoff .agents/skills/planning-parallel-issues
uv run pytest tests/skills .agents/skills
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
git diff --check
```

新規context/統合テストの実行コマンドも詳細Planへ明記する。上記は今回実行したコマンド一覧ではなく、変更後の検証条件である。無関係なワールドpytest、ResoLoop全テスト、実機ワールド操作は含めない。

## 8. 終了条件と反復防止

- [x] R3/R4/R7/R10/R15の文書不一致が解消し、現在の許可境界と履歴表示が一致する
- [x] R5の2競合とentry種別変更で、既存内容を消さず、拒否時に他者のentryへ書かない
- [x] R6/R14の親誤選定・無説明終了を、fetch/文書書込より前の共通照合で拒否する
- [x] R1/R2/R9/R11/R12/R13の既存修正を退行させない
- [x] root/URL検査の実装、承認・状態の説明、現行コピー手順の正本がそれぞれ特定できる
- [x] 新しいテストがCIで実行され、経路ごとの受入証拠がそろう
- [x] 未検証R8/R17、未実施検証、既存履歴と今回の結果を区別する
- [x] 本Specの内容承認、詳細Planの実行許可、選択した実行方法を記録し、既存PRへ反映する

設計/実装の確認は同じマトリクスと固定HEADを使って1回の統合判定をする。新しい問題が出たら、その不変条件に欠けたセルがあったのか、別の設計変更なのかを先に判定する。「修正コミットを1つ足して別モデルで再レビュー」を既定のループにしない。新しい重大な事実を打ち切り規則で無視しない。

## 9. 対象外・次のゲート

- 任意cwdから親を自動探索すること、clone、remoteなしのPR連携、一般的な外部コード実装の新規許可。
- 汎用文書台帳、approval parser、状態管理エンジン、UI、可変latestリンク、自動コピー番号採番。
- インストール済みSuperpowersスキルの変更、取り込み22件の本文/パス変更、過去外部実装の再検証。
- R8の許可パターンを未実証のまま広げること、PRマージ、無関係なワールドの変更。

**非置換コピーへの切替とreplace-from廃止 / 現行の外部実装許可境界の維持 / 共通resolver導入** はユーザが本書提示後に承認した。詳細Planの作成直後の実行も同じ指示で許可されているため、追加の承認待ちは挟まない。実行方法は同期subagent-driven-developmentとし、既存review-fixワークフローの検証・反映手順を使う。Plan本文への個別承認やPRマージ許可を推定しない。

## 10. 実装・検証記録（2026-10-04 UTC）

内容承認の版は `79330776e52a4b077c8a596b035ab8f48a242123`。ユーザが提示内容を承認した後、その内容を変更せず保存した版であり、このSHAを閲覧した承認とは主張しない。以下は設計の変更ではなく、実施結果の追記である。

- コードの検証版: `1987715653fba088bafa0033b48b8304166f42c7`。Task 1・2・3、Task 3の指摘修正、全体レビューのCI履歴取得と過去承認記録の補正を実装済み
- Task 1・2のレビュー、Task 3の再レビュー、全体レビューの指摘2件の再レビューで、未解決のCritical/Importantなし。R8/R17は引き続き未実証・対応しない
- 最終コードの必須ローカル検証: bashランナー27本、unittest 72件、スキル399 passed / 1 skipped、実配置検査・全4プロジェクトのResoLoop同期検査、構文・diff検査が成功。skipは既存の `SKILL_UNDER_TEST` 未設定ケース
- controllerは共通コード版 `4241b31` で全必須検証を独立実行（終了0）。最後のCI・履歴メタデータ修正版ではCI/文書/指示検査とライフサイクル20件を追加実行（終了0）
- shallowな一時checkoutで基準コミット不在を再現し、履歴取得後に取り込み22文書のblobとSHA-256が一致。旧文書の本文・チェックリストは保持
- 運用受入: `0f6ff4619e32dbf27b6204e2a7e010498c319b8c` のSpec/Planを親checkoutへ非置換コピーし、コミット内のバイト列・SHA-256と一致。既存PRへのpush成功とAPI HEAD一致を確認
- 公開版をGitHub contents APIから空の一時領域へ復元し、両文書が同じコミットのblobと完全一致。復元用一時領域は検証後に削除
- GitHub CI: [push実行](https://github.com/usaturn/create-reso-world/actions/runs/37190611006)・[PR実行](https://github.com/usaturn/create-reso-world/actions/runs/37190613778)の各4チェックが成功。監視は2026-10-04 08:59:40 UTCに終了0
- この追記は完了・公開の事実を記録するメタデータ更新。内容承認版は保持し、最終記録版も別名の確認用コピーを作成して同じPRへ反映する。マージ未実施

自然言語の規約/evalは全ランタイムの遵守を、固定順序の競合テストはすべての並行実行を保証しない。過去文書の個別内容承認は捏造しない。公開の実際と復元版SHAは後続の結果記録・PRコメント・handoffに分けて記録する。
