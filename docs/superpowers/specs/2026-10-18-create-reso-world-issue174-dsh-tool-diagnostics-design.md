# Issue #174: DSH ツール結果と API 認証診断の分離

## 管理・実行許可

- 状態: completed（PR #180 の PTC 経路のレビュー修正・検証完了。実行許可に基づく完了であり、内容承認は推測しない）
- 文書・実装対象: usaturn/create-reso-world
- Issue: https://github.com/usaturn/create-reso-world/issues/174
- 調査した HEAD: `1335f410e624355cd558029bdcdad65eaa944ed8`
- 利用者の指示: `/skill:issue-to-pr #174`（issue-to-pr スキルの明示読み込みと `#174`）
- 実行許可: スキルの委任に従い通常の設計判断を推奨案で決め、検証・commit・push・PR 作成まで実施する。Spec/Plan の承認を推測しない。マージしない。
- 作業場所: `/workspaces/reso-world/.worktrees/issue-174-dsh-tool-diagnostics`
- branch: `fix/issue-174-dsh-tool-diagnostics`
- 確認用コピーは作らず、Spec/Plan を作業 PR に含める。

## 意図と根拠

DSH がファイル読み取りエラーから回復し、有効な final を返した場合に、行数やファイル名の 401/403 を API 認証エラーと誤認して回答を捨てないようにする。fallback なしの実行でも完成した回答を取得し、fallback ありでも不要な追加実行を避ける。

変更前の `_classify` は `tool_result(status=error).result` を `_diagnostic` に渡す。`_AUTH` は単独の 401/403 に一致し、構造・completed/final の確認前に `awaiting_authentication, None` を返す。HEAD 上の最小再現で 402 行は success、403 行は awaiting_authentication を確認した。変更前の DSH テストは 124 件成功した。

## 仕様

1. ファイル操作等のツール結果は任意の内容を含む。ツール結果中の数値・認証に見える文字列は、DSH のモデル API 認証失敗の証拠として使用しない。
2. `tool_result(status=error)` では、DSH の固定版が生成する承認拒否・承認待ちの理由全体に一致する場合だけ awaiting_approval とする。直接の `Error: ` と、PTC の `code run failed (exception): ToolCallError: ` に包まれた理由を同じ定義で判定する。PTC のスタック・Captured output は理由に含めない。任意のパス・本文への汎用的な承認検索は行わない。数値 401/403 を含む名前でも実際の拒否形式は成功にしない。
3. top-level `error`、非 completed の `turn_end.reason`、失敗ストリームに対する stderr の既存診断は変更しない。真の API 認証エラーは、有効な final が後続しても成功にしない。
4. completed/final・JSON payload・イベント構造・観測 identity の検証は維持する。非ゼロ終了や停止未確認を成功にしない runner の処理も変更しない。
5. 403 行、401 行、ファイル名 `401.py`、ファイル名 `403.py` の読み取りエラーを、それぞれ一つだけ含む実行で確認する。402 行を正常対照とする。
6. 実プロセスの偽 CLI が既存の session v4 fixture と有効な final を出す。上記各入力について、fallback なしで batch success と payload 保持、fallback ありでも primary 成功の 1 試行となることを確認する。
7. top-level 認証エラー、承認拒否、非ゼロ終了、identity 欠落・不一致の失敗条件を保つ。テストは実モデル・課金 API を一切使用しない。

## 変更する部分

- `tools/agent_runner/adapters/dsh.py`: tool_result の診断を承認に限定する。
- `tools/agent_runner/tests/adapters/dsh/test_adapter.py`: collector の payload 保持と真の診断の回帰。
- `tools/agent_runner/tests/adapters/dsh/fake_cli.py`: ファイルエラーを出す偽 CLI mode。
- `tools/agent_runner/tests/adapters/dsh/test_runner.py`: fallback 有無の実プロセス回帰。
- 本 Spec と対応 Plan。

## 対象外・編集禁止

全プロセスの sandbox 強化、output-dir の symlink 対応、実機 rebuild、DSH 更新、他の adapter、runner 全体、設定や共有認証情報には手を加えない。O-M1/G-M1 の診断ラベル問題は本 Issue では不採用とし、独立した持ち越し候補のまま維持する。

## 決定記録

| 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- |
| 初回: ツール結果では承認診断だけを行う（下記レビュー修正で全文判定へ更新） | 全経路の `_AUTH` を HTTP 文脈付き正規表現へ変更する | ツール本文と API の信頼境界を分ける最小修正。top-level の認証判定を弱めない | issue-to-pr の通常設計委任。真の認証エラーを成功にする必要が生じたら停止 |
| completed/final の既存検証へ進む | 有効な final があれば全エラーを無視する | final は認証・承認・終了・identity の失敗を覆せない | Issue の受け入れ条件 |
| 偽 CLI を実プロセスとして起動する回帰 | 実モデルで再現する／文字列検査のみ | batch/fallback の挙動を課金や資格情報なしで確認できる | 実モデル禁止。想定外の外部送信は停止 |
| inline の executing-plans | SDD による実装委譲 | 1 Task で fixture とテストを逐次変更する小さな修正。独立調査・最終レビューは別担当へ委譲 | issue-to-pr の実行方式選択規則 |

## 検証

