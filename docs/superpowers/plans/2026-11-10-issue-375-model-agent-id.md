# Issue #375 Model Agent ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 記号を含む正確なモデル名を保持し、過去の記録を壊さずに状況コメントを投稿・更新する。

**Architecture:** 旧変換が成功するモデル名の ID は不変。旧変換で失敗する有効な識別値は `model--` と元の UTF-8 の SHA-256 へ変換する。コメント側ではモデル名から一度だけ導出する。

**Tech Stack:** Python 標準ライブラリ、pytest、既存の fake GitHub。

**Spec:** `docs/superpowers/specs/2026-11-10-issue-375-model-agent-id-design.md`

- 状態: draft。issue-to-pr の実行委任で進め、承認済みとはしない。
- 実行方式: SDD。Task 1 は runner `pi_opencode-go_deepseek4-flash_max`（利用者指定、fallbackなし）へ依頼。Task 2 は controller の統合責任。Task 1・2 は完了済み（下記実行記録）。
- 継続 run（2026-11-12）: 利用者の明示指示で既存 PR #385 を続行。Task 3（最終化）を追加。この run の指定は Spec レビュー・Plan 実装とも `pi_alibaba_qwen4-max_max`、ループは inspect=`pi_alibaba_qwen4-max_max,pi_openai-codex_gpt6-sol_xhigh`・implement=`pi_alibaba_qwen4-max_max`（check 済み）。実行許可の詳細は Spec の「実行許可（続行・2026-11-12・この run）」に従う。

## Global Constraints

- `planner.model`、ループの controller model、コメント見出しには入力の正確なモデル名を保持する。追加の CLI 引数やモデルの手動置換は不要。
- 旧変換が成功するすべてのモデル名の ID は変えない。旧 v1/v2 記録とマーカーを引き続き読み取れる。
- 新 ID は `model--` + 元の文字列の UTF-8 バイト列に対する SHA-256 の小文字16進64桁。モデル名と導出済み ID を混同しない。
- 空・空白のみ・制御文字・改行・HTML コメントの開始/終了マーカーは既存の識別値検査で拒否する。
- 旧形式同士の衝突、review_file 変換、記録スキーマ、ランナーの選択規則は変更しない。
- 追加の恒久テストは AGENTS.md の S に限る。F/L は実行確認、同じ守りの D は追加しない。実 CLI・課金モデルをテストとして起動しない。

## 受け入れ基準

- 動作環境: この Dev Container の uv/Python、既存 pytest と fake GitHub。外部通信なしで導出・保存・再読取・コメント更新を確かめる。
- 実入力: `deepseek-v4.1-flash:1017[1m]`、`provider/model@release`、`日本語モデル[大]` のような単一行の正確なモデル名。旧形式 `opencode/deepseek-v4-flash-free` も保持する。
- 防御範囲: 新形式と、同じ ID に見えるリテラルの旧モデル名を区別する。異なる記号のモデル名を区別し、record-less コメントの初回作成→再投稿では自分のコメントのみ更新する。記録付きコメントでは正確なモデル名を round trip で保持する。対象外は旧変換で以前から同一 ID になるモデル名同士の全面移行、ファイル名規則の変更。空白のみ・制御文字・HTMLコメントマーカーは受理しない。

この本文を実装担当と Task レビュアーに同じ内容で渡す。

## Review Focus

- 二重変換で `model--` が壊れ、投稿が重複する経路（Task 1 の実行回帰）。
- 新形式の値そのものをモデル名に指定する反例との区別（Task 1 の名前空間テスト）。
- JSON/コメントから読み戻した planner.model が短縮される経路（Task 1 の round trip）。
- 単一行・制御文字拒否の範囲の意図しない拡張（Task 1 の一時確認、恒久 L テストは不要）。
- SKILL に旧変換の別実装を増やさないこと（Task 2 の差分確認）。

### Task 1: 互換性を維持した ID 導出とコメント更新

**Files:**
- Modify: `.agents/scripts/review_records.py`
- Modify: `.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py`
- Modify: `.agents/review-records.md`
- Test: `.agents/scripts/tests/test_review_records.py`
- Test: `.agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py`

**Interfaces:**
- Consumes: `agent_id_for(model: str) -> str`、`identity_problems(value, where)`、既存の `compose_comment`/`read_state`、`marker_for`/`compose_body`/`upsert`。
- Produces: 同じ API。既存 ID は不変、新しい ID は Spec の定義どおり。導出済み ID の二重変換はしない。

