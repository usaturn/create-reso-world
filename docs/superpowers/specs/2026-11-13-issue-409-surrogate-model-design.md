# Issue #409: 単一サロゲートを含むモデル名の拒否を回復する

## 管理・実行許可

- 状態: `completed`（実装・検証・レビューの完了。内容の承認を記録するものではない。マージ結果は状況コメントと完了報告に記す）
- 対象: https://github.com/usaturn/create-reso-world/issues/409
- 利用者の明示指示:
  ```text
  #409 --merge
  --spec-review devin_swe2_max
  --implement pi_openai-codex_gpt6-terra_xhigh
  --assign implement=pi_openai-codex_gpt6-terra_xhigh
  --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default
  ```
- 通常の設計判断、検証、commit、scan、push、PR 作成、および PR 修正ループの finalize.py によるマージを許可された範囲とする。安全境界・仕様の意味を変える判断は含めない。
- 適用規約: ルート `AGENTS.md`、`.pi/APPEND_SYSTEM.md`、issue-to-pr。
- 実装・文書の保存先: create-reso-world の同一 worktree。同テーマの既存文書はない。#375 の Spec は過去の別テーマの記録として変更しない。

## 目的・現状

#385 のモデル ID 拡張で、従来形式に収まらないモデル名は元の UTF-8 バイト列の SHA-256 から ID を作るようになった。この `model.encode("utf-8")` は JSON の `\ud800` エスケープから生じる単一サロゲートで `UnicodeEncodeError` を送出する。呼出元は `RecordError` を捕捉するため、コメント ID 付きの拒否でなく未捕捉のトレースバックになる。

`agent_id_for()` でエンコード失敗だけを `RecordError` に変換し、既存の呼出元による拒否を回復する。不正なモデル名に ID を作ることはしない。正常なモデル ID、記録スキーマ、信頼判定、コメントの選択・除外、書込対象は変えない。

## 調査・根拠

- 捕捉対象: `_check_planner()` → `validate_record()`、`collect_records()` → `read_state()` → CLI `fold`、CLI `validate`、upsert の `sanitize_agent_id()`。
- 発生箇所: `.agents/scripts/review_records.py` の `agent_id_for()`、SHA-256 用 encode。
- CPython の現行文書を Context7 CLI で確認（`/python/cpython`、`Doc/builtins/stdtypes.rst`・`Doc/library/codecs.rst`）。strict UTF-8 はサロゲートをエラーにし、JSON decoder は対を成さない `\uXXXX` を文字列へ復号できる。
- 準備時の関連テスト: 109 passed、終了コード 0。
- 捕捉した base `9c3ad41e` の feature worktree で、v2 の正常記録の `planner.model` だけを `x\ud800y` にした信頼済みコメントを `fold` に入力。終了コード 1、`UnicodeEncodeError`、コメント ID の診断なしを再現した。
- 再現・文書取得ログ: `/workspaces/reso-world/tmp/agents/issue-409.8hux350m/`（コミットしない）。

## 検討案・決定記録

### D1: 例外変換の境界

- 選択: `agent_id_for()` 内で UTF-8 encode の `UnicodeEncodeError` を捕捉し、`planner.model:` で始まる安全な問題文の `RecordError` にする。問題文へ生の不正文字列を埋め込まない。
- 別案: 各 CLI・読取・書込 caller に `UnicodeEncodeError` の捕捉を追加する。
- 理由: 原因が一つなので、共通境界一箇所で既存の例外仕様を回復し、全 caller に同じ振る舞いを適用できる。caller の取りこぼしを増やさない。
- 委任・停止条件: issue-to-pr の通常の設計判断。正常モデルの ID 変更や別欄の仕様変更が必要なら停止する。

### D2: 不正な値の扱い