- 新しい挙動テストが修正前に失敗し、修正後に成功することを確認する。
- DSH 全 124 既存ケースと新規ケースを実行する。
- README の入口（ワールドを除く）: `.devcontainer/run-tests.bash`、`scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。
- `git diff --check` とブランチ全体の読み取り専用レビューを実施する。
- 公開前に親 checkout の `scripts/scan-before-push.sh` を使い、検査した SHA のみを push する。private リポジトリの停止済み CI は確認しない。

## 初回実装の記録（レビュー修正前）

実装と検証を完了し、https://github.com/usaturn/create-reso-world/pull/180 で公開した。内容の明示承認は受けていないため状態は draft を維持する。DSH 147 件成功、全 Python 回帰 2591 件成功・1 件スキップ、33 本のスクリプトとレイアウト検査が成功した。ブランチ全体の独立レビューに修正指摘はない。詳細は対応 Plan に記録した。実モデル・実 API の動作確認とマージは行っていない。

## PR #180 レビュー修正（2026-10-19）

この節は `7000cde` までの履歴である。現行の分類・設計・証拠は末尾の「PTC の拒否ラッパーに対するレビュー修正」に記録する。

### 範囲・実行許可・入力

利用者の `/skill:review-fix-planning #180` と「Issue #176 も読んで対応して」を、現行 PR の修正・検証・自己レビュー・commit・push・状況コメントの実行許可として扱う。#176 の未マージ worktree は読まず、Issue の原因単位・両側検証・証拠の独立性を適用する。別テーマのスキル改善は持ち込まない。

対象 PR は usaturn/create-reso-world#180、現行 HEAD は `f5550936db665490aa7908b4d0f4906be479431c`。入力は `reviews/usaturn/create-reso-world/#180-fix-issue-174-dsh-tool-diagnostics/` の全4ファイル。SWE-2-Max、claude-opus-5-5、gpt-6.1-sol、opencode-go-deepseek-v4.1-flash の各レビュー対象はすべて `f5550936db66` であり、取得した PR head の祖先である。

### 全指摘の分類

解消済み **0** / 対応する **4** / 対応しない **0**（入力レビュー2件・自己レビュー2件。同一原因の経路漏れと修正による回帰を含む）。claude-opus-5-5 と gpt-6.1-sol は指摘0件。レビュー中の反証済み候補・未検証候補も読み、独立に到達条件を確認した。

| ID | 分類 | 根拠・発生条件 |
| --- | --- | --- |
| SWE I-1 | 対応する | error の read が `/approvals/cancelled.json` を含むと、有効な completed/final があっても awaiting_approval / payload None。fallback なしの正式な構成で完成回答を取得できず主要処理が失敗する（分類(a)）。 |
| DeepSeek L-1 | 対応する | `approval-cancelled.md`、`approval-unavailable.txt`、`approval-rejected.md`、`notes/requires approval.md` も同様。固定版 read はエラー内に対象パスを含めるため実在する使い方で到達可能（分類(a)）。 |
| SR-C1（反証） | 対応する | 自己レビューが `run_code` のsubject=programを発見。今回のmatcherがcommand/operationしか認めず、DSH_TOOLS_MODE=both/ptcの正式な構成で本物の拒否を成功にする回帰。collectorと偽CLI実プロセスの2件でREDを確認（分類(a)）。 |
| SR-T1（検出力） | 対応する | 同じprogram経路をfixtureと生成元15件の照合がともに落としていた。SR-C1と同じ原因であり、独立した別修正は不要。全呼出元と生成元パラメータの照合へ見直す（分類(a)）。 |

隔離 worktree（HEAD照合済み）で5つのパスは全て `('awaiting_approval', None)`、正常対照 `safe.md` は success を再現し、検証後 worktree と親ディレクトリを回収した。Low/Info、設計判断という分類や失敗側へ倒れることは、fallback なしの処理停止を不採用にする理由にはしない。

### 守る条件の設計・原因と設計判断

守る条件: ツール結果の任意データをモデルAPIの認証・承認制御と混同せず、回復済み final を保持する。一方、固定版DSHが error の理由として生成する実際の承認拒否は、どのツール・turn・後続finalでも成功にしない（completed結果の任意データは下表のとおり別扱い）。終了・停止・identity・イベント構造が不正な場合は引き続き成功にしない。

原因は「エラー本文は制御診断とみなせる」という前提をツールデータ境界へ持ち込んだこと。`4a41d95` は AUTH だけを外し、同じ前提の APPROVAL を残した。PR履歴と既存Specに以前のレビュー修正コミットはなく、規定のきっかけ1・2には該当しないが、Issue #176 に従い初回から仕組みを見直す。後続指摘は既存原因の適用漏れとして扱い、別原因・新要求とは区別する。

採用: 入力元に応じて判定を分け、tool_result は固定版DSHの生成する `Error: ...` 全文の拒否テンプレートだけで判定する。top-level error / 非completed turn_end / 失敗時stderrは従来の汎用診断を保つ。実装には共通のtool専用matcherを1つだけ置き、read/bash/他ツールのパス別例外にはしない。

| 比較案 | 判断と理由 |
| --- | --- |
| 汎用正規表現へ除外パスを足す点の修正 | 不採用。任意のパス・本文すべてを除外できず、隣の語で再発する。 |
| 制御診断とtool本文の判定を分離する | 採用。拒否文の生成元に基づく全文一致で任意部分文字列を制御として扱わない。 |
| 承認拒否の保証をなくし全toolエラーを回復可能にする | 不採用。真の拒否を成功にする回帰となる。 |
| DSH側へ構造化拒否フィールドを追加する | このPRでは不採用。headless JSONには区別がなく、別リポジトリの実装・更新が必要。 |