**テストの要否:** S は書く。別モデルの同一視・誤ったコメント更新、正確な記録の損失を防ぐ。旧挙動の単なる固定値の一覧、未対応名の例外の解消だけ、文書文言は恒久テストにしない。

- [ ] Step 1: 既存テストの構造を読み、次の守りの代表テストを先に追加する。名前空間の分離（生成した新 ID と、その ID 自体をモデル名とした旧変換の値が異なる）、異なる記号を使うモデル名が同一視されないこと、正確なモデル名を compose/extract/fold で失わないこと。fake upsert は記号を含むモデル名の作成→更新を実行し、既存の異なるモデルのコメントを PATCH しないことを確認する。期待値をすべて実装関数から作るだけにしない（独立した hashlib の導出や固定 prefix 構造・実際の PATCH 対象を確認する）。同じ守りの組合せを増やさない。
- [ ] Step 2: 対象テストを実行して RED の実出力を確認する。
- [ ] Step 3: `agent_id_for(model: str) -> str` に既存の識別値検査を適用し、旧形式が安全なら維持、そうでなければ Spec の SHA-256 ID を返す。`compose_body` のモデル名→マーカー呼出しを一度の導出にする。不要な API・スキーマ変更はしない。
- [ ] Step 4: `.agents/review-records.md` 3章と docstring を更新し、名前空間分離と SHA-256 の衝突耐性、正確な model 保存、旧モデル間の既存衝突は不変であることを記す。
- [ ] Step 5: `uv run pytest .agents/scripts/tests/test_review_records.py .agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py -q` と `uv run pytest tests/skills .agents/skills .agents/scripts tools` を同期実行する。新規の単なる例外拒否テストは一時実行にし、既存 test の入力 `bad<model>` が新しい有効範囲と食い違えば、意図する拒否（HTML コメントマーカー）へ最小修正する。`git diff --check` も確認。失敗の内容を報告し、無関係な修正へ広げない。
- [ ] Step 6: 明示ファイルだけを stage、`fix: support exact model identifiers in review comment IDs` で commit。実行時間、RED/GREEN、実行コマンド・終了コード・懸念を JSON 結果に含める。

### Task 2: 条件単位の統合確認・公開・ループ（controller）

**Files:** 上記の差分を読取り。必要に応じ本 Plan の実行記録だけ更新。

**Interfaces:** Task 1 の受け入れた HEAD、捕捉済み base SHA、検証・レビュー記録。

**テストの要否:** 新しい恒久テスト不要（D）。共有するモデル名→導出→コメント保存→読取→更新の入力と順序を controller が確認する。

- [ ] Step 1: runner 結果を受け入れ、依頼ごとに記録して cleanup。controller も関連テストを再実行する。Task 1 の brief/結果/差分を同じ受け入れ基準で read-only レビュアーへ渡す。
- [ ] Step 2: 全ブランチのレビュー（Spec/Plan を含む）を別途実施。必要な修正は同じ runner 担当へ依頼、勝手に self で実装しない。
- [ ] Step 3: 最後の commit の後、clean HEAD で README の3入口 `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` を実行し、argv/終了コード/ログ/HEAD/base をセッションディレクトリへ保存する。
- [ ] Step 4: 要件→Task→実出力を照合し、base/Issue/競合再確認、Gitleaks、検査済み SHA の push、PR 作成と head/base の照合。`Closes #375`。
- [ ] Step 5: 指定の pr-review-fix-loop を起動。全レビュー完了・停止確認を同期で待ち、review-fix-planning と finalize のみでマージ。Actions は無効のためローカル検証を使用する。

### Task 3: 継続 run の最終化（controller・2026-11-12）

**Files:**
- Modify: `docs/superpowers/specs/2026-11-10-issue-375-model-agent-id-design.md`（実行許可・レビュー記録・完遂手順の反映。最終化コミットは Spec 1 ファイルだけ）
- Modify: 本 Plan（実行記録の追記。最終化コミットには含めない）

**Interfaces:** 既存 PR #385（head `c9fb38e4` から開始）、既存 feature worktree、前 run の検証・再現証拠（`tmp/agents/pr385-complete.bo8wtrs9/`）、review-fix-planning / pr-review-fix-loop / review-verify の各手順。

