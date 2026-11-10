# Issue #370: 承認待ちの構造化された根拠を診断へ残す

## 管理・実行許可

- 状態: `completed`。実装・検証・PR #384 の採否確認を完了。内容の承認は未取得であり、issue-to-pr / review-fix-planning の実行委任を承認と混同しない。マージ・Issue更新の結果はこの文書では先取りせず、PRの状況コメントと最終化結果で記録する。
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

準備時の関連テストは58件成功、終了コード0（`/workspaces/reso-world/tmp/agents/issue-370.kiyh524z/baseline.log`）。

2026-11-10 再開: 利用者の残存成果からの続行指示に基づき、認証待ちで終了した旧担当の未コミット差分を救出し、同じ指定担当へ再依頼した。`d3eca560` で正式成果を取り込み、Taskレビューで再現した診断の認証優先の回帰と重複テストを `9f838ec4` で修正した。既存の認証分類を保持しながら承認根拠を保存するため、設計の認証優先は変更していない。

調整役の関連テスト69件と実adapterによる認証優先の修正前後の対照は終了コード0。実装担当は回収後の保存診断を含むRED/GREENと関連回帰の成功を報告し、Taskの修正レビューは指摘2件を解消済みと判定した。全体の検証・レビュー・公開は別途記録する。証拠と救出パッチは `/workspaces/reso-world/tmp/agents/issue-370-recovery.evovwtrp/`、元の進捗・予算は `/workspaces/reso-world/tmp/agents/issue-370.kiyh524z/`。元の承認済み版はなく、内容の承認は記録していない。

## PR #384 レビュー修正ループ: サイクル1

- 実行許可: 利用者の明示`--merge`、指定実装担当・inspectの3担当、および「main が進んでいるが、途中で止めずに最後まで対応せよ。また、今後も最後に main を確認した時より進んでいても、最後まで対応せよ」。mainの前進では検証を省かず、新しい先端との組み合わせを再検証して続ける。
- planner: `openai-codex/gpt-6.1-sol`（pi）。検証・採否は調整役が行い、独立reconで診断とrunnerの接続を確認した。
- 対象HEAD: `d43fefa6d040f022500919acb2ccb9a175adc6fe`。同じHEADを3レビュアーとも今回レビューし、失敗・却下はない。

| レビューファイル | モデル / runtime | HEAD | 今回実行 | 推奨 |
|---|---|---|---|---|
| claude-opus-5-5.md | claude-opus-5-5 / claude-code | d43fefa6d040 | yes | Approve |
| SWE-2-Max.md | SWE-2-Max / devin | d43fefa6d040 | yes | Approve |
| deepseek-v4.1-flash.md | deepseek-v4.1-flash / pi | d43fefa6d040 | yes | Approve |

### 全指摘と採否

解消済み0 / 対応する0 / 対応しない4件（重複をまとめた2論点）。重大度ラベルや票数ではなく、現行HEADの事実とreview-fix-planningの採用条件で決定した。

| 出典 | 判定 | 根拠・見直す条件 |
|---|---|---|
| claude-opus-5-5#L-1@d43fefa6d040 | 対応しない | denialと別原因が共存すると、認証以外のrate_limit/connection/sandboxがcauseではapprovalになることを実adapterの隔離fixtureで再現した。有効な拒否根拠を優先する設計4と一致し、別原因を優先すべきかは仕様・設計の是非である。成功化・秘密露出・破壊的操作・主要処理停止は起こらない。別原因を優先する利用者の名指し指示、または具体的な致命的損害の再現で見直す。 |
| claude-opus-5-5#I-1@d43fefa6d040 | 対応しない | records.mdのapproval欄/分類説明の追記漏れはコミット済み内容で確認したが、列挙不足であり致命的な誤操作を指示する手順ではない。非致命的な文書追記は今回の採用条件外。名指し指示または具体的な誤操作で見直す。 |
| SWE-2-Max#I-1@d43fefa6d040 | 対応しない | 上の文書追記漏れと同じ論点。判断の記録で同じsourcesへ統合。 |
| deepseek-v4.1-flash#I-1@d43fefa6d040 | 対応しない | 上の文書追記漏れと同じ論点。判断の記録で同じsourcesへ統合。 |