独立した根拠は、導入済み `@deepseek-ai/dsh@0.2.0-rc.2` の配布ソース。`dsh-tools/lib/index.js:3238-3256,3444-3485` がtool拒否を、`dsh-sandbox/lib/index.js:97-121` が昇格拒否を生成し、`dsh-headless/lib/json-stream-BA-F3lfb.js:246-253` は本文のみを投影する。`dsh-tool-fs/lib/index.js:53` はパス付きreadエラーを生成する。実装側のmatcherからfixture/期待値を生成しない。

既知の制限: headlessには構造的な拒否種別がなく、ツールエラーが拒否文全体と完全に同じなら識別不能。固定版以外の新しい拒否文・任意pluginは未対応。標準headless・固定版・approval never の公式経路を対象とする。DSH更新時には生成元との再照合が必要。実モデルの実行はしない。

### 影響経路と証拠

| 守る条件 | 経路 | 判定 | 変更前の挙動 | 確かめる assertion・実行証拠 |
| --- | --- | --- | --- | --- |
| 任意tool本文を制御と混同しない | `_classify` tool_result error（readのパス・行数、認証風・承認風の文字列） | 修正する | 承認風パスでpayload破棄 | collector: success・同じpayload/identity。実プロセス: fallback有無でprimaryの1試行。 |
| 真のtool拒否は成功にしない | tool拒否・cancel・unavailable・agent/service不在、sandbox昇格の全subject（下表） | 修正する | 汎用検索で拒否 | 独立した生成元形式の各fixtureが awaiting_approval・payload None。matcherを外した対照で負例が失敗。 |
| completedの通常結果は制御診断にしない | completed tool_result、複数turn、回復後のread | 既に満たす | finalを保持 | 完成tool本文内の拒否文・前後turnの回復をcollectorで確認。 |
| APIの認証・承認失敗はfinalに優先する | `_diagnostic` の全呼出元: top-level error、非completed turn_end、response_failed時stderr | 既に満たす | それぞれの失敗状態 | 各入口でauth/approval状態・payload None。tool側の絞り込みを共有しない。 |
| 不正な構造・finalを成功にしない | `_intermediate_event_valid`、turn順序、JSON/text finalの抽出 | 既に満たす | response_failed | 既存の異常streamテストとDSH全体。 |
| identity欠落・不一致を成功にしない | `Dsh.collect` → `read_session_identity` → runner `_collect` | 既に満たす | response_failed | 既存collectorと実プロセスのmissing/mismatched-session。 |
| 終了・停止確認の失敗を成功にしない | runner attemptのexit/state・cleanup・redaction → batch assignment | 既に満たす | 失敗／fallback停止 | 既存nonzero、timeout、cancel、unconfirmed stop、cleanup異常のDSHテスト。 |
| 拒否分類は入力状態を書き換えない | `Dsh.collect`のstdout/stderr/session読取・Receipt生成 | 既に満たす | 読取のみ | 入力準備後のwork/attempt全体（有無・bytes・mode・リンク先）を前後比較。共有リンク先・資格情報・backup・tmp sentinelも含む。外部コマンドなし。 |
| 他adapterの異なる仕様 | pi / claude_code等 | 対象外 | 別のprotocol | 同一matcherの呼出元ではなく、変更しない。 |

### 実施手順と検証方針

1. テスト先行: 承認風パスのcollector・実プロセス回帰を追加しREDを確認する。必要な挙動テストだけを書く（文書の文字列テストは不要）。
2. 実際の拒否fixtureへ差し替え、全生成形式と反対側、各制御入口・順序を検証する。tool専用の全文matcherで修正する。
3. DSH全テスト、`.devcontainer/run-tests.bash`、`scripts/check-layout.sh`、diff checkを同期実行する。失敗を直したら最終版で再実行する。
4. 拒否guardを外す対照は一意な隔離worktreeだけで行い、負例の失敗数を記録してteardownする。collectorは読取のみで状態変更途中のI/O書込みは存在しない。read I/O失敗は既存のresponse_failed経路を維持する。
5. 自己レビューは反証・PR全体・検出力の3観点を1回だけ行う。指摘を全て判定して検証後に本Specをcompletedにし、修正と一緒に1回コミットする。既存Planは初回実装の履歴として変更しない。

### 自己レビューでの再発と設計の見直し

自己レビューは反証・PR全体・検出力を読み取り専用の3担当へ委譲し、1回だけ実施した。最初のdispatchは必須scope/template不足でレビューを開始せず停止したため、正式なbranch scopeとupstream templateを付けて各観点を実行した。PR全体担当は指摘0、反証・検出力担当はそれぞれ同じprogram漏れを報告した。未実施の実モデル確認を解消したとは扱わない。

SR-C1/SR-T1は**きっかけ3（自己レビューでの再発／今回の修正による回帰）**。最初の全文matcherは生成テンプレートのsubjectを呼出元2種類の列挙と取り違えた。生成関数だけを実行しても、実装とfixtureで同じ不完全な呼出元一覧を共有していたため足りなかった。過去の初回修正 `4a41d95` は同じ前提をAPPROVALに残し、今回の未コミット修正は任意本文の検索を除いた一方で拒否の正常な可変値を制限した。

