# Issue #154 review-verify の移植

- 文書管理・対象: `usaturn/create-reso-world`、Issue #154（親 #116）
- 基準 HEAD: `a024a22626d4ff6daa46e92aa7cb8aae081aa7ac`
- 状態: `draft`。内容承認の記録はない。
- 実行許可: 引き継ぎに記録された利用者の `/skill:issue-to-pr #154` と、今回の `$superpowers:subagent-driven-development`。通常判断、Spec/Plan、実装、検証、commit、push、PR 作成まで。マージは含まない。
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
