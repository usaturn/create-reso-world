# Issue #285: レビューのテスト提案を対象リポジトリの方針に揃える

## 管理・実行許可

- 状態: completed（内容の承認は未取得。実行許可に基づく完了記録）
- 対象: usaturn/create-reso-world #285
- 指示: `issue-to-pr #285 --merge --max-cycles 3`
- 許可: 通常の設計判断を推奨案で決め、検証・commit・push・PR 作成と、指定されたレビュー修正ループによるマージまで実行する。内容承認を意味しない。

## 意図と範囲

`.agents/skills/pr-review/SKILL.md` の「推奨対応」と `Test suggestions` が、テストの追加が不要な指摘にも追加を求めるように読める不整合を除く。観点・セルフチェックとテンプレートを揃え、追加の要否は対象リポジトリのテスト方針で決める。

- create-reso-world では `AGENTS.md`「テストの採用基準」を参照し、分類の定義をスキルへ複製しない。
- 外部リポジトリではそのリポジトリのテスト方針に従う。
- テスト提案が不要なら「なし」と記載でき、必要に応じてツール実行・静的解析・構造確認等の代替検証を記載できる。
- `Test suggestions` の見出し、指摘のラベル、既存のレビュー形式は維持する。
- 共通基準や既存テストの再分類・削減、パーサーの変更、他文書の例の一括修正は対象外。

## 決定記録・比較案

| 項目 | 選択した案 | 検討した別案 | 理由・委任範囲 |
| --- | --- | --- | --- |
| 変更範囲 | テンプレート2か所と必要なセルフチェックの最小編集 | 各所への分類一覧の複製、形式変更 | Issue の範囲内で一律要求の誘因を除き、定義の二重管理と後段の互換問題を避ける。通常判断の委任に基づく |
| 検証 | 構造・参照・差分と3例の判断照合 | 固定文言テスト、反復モデル評価 | Issue は固定文言テストの新設を禁止し、有料モデル評価を要求していない。動作保証や改善率は主張しない |
| 実行 | 単一Taskを sp-implementer に同期委譲し、Task・全体レビュー | 小編集の分割・並列実装 | 同じファイル内の一連の変更であり独立に分割しない。runtime の委譲指定に従う |
| Plan実装担当 | 既定の self、fallback なし（SDDの子へ委譲） | CLIで担当を置換 | implement_task.py check の観測結果。利用者による担当指定ではない |
| マージループ | max_cycles=3 | 上限変更・ループ省略 | 利用者指定。review inspect は既定の claude-opus/devin-swe/pi-deepseek、fix implement は claude-opus、self-review/fix-check は self、fallback は全てなし。check-options の観測結果であり、指定された担当とは記録しない |

ループ設定: template=`/workspaces/reso-world/.devcontainer/agent-runner.toml`、config=null、assign={}。対象・競合・安全境界の変化、必要なツールの失敗では issue-to-pr の停止条件に従う。

## 受け入れ基準と検証

1. 文書・設定の写しや通常利用・静的解析で検出できる誤りに、コミットするテストを一律要求しない。
2. 静かな損害を防ぐ必要なテストと拒否に対応する正例を妨げず、重複する組み合わせ網羅を求めない。
3. 「文書の追随漏れ」はテストなし＋参照・diff確認、「静的解析で検出できる誤り」はテストなし＋静的解析、「失敗を成功として報告する不具合」は代表の挙動テスト（拒否なら正例も）という判断を、AGENTS.md と修正文の意味で照合する。これらは検証例でありスキルへの分類一覧追加ではない。
4. 既存の観点・セルフチェックとテンプレートを両方向から読み、見出し・ラベルと参照先の実在を確認する。
5. 新しいテストは追加しない。README のワールド以外の既存検証を実行する。モデルによる出力挙動の実測は対象外であり、文言修正だけで挙動の保証を確定しない。

## 初期観測

- 対象の現行版: c9cdc8ba30fe9fe14751f91cd08f5a54b16fac37。
- Issue の全コメントは0件、依存なし、親なし。関連 #228/#229 は closed。既存PR・担当予約・同番号のbranch/worktreeなしを着手前に確認。
- 初期検証: shell 23件、pytest 1237件、check-layout はすべて終了コード0。ログは親 checkout の `tmp/agents/issue-285.xk_yzd1u/baseline-*.log`。