守る条件を、個々の名前ではなく「固定版の拒否生成テンプレートと、そのすべての呼出元が渡すパラメータで実際の拒否を認識し、その他の回復済みデータを保持する」と定義する。拒否の前後、同じturn／別turn、後続final、identityや停止の失敗の各位置でも前節の表の条件を維持する。

| 比較案 | 判断 |
| --- | --- |
| subject列挙にprogramだけを足す点の修正 | 不採用。別の呼出元で同じ漏れを繰り返す。 |
| 生成テンプレートの可変slotを1つのmatcherで扱う | 採用。name/mode同様、subjectも引用符・改行以外の可変部分として全文テンプレートで扱う。呼出元ごとのホワイトリストを実装に重複させない。 |
| run_code等を禁止し保証を狭める | 不採用。環境許可リストと標準headlessが既にサポートする経路を無断で削る。 |

`approveEscalation(` を導入済み全JSで検索して、呼出元から表を作り直した。bundleとtypes/ptc.jsの二重出力は同じ処理として整理した。共有stateへの書込みはない（collectorは読取→Receipt返却だけ）。制御診断・構造・payload・identity・終了/停止・redaction・fallbackの入口と失敗位置は前節の表をすべて維持する。

| 経路・入力 | 判定 | 変更前（今回の未コミット版） | assertion・証拠 |
| --- | --- | --- | --- |
| dsh-tools:serviceAskの拒否/cancel/unavailable/agent不在/service不在 | 既に満たす | 正しく拒否 | 独立した生成元5件・13件のcollector拒否fixtureで状態/payloadを確認。 |
| dsh-tool-bash:364、dsh-tool-pwsh:335 → subject=command | 既に満たす | 正しく拒否 | 生成元の拒否・cancel・unavailable・agent/service不在の5件とcollectorで状態/payloadを確認。 |
| dsh-tool-fs:1128 → subject=operation | 既に満たす | 正しく拒否 | 同じ5件とcollectorで確認。readエラー側は独立した回復fixtureも確認。 |
| dsh-tools:1194（types/ptc.js:308）→ run_code、subject=program | 修正する | 拒否後にsuccess | 公式env経路はrunner:420-436→headless/cordis.patch.yml:18。単独collector・実プロセスRED2件→GREEN、生成元5件。 |
| dsh-plugin-manager/lib/types/tools.js:32 → subject=plugin management operation | 既に満たす（最終matcher） | 狭いsubject列挙では不一致 | 標準profileへの有効化や管理処理は本修正の対象外だが、同じ生成元の5件を照合し、可変slotへの依存を検証。管理処理自体は一切実行しない。 |
| 通常のパス・行数・承認風本文、completed結果 | 修正する／既に満たす | 誤拒否／正常結果 | collectorのpayload、実プロセスのprimary1試行、snapshot。 |
| API error、非completed turn_end、失敗時stderr | 既に満たす | 汎用診断 | 各入口のauth/approval状態とpayload None。 |
| 拒否/回復の前後・同一/別turn、各停止/失敗位置 | 既に満たす | 汎用拒否・後続検証 | 順序4件と構造/final/identity/exit/timeout/cancel/stop/cleanupの既存DSHケース。 |

可変slotの一般化は、任意の部分文字列で拒否する方式へは戻さない。`Error: the user rejected escalating this ... to "..."; it stays denied, so stop and explain instead of working around it` の全文が必要である。構造情報がなく拒否全文そのものと同一のデータを識別できない制約は変わらない。

**自己レビュー後のこの設計変更・修正は再レビューしない。** 最終版で全必要検証とguard除去対照を再実行する。

### 最終結果

- 結論: **1 修正して既存PRへpush**（マージしない）。採用4件は全て修正・検証済み。Specは本ファイルを更新し、同テーマの別文書は作成しない。push・コメントの実行結果はPR状況コメントに残し、記録だけの追加commitは作らない。
- 調査担当は実DSHの配布ソース・影響経路を読み取り専用で確認した（実行テストは統合担当が行う）。
- RED: `pytest test_adapter.py test_runner.py -q -k recovered --tb=line` は **16 failed / 17 passed**。6件のcollector誤判定、fallbackなし5件のbatch failed、fallbackあり5件のagent bへの不要切替が意図した失敗。
- 自己レビュー前のGREEN: `uv run --locked pytest tools/agent_runner/tests/adapters/dsh -q` は **185 passed / 27.74秒 / exit0**。初回の状態比較テストは改行fixtureの誤記で1件失敗したため、JSONLの改行だけを直し再実行した（実装の失敗ではない）。
- 独立した実装照合: 導入済みToolRuntime.serviceAskとapproveEscalationをローカルの偽approval serviceで直接呼び、実際に生成された **15件の拒否文** を全て awaiting_approval / payload None と確認。DSH CLI・モデル・外部APIは起動していない。
- 失敗時の検証: collectorの入力状態全体をread-error成功と真の拒否の両側で比較し、不変を確認。比較範囲はwork/attempt全体、stdout/stderr、session、資格情報・backup・cache・tmp sentinel、symlink参照先・hardlink相手のbytes/mode/種類/リンク先。書込みを行う処理ではないため、途中のI/O書込み回復は対象外。
- 自己レビュー前のGuard対照: 一意な隔離worktreeに修正後の内容を写し、tool拒否判定だけを無効化。**18 failed / 8 passed / exit1**。拒否形式12件、同一/別turnの順序4件、拒否時の状態比較1件、実プロセスapproval1件の全負例が失敗し、正常側8件は成功。隔離worktreeは登録解除済み。
- 自己レビュー前の必須環境検証: `.devcontainer/run-tests.bash` は **33本PASS**、`scripts/check-layout.sh` は **PASS**、diff check成功。環境検証の同期終了コードは0（367.7秒）。スキルファイルは変更していないのでスキル用pytest追加実行は不要。
- 自己レビューの2件を上記のとおり再現し設計変更で修正した。`-k program` のREDは **2 failed**、修正後は **2 passed**。再レビューはしない。
- **最終修正後の検証**: DSH全体 **187 passed / 21.69秒 / exit0**、`.devcontainer/run-tests.bash` **33本PASS**、`scripts/check-layout.sh` **PASS**、diff check成功。環境検証は344.7秒で同期終了・exit0を確認した。
- 最終版の独立生成元照合は **25件全て成功**（tool生成元5件＋全4subject×5状態）。headless/agent/approvalの起動ではなく、ローカル偽approval serviceで生成関数だけを呼んだ。
- 最終版のguard除去対照は **20 failed / 8 passed / exit1**。拒否fixture13件、順序4件、拒否時のsnapshot1件、実プロセスtool拒否とprogram拒否2件が全て検出した。正常側8件は成功。mutation worktreeは登録解除済み。最終修正後の再レビューは未実施（規定の1回上限）。
- 実DSH＋実モデル・実APIのsmoke、更新版DSHとの互換性、有料行動評価は未実施であり、テスト成功やレビュー0件で代用しない。自己レビュー後に変えたsubjectの扱いは、最終テスト・生成元照合・対照検証を根拠とする。
- 所要時間（統合担当の実測区間）: 03:58〜04:36 UTC、検証完了まで約38分。準備・調査約9分、初回実装と対照約4分、初回環境検証・記録約7分、自己レビュー約10分、再設計・再検証約8分。公開作業の時間・SHAはPRコメントと完了報告に記載する。

