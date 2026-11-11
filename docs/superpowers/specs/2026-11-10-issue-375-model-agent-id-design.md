# Issue #375: 正確なモデル識別子から安全なコメント ID を導出する

- 状態: draft
- 対象: https://github.com/usaturn/create-reso-world/issues/375
- 既存 PR: https://github.com/usaturn/create-reso-world/pull/385（`fix/issue-375-model-agent-id`）
- 実行許可（初回・2026-11-10）: 利用者は `/skill:issue-to-pr` 相当の明示入口から `#375 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max` を指示した。通常の設計判断、実装・検証・commit・push・PR、指定ループ内の finalize によるマージを委任している。内容の承認とは区別する。
- 実行許可（続行・2026-11-11）: 利用者は「main が進んでいるが、途中で止めずに最後まで対応せよ」と指示した。main の進行だけでは停止せず、新しい base との統合ツリーを隔離 worktree で実際に検証して続行する。未検証の base へ記録だけを書き換えること、安全検査の省略、担当変更、予算の無断延長は許可しない。
- 実行許可（続行・2026-11-12・この run）: 利用者は PR #385 の存在を明示したうえで `/issue-to-pr #375 --merge --spec-review pi_alibaba_qwen4-max_max --implement pi_alibaba_qwen4-max_max --assign implement=pi_alibaba_qwen4-max_max --assign inspect=pi_alibaba_qwen4-max_max,pi_openai-codex_gpt6-sol_xhigh` を指示し、「ローカルの作業中のものがあれば改修して作業を続行せよ。既に main は進んでおり、さらに途中でメインがマージされる可能性があるが、追随して作業を止めずに続行せよ。途中で停止せずにマージまで必ず完了させよ」と述べた。既存 PR・worktree の続行、main 追従（実統合検証付き）、完了済み作業の再利用、この run の明示指定による担当変更、finalize によるマージまでの完遂を許可する。前 run の予算停止（await-user）はこの明示指示で解除し、継続 phase の予算は新 ledger で数える（下記「実行予算」）。安全検査・停止条件・L-1 の skip 維持は緩めない。記録: `tmp/agents/issue-375.r6210n1p/execution-authority.md`（コミットしない）。
- 捕捉 base（初回）: usaturn/create-reso-world / origin / refs/heads/main / `1f20820f0b628c707784aa6f7f55146225139fd2`。以後 main の進行に追随し、`70634b5d`・`50f0e6a9`・`b0deb7f8` との統合ツリーを実検証済み（下記「統合検証の履歴」）。この run では最新 origin/main を取り直し、隔離統合ツリーで検証してから採用する。

## 意図・原因

正確なモデル ID `deepseek-v4.1-flash:1017[1m]` は現在の `agent_id_for()` の許可文字に収まらず、レビュー後の状況コメントで停止する。モデル自体を手で短縮すると実際の担当を追跡できない。原因は、正確な識別値とマーカー向けの導出値を、旧変換で表せる範囲だけに限定していることにある。

## 仕様

1. `planner.model`、ループの controller model、コメント見出しには入力の正確なモデル名を保持する。追加の CLI 引数やモデルの手動置換は不要。
2. `agent_id_for(model: str) -> str` は既存の `/`・半角空白から `-` への置換と連続 `-` の圧縮を最初に試し、結果が既存の許可形式に収まるなら、その値を変えない。旧 v1/v2 記録とマーカーを引き続き読み取れる。
3. 旧変換で表現できないが既存の単一行識別値として有効なモデル名は、`model--` + 元の文字列の UTF-8 バイト列に対する SHA-256 の小文字16進64桁へ変換する。旧変換は `--` を残さないため新旧の名前空間は交わらない。新形式間は SHA-256 の衝突耐性を利用する。絶対的・数学的な一意性は主張しない。
4. 空・空白のみ・制御文字・改行・HTML コメントの開始/終了マーカーは、既存の識別値検査で拒否する。山括弧だけを含む単一行名はその検査が許す範囲で受け入れる。
5. `agent_id_for()` の引数は常にモデル名であり、導出済み ID を再び変換しない。特に record-less コメントの compose→find→PATCH が同じ ID を使う。`model--...` 自体をモデル名として渡した場合は旧変換され、対応する拡張モデルの ID と衝突しない。
6. record 付きコメントも既存の compose→validate→extract/fold→upsert を通し、正確なモデル名と導出 ID の対応を保持する。信頼する投稿者・PR/head・サイクルの検査や公開前の安全検査は緩めない。

## 範囲・対象外