- 選択: strict UTF-8 のまま拒否する。
- 別案: `surrogatepass`、置換、無視によりハッシュを作る、または全ての文字列欄へ新しい制限を導入する。
- 理由: 前者は不正な識別子の受理や異なる文字列の同一視につながる。後者は自由記述等の別原因へ範囲が広がる。今回必要なのは #375 の回帰を解消すること。
- 委任・停止条件: 他欄の単一サロゲートを含む問題は対象外として明示する。黙って受理や置換で成功にしない。

### D3: テストと証拠

- 選択: 記録コメントの読取でコメント ID を失わず `RecordError` になる S の回帰テストを、守りの実装を持つ `review_records` のテストに代表 1 件だけ追加する。既存の正常・非 ASCII 入力の対照を残す。
- 別案: 全サロゲート、全 caller、v1/v2 の組み合わせごとに追加テストをコミットする。
- 理由: 実際に起きた診断情報喪失の回帰を防ぐ。同じ守りの網羅は D なので追加しない。CLI の終了コード・upsert の拒否・除外による復旧は一時検証で確認する。
- 委任・停止条件: AGENTS.md の S/D/L 基準を採用。固定文言の写し合わせではなく実入力で確かめる。

### D4: 担当と公開

- 選択: 明示された `devin_swe2_max` で Spec レビュー後、Plan を作成し、`pi_openai-codex_gpt6-terra_xhigh` に Task を runner で依頼する。両 assignment の fallback は個人設定を保ち、検査結果はいずれも空。
- 別案: controller の self 実装、Spec の builder check、別モデルへの暗黙の切り替え。
- 理由: 利用者の明示指定。Spec レビューが builder check を代替する。失敗時に self で引き取らない。
- ループ: `inspect` は明示された 3 担当、修正担当も明示値。`self-review`・`fix-check` は設定の既定 `self`。最大サイクル数 3 は既定の適用であり利用者指定ではない。
- 委任・停止条件: 各 helper の check は終了コード 0。Spec・担当の失敗や停止未確認では停止する。

### D5: base・範囲

- 選択: `usaturn/create-reso-world` / `origin` / `refs/heads/main` の捕捉済み SHA を開始点とし、Spec・Plan とコードを同じ PR へ入れる。
- 別案: 親 checkout への編集、別 base や文書専用 PR。
- 理由: Issue に親・先行依存・要求 base・コメントはなく、同 Issue の既存 PR・branch・claim は見つからない。既定 `main` を使用する。
- 委任・停止条件: 未 push の非重複 fast-forward だけ、issue-to-pr の helper の条件と上限で追随する。push 後の base 移動では停止する。

## 受け入れ基準

1. 動作環境: Ubuntu Dev Container、uv 管理の CPython、オフラインの fixture/fake を使用。実 GitHub への不正コメント投稿や有料モデルの検証用起動はしない。
2. 実入力: 有効な v2 JSON の `planner.model` が `x\ud800y`、コメント ID 12345、信頼済み投稿者のコメント。JSON としては有効だが、モデル識別子としては不正である。
3. 防御範囲: `agent_id_for()` に渡る UTF-8 エンコード不能なモデル名を拒否する。`fold` はコメント ID 付きの診断・終了コード 65・トレースバックなし。`validate` も 65、upsert のモデル名変換は既存 `CommentError` で拒否し外部書込へ進まない。
4. 正常側: 既存 ASCII 形式と日本語等の有効なモデル名の ID・compose/extract/fold の往復は変わらない。不正コメントの `--exclude-comment 12345` では残った正常記録を従来どおり処理できる。
5. 対象外: `_text()` の全欄への新しい制約、自由記述・seat model 等の出力エンコード問題、スキーマ変更、投稿者信頼や ID 導出の刷新、他セッションの worktree の片付け。

## 変更範囲・統合責任

