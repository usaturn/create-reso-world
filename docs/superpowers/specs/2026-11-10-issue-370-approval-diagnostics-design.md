# Issue #370: 承認待ちの構造化された根拠を診断へ残す

## 管理・実行許可

- 状態: `draft`。内容の承認は未取得。issue-to-pr の委任による実行であり、承認と混同しない。
- 対象: https://github.com/usaturn/create-reso-world/issues/370
- 利用者指示: `#370 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`、および「途中で main が進んでいる場合は留意して止めずに進めてください」。
- 許可: 推奨案の選択、Spec/Plan、指定担当による実装、検証、commit/push/PR、指定ループの finalize によるマージ。安全ガードの解除・force push・実モデルを使う検証は禁止。
- 起点: origin / refs/heads/main / `1f20820f0b628c707784aa6f7f55146225139fd2`。
- #370 はボード #349 の native な子ではない。裁定コメント https://github.com/usaturn/create-reso-world/issues/370#issuecomment-6764066965 に従い #363 → #370 → #356。#363 は PR #379 の main へのマージと state_reason=completed を確認済み。

## 目的・原因・範囲

Claude adapter は terminal permission_denials を検出すると awaiting_approval にするが、payload=None として判定根拠を捨てる。ループは success terminal を失敗テキストへ入れず、回収後は cause=unknown だけが残る。承認を迂回せず、実際に使った判定経路の安全な要約を診断へ保存する。

変更範囲は `tools/agent_runner/adapters/claude_code.py`、`.agents/skills/pr-review-fix-loop/scripts/loop.py` の診断節とそれぞれの関連テスト。runner 全体のモデル・受入判定、設定、他の子の所有文書は変えない。API/CLI の呼出仕様を変えず、既存イベント解析を使う。過去の事例の判定経路は確定せず、履歴を書き換えない。

## 設計

1. 既存 Receipt.payload → Attempt.payload の保存経路を使い、awaiting_approval の場合だけ `approval` キーに安全な診断情報を返す。失敗 payload は回答ではなく診断であり、status は変えない。成功 payload は従来どおり。
2. 最低限の情報は、判定元（permission_denials / diagnostic_text）、terminal subtype の正規化（success / error / other / 未観測）、is_error（bool または未観測）、permission_denials の有無と件数（list でなければ件数は未知）。任意の subtype 文字列をそのままコピーしない。テキスト経路は stderr / 明示 error event / terminal failure のどこを照合したかを固定の列挙値で区別できるようにする。認証優先を含む既存の状態・優先順は維持する。
3. ループは Claude の承認待ち試行からだけこの情報を受け取り、許可したキー・列挙値・厳密な bool/非負 int に再構築して AttemptDiagnostic.approval へ保存する。成功回答や他ランタイムの同名キーを診断根拠として信頼しない。異常な値・未知のキーをそのままシリアライズしない。
4. 有効な構造化された根拠があれば cause=approval とする。通常の回答本文、引用ログ、tool result に承認語があるだけでは新たに分類しない。旧結果など根拠の無い試行は既存分類を維持し、状態だけから判定元を推測しない。
5. tool_input・tool 名/ID・コマンド全文・認証値・生ログ・native session・任意のメッセージを追加保存しない。ログ読み取りの停止確認・sensitive_paths・保存先の境界・symlink/特殊ファイル・部分読取りの既存ガードを変えない。安全なメタデータの保存は新しいログ読み取りを必要としない。

## 受け入れ基準・動作環境・防御範囲

動作環境は Linux Dev Container、uv のプロジェクト環境、pytest。実 API/有料モデルをテストから起動しない。実入力は Claude の NDJSON terminal success / is_error=false / permission_denials 非空、stderr の requires approval、承認語を含む正常な複数行・日本語回答/ツール出力。拒否 fixture の tool_input と subtype に偽の秘密マーカーを含める。

- A1: 実 adapter.collect → runner の既存保存経路 → verify_reviewer → keep_diagnostic → 生ログ回収後、terminal denial と stderr 承認要求の判定元・件数・terminal 情報が安全な診断で区別できる。
- A2: 正常回答・引用・ツールデータだけの承認語や approval 同名キーで、成功を失敗扱いしたり診断根拠を作らない。
- A3: 保存結果と診断に tool_input・秘密マーカー・任意 subtype 等が漏れず、停止未確認・sensitive_paths・保存先境界の既存ガードを維持する。
- A4: exit0・最終JSON・成果物があっても permission_denials 非空は awaiting_approval のまま、レビュアーを受け入れない。
- A5: terminal denial / stderr 対照 / 成功 / 秘密入り fixture の実行検証が通り、既存 adapter/診断の回帰がない。

新たな成功判定、承認解除、全文の保存、#356 の reconcile/診断分類全体の変更は対象外。既存の API 形状を一般化して全 runtime を変更しない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 理由・委任または停止条件 |
|---|---|---|---|
| 根拠の伝搬 | 失敗時の既存 payload に小さな許可リスト | runner 専用フィールドの新設 / ループだけで再解析 | 既存伝搬を使い #370 の所有範囲に収め、ログ回収・部分読取りに依存しない。広いモデル変更はしない |
| 型と秘密 | 正規化した列挙・bool・件数のみ | 元 result の一部を無検査コピー | 診断のもっともらしい誤分類と秘密の永続化を防止する |
| 実装 | pi_opencode-go_deepseek4-flash_max、fallback なし | self | 利用者の --implement 指定。失敗を理由に別モデルへ引き取らない |
| レビュー | inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max | 既定レビュアー | 利用者指定。ループ上限3は check-options が適用した既定値、self-review/fix-check=self も既定値 |
| main の進行 | 旧/新 SHA と差分を保存し、同じ origin/main を取り込み全影響経路を再検証してから再捕捉 | SHA だけ差し替え / 更新だけで終了 | 利用者が進行時の続行を明示。未検証の SHA 差し替え・安全境界の迂回はしない。競合を安全に解消できない場合は停止 |

## 検証・結果

準備時の関連テストは58件成功、終了コード0（`/workspaces/reso-world/tmp/agents/issue-370.kiyh524z/baseline.log`）。実装後の証拠は Plan とセッション記録へ追記する。