**テストの要否:** 新しい恒久テスト不要（D・実装変更なし）。検証は最新 base との隔離統合ツリーで既存の標準入口を実行する。

**受け入れ基準（残作業分）:** Spec の「仕様」「範囲・対象外」の条件は実装済みで変わらない。追加の条件は次のとおり。
- 動作環境: この Dev Container の uv/pytest・fake GitHub。実 GitHub は PR #385 のレビュー・コメント・マージのみ。
- 実入力: 最新 origin/main を merge した隔離統合ツリーでの全 pytest・Dev Container テスト・配置検査。ループのレビューは指定 2 担当の実際の出力。
- 防御範囲: 検証記録の base だけの書き換え・安全検査の省略・force push・手動マージ・L-1 の根拠なき見直し・担当の暗黙切替はしない。対象外: 旧形式同士の既存衝突、review_file 変換、記録スキーマ（Spec の除外範囲どおり）。

- [ ] Step 1: Spec にこの run の実行許可・L-1 引き継ぎ・統合検証履歴を反映して commit（このコミット）。Plan も更新して commit。
- [ ] Step 2: review_spec.py で `--spec-review pi_alibaba_qwen4-max_max` の Spec レビューを実施。結果の全 findings を採否し、採用分を Spec に反映して decide・commit。失敗は停止（builder check で代えない）。
- [ ] Step 3: 最新 origin/main を捕捉し、mktemp の隔離 worktree で PR head（文書 commit 後）と merge したツリーを検証。対象 pytest・全体 pytest（必要なら分割）・Dev Container・配置検査・diff 検査の argv/終了コード/ログをセッションディレクトリに保存。checks 形式（head/base/commands）の記録を作る。
- [ ] Step 4: 親の scan-before-push.sh で全 worktree を検査し、検査済み SHA だけを既存 head ブランチへ fast-forward で push。PR の head/base を照合。
- [ ] Step 5: 親の loop.py で既存 PR のループを start（--controller-model は提示された正確な ID、--controller-runtime claude-code、利用者の --assign 2 件）。cycle-begin→review→review-fix-planning 完遂→cycle-end→finish を手順どおり実行。レビューは指定 2 担当の実際の出力を使い、rejected を指摘 0 件として扱わない。
- [ ] Step 6: 完遂の結論 2 なら、検証記録を再利用（同一 HEAD・clean・全終了コード 0・ログ実在の条件）し、Spec を `completed` にした Spec 1 ファイルだけの直接の子コミット S を作成。記録付き状況コメントを head が reviewed_head のうちに投稿し、S を検査付き push。finalize.py --spec-commit S でマージ・Issue 更新。base_moved は実行記録を作り直して再実行（上限 3 回）。merge_parent は手順どおり補足コメントと報告。
- [ ] Step 7: マージ後の PR・Issue 状態を観測。工程の記録（planning.json）を更新し、セッションディレクトリの後片付け、完了報告（ループの最終報告の項目を含む）。

## 要件・原因・検証の対応

|条件|Task|観測する結果・検証|
|---|---|---|
|記号を含む正確な名前を保存・導出|1、2統合|新形式の round trip で model 完全一致、旧形式も読取可能|
|新旧/新新の取り違えを防ぐ|1、2統合|名前空間分離、記号違いを区別、独立に構成した入力|
|コメントの生成と照合が同じ変換|1、2統合|fake 作成→再投稿で自分のコメントを更新、他モデルのコメントは不変|
|不正な識別値を受け入れない|1、2統合|制御文字/空/HTMLマーカーの一時確認と既存検査|
|旧形式同士の衝突・review_file変換|対象外|Spec の除外範囲と差分を照合|

## 実行予算

能動時間360分（準備30・実装/レビュー60・検証/PR30・ループ最大3×80分）。ledger は run のセッションディレクトリ `tmp/agents/issue-375.tvb249sg/budget.jsonl`、SDD は同ディレクトリの `sdd/2026-11-10-issue-375-model-agent-id/`。phase 境界、50%/100%、worker 失敗直後を checkpoint にする。runner implement の役割期限90分、レビュー45分。pi は timeout 無しの同期呼出しで待つ。共有 worktree/検証には事前打切りを適用せず、runner の停止確認を使う。実装1依頼、Taskレビュー1、全体レビュー1、各レビューの修正は規則内で同担当に最大1依頼を基本とする。ループは指定3レビュアー/最大3サイクル。同じ信頼性失敗の再試行は1回まで、安全失敗・担当失敗・予算100%は停止。既存の停止条件を緩めない。

