# Issue #420: Spec/design cleanup の削除前メタデータ検査

## 管理・実行許可

- 状態: `draft`。実行許可であり内容の承認ではない。
- 対象: https://github.com/usaturn/create-reso-world/issues/420
- 利用者指示: `#420 --merge --spec-review devin_swe2_max --implement pi_openai-codex_gpt6-terra_xhigh --assign implement=pi_openai-codex_gpt6-terra_xhigh --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default`（改行を空白で表記）。
- 許可範囲: 通常の設計判断、指定担当での Spec レビュー・実装、検証、commit、scan 付き push、PR 作成、指定レビュー修正ループ内の finalize によるマージ。実機操作・他セッションの回収・任意の記録修復は許可に含めない。
- コード・文書とも usaturn/create-reso-world。同一 worktree/PR。origin / refs/heads/main / `9c3ad41e99bfc91e557f900a301bc6d6884edf0d` を捕捉。親 Issue・要求 base・未完了依存・競合 PR・番号一致の branch/worktree/claim は確認時になし。

## 意図と現状

保存済み request が JSON として読めても、削除成功証拠に必要な review_id/spec_sha256 が欠けると、初回 cleanup は worktree を削除した後に callback が失敗する。成功証拠が残らず、request を復元しても通常 cleanup は証拠のない missing を拒否し続ける。正常な request が自然に欠落するとは確認していない。対象は保存済みメタデータの不完全化・破損・手編集である。

原因は「副作用後に使う識別情報の形と対応を、副作用前に確定していない」こと。対象経路は review_spec.cleanup → implement.remove_attempts → on_removed → _cleanup_success/_cleanup_event と、同じ cleanup に委譲する review_design.cleanup。implement の一般 cleanup や runner 本体の仕様は変更しない。

## 方式の比較・決定記録

| ID | 選択した案 | 検討した別案 | 理由 / 委任・停止条件 |
|---|---|---|---|
| D1 | cleanup 専用の読取事前検査で、証拠作成に必要な入力を最初の削除より前に確定する | callback の KeyError だけ捕捉する / 保存済み request 全体の新形式への移行 | 削除後の捕捉では証拠が失われる。保存形式変更や submit/decide 全体の改修は不要。通常の設計判断として選択 |
| D2 | 識別情報の型と、利用可能な保存済みレビュー・Spec 写し・batch の対応を確認する | 非空文字列だけ確認 / 現在の編集後 Spec や HEAD と照合 | 型だけでは別レビューの識別情報を証拠にできる。cleanup はレビュー後の Spec/HEAD 更新を妨げないよう保存済み記録を使う |
| D3 | 不正メタデータは lock 作成・receipt 再追記・削除より前に拒否する | ロック取得後に検証 / 不正値を自動補完 | 対象・既存 ledger を変更せず、復元後の通常回収を可能にする。補完・過去証拠の捏造はしない |
| D4 | CleanupInputError の既存 retained/records 形式を使う | traceback の整形だけ / 新しい回復コマンド | 保持対象・照合先・理由を完全パスで示す。正常結果の形は変えない |
| D5 | 同じ守りの代表 S テストを一件にまとめ、広い変種・design/fallback は一時検証と既存検査で補う | 不正値の全組合せや文言・終了コードだけの恒久テスト | AGENTS.md の S/D/L/F 基準。正しい入力の cleanup→再実行 no-op も同じ流れで確かめる |
| D6 | 指定 Spec レビューだけを行い、builder check/設計レビューは追加しない | 設定から暗黙に設計レビューも起動 | 明示 --spec-review=devin_swe2_max、fallback=[]、self=false を check 済み |
| D7 | Task ごとに指定 runner 実装担当へ直列依頼し、controller が統合・Task review を行う | 同時書込 / 担当失敗時に self が引き取る | --implement の明示値 pi_openai-codex_gpt6-terra_xhigh、fallback=[]、self=false を維持。担当失敗は停止 |
| D8 | PR 後の指定ループ1サイクル目を最終ブランチレビューにする | PR 前後に同じ全体レビュー | --merge の規則。max_cycles=3 は既定。inspect の3担当・fix implement は利用者指定、self-review/fix-check=self と fallback=[] は設定の適用 |

## 削除前検査の仕様

