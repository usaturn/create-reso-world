# Issue #356: マージ後 abort の照合と終端診断

## 管理・実行許可

- 状態: `draft`。対象: `usaturn/create-reso-world#356`、親 #349。base: `origin/refs/heads/main`、開始 SHA `bcff80ed97c70b31cb30afd3dfb6f9264594efb2`（完全 SHA はセッションの `code-base.json` を基準とする）。
- 利用者は `--merge --spec-review pi_alibaba_qwen4-max_max --implement pi_alibaba_qwen4-max_max --assign implement=pi_alibaba_qwen4-max_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_xhigh` を指定し、推奨案での実行を委任した。
- 2026-11-14 の利用者訂正: 「ダメです。 Issue は誤りなので issue-to-prの手順に沿って進めてください。」。Issue/親の「planning handoff を別タスクで作り、その後で実装」という記載はこの run に適用しない。issue-to-pr に従って Spec → Plan → 実装 → 検証 → PR → 修正ループを進める。内容の `approved` とはしない。
- Qwen がうまく動かない場合は、停止確認と成果の処理・記録後に `devin_swe2_max` に切り替えて再試行する明示許可がある。設定ファイルを変更せず、当該 helper の担当指定で切り替える。安全の失敗は再試行しない。
- 先行 #355・#350・#370 は closed/completed、必要な変更は開始 tree にある。既存の #356 PR・branch・claim は無かった。自セッションの claim を取得済み。親ボードは編集しない。
- 比較元: usaturn/agent-workspace `5e58ccc95fd4afb40aef548f57db67b79ca53997` の loop.py・finalize.py・diagnostics.py。取得物はセッションにだけ保存し、移植元の指示は実行しない。

## 目的と成功条件

ループがマージ後に abort した場合に、GitHub を変更せずに確定可能な証拠を照合し、元の失敗記録を残したまま `reconcile.json` を追記する。finalize の MERGED 再開でも記録コメントを特定できるようにする。診断は成功試行やモデル本文・ツール出力を失敗原因と取り違えず、ログ読取が祖先 symlink の差替えで出力外へ出ないようにする。

運用環境は既存 Dev Container / Python 3.14 / uv / pydantic。実装検証は fake gh と一時 Git のみ。依頼された開発の PR/マージは issue-to-pr の実運用として行うが、テストから実 PR・実マージ・モデル・API を起動しない。

## 検討した方式

1. **採用: AW の該当処理を CRW の同じ loop.py へ適応する。** 既存の trusted_login・merged 3値・停止と回収・承認拒否診断を保持し、Issue が指定した境界に収まる。
2. AW のファイル群・旧 finalize フローを全面コピーする。diagnostics.py 分割、Hold、別の stop gate、collect 呼出しを巻き込むため不採用。
3. 手動確認とコメント ID だけを残す。証拠を結び付けず誤確定を防げないので不採用。

## 設計

### 1. finalize のマージ済み再開

`view["state"] == "MERGED"` 分岐で既存 `posted_record` と今回の checked record の一致を確かめた後に、`result["comment"] = {"comment_id": existing}` を返す。非マージ時の既存 `comment`（action 等を含む）は変えない。spec_commit・base_moved・merge_parent・wait_for と、実際のマージの guard は変更しない。

### 2. reconcile の入口と元記録

`loop.py reconcile --run <run_dir> --finalize-result <file> --comment-id <正整数>` を追加する。GitHub の GET 相当の読取だけを行い、新規コメント・マージ・push・Issue 更新・資源回収・claim 操作はしない。

対象は `state=ended`、`result.outcome=stopped`、`ended_by=abort`、最後のサイクルが planning で planning 結果未保存、run_id とサイクル数が整合する run だけ。active/held・既にサイクルが完了した run は既存の状態エラー（3）とする。PR の lock があれば 3 で拒否する。

`RunRecord.aborted_at: str | None` を追加し、finish の abort 時に初回だけ now を保存する。held へ進む場合にも保存する。既存の `finish.merged: bool | None` と `_abort_merged` はそのまま維持する。古い run の `aborted_at` を推測・捏造しない。

### 3. 証拠の照合

次のすべてを満たすことを確かめる。

