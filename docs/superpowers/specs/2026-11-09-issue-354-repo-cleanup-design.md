# Issue #354: マージ済み branch と残存 pinned ref の整理

## 管理・実行許可

- 状態: `draft`（実行許可であり内容の承認ではない）
- 対象: usaturn/create-reso-world #354、親 #349、base `main`
- 利用者の指示: `/skill:issue-to-pr #354 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`。続けて「#364が完了したことを確認して作業を実行してください。」
- 委任: 通常の設計判断、検証、commit、push、PR、指定ループの finalize によるマージ。実際の利用者の branch/ref/worktree を掃除する許可ではない。
- #364 は closed/completed、PR #371 は MERGED。merge commit `b61b36a3e11f969f4e4ab41c401dadfa00a86e90` は捕捉 base に含まれる。直接の先行 #351 も closed/completed。
- base は origin / refs/heads/main / `b61b36a3e11f969f4e4ab41c401dadfa00a86e90` に固定する。

## 目的・現状

祖先判定だけでは squash/rebase の元 branch を残してしまう。通常 branch の判定は merged PR と local tip の一致を要求しておらず、手順 8 とゲート B も祖先型だけである。また、helper が見ないセッション無しの ref と version 7 が残す ref に整理経路が無い。既存の手順 5 が許可する version 7 の狭い例外とゲート A・ガードレールの保持規則が食い違う。

## 要件

R1. 取り込みの証拠を祖先型と PR 型にする。どちらも対象 repository に明示した PR の `state == MERGED`、branch 名と `headRefOid` の完全一致を確認する。`isCrossRepository` が true、対応不明、欠落・照会失敗は保持する。PR 型では `mergeCommit` が選択した取り込み先 base に到達可能なことも確認し、別 base にしか入っていない PR を取り込み済みにしない。`git log` が非空なことだけでは拒否しない。

R2. 手順 3・通常ツールの候補照合・手順 8 の `-D` の再確認・ゲート B の候補提示で同じ意味の判定を使う。`-d` が拒否しても、直前に R1 を再確認した branch だけを `-D` にできる。他 worktree が保持する branch、既存 local main/base、open PR、dirty/ignored の保護は維持する。リモート branch は祖先一覧だけに限定せず PR 型も提示するが、削除には必ず別のユーザー確認が必要。

R3. `refs/pr-review/repos/<owner>/<repo>/<N>` と旧 `refs/pr-review/<N>` を一覧から調べる。セッション無しの ref も対象。対応 repository と PR を確定し、PR が MERGED/CLOSED、関連する全 open PR と現行・保持中の session が ref を使わないことを確認したものだけ削除できる。session の照会が成功しただけで完全な一覧としない（登録のない残骸・bundle 等も考慮）。unknown は保持。fork/upstream で旧 ref の所属が一意に分からなければ、片方の終了だけで消さない。ref の現在値を読んで `git update-ref -d <ref> <読んだ値>` で compare-and-delete。並行更新で値が変わったら保持し、新しい値で無条件にやり直さない。

R4. coordinator の決定 https://github.com/usaturn/create-reso-world/issues/354#issuecomment-6743479090 を本文より優先。version 7 の ref は SKILL の残存 ref 手順で扱い、`pr_review_workspace.py` は一切変更しない。手順 5 は変更せず、`run_context` の無い version 7 が helper に終了コード 1 で拒否された場合だけ通常の clean/worktree/ゲート A 経路へ進めることをゲート A・ガードレールにも明記。version 8、run_context 付き、終了コード 2 は保持する。`removable` を保存・停止・所有の検証の代わりにしない。

## 範囲と除外

編集は `.agents/skills/repo-cleanup-after-merge/SKILL.md` の対象判定・手順 3・8・ゲート B・残存 refs・ゲート A/ガードレールの例外整合、および同 `tests/`、本 Spec・Plan。手順 5、helper、CLEANUP_BASE、fork sync、version 7/8 の gate A の照合本体、removable 定義、force 禁止、ignored gate は変更しない。AW の projects.toml・submodule force は移植しない。実環境の掃除や remote branch 削除、設定・CI の追加は対象外。

## 決定記録