- `.agents/scripts/review_records.py`: encode 失敗を既存の拒否経路へ戻す最小変更。
- `.agents/scripts/tests/test_review_records.py`: S の代表 1 件。正常例は既存のものを保持。
- 本 Spec と対応 Plan のみ文書として変更。
- controller が同じ入力の解釈と、読取→診断→除外による復旧、validate/upsert の共通例外の接続を統合確認する。Task ごとのテスト成功だけを全経路の保証にしない。

## Spec レビュー記録

- helper `review_spec.py` による外部レビュー、1 回目。requested/actual agent は `devin_swe2_max`、identity は model `SWE-2 Max`、session `highly-soapwort`、CLI `3000.12.57`（provider/effort は未観測）。fallback 使用なし。
- review ID: `2dba7a1023314d4f9c04fda9d1300642`、reviewed Spec SHA-256: `3e8bd25455ac0bb844d294ae7749e99a5be11c29e1a99bfbf6d99c46432db8cc`。
- review_dir: `/workspaces/reso-world/tmp/agents/issue-409.8hux350m/2026-11-13-issue-409-surrogate-model-design.spec-review/review-1`。所要 244.527 秒、`completed`、findings/incomplete は空、attempt 終了コード 0、停止確認 true。
- 全指摘 0 件につき採否も空。設計・受け入れ基準の実質変更なし。Spec レビューが builder check を代替し、再レビューは行わない。
- `outside_changes=[]`。`unprotected_changes` は事前から不在の他セッションの登録 6 件（`/tmp/pr-review-376-2f0d17b0/worktree`、`/tmp/pr-review-376-79fe98e5/worktree`、`/tmp/pr-review-376-7f95b4e6/worktree`、`/tmp/pr-review-376-c9a6d3e9/worktree`、`/tmp/review-fix-planning.9AkFc2/worktree`、`/tmp/review-fix-planning.a6ogtH/worktree`）。対象 checkout の変更ではなく、他セッションとの因果は断定しない。これらは片付けない。

## PR #426・サイクル1の確認と結論

- 対象: https://github.com/usaturn/create-reso-world/pull/426
- 判断対象HEAD: `376fcb00182199f59feb50979e009892c4b23627`。plannerはランタイム提示の `gpt-6.1-sol` / `pi`（provider `openai-codex`）。issue-to-pr の明示 `--merge` によりreview-fix-planningを完遂する実行許可で進めた。
- 現行の本SpecとPlanを基準に確認し、同テーマの新しいSpecは作らない。この追記は最終化用の文書のみの変更で、実装・設計・受け入れ条件を変えない。

### レビュアーの構成

| ファイル | モデル / runtime | 対象HEAD | 再実行 / Mode | 推奨 | 実測レビュー時間 |
|---|---|---|---|---|---|
| SWE-2-Max.md | SWE-2-Max / devin | 376fcb001821 | true / Initial | Approve | 228.764秒 |
| deepseek-v4.1-flash.md | deepseek-v4.1-flash / pi | 376fcb001821 | true / Initial | Approve | 514.163秒 |
| claude-opus-5-5.md | claude-opus-5-5 / claude-code | 376fcb001821 | true / Initial | Approve | 114.358秒 |

入力は `/workspaces/reso-world/reviews/usaturn/create-reso-world/#426-fix-issue-409-surrogate-model/` の全3本文・候補JSON・実行記録。loopは3担当ともaccepted、rejected/retainedなし、outside_changesなし。unprotected_changesは他者の不在checkout6件で、今回の対象ではない。全候補JSONのvalidateと本文とのcheck-pairも成功した。

### 全指摘の採否・結論

- 全指摘・未検証候補は0件。解消済み0 / 対応する0 / 対応しない0。以前の判断記録も空で、引き継ぎ・見直しはない。IDを補って存在しない指摘を作らない。
- 結論2: 修正不要として最終化する。単なるApprove票数ではなく、条件ごとの実行証拠、全変更ファイルと共通境界の読解を照合した結果である。
- 追加の実装修正・テスト追加・設計見直しはない。run_roles.pyは未実行、修正後の自己レビュー0回（修正がないため）。loopの割り当てはimplementが明示 `pi_openai-codex_gpt6-terra_xhigh`、self-review/fix-checkは設定のselfだが、未実行を実施済みとしない。
- 確認済み一覧: `verified/376fcb001821.json`（review-findings/v2、全判定0、coverage.remaining空）。工程記録は投稿後に同stemのplanning.jsonへ実施した工程だけ記録する。