## PTC の拒否ラッパーに対するレビュー修正（2026-10-19）

### 入力・分類・実行許可

利用者の `$review-fix-planning #180` と今回限りの補助指示1〜6を完遂の実行許可として扱う。スキルは変更しない。対象は同じ PR・Issue・テーマであるため本 Spec を更新し、初回 Plan は履歴のまま残す。承認を推測せず、修正・1回の自己レビュー・検証・既存PRへの通常push・状況投稿まで行う。

入力ディレクトリは同じ `reviews/usaturn/create-reso-world/#180-fix-issue-174-dsh-tool-diagnostics/`。全5ファイルを読んだ。gpt-6.1-sol は `f5550936db66`、SWE-2-Max・claude-opus-5-5・opencode-go-deepseek-v4.1-flash は `7000cde47e01`、gpt-6-astra は `7000cde47e01a`。履歴の旧対象を含め全SHAが現行 `7000cde47e01a34437c0ddf3411d34b8355a2559` の祖先であることを確認した。

| ID | 採否 | 原因との関係・根拠 |
| --- | --- | --- |
| SWE I-1 | 解消済み | `7000cde` が承認風パスを全文判定から除外。現行の回復fixtureと実プロセスで再確認し、success/payload保持・primary1試行を確認（E2）。 |
| DeepSeek L-1 | 解消済み | 同じ旧誤拒否。承認風ファイル名でも primary の payload を保持することを確認（E2）。 |
| Claude L-1 | 対応する | 分類(a)。正式な `DSH_TOOLS_MODE=both/ptc` で内側の拒否を捕捉しない program が外側のエラーに包むと、拒否した試行を正常結果として採用する。 |
| Astra H-1 | 対応する | 分類(a)。同じ原因の独立報告。collector・runner の双方に及ぶ。前回の直接 program 昇格拒否とは異なる未修正経路を含む。 |

入力分類: 解消済み2 / 対応する2 / 対応しない0。自己レビューの補足SR-D1を含む最終分類は **解消済み2 / 対応する2 / 対応しない1**。gpt-6.1-sol は指摘なし。SWE の未検証候補（将来版・任意plugin・tool本文だけのAPI失敗）は、固定版標準profileの生成元と既存の対象外条件に照合し、今回の新規要求にしない。

### 要件照合・守る条件の設計

守る条件は「回復した任意のツールデータを制御失敗と誤認せず、固定版が error の理由として返した実際の承認拒否は直接・PTCのどちらでも成功にしない」。終了・停止・identity・構造・最初の制御失敗を優先する操作順も維持する。

破れた前提は「拒否生成元の本文が外側 tool_result まで必ずそのまま届く」であり、PTC binding が内側の失敗を ToolCallError にして、そのスタックを CodeRunFailedError に包む変換境界を漏らしていた。`7000cde` 前後で、同じPTC拒否本文は旧 `_diagnostic` では awaiting_approval、現行 `_classify` では success/payload保持になる。**既存原因の適用漏れであり、修正による回帰でもある**。きっかけ1（同じ守る条件の2回目）・2（レビュー修正が生んだ回帰）に該当する。

前回 `4a41d95` はtool本文のAUTHだけを除き、`7000cde` は直接の拒否生成関数と可変subjectまでを扱ったが、生成後の例外変換を列挙していなかった。今回は生成→binding→例外化→外側整形→headless投影→collector→runner→fallbackから経路表を作り直す。collector自体の共有state書込みはない。