既知の制約はPR本文にも記載する。情報が失われないという保証はadapterが実際に承認待ちとした安全な根拠を対象とし、同時にログへ出た認証以外の原因をcauseへ並列保存する保証ではない。原因分類全体の再設計、records.md等の網羅的な追記はここでは実施しない。

### 要件対応・検証

A1/A3は実adapter→runnerの保存→keep_diagnostic→生ログ回収後の構造情報と非漏えい、A2/A4は正常回答/同名キーの非採用とexit0での拒否、A5は関連回帰で確認済み。共有条件の統合は調整役が担当し、これらの保証を広げたり狭めたりする修正は追加していない。対応する指摘がないため、修正用の影響経路表・追加実装・run_rolesの自己レビューは該当しない（0回、未実施を成功扱いしない）。同じ条件の再発・修正による回帰の設計見直しも今回はなし。

- 元HEADの全体検証: shell27スイート・pytest1398件・配置・diff-check、すべてexit0、clean HEAD。
- mainが`1f20820f0b628c707784aa6f7f55146225139fd2`から`70634b5d1ad7bc7bab24ca6258edfed0a7c16fe7`へ進行。PR HEADへ新baseをmergeした一時ツリー`79cae3c93c26ac83c945a16e1c47475496976f7b`を作り、shell27スイート・pytest1401件・配置・diff-checkをすべてexit0で再確認した。テストのみ一時HOMEへ隔離し、実HOMEは差し替えていない。検証後に一時worktreeを回収した。
- 実adapterの採否用対照: 利用上限・隔離・接続はcause=approval、認証はauthenticationを保持、承認根拠は保存（exit0）。静的な文書照合もexit0。検証のための実CLI/APIは未使用。
- 確認済み一覧: `reviews/usaturn/create-reso-world/#384-fix-issue-370-approval-diagnostics/verified/d43fefa6d040.json`。工程の記録は同stemの`.planning.json`。入力3件の候補一覧はvalidate/check-pair成功。
- 最終投稿前にmainがさらに`50f0e6a9fb3c166efd6dfb6c8404dbf72a1a9291`へ進行したため、未公開のSpecコミットだけを更新した。PRのコードHEADは動かさず、同じHEADへ新baseをmergeした一時ツリー`249bc0b70ee960275339da0f2695d3549261c8cc`で再検証した。全収集1442件のpytestを重複しない8組へ分割し、各組固有のHOME/TMPDIRで全件1回ずつ実行、全組exit0。shell27スイート・配置・diff-checkもexit0。一時worktreeは回収済み。検証範囲は削減していない。2回目の再検証は`merge-verification-2.json`と`advanced-base-2-check-1.log`〜`advanced-base-2-check-11.log`に保存。
- 再検証記録: `/workspaces/reso-world/tmp/agents/issue-370-recovery.evovwtrp/merge-verification.json`、`advanced-base-check-1.log`〜`advanced-base-check-4.log`、`review-causes-probe.log`、`review-statement-search.log`。
- 担当時間: レビュアー実測はClaude203.4秒、Devin963.4秒、DeepSeek728.4秒（並行なので合算しない）。main統合の再検証は約819秒。plannerの採否時間は未計測。実装と自己レビューの担当起動は今回なし。

結論2: 修正不要。検証したコードHEADの上に、このSpecだけのコミットを載せ、状況コメント・秘密検査・head/baseの再確認・finalizeの照合を経て最終化する。マージとIssue更新の実施結果はPRの状況コメント・finalizeの結果・完了報告に残す。