1. cleanup が参照する保存済み request の mode、review_id、spec_sha256、runner_dir、request.repository/spec_path を、欠落・null・不正型を含め検査する。mode は self/external、識別子は空白だけや NUL を許さない文字列、spec_sha256 は保存済み Spec 写しの SHA-256 として成立する値、パスは使用前に絶対パスとして解釈可能な値とする。external には runner_dir が必須。削除証拠へ渡す値について、削除後にはじめて型検証や必須キー参照が失敗する状態を残さない。self は削除しない既存仕様を保つ。
2. 保存済み review.json の mode と request の mode を対応させ、構造化 result がある場合は種類別 result の検証と review_id/spec_sha256 の一致を確かめる。Spec の照合は review_dir/spec.md の生バイトに対して行い、レビュー後に編集された元 Spec を基準にしない。失敗した試行の不正 payload はレビュー失敗の正常な記録でもあるため、それを有効なレビュー結果として採用・補完しない。result が無い正規の失敗レビューを、成功 result 必須という理由だけで回収不能にしない。
3. batch/試行と削除対象・証拠の対応には既存の厳密な BatchResult 検証、path→試行 map、private evidence/receipt、common-dir 照合と分類を維持する。新しい事前検査は副作用前に削除証拠の必要条件を満たすかを確かめるものとし、任意の破損記録を推測修復する仕組みにしない。
4. 識別情報不正を検出した場合、worktree 実体・Git 登録・runner-dir・既存 ledger/runner メタデータ・CODE_ROOT・Spec を変更せず拒否する。cleanup.lock や成功証拠、cleanup.jsonl を新規作成・追記する前に止める。CLI は既存の構造化エラーで reason、retained（読取記録から確定できる全試行と runner-dir）、records（request/review/receipt/既存 sidecar/試行 request 等）を返す。対象を確定できない破損では推測せず、確定できる照合先を示す。
5. 一時 fixture の不正 request を元の生バイトへ戻した後、通常の別 CLI プロセスから全正規対象を回収でき、再実行は no-op になる。通常 cleanup の証拠保存→JSONL 追記、再追記による復旧、再出現・証拠なし missing の拒否は変えない。

## 受け入れ基準

- 動作環境: Linux Dev Container、uv、実 Git worktree、実 agent-runner＋fake adapter/CLI。テストでは実モデル・資格情報・実サービスを使わない。
- 実入力: 日本語・複数行（CRLF を含む）の保存済み Spec/Issue、非 ASCII を含む runner パス、成功単一試行と失敗 primary＋成功 fallback。saved request の review_id 欠落、spec_sha256 欠落、review_id=null/型不正を扱う。通常対照も必須。
- 防御範囲: Spec/design 共通 cleanup の削除前メタデータ検査、削除対象・保存済み記録との対応、拒否後の復元→回収→no-op、全保持対象の報告。private receipt/証拠、common-dir、symlink、停止未確認、JSONL 単発障害復旧の既存拒否・復旧を維持する。
- 対象外: 他セッションの実資源回収、runner/implement cleanup の再設計、同時手編集に対する新しいトランザクション機構、署名・真正性認証、証拠保存前 crash の自動復旧、過去に証拠なしで消えた対象への成功証拠の後付け、既存失敗記録の書換え。
- 過去に証拠なしで削除された対象は retained のまま、完全パスと照合先・理由を示す。元 request を直すだけでその過去の消失を回復済みにしない。本修正の復元可能性は、事前拒否でまだ削除していない対象についての保証である。

## 既存記録の訂正と検証方針

#390 Spec の「破損 request では削除前に止まる」という一般化は、不正 JSON・mode/runner_dir 欠落の観測に限られる。#420 が示す review_id/spec_sha256 欠落・null では削除後失敗であり、その一般化は成立しない。本 Spec で訂正し、過去の採否・実行証拠は書き換えない。PR #419 の回帰とは扱わない。

恒久テストは、識別メタデータの欠落を代表に、削除・登録・記録の無変更と復元後の通常 CLI 回収/no-op を実 runner＋fake で確かめる S を置く。同じ守りの variant や design への複製を増やさず、Issue の他代表入力・fallback・正常対照は一時検証にする。対応不一致の新しい守りに独立した S の損害がある場合は、同じ受け入れフロー内で必要な代表だけを追加する。既存の安全 S テストは削らない。

検証入口は README の `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` と関連 pytest。一時検証とログは SESSION のみ。ベースラインは関連 pytest 132 passed / exit 0（608.21 秒）、`/workspaces/reso-world/tmp/agents/issue-420.xlpq2lqf/baseline.log`。GitHub Actions は無効のまま。