| 既存の約束・制限 | 今回の担当と観測する結果 | 検証 |
| --- | --- | --- |
| Spec 1・5・6 / Plan Task 1: 任意tool本文と401/403を認証と混同しない | 統合担当: 直接・PTC readのsuccess/payload、fallback有無でprimary1試行 | collectorと実プロセスの対照 |
| Spec 2・7 / PRの拒否ガード維持 | 統合担当: 直接とPTCの拒否がawaiting_approval/payload None | 生成元の独立プローブ・全拒否テンプレート・実プロセス |
| Spec 3・4: 制御診断、構造、identity、終了・停止 | 統合担当: 既存状態と優先順を維持 | DSH全体、同一/別turn、失敗後の次操作 |
| 実モデル/APIを使わず、固定版標準headlessを対象とする | 調査担当: 配布コードと偽transportのみ。統合担当が生成物を確認 | 配布版・ソース位置・生成物を記録。DSH更新・別adapterは行わない |

入力解釈・状態・操作順をファイルごとに分断しない。生成元調査担当と要件調査担当の根拠を統合担当が照合し、fake/fixtureと期待値はadapterのmatcherから生成しない。

| 直し方 | 判断・理由 |
| --- | --- |
| PTC文字列だけの別matcherを追加する点の修正 | 不採用。直接の拒否定義と二重管理になる。 |
| 拒否理由の定義を一元化し、固定版の外側形式だけを解く | 採用。直接は全文、PTCは厳密な固定prefix直後の例外先頭行を同じ理由matcherへ渡す。stack/captured outputは検索しない。 |
| PTCを禁止、または拒否保証を狭める | 不採用。既に正式なenv経路であり、既存保証を削る。 |
| durable sessionから新しい拒否判定系を追加する | 今回は不採用。捕捉済み例外や原因が失われた出力上限まで新しく失敗扱いにする別仕様となる。既存のcompleted結果はデータという条件を保つ。 |

### 影響経路・観測と証拠

実装前に作った表を、下記 E1〜E5 の実行証拠へ対応付けて更新する。V1 は `7000cde` に今回の差分を適用した版（下記SHA-256）。

| 守る条件 | 経路 | 判定 | 変更前の挙動 | 観測する結果・assertion | 検証方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- | --- |
| 真の拒否を成功にしない | serviceAsk / approveEscalationの全直接形式→tool_result error | 修正する（共通定義へ移す） | awaiting_approval | 同じ状態・payload None | 13拒否テンプレートをcollectorへ | V1/E2:直接13・PTC13形式すべてawaiting_approval、payload None。E4で26件すべて検出 |
| 同上 | PTC binding→ToolCallError→prepareException→CodeRunFailedError→tool/result→JSON | 修正する | success/payloadあり | awaiting_approval/payload None、identityを保つ | 実配布生成とPTC化13形式、実プロセス | `7000cde` 隔離worktreeで直接拒否/入れ子successを再現。V1/E2・E3:実生成4拒否も拒否/payload None。identity保持 |
| 任意データを制御と混同しない | 直接readとPTC内read、401/403、承認風パス、Captured output・stackだけに拒否文字列 | 既に満たす（修正後も確認） | success | payload/identity保持、primary1試行 | 独立生成fixture、collector/runner対照 | V1/E2・E3:read/read_403/captured_onlyがsuccess、payload保持。runnerはfallback有無で1試行 |
| 拒否の順序に依存しない | 拒否→回復／回復→拒否、同一turn／別turn→final | 修正する（PTCへ適用） | PTCだけ拒否を失う | どの順も拒否・payload None | 既存順序ケースを直接/PTCで実行 | V1/E2:8ケースすべて拒否/payload None。E4で8件すべて検出 |
| completed結果はデータ | 捕捉した例外をconsoleへ出して正常終了→completed tool_result | 既に満たす | success | success/payload保持 | 実配布生成、completedのPTC対照 | V1/E2・E3:caught_rejectionは旧版もV1もsuccess。実プロセスでもprimary1試行 |
| 拒否後に明示fallbackへ進む | collector→runner終了/identity→assignment | 修正する | primary成功でfallbackなし | 無fallbackならfailed、有ならa拒否後b成功、a payload None | 実プロセス4拒否×fallback有無 | V1/E2:8ケースでa拒否/payload None、無fallbackでbatch failed、有fallbackでb成功/2試行。E4で全8件検出 |
| 入力を書き換えない・次のcollectに状態を持ち越さない | stdout/stderr/session読取→Receipt、拒否後の正常collect | 既に満たす（修正後も確認） | 読取のみ | work/attempt/資格情報/backup/cache/tmp・リンク共有先のbytes/mode/種類/参照先不変、次の正常入力成功 | snapshotをPTCでも比較、連続collect | V1/E2:直接/PTCの拒否・回復4件で全snapshot不変、実生成8ケース後の正常collectもsuccess。E4で拒否snapshot2件が失敗 |
| 既存制御ガードを維持 | top-level error / turn_end / stderr / malformed / identity / exit / cancel / timeout / stop / cleanup | 既に満たす | 各既存失敗状態 | 最初の制御失敗を維持しsuccessにしない | 既存DSH全体・PTCと制御の前後対照 | V1/E2:233件成功。auth→PTCはawaiting_authentication、逆順はawaiting_approval。既存exit/identity/timeout/cancel/stop/cleanupテスト成功 |
| 表示末尾の切詰めでも拒否理由を保つ | headless boundJsonLine、長いcaptured logs | 修正する | PTC拒否を失う | 先頭理由が残るtruncated=trueのerrorは拒否 | 配布生成8192bytes出力、collector | V1/E2・E3:長いcaptured logsのtruncated errorも拒否。実spill後も先頭行保持（E3） |
| 原因を含まない結果の新規推測をしない | runtime output-limitで拒否理由自体が消える／programが捕捉して正常終了 | 対象外（新しい要求） | 旧版も拒否状態を復元しない | 外側errorに拒否理由が無ければ推測しない。completedの保証は維持 | 配布コードと旧/現行判定の対照。Spec 2の認識可能なerror理由とcompletedの既存仕様に対応 | E3:旧f555093とV1の双方でcaught/output-limitはsuccess。判定不能な理由を新たに推測しない既存仕様 |
| 到達しない変換を勝手に追加しない | tools.run_codeをさらに内側から呼ぶ | 対象外 | binding未公開 | dsh-tools:1401–1408でrun_codeを除外。再帰剥離しない | 配布コード・偽transportプローブ | E3:nested_run_codeはTypeError、旧版/V1とも回復可能。実配布にbindingなし |
| 別仕様を変更しない | 将来版・任意plugin・他adapter・実API | 対象外 | 既存の対象外 | 保証を広げず、成功の証拠にも使わない | 既存Spec/Plan/PRの制限と照合 | 既存の対象外を維持 |