## PR #286 サイクル1の確認・結論

- 検証対象: `6d2fd8d3cf3b85ad468d1f6006b836b763137639`、base `c9cdc8ba30fe9fe14751f91cd08f5a54b16fac37`。
- planner: `gpt-6.1-sol` / pi（PI_PROVIDER=openai-codex、PI_MODELの実測値）。実行許可: 上記の `--merge --max-cycles 3` による完遂。
- 結論2: 修正不要。解消済み0 / 対応する0 / 対応しない1。現行HEADの全変更ファイル、関連する形式と分類基準、全指摘を確認した。票数や重大度だけで採否を決めていない。

| レビューファイル | モデル | runtime | HEAD | 再実行 | 判定 |
| --- | --- | --- | --- | --- | --- |
| claude-opus-5-5.md | claude-opus-5-5 | claude-code | 6d2fd8d3cf3b | true | Approve |
| SWE-2-Max.md | SWE-2 Max | devin | 6d2fd8d3cf3b | true | Approve |
| deepseek-deepseek-v4.1-flash.md | deepseek/deepseek-v4.1-flash | pi | 6d2fd8d3cf3b | true | Approve |

### 全指摘の採否

`deepseek-deepseek-v4.1-flash#I-1@6d2fd8d3cf3b`: **対応しない**。SpecとPlanの名前にリポジトリ語がなく、`docs/superpowers/README.md:8` の命名規約と不一致なのは事実。両ファイルのコミット済み内容とtreeで確認した。本文に対象リポジトリとIssueがあり、同README:10の内容による文書照合はできる。主要処理の停止、誤った対象への操作、データ損失、秘密露出に至る条件はなく、review-fix-planningの致命的な指摘だけを直す基準では改名しない。実害のある誤選択経路が確認されるか、利用者が改名を名指しで依頼した場合に見直す。

### 要件と証拠の対応

- 一律要求を除去し、必要なテストは対象側の方針で提案できる。Task `0625048` の3行変更と、文書追随漏れ・静的解析・失敗の成功報告の3例をAGENTS.mdと照合。前2例はテストなし＋代替検証、最後は代表の挙動テストと正常側の正例を維持できる。
- 観点→推奨対応→Test suggestions→セルフチェックの共通条件はcontrollerが統合確認した。分類の複製なし。git objectでbase/headの見出し・ラベルが同一、相対リンクが実在することを再確認した。
- 検証済みHEADとbaseは上記のとおり。検証前後ともclean、全終了コード0。`bash .devcontainer/run-tests.bash` は23件、`bash scripts/check-layout.sh` はPASS、`uv run pytest tests/skills .agents/skills .agents/scripts tools` は1237件、`git diff --check` は成功。関連検証298件・skill-efficiency-checkも成功。
- 最終pytestでは親checkout由来のVIRTUAL_ENVをuvが無視する警告が1件あったが、worktree側の環境で全件成功。モデル遵守率・外部適用の実測は要求外で未実施、保証しない。
- ログ・checks-fileは `/workspaces/reso-world/tmp/agents/issue-285.xk_yzd1u/`。同一HEAD・clean・各exit 0・ログ残存の条件を確認し、issue-to-prの検証再利用規則を適用した。baseを再取得し、先端が検証済みHEADの祖先で同じSHAであることを確認した。
- 確認済み一覧: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#286-fix-issue-285-review-test-guidance/verified/6d2fd8d3cf3b.json`。工程の記録は同ディレクトリの `6d2fd8d3cf3b.planning.json` にサイクル終了時に保存する。未確認の候補・必要な検証の欠落なし。
- 対応する指摘がないため修正方針・影響経路表の新設、run_rolesによる実装・自己レビュー・fix-checkは行わない（呼出し0回）。指定の既定割当を別の担当に置換していない。Piのcycle補助委譲は期限付き停止条件を満たせないため省略。
- SDDのTaskレビュー・全体レビューとも修正指摘なし、SDD作業領域は証拠をセッション直下に保存後に削除した。実装1350秒、Taskレビュー約2分、全体レビュー計測区間121秒、最終全検証674秒。PRループのレビューは並行で各271.39秒・285.75秒・412.53秒。plannerの時間とコメントURL、push・マージ・Issue更新の結果はサイクル記録と最終報告に残す。