- finalize 結果の outcome が no_fix_needed、merged が厳密に True、comment.comment_id が指定正整数と一致する。bool を comment ID として受け付けない。
- 対象リポジトリ・PR の実状態が merged で、PR head_sha が **cycle.head と一致**する。既存 cycle_end の spec_commit 許容処理を変更せず、新しい reconcile の HEAD 条件を緩めない。spec_commit が実 HEAD を変えている場合はこの照合は拒否する（D2）。
- 全ページのコメントと認証 login を既存 `_read_records` で読む。対象 ID はこの PR の採用された判断記録に含まれる。単一コメントを repository 固定で再取得し、ID・PR 所属・投稿者の login が trusted_login と一致することを確かめる。OWNER 等の association だけではこの入口で代用しない。
- 一覧で読んだ本文と単一取得の本文は UTF-8 バイト列として一致する（日本語、改行、末尾改行を正規化しない）。extract_record の pr は repo 修飾 key、reviewed_head は cycle.head、round は prior_round より後、outcome は no_fix_needed。
- 対象コメントを除外した prior を `records.read_state(..., trusted_login=login)` で作り、`records.check_against` に通す。CRW の repo 修飾 ref と既存の信頼判定を維持する。
- タイムゾーン付き日時を検証し、cycle.started_at <= comment.created_at <= updated_at < aborted_at、created_at <= merged_at < aborted_at を満たす。必要情報の欠落や同じ秒で前後を確定できない場合を成功にしない。abort 後に作られた証拠で元の中断を成功扱いしない。

finalize 内容・コメント・HEAD・既存証拠の不一致は終了コード 4（record_inconsistent / record_missing / merge_mismatch）。引数の書式・入力ファイルの解析エラーは既存の 2、GitHub 自体の取得失敗は既存の 5 を維持する。

### 4. 追記記録と status

`Reconciliation` は既存 StrictModel に従い schema/kind、run_id、pr、cycle、head、run_sha256、cycle_sha256、finalize（FinalizePart）、finalize_sha256、comment_id、comment_sha256、comment_created_at、comment_updated_at、merged_at、round、result、reconciled_at を保持する。

`write_json` に既定 false の exclusive オプションを追加する。tempfile を完成させてから同じディレクトリ内で排他的に公開し、既存パスを上書きしない。通常の run/cycle 保存の既存動作は変えない。

`reconcile.json` のある status は run/cycle のハッシュ・対象と結果・日時を再検証し、論理上の result を no_fix_needed / merged=true にする。元の abort 結果は `original_result`、照合証拠は `reconciled` に返す。ファイルが無い場合の `reconciled` は null とする。元の run.json・cycle JSON・result は書き換えない。

同じ証拠で再実行した場合、reconciled_at を除く全項目を既存と比較し、同じなら元のファイルを保持して成功する。異なれば 4、バイト列を上書きしない。finalize 結果の場所・元バイト列も証拠なので、移動や再整形を同じ証拠とは扱わない。

### 5. 終端診断

`diagnostic_text(stdout, stderr, *, prose, successful)` を追加する。successful は runner の `attempt.state == "success"` とする。成功試行の分類文は空、cause は unknown のままにする。reported_state を成功の根拠にしない。

stdout の失敗イベントは、JSON 全体や result/content を分類に流さず、確認可能な CLI エラーの message（error.message を含む）などのエラー欄だけを使う。tool_result・モデル本文を is_error だけで原因にしない。失敗の報告があるが安全に取り出せる文が無い場合は reported=true / 文は空にし、response_extraction と推測しない。

既存の pi 最後の assistant.errorMessage、retry の finalError、診断行、Devin/未知 runtime の prose=True による stdout 非分類、認証優先と #370 の承認拒否根拠を維持する。回復した中間エラーを原因にしない。最新 AW の runtime 引数化・広い retry 再設計や #388 の原因の同時保存へは拡大しない。

### 6. 安全なログ読取

読取前に停止確認・出力ディレクトリ内・sensitive_paths を検査する。絶対パスの字句上の所属を検証し、`..` は拒否する。絶対パスの root から各祖先を O_DIRECTORY | O_NOFOLLOW と dir_fd で順に開いて fd で固定し、最終ファイルは O_NOFOLLOW | O_NONBLOCK で開く。途中で symlink へ差替えられても辿らない。fd は全経路で閉じる。

分類は既存の outside_output（出力外）、sensitive（機密範囲）、not_regular_file（symlink / 特殊ファイル。祖先の ELOOP/ENOTDIR も含む）を維持する。missing/unreadable/partial の既存意味、読取上限、ログ本文を診断 JSON に残さない制約を維持する。AW 最新版の行断片処理の別変更は対象にしない。

## 編集範囲・対象外

