# Issue #174: DSH ツール結果と API 認証診断の分離

## 管理・実行許可

- 状態: completed（PR #180 のレビュー修正・検証完了。実行許可に基づく完了であり、内容承認は推測しない）
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
2. `tool_result(status=error)` では、DSH の固定版が生成する承認拒否・承認待ちのメッセージ全体に一致する場合だけ awaiting_approval とする。任意のパス・本文への汎用的な承認検索は行わない。数値 401/403 を含む名前でも実際の拒否形式は成功にしない。
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

守る条件: ツール結果の任意データをモデルAPIの認証・承認制御と混同せず、回復済み final を保持する。一方、固定版DSHが生成する実際の承認拒否は、どのツール・turn・後続finalでも成功にしない。終了・停止・identity・イベント構造が不正な場合は引き続き成功にしない。

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
