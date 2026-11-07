# Issue #3 読み取り証跡基盤 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or, if the role tool remains unusable, superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** raw採取と通信結果の照合を独立した再利用可能なモジュールへ移し、書込みの許可と混同しない。
**Architecture:** 型付き要求→固定argv→排他的raw保存→hash/argv照合。既存のworld/state処理と分離する。
**Tech Stack:** Python3.14、標準ライブラリ、uv、pytest、ResoLoop0.2.0。
**Spec:** ../specs/2026-11-07-resonite-emission-editor-issue-3-read-receipts-design.md

- 状態: draft
- 対象: usaturn/resonite-emission-editor Issue#3、コード開始点7d34f6b77dcedb7bf4a87c85e36ba9ef25e06548。
- 文書管理: usaturn/create-reso-world。既存ツールPlanとは独立したraw基盤の補足で、S4全体の代替ではない。
- 実行許可: Spec記載のIssue続行指示とissue-to-prの通常判断の委任。新しい内容承認と記録しない。

## Global Constraints
- Python3.14以上、標準ライブラリのみ。既存live inspect/register/unregisterは無変更・無効のまま。
- 実機は使わず、実行可能な偽resoloopだけで検証する。
- completeとexecutionPermissionは常にfalse。transportSucceededは通信の結果だけ。
- 任意argv、shell、batch、retry、mutation、state/adopt/deployを受け取らない。
- world/HOME/config/保存済みパネル/登録/旧履歴を変更しない。旧tmp/worlds/toolsを探索しない。
- テストはSだけ。構文/import/文書文言/固定一覧だけのテストは追加しない。

## 受け入れ基準
Specの「受け入れ基準・防御範囲・環境」を実装担当とレビュー担当の双方へ同文で渡す。
実入力は改行・非ASCIIのJSON envelopeとbinary stderr。許可内の採取は通し、許可外起動・上書き・失敗成功化・改変を防ぐ。
全preflight/session/結線/封印資料の判定と、全証跡改変への認証は対象外。

## Review Focus
- JSON falseと整数0の混同によって失敗を成功化しない。
- 対象IDやURLにCLIオプションを混ぜても、別対象/別コマンドへ送らない。
- 同じ出力先やsymlinkを再利用して以前のrawを消さない。
- exit非0/ok=false/不正JSONでrawを残し、成功へフォールバックしない。
- argv/request/rawの整合性だけをnative/full preflight成功と表示しない。

## 実行方式と依存
1Taskのみで並列writerは無い。CODE_ROOTは準備済みのfeat/issue-3-resume worktreeを継続する。DOC_ROOTは専用docs worktree。
subagent起動がno outputかつ指定report不在で利用不能なため、実装はexecuting-plansへ切替可能。最終独立レビューは試み、失敗をcleanとしない。
公開は必要なレビュー/検証が揃うまで行わない。独立レビュー不能なら未レビューとして停止し、実機工程へ進めない。

## 実行予算
この補足の能動時間90分（既存world試験の予算は変更しない）。設計/計画15、実装30、検証15、レビュー15、保存15分。
ledger: /workspaces/create-reso-world/tmp/agents/emission-issue-3-rebuild.czcbepii/budget.jsonl
workerは同期、目安20分・保存予約5分。共有writerに外側timeoutは付けない。検証も同期で待つ。
同じ信頼性失敗の再試行は1回まで、安全失敗は全体停止。phase境界と50%/100%でcheckpoint。
代替候補: full gateまで一度に作らずraw基盤だけを切り出す（本補足で選択済み）。必要なレビューが成立しなければ公開・実機を停止する。

## contingency（代替策）
API形状差はrawを保持し、仕様の意味を保つ最小修正だけをledgerに記録する。安全境界や完了条件を緩めない。
旧資料不在は新しい封印済みDrivegate準備を後続にする理由であり、現在のrawを過去baselineと同一と仮定しない。

### Task 1: 制限したread receiptの採取・照合
**Files:** Create scripts/emission_editor/read_receipts.py、tests/test_emission_read_receipts.py。Modify README.md（内部基盤の範囲と制限だけ）。
**Interfaces:**
- ReadRequest(operation: str, url: str, target: str | None = None, depth: int = 0)。argv() -> list[str]。
- collect_read(request: ReadRequest, directory: Path, *, cwd: Path) -> dict。
- load_read(directory: Path) -> dict。同じ形でtransportSucceeded/complete=false/executionPermission=falseとresponse/request/exitCodeを返す。
- operations: discover/doctor/hierarchy/inspect/component-inspect。IDはRoot/Reso_HEX/UUID、URLは明示ws loopback:port、depthはinspect/hierarchyだけ0..64整数。
**テスト:** S。未承認起動/別対象送信/証跡上書き/失敗の成功化/改変受理を防ぐ。偽CLI以外への呼出しなし。

- [ ] Step1: 偽CLI fixtureとSテストを先に書く。正例でrawの改行/非ASCII/binary保持、明示endpoint/target、permission=falseを確認。拒否で許可外operation/target/URL、既存出力先の不変と未起動を確認。exit非0/ok=false/不正JSON、raw/hashまたはargv改変、bool終了コードの拒否を代表例で検証。
- [ ] Step2: uv run pytest tests/test_emission_read_receipts.py -q --basetemp=<session>/red を実行し、未実装によるREDを確認する。
- [ ] Step3: ReadRequest.argv、collect_read、load_readを最小実装。同期subprocessはstdin閉鎖、capture_output、shellなし、CLI内timeoutのみ。新規directory0700、固定ファイル0600/O_EXCL。起動失敗もrawとreceiptへ残す。
- [ ] Step4: 対象テスト→全uv run pytest→compileall→git diff --checkを実行し、出力と終了コードを保存する。問題があればsystematic-debugging、各S修正はRED/GREEN。
- [ ] Step5: READMEへ「内部raw基盤でありnative/full preflight成功や書込み許可ではない」と追記し、対象3ファイルだけをcommitする。
- [ ] Step6: baseからのreview packageを作り、Review scope: taskの独立レビュー。独立レビューが利用不能ならTaskをreview cleanにせず、未実施を記録して停止。問題の採否・修正はreceiving-code-reviewと既存の採用基準を守る。

## 要件照合
argv制限→ReadRequest/偽CLIの未起動、保存不変→排他的directory/file/raw検査、通信結果→失敗の正反例、改変→load_readのhash/argv整合。full gateをfalseのままにすることを全正例で確認する。
レビュー後は全差分のReview scope: branchを行う。どの段階もworldへの書き込み許可を発行しない。