変更範囲は共有導出関数、コメントの導出呼出し、規則を定義する `.agents/review-records.md`、必要な回帰テスト。レビュー用ファイル名の変換、記録スキーマ、ランナーのモデル選択、マーカーの構文は変更しない。既存の `/`・空白・連続ハイフンによる旧形式同士の衝突の全面解消は対象外（互換性を保つため）。外部 API 送信を増やすこともない。

## 決定記録

|項目|選択した案|検討した別案|理由|委任指示・停止条件|
|---|---|---|---|---|
|導出|旧形式を維持し、未対応文字だけ専用名前空間+SHA-256|単純置換、全モデルをハッシュ化|単純置換は別モデルの同一視、全変更は過去記録の検査・更新を壊す|通常の設計判断の委任。履歴の破壊は不可|
|入口|正確なモデル名をそのまま受理|起動前拒否、別 agent-id 引数|拒否は目的の機能停止を解消せず、別引数は不要な運用負荷|既存の安全な識別値の拒否は維持|
|実装担当|runner の pi_opencode-go_deepseek4-flash_max、fallbackなし|self|利用者の --implement。check の self=false|失敗を理由に self へ切り替えない|
|実行方式|SDD の1実装Taskを runner に依頼し統合担当が検証|inline|明示担当を守り変更範囲を一括で扱う|各依頼後に accept/cleanup。失敗は規則どおり停止|
|ループ（初回）|上限3サイクル（既定）、inspect は指定3担当、implement は指定担当|既定レビュアー|check-options 成功。template は .devcontainer/agent-runner.toml、config 指定なし。fix の self-review/fix-check は既定 self|既定値を利用者指定とは記録しない|
|続行（2026-11-12）|既存 PR #385・既存 worktree を使い、完了済み作業を再利用してマージまで完遂|新規 PR・worktree の作成、予算停止の維持|利用者が PR の存在を明示して続行を指示。重複作成・完了済み検証の繰り返しを避ける|安全検査・スキルの停止条件は維持。新しい PR・機能ブランチは作らない|
|担当（この run）|Plan 実装・Spec レビュー: pi_alibaba_qwen4-max_max。ループ: implement=pi_alibaba_qwen4-max_max、inspect=pi_alibaba_qwen4-max_max,pi_openai-codex_gpt6-sol_xhigh|初回指定の維持|利用者の 2026-11-12 の明示指定。check-options・implement check・spec-review check 成功（fallback は設定どおり空）。実装は完了済みで、この指定は残作業（Spec レビュー・ループ内の修正）に適用する|失敗を理由に self へ切り替えない。spec-review の失敗を builder check で代えない|
|L-1 の扱い|round 2 の skip を引き継ぐ（inherited）|再検討・例外形式の改善|隔離再現で旧版も書き込み前に停止することを確認済み。新しい根拠がない（round-records の引き継ぎ規則）|有効な UTF-8 の通常入力で停止・誤更新・状態破損・失敗の成功扱いが確認された場合だけ見直す|
|Spec レビュー|外部担当 pi_alibaba_qwen4-max_max（review_spec.py）|self、省略|利用者の --spec-review 明示指定|レビュー失敗は停止。builder check では代えない|

## 検証

旧形式と新形式の名前空間分離、同じ見た目に置換される異なるモデル名の区別、正確なモデル情報の保存、別コメントの誤更新を防ぐ実行テストは S（取り違え・上書きの防止）として残す。単に未対応名で例外を出さなくなること、制御文字拒否の単独確認、文書文言などは L/F のため新規の恒久テストを増やさず、実行確認と差分確認で代える。実 GitHub はこの run の PR/レビューでのみ使用し、回帰テストは fake GitHub を使う。

## レビュー記録（引き継ぎ）

実装は完了済み（commit `62540059`・`adad6fdd`、記録の公開 head `c9fb38e4`）。初回実装担当はテスト後に認証エラーで失敗したが、失敗結果は受け入れず、差分を保全して同じ担当の新しい依頼で検証・commit・取り込みを行った。重複テスト（D）の指摘は同じ担当が修正し、再レビュー済み。

|サイクル|内容|結果|
|---|---|---|
|round 1（2026-11-10）|3 レビュアー（claude-opus-5-5 / claude-code、SWE-2 Max / devin、deepseek-v4.1-flash / pi）が head `c9fb38e4` をレビュー。全員 Approve|base 移動（`1f20820f`→`70634b5d`）で結論 3 停止。L-1 は未確認のまま記録。https://github.com/usaturn/create-reso-world/pull/385#issuecomment-6776030964|
|round 2（2026-11-10）|同一 head のため reuse（有料レビュアーの再起動なし）。L-1 を隔離再現で独立確認|L-1 は skip（致命的でない）。停止理由は base 移動ではなく引き継ぎ予算 360 分の超過。https://github.com/usaturn/create-reso-world/pull/385#issuecomment-6777027153|