### 実施手順

1. 実際のPTC生成物から独立fixtureを作り、collector・runner・順序・状態不変の挙動テストでREDを確認する（実在不具合の再発防止なのでテスト必要）。
2. 理由matcherを一元化し、直接全文と固定PTC例外先頭行を解析する。DSH全体と必須環境検証を実行する。
3. 安全境界のguardを隔離worktreeで1つずつ外し、対応する負例がすべて失敗、正常側は成功することを確認する。
4. 反証・PR全体・検出力の自己レビューを並列で1回だけ実施。必要修正後は再レビューせず影響経路を再検証し、結果を本表へ更新する。
5. 文書は新しい固定文言テストを作らず、構造・参照先・シナリオと実行証拠を照合する。全証拠が揃ってからcompleted・1回のcommit・秘密検査・既存PRへpush・状況投稿を行う。

### 実行証拠と独立性（V1）

対象版 V1 は `7000cde47e01a34437c0ddf3411d34b8355a2559` ＋本修正。adapter の SHA-256 は `cb601bfc9b5ad92c52fc28dcfd8def8c9aa3a5b9103ae4120b1c11136a16a685`、実生成fixtureは `aba1b951af8793d526e953f79c296b12b2008fed013a61bf34fb5a40358f58b8`。自己レビュー後にコードを変えた場合はこの証拠を無条件に流用しない。

- **E1 RED**: `uv run --locked pytest tools/agent_runner/tests/adapters/dsh/test_adapter.py tools/agent_runner/tests/adapters/dsh/test_runner.py -q -k 'ptc or approval_error_in_tool_result or real_denial or approval_classification' --tb=line`。修正前adapter＋今回のテストで **32 failed / 33 passed / 145 deselected / 3.67秒 / exit1**。失敗はPTC拒否13形式・順序4・拒否snapshot1・実生成拒否4・truncated1・制御順序1・runner8。無関係なfixture/setupの失敗ではない。
- **E2 GREEN**: `uv run --locked pytest tools/agent_runner/tests/adapters/dsh -q`。V1で **233 passed / 18.46秒 / exit0**。拒否側・正常側・後続collect・既存ガードを含む。snapshotは比較前の実状態を期待値にし、異常は拒否1個だけを入れる。collectorは読取専用であり、I/O書込み中のrollbackは存在しない。既存read失敗・中断・cleanup経路はDSH全体で再確認した。
- **E3 独立生成元**: 導入済み `@deepseek-ai/dsh@0.2.0-rc.2` に対して `node /tmp/review-fix-planning.OQFX5p/probe.mjs`、`node /tmp/review-fix-planning.OQFX5p/spill-probe.mjs` を実行、両方exit0。approveEscalation/serviceAsk→実ToolRuntime binding→実runProgram→外側dispatchToolBody→実projectJsonRunを通し、承認応答と通信だけをfakeにした。子プロセス入口を外してrunProgramをexportした一時コピーを使用し、配布元は変更していない。fixture8件は得られたJSON eventそのもので、スタックの一時ディレクトリだけ `file:///fixture/` へ正規化。adapterの定義は生成に使わない。
  - 統合担当が `uv run --locked python` から実生成13ケースを `_classify` に入力し、V1で拒否5・通常データ8すべての状態/payloadが期待値に一致。コミット済み `f555093` の `_classify` と同じ入力で対照し、拒否5件は旧版でも拒否、read承認風パス/captured_onlyの旧誤拒否はV1で成功、caught/output-limit/nested呼出不能/長い通常errorは旧版もV1も成功と確認。
  - headless投影は `tool/ptc-dispatch` を無視し、外側 `tool/result` だけを出す。20,000字captured logでは8192bytes/truncated=trueでも拒否先頭行を保持。実spill handlerは100,506→49,931→headless 8,192bytesでも先頭を保持。
  - 生成元: `dsh-tools/lib/index.js:1311–1434,3427–3487,3616–3628`、`dsh-ptc-runtime-node/lib/process.js:876–902,997–1040`、`dsh-headless/lib/json-stream-BA-F3lfb.js:12–35,245–256`、`dsh-sandbox/lib/index.js:97–121`、`dsh-spill-policy/lib/index.js:214–258`。dsh-tools SHA-256 `40f47709337c3c205d4e09e647f8588f4977e66f6d52f019b3cc7ef81159d84f`、PTC runtime `1a5631d2a92980bfc86966921c16ff1ad345f4dc1d22328753dc60c281f58cfe`。