継続 phase（2026-11-12・Task 3）: 上記 360 分は round 2 時点で超過し await-user で停止。利用者の「マージまで必ず完了」の明示指示で続行を許可され、旧 ledger は resume+end でクローズ（履歴は補正しない）。新 ledger `tmp/agents/issue-375.r6210n1p/budget.jsonl` で能動 180 分（Spec 更新・外部 Spec レビュー 30・Plan 更新・統合検証 30・ループ枠 120＝期待値 2 サイクル×（レビュー 45＋計画・修正 約 15）。max-cycles 3 は上限で、3 サイクル目は予算に余裕がある場合だけ。予算 100% の停止が優先）。checkpoint・再試行上限・停止条件は同じ。完了済みの検証・有料レビューは同一 HEAD・base で再利用する。ループのレビュアーはこの run の指定 2 担当。

## contingency（代替策）

最初の RED が fixture/API の前提違いなら意味を保つ最小修正を ledger に残す。仕様の意味が変わるなら停止する。過去記録の互換問題は既存の導出を維持する案に戻し、新スキーマや移行を増やさない。担当失敗なら self に切り替えない。新しい依存・競合・base 移動、公開前の秘密検査失敗は停止し資源を報告する。範囲縮小候補は別の旧モデル間衝突の修正を除外した現範囲であり、必須条件の黙示の削除はしない。

## 実行記録（2026-11-10）

- Task 1 の初回依頼は、RED（7 failed / 105 passed）と GREEN（対象112件・全体1394件）を観測した後、認証エラーで失敗した。停止は確認済みだが、有効な最終結果が無いため受け入れなかった。5ファイルの未コミット差分をローカルに保全した。
- 利用者が同じ担当・割り当てで救出と続行を明示したため、差分と同じ要件を新しい依頼に渡した。担当はすべて `pi_opencode-go_deepseek4-flash_max`、runner の実測は `opencode-go/deepseek-v4.1-flash`、effort=max。self への切替や失敗記録の変更はしていない。
- 救出の依頼は934.36秒で成功し、`6254005961ffdcbbc074434771cf01212a08f9d5` を helper で受け入れた。タスクレビューで同じ守りの重複テスト（D）が1件指摘され、規約とコードを照合して採用した。
- 同担当の修正依頼は76.29秒で成功し、`adad6fdd3e61d90f889349a48af3f3301461f3b9` を受け入れた。対象のテストを代表例へ整理し、controller の対象テスト109件が成功。修正部分の再レビューで指摘対応済み・新規不具合なしを確認した。
- 成功した2依頼は記録とログを保全して cleanup を実施し、残した資源は無い。初回失敗のworktreeは未コミット差分があるため cleanup が拒否し、削除せず保持している。
- Task 1 は完了。Task 2 の全体レビュー・最終コミットでの全検証・公開・指定ループは、この記録時点では未実施。Spec・Plan の状態は draft のままで、内容承認は記録しない。

## 実行記録（2026-11-11・引き継ぎ）

- Task 2 の公開（Gitleaks・push・PR #385 作成・head/base 照合）と初回ループ（3 レビュアー、round 1・2）は完了。round 1 は base 移動、round 2 は予算超過で停止（マージなし）。詳細は Spec の「レビュー記録」「統合検証の履歴」と handoff `20261111T012823Z-issue-375-pr385-finalization` を参照。
- main 追従の統合検証は `b0deb7f8` まで完了（全 1446 件成功）。L-1 は隔離再現で skip を確定。

## 実行記録（2026-11-12・継続 run）

- 利用者の明示指示（PR #385 の続行・main 追従・マージまで完了・新担当指定）を受け、Task 3 を追加。旧予算 ledger をクローズし、継続 phase の新 ledger（180 分）を開始。
- 開始時の状態: feature worktree は clean・head `c9fb38e4`（PR head と一致）。origin/main は `23cf4bc7`（検証済み base `b0deb7f8` から進行）。claim ref なし・他セッションの競合なし。
- Spec にこの run の実行許可・L-1 引き継ぎ・統合検証履歴・残作業を反映。Plan に Task 3・継続予算・この記録を追記（このコミット）。