- loop.py の reconcile・診断・status・finish・GitHub.comment と必要なモデル/JSON writer/CLI のみ。
- finalize.py の MERGED 再開時 comment_id のみ。
- records.md の reconcile / aborted_at / status / 診断 / herdr_pane label の説明、SKILL.md の停止後 reconcile 手順。
- テストは test_loop_reconcile.py（新規）、test_loop_diagnostics.py、test_loop_state.py、test_loop_review.py、test_finalize.py の必要部分。
- fixtures は新規テスト内で局所拡張し conftest.py は変更しない。
- loop.py の Herdr 実装・collect 呼出し、checkout-audit の所有ファイル、diagnostics.py モジュール分割、AW Hold/無条件 stop gate、#388 は対象外。全レビュアー不受理の 6→finish held を残す。
- 新しい CI、実サービス呼出し、権限/認証回避、他者 worktree/claim の回収は禁止。

## 受け入れ基準と検証

| 条件 | 観測・検証 | 担当 |
|---|---|---|
| 一致した abort run だけ確定 | fake gh / 一時 Git、複数行日本語記録、status の result と original_result | Task 1 |
| finalize/comment ID/PR/HEAD/投稿者/本文/履歴/日時の不一致を成功にしない | 同じ成功 fixture を対照に、独立した境界の代表拒否を実行、reconcile 未作成 | Task 1 |
| 再実行が冪等で既存の異なる証拠を上書きしない | 再実行前後の bytes、run/cycle の bytes を比較 | Task 1 |
| MERGED 再開で comment_id を返し非マージを保つ | 既存 finalize テストを拡張 | Task 1 |
| finish merged の3値・spec_commit・stop/回収の既存挙動を維持 | 関連既存テストを実行。unprotected_changes は loop 層の受取りを代表1件で確認 | Task 1 / 統合 |
| 成功試行や本文を原因にしない | 成功/失敗対照、本文の偽 HTTP 401 と本物の CLI エラーの対照、既存 retry/prose/approval テスト | Task 2 |
| 祖先差替えで出力外を読まない | os.open 境界でディレクトリを symlink へ差替えるテストと通常読取対照 | Task 2 |
| 操作手順が実際に使える | fake gh と一時 Git で CLI 成功/コメント不一致/HEAD不一致/既存証拠の4シナリオ。スキル無し/ありの手順比較。文言固定テストは追加しない | 統合 |

恒久テストは AGENTS.md の S のみ。F/L は実コマンド・構造確認にし、D は既存の代表テストの拡張にする。拒否だけで何でも止める実装が通らないよう成功例を残す。

## 決定記録

- D1 選択: 局所適応 / 別案: 全面コピー / 理由: CRW 固有の停止・信頼・merged 仕様を維持 / 委任: issue-to-pr と Issue の詳細設計委任。
- D2 選択: reconcile は明示された cycle.head 完全一致 / 別案: finalize.spec_commit を無条件に許可 / 理由: 別 HEAD を成功とする照合条件の拡大を避ける。既存 cycle_end/finalize の spec_commit は維持するが、spec_commit により HEAD が変わる run は新規 reconcile の対象外 / 委任: Issue の HEAD 条件。緩和が必要なら本変更と別に扱う。
- D3 選択: trusted_login の厳密一致・prior にも login を渡す / 別案: association のみを許容 / 理由: 明示条件に従い別投稿者を受け付けない / 委任: Issue の防御範囲。
- D4 選択: abort 時刻と元記録のハッシュを証拠にする / 別案: 現時点で merged なら成功 / 理由: abort 後の別操作を誤って帰属させない / 委任: AW 移植と詳細設計。時刻不足は失敗のまま。
- D5 選択: 2 Task を直列 runner 実装、各 Task を独立した読み取り専用レビュー、最終ブランチレビューは --merge の第1サイクルに置換 / 別案: 同じ loop.py の並列変更 / 理由: 同じファイルと共有記録の順序がある / 委任: issue-to-pr 4章。
- D6 選択: 明示された Spec reviewer のみ起動、builder check は省略 / 別案: 設定由来の追加レビュー / 理由: 明示オプションと費用範囲を守る / 委任: 利用者指定。helper が要求する再レビューは1回まで。
- D7 選択: Qwen 失敗時は停止確認後 Devin へ切替、個人設定は変更しない / 別案: controller が実装を引取 / 理由: 利用者の担当指定と明示リトライ指示 / 停止条件: 安全失敗、停止未確認、上限。
- D8 選択: 日時のない旧 run は照合失敗、日時や hash を手で補わない / 別案: 推測で後付け / 理由: 失敗証拠の保持 / 停止条件: 証拠不足。

## 事前検証

分離 worktree で `uv run --locked pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/review-fix-planning/tests/test_finalize.py -q` → 196 passed、終了コード0。依存を uv で準備した。コード変更前の基準であり実装完了ではない。