### 要件・共有条件と証拠

| 条件・経路 | 今回の判定 | HEADで観測した結果・証拠 |
|---|---|---|
| encode不能なplanner.modelを共通境界で拒否 | 既に満たす | SテストのRED→GREEN、再base後の統合fold/validateは65・コメント12345付き診断・stdout空・tracebackなし |
| 正常ASCII/非ASCIIのID・往復を維持 | 既に満たす | 既存テストを含む関連110件成功。旧形式の早期returnと成功時のUTF-8 bytesは変更なし |
| 不正コメント除外後の読取復旧 | 既に満たす | 正常単独と不正＋正常からexcludeしたfoldの結果が一致、正常コメント22222を保持 |
| upsertの外部操作前の拒否 | 既に満たす | compose_bodyの実入力でCommentError、正常モデルの対照成功。upsertはcompose/validate後に初めてghを呼ぶコード順序も確認 |
| 別欄の自由記述や環境拡張 | 対象外 | Specの除外範囲と一致。今回の差分は共通encode境界だけで、その原因と無関係な新制限は導入しない |

controllerが共有するモデル入力・RecordErrorの伝播・collector診断・除外復旧・writerの副作用順序を統合照合した。読み取り担当sp-reconが変更したreview_recordsとテストの全文、関連upsertの捕捉・通信順序を確認し、controllerがHEAD一致/clean状態を確認した。既存の正常fixtureにplanner.modelだけをJSONエスケープで差し替え、他の拒否条件に隠れない入力を使用。今回の修正によって影響する経路に未確認はない。

### 最終検証・base前進

初回の最終検証後、未pushの非重複fast-forwardをhelperで1回追随した。old base `9c3ad41e99bfc91e557f900a301bc6d6884edf0d` → new base `181042480de8b500126b025030255fd34640f71a`、old head `763657b8f1480415ecefc087502e1b941ae5dfa2` → reviewed head `376fcb00182199f59feb50979e009892c4b23627`。所有パスと安全規約・今回の共有入力/例外境界の前提に変更なし。必須コマンドを全て再実行し、前後clean・同一HEADを確認した。

- `bash .devcontainer/run-tests.bash`: 27本PASS、exit0。
- `bash scripts/check-layout.sh`: PASS、exit0。
- `uv run pytest tests/skills .agents/skills .agents/scripts tools -q`: 1486 passed、1209.41秒、exit0。
- 再検証・統合ログ: `/workspaces/reso-world/tmp/agents/issue-409.8hux350m/reverify-{1,2,3}.log`・`integration-after-advance.log`・`integration-result.json`。`checks.json`と`verification-current.json`でHEAD/base/コマンド/clean状態/保存ログhashを照合した。
- サイクル1は同じHEADなのでissue-to-prの再利用条件を満たす。baseを再取得し、上記new baseが現行mainかつheadの祖先であることを確認。検証したのはhead単独のツリーで、新しい組み合わせのmergeは不要。Actionsは規約どおり無効、実機受け入れの残りはない。
- Specレビューのcleanupはretainedなし。実装担当も専用worktree/run-dirのcleanup済み。実装のRED/GREEN/全体ログは `/workspaces/reso-world/tmp/agents/issue-409-implement.xi2dl71o/task-1-evidence/` に保持する。

マージ・Issue更新はまだ実施済みとせず、このSpecだけのcommit・状況記録を照合した後にfinalize.pyで行う。結果・コメントURL・ループID・最終所要時間はPRの状況記録と完了報告へ残す。