| ID | 選択した案 | 検討した別案 | 理由・委任/停止条件 |
|---|---|---|---|
| D1 | SKILL 内の実行できる判定と fake gh/使い捨て Git のテスト | 文言だけの追記、別 helper 新設 | 安全条件を実行で確かめる。新 helper は所有範囲外。判定と削除の証拠を揃える |
| D2 | R1 の PR head と取り込み先の証拠 | branch 名/MERGED だけ、祖先のみ | 再利用 branch・後追い commit・未統合 base の誤削除を防ぎ squash/rebase に対応 |
| D3 | ref は手順で所属・open PR・session を照合し CAS | helper version7 の改変、prefix 一括削除 | coordinator の明示決定。判定不能なら保持する |
| D4 | 手順5を維持し gate A/ガードレールへ例外を揃える | version7 を全面保持 | coordinator の明示決定。保護の意味が変わる変更は停止 |
| D5 | Task を runner に直列依頼 | controller が実装、同時書込 | `--implement` の指定。check は self=false、agents=[pi_opencode-go_deepseek4-flash_max]、fallback=[]。失敗時に controller へ切替えない |
| D6 | PR 後に指定 inspect 3名と implement のループ | マージしない、自前でマージ | 利用者の --merge。max_cycles=3 は既定、inspect と implement は利用者指定。self-review/fix-check は既定 self。通常の範囲/安全停止は維持 |

## 検証方針

動作環境は Linux Dev Container、Bash、Git、gh の fake、uv/pytest。`mktemp` 相当の一意の一時 Git repository に非 ASCII・複数行の内容と空白入りパスを用意する。祖先・squash・rebase の正例、未マージ・PR 不明・head 不一致・別 repo/base の反例を実行する。ref は閉じた PR の削除正例と open PR/session/所属不明/並行更新の保持を確かめる。外部の実 PR/API をテストには使わない。HOME はワンショットで隔離し GIT_* を除去する。

追加テストは実際の気付きにくい誤削除・誤分類・競合を防ぐ S と、実際の不具合の再発防止だけ。文言・frontmatter の写し合わせ、一般的な構文/オプションの L テストは追加しない。同じ守りは代表1件。SKILL のコードブロックを抽出して実行し、単なる文字列検査にしない。writing-skills の無し/ありの適用シナリオは別の読み取り専用担当で各1回、作業前後を比較する。

## 実行記録（公開前）

- Task1 は `9361d044`、base 除外の修正は `d9180ca3`。Task2 は `0d27e0e3`、symbolic ref/CAS/session 検証の修正は `4a7219b8`。全体レビューの root/大小文字/一覧上限/重複テスト修正は `9be97ac9`。
- 指定 runner は全依頼で `pi_opencode-go_deepseek4-flash_max`、観測モデルは `opencode-go/deepseek-v4.1-flash`、effort max。Task1 2依頼（約1191秒・115秒）、Task2 2依頼（約825秒・390秒）、全体修正1依頼（約405秒）。全て importable/accepted、停止確認 true、cleanup の retained は無し。
- 各 Task と限定再レビュー、最後の全体レビューと1回の修正・限定再レビューを実施。最後の関連テストは controller が clean HEAD `9be97ac9` で51件成功、終了コード0。追加テストはS、重複CASテストはDとして代表へ集約した。
- R1/R2: 実 Git の祖先/squash/rebase と、未マージ・不明・head/base不一致を確認。最後の修正で残存 TARGET_ROOT の別 clone 削除、repository 大小文字の session 取り違え、100件での一意性誤判定を再現して防いだ。
- R3/R4: session 無し終了PRのref削除正例、open/current session、曖昧な旧ref、symbolic ref、一覧後の更新、所属の型/形式不正の保持を確認。手順5/helperは変更しない。GREEN適用では旧形式の複数所属・不完全なsession一覧は保持、version7の限定例外のみ従来経路と判定した。
- GREENの担当がrebase入力に「mergeCommitがnull」という未提示の前提を加えたため、その部分は採用しない。入力はAと同じreachableなmergeCommitであり、実rebase履歴テストと公式REST/GraphQL資料をcontrollerが照合した。欠落時は安全側に保持する。
- skill-efficiency-check は終了コード0、Issues/Warningsなし。別helperファイルへの分離は所有範囲外なので、SKILL内の実行ブロックを維持する。
- 共通の全体検証・scan・PR・指定ループは、この記録の後で実行し、HEAD/base/ログをPRとセッションへ記録する。未実行を成功としない。

## 既知の baseline

変更前の読み取り専用適用シナリオで、squash/rebase は `git log` が非空のため保持、セッションの無い ref は手順が無いため保持となった。version7 の例外と gate A の衝突も残る。これは新しい手順で改善すべき挙動であり、機械テストと合わせて再確認する。