- **E4 guard除去対照**: 一意な隔離worktree（HEAD照合済み）へV1の5コード/fixtureファイルをコピーし、`if _tool_denial(...)` 1箇所だけをFalseへ変更。`uv run --locked pytest tools/agent_runner/tests/adapters/dsh/test_adapter.py tools/agent_runner/tests/adapters/dsh/test_runner.py -q -k 'approval_error_in_tool_result or real_denial or approval_classification or ptc or real_process_state' --tb=line` は **52 failed / 22 passed / 136 deselected / 6.26秒 / exit1**。内訳は直接/PTCテンプレート26・順序8・拒否snapshot2・実生成拒否4・truncated1・制御順序1・既存実プロセス拒否2・PTC fallback8。対応する全負例が検出し、正常側と他の制御ガード22件は成功。worktree登録解除後、親ディレクトリも回収済み。
- **E5 環境検証**: V1で `bash .devcontainer/run-tests.bash` は **33本PASS**、`bash scripts/check-layout.sh` は **PASS**。05:04〜05:10 UTC、同じ同期シェルのexit0を確認。`git diff --cached --check` 成功。スキル変更はなくスキル用pytestの追加実行は不要。

広い保証文の「拒否」は既存の仕様2・completed経路と照合し、errorの理由に実拒否本文を観測できる場合と具体化した。捕捉済みのcompleted結果・原因が消えたoutput-limitを新たな拒否にしない点は旧版との実行対照があり、今回保証を狭めて指摘を解消したものではない。内容が生成元形式と完全に同一の任意データは構造タグなしには識別不能という既知の限界も維持する。


### 自己レビュー・最終照合・結論

反証・PR全体・検出力の3担当を同時に起動し、**1回**の自己レビューとして実施した。致命的な指摘は0件。検出力担当の補足も次のとおり判定し、未判定は残していない。

| ID | 採否 | 原因との関係・理由 |
| --- | --- | --- |
| SR-D1（検出力の補足） | 対応しない | 新しい要求／将来の保険。snapshotはhardlinkの相手のbytes/mode/存在を比較するがinodeによる共有関係までは比較しない。collectとidentity読取に書込み・link変更・外部コマンド実行がなく、現行で状態が変わる誤動作はない。固定文言や実装の写しのテストを増やさない採用基準に従い追加しない。 |

- 反証担当: 実配布生成で追加8ケース（Promise.all、finally、同一例外の再送出、Captured output、改行入りpath、通常Error、捕捉済みcompleted等）を作り、拒否4・受理4を同一/別turn・前後順で確認。限定プローブ72件成功。追加生成は既存fake transportを共有するが、RPCの失敗本文処理も配布コードと独立に照合。約2分25秒（読取90秒、プローブ35秒、記録・回収20秒）。
- PR全体担当: merge-base `1335f41` から現行の全差分・7変更ファイル全文とrunnerを確認。致命的指摘なし、diff check成功、V1のadapter/fixture hash一致。約1分（全文40秒、関連照合18秒）。先行したorigin/mainの逆差分は対象に含めない。
- 検出力担当: RED32・mutation52の実ログ内訳、fixture8件と実生成JSONの正規化だけの一致、実生成13ケースの状態/payloadを独自の読取プローブで再確認。致命的不足なし。約4分（コード/Spec2分、ログ/独立照合2分）。
- 自己レビュー後のコード・テスト・fixture修正は **なし**。Specの状態・履歴の区別・結果だけを追記した。V1から実行経路・入力・期待値が変わっていないためE1〜E5を維持する。2回目のレビューは行っていない。
- 統合担当は要件表と経路表を再照合。修正する／既に満たす各行にV1の対象版・入力・コマンド・観測結果があり、対象外の各理由は既存仕様と旧版実行対照に一致する。テスト件数や指摘0件を未確認の解消に代用していない。文書は全表の列構造・参照先実在・要求とシナリオ・検証内訳の一致を確認した。
- 未実施は実DSH CLI＋実モデル/APIのsmoke、将来版・任意pluginの互換性。これらを成功と扱わない。runtimeが拒否理由を消すoutput-limit、捕捉済みcompletedの既存仕様、同文データとの識別限界をPR本文にも記す。
- 結論: **1 修正して既存PRへpush**。マージ・Issue closeは行わない。採用2件は同じ原因の報告であり、直接・PTC・runner/fallbackの全対象経路を修正・検証済み。本Specを修正と一緒に1回コミットし、秘密検査したSHAを通常pushする。公開結果は状況コメントに残す。
- 統合担当の所要時間: 04:59 UTC開始、05:15 UTCごろ公開準備完了、約16分。準備/入力/原因調査約4分、設計/TDD/独立照合約3分、環境検証と証拠記録約5分、自己レビュー/照合約4分。公開所要時間はPRコメントで報告する。
- 初期再現とguard対照の隔離worktree、生成元担当・反証担当のscratchは登録解除・回収済み。検証ログは `/tmp/review-fix-planning.ECmwQM/` に一時保存し、本Specへ結果を転記後、公開・停止確認を終えて回収する。再利用した既存worktreeはこのセッションの片付け対象ではない。