- `SWE-2-Max#L-1@c9fb38e4c9dc`（単一サロゲートの例外形式）: 隔離した PR head と旧 base でサロゲート 3 種と正常入力を実行。新実装は `UnicodeEncodeError`、旧版は `RecordError` で、どちらも POST/PATCH などの書き込み前に停止する。有効な UTF-8 の通常モデル名での機能停止・誤結果・誤更新・失敗の成功扱いはないため、致命的な指摘に該当せず skip。証拠: `tmp/agents/pr385-complete.bo8wtrs9/reproduce-surrogates.log`・`reproduce-surrogates.py`（コミットしない）。この run は新しい根拠がないため inherited で引き継ぐ。
- レビュー本文の保存先: `reviews/usaturn/create-reso-world/#385-fix-issue-375-model-agent-id/`。
- この run の Spec レビュー（pi_alibaba_qwen4-max_max）とループのレビュー記録は、実行後にここへ追記する。

## 統合検証の履歴

main の進行に追随し、いずれも隔離 worktree（mktemp の一意ディレクトリ）で PR head と base を merge したツリーを実検証した。統合 commit は push していない。

|base|結果|証拠（コミットしない）|
|---|---|---|
|`70634b5d`|全体 pytest 1394 件成功|`tmp/agents/pr385-complete.bo8wtrs9/next-*`|
|`50f0e6a9`|全体 pytest 1435 件成功（6 組分割）|同上|
|`b0deb7f8`|全体 pytest 1446 件（71 モジュールを 16 組分割、重複・除外なし）・Dev Container 27 件・配置検査・diff 検査成功。全 19 コマンド終了コード 0|`tmp/agents/pr385-complete.bo8wtrs9/third-checks-final.json`・`third-evidence-final.json`・`third-*.log`|

この run では最新 origin/main を base として同じ方法で検証し直す（検証記録の base だけを書き換えない）。検証の標準入口:

```bash
uv run pytest .agents/scripts/tests/test_review_records.py .agents/skills/review-fix-planning/tests/test_upsert_pr_comment.py -q
uv run pytest tests/skills .agents/skills .agents/scripts tools
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
```

## 実行予算（継続 phase・2026-11-12）

初回の能動時間予算 360 分（ledger `tmp/agents/issue-375.tvb249sg/budget.jsonl`）は round 2 時点で超過し、await-user で停止していた。2026-11-12 の利用者の明示指示（マージまで必ず完了）により続行を許可され、旧 ledger は resume+end でクローズした（履歴の補正・リセットはしない）。継続 phase は新 ledger `tmp/agents/issue-375.r6210n1p/budget.jsonl`（能動 180 分）で数える。内訳の目安: Spec 更新・外部 Spec レビュー 30 分、Plan 更新・統合検証 30 分、ループ（最大 3 サイクル ×（レビュー 45 分＋計画・修正））120 分。checkpoint は phase 境界・50%・100%・worker 失敗直後。同じ信頼性失敗の再試行は 1 回まで。安全失敗・予算 100% は停止（「途中で停止せずに」の例外）。完了済みの検証・有料レビューは同一 HEAD・base で再利用し、セッション交代だけで繰り返さない。

## 残作業と完遂手順（この run）

1. この実行許可・引き継ぎ記録の Spec 反映（このコミット）と Plan の更新。
2. `--spec-review pi_alibaba_qwen4-max_max` の Spec レビュー（review_spec.py）。採否を反映して commit する。
3. 最新 origin/main との隔離統合ツリーで検証し、記録する（head は文書 push 前の HEAD）。
4. Gitleaks 検査済み SHA を既存 PR #385 の head ブランチへ fast-forward で push する（新しい PR は作らない）。
5. 利用者の指定（inspect=pi_alibaba_qwen4-max_max,pi_openai-codex_gpt6-sol_xhigh、implement=pi_alibaba_qwen4-max_max）で既存 PR のループを start する。終了済み run の記録は reuse 判定に任せ、--fresh-review は足さない。
6. ループ内の review-fix-planning 完遂で採否・検証・状況コメントを行い、結論 2 なら Spec を `completed` にした Spec 1 ファイルだけの直接の子コミットを載せ、finalize.py --spec-commit でマージと関連 Issue の更新を行う。head/base・merge 第一親の照合は省略しない。
7. マージ後に PR・Issue の状態を観測して報告する。L-1 の skip は新しい根拠がない限り維持する。
