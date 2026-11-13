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

1. cleanup が参照する保存済み request の mode、review_id、spec_sha256、runner_dir、request.repository/spec_path を、欠落・null・不正型を含め検査する。mode は self/external、識別子は空白だけや NUL を許さない文字列、spec_sha256 は保存済み Spec 写しの SHA-256 として成立する値、runner_dir・request.repository・request.spec_path は保存済みの値自体が文字列で `Path(value).is_absolute()` を満たし、空・相対・NUL・不正型を拒否する。external には runner_dir が必須。削除証拠へ渡す値について、削除後にはじめて型検証や必須キー参照が失敗する状態を残さない。self は削除しない既存仕様を保つ。
2. mode とパス等は self 分岐前に裸アクセスを避けて読取検査し、読める review.json/batch から保持対象を収集してから構造化拒否する。review.json がある場合は self を名乗る request も mode の一致を確認し、external を self に変えて成功 no-op にしない。正規の未 submit self（review.json なし）は既存 no-op を維持する。保存済み review.json が `state=completed` の場合だけ、構造化 result の種類別検証と review_id/spec_sha256 の一致を必須とする。`state=failed` には不一致 result 自体が正常に保存されるので、それだけを理由に回収を拒否しない。Spec の照合は review_dir/spec.md の生バイトに対して行い、レビュー後に編集された元 Spec を基準にしない。失敗した試行の不正 payload はレビュー失敗の正常な記録でもあるため、それを有効なレビュー結果として採用・補完しない。result が無い正規の失敗レビューを、成功 result 必須という理由だけで回収不能にしない。
3. batch/試行と削除対象・証拠の対応は、既存の厳密な BatchResult 検証、path→試行 map、private evidence/receipt、common-dir 照合と分類に加え、request.runner_dir と batch.artifact_dir の一致、記録された試行の work_dir/request_path が同じ runner 領域の正規絶対パスであることを、最初の副作用前に確認する。runner外の別directory・同repoの別worktreeを削除対象にしない。正規の失敗・fallback・準備前失敗のnullableなpathと、準備失敗で実体が作られなかったpathを区別し、単に存在しないことだけで一律不正にしない。runner未返却のbatch=Noneは削除せず保持する。新しい事前検査は副作用前に削除証拠の必要条件を満たすかを確かめるものとし、任意の破損記録を推測修復する仕組みにしない。
4. 識別情報不正を検出した場合、worktree 実体・Git 登録・runner-dir・既存 ledger/runner メタデータ・CODE_ROOT・Spec を変更せず拒否する。cleanup.lock や成功証拠、cleanup.jsonl を新規作成・追記する前に止める。CLI は既存の構造化エラーで reason、retained（読取記録から確定できる全試行と runner-dir）、records（request/review/保存済み Spec 写し `review_dir/spec.md`/receipt/既存 sidecar/試行 request 等）を返す。対象を確定できない破損では推測せず、確定できる照合先を示す。
5. 一時 fixture の不正 request を元の生バイトへ戻した後、通常の別 CLI プロセスから全正規対象を回収でき、再実行は no-op になる。通常 cleanup の証拠保存→JSONL 追記、再追記による復旧、再出現・証拠なし missing の拒否は変えない。
6. 削除前に読む保存済み review.json/spec.md がFIFO・device・それらへのsymlink等の非regular fileなら、writerや無限入力を待たず構造化拒否する。正規regular fileの正常/failed回収は維持する。

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

## Spec レビューの記録

- helper review_spec.py / 外部担当、1 回目。review_dir: `/workspaces/reso-world/tmp/agents/issue-420.xlpq2lqf/2026-11-13-issue-420-cleanup-preflight-design.spec-review/review-1`、review_id: `61af556355184a0ba6a3961f03dcc2e8`、reviewed SHA-256: `0cf124d1cbd20161407bbfe515720451060db55b346f9d34ea8507e093f66e77`。
- requested/actual: devin_swe2_max（明示指定）、identity.model=SWE-2 Max、session_id=plaid-song、cli_version=3000.12.57、provider/effort=null、fallback=[]。elapsed_seconds=1049.446099278999。全試行停止確認済み、sensitive_paths=[]、outside_changes=[]。
- unprotected_changes は既存 /tmp の6登録と親 checkout。親 HEAD は並行作業のマージで `181042480de8b500126b025030255fd34640f71a` へ前進。保護対象 feature checkout はレビュー中変更なし。base 前進は公開前に専用 helper で所有パス・前提を照合し、許可される未 push 追随と再検証を行う。
- S1〜S4 はすべて minor として採用。S1: 保存値自体が絶対パスである要件を明記。S2: 正常生成される failed result の不一致は回収阻害に使わず、completed の対応を検査。S3: self 早期分岐・retained 収集・batch 未完了との順序を明記。S4: 照合先 spec.md を records に含める。assess/cleanup/既存 mismatch テストで根拠を確認。構築対象の変更ではなく、既存の正規失敗回収と副作用前拒否を具体化したもの。important 採用なしのため再レビューしない。

## PR #428 レビュー修正サイクル1

### 範囲・実行許可・構成

対象HEAD `06c16cf3f9d2d9874c04b562358a81863706cffd`、base `38eec3263d0558b190602d5b6dd8ffdd31874610`。planner=openai-codex/gpt-6.1-sol / pi。利用者の#420 --mergeと指定loopによる完遂の実行許可。現行Specは本ファイル1件、Planも同テーマ1件を確認し、新しい回別文書を作らない。issue-to-prの規則に従い状態draftを維持し、実装・検証・レビュー修正の完了を実行記録に残す。内容承認とは区別し、文書だけを先にcommit/pushしない。

| レビュー | モデル/runtime | HEAD | 今回再実行 | 推奨 |
|---|---|---|---|---|
| SWE-2-Max.md | SWE-2 Max / devin | 06c16cf3f9d2 | true | Approve |
| deepseek-v4.1-flash.md | deepseek-v4.1-flash / pi | 06c16cf3f9d2 | true | Request changes |
| claude-opus-5-5.md | claude-opus-5-5 / claude-code | 06c16cf3f9d2 | true | Approve |

全3担当accepted、rejected/retained/outside_changes=[]、全停止確認済み。旧/tmpの6登録だけunprotected。候補6出典を3性質へ集約し、レビュー本文/候補ペアを検査。確認済み一覧は`/workspaces/reso-world/reviews/usaturn/create-reso-world/#428-fix-issue-420-cleanup-preflight/verified/06c16cf3f9d2.json`、工程記録も同stemのplanning.jsonへ記す。

### 全指摘の採否

| 判断ID（全出典） | 区分 | 現行HEADでの根拠・判断 |
|---|---|---|
| `deepseek-v4.1-flash#H-1@06c16cf3f9d2` | 対応する | (a)実runner＋fakeで正常識別子のrequest.runner_dirだけを別絶対directoryに変えるとvictimを削除し、batch.attempt.work_dirだけを同repoの別登録worktreeへ変えても誤削除。データ消失・誤対象操作で致命的。baseでも成立したためintroducedという報告は訂正しpreexisting。ただしIssue420の保存済みレビュー/試行との対応と本PRの保証に直結する適用漏れで、無関係な既存問題として除外しない |
| `SWE-2-Max#M-1@06c16cf3f9d2`（`deepseek-v4.1-flash#L-1@06c16cf3f9d2`と統合） | 対応する | (a)review.json/spec.mdをFIFOにした現行HEADでCLIがwriter待ちとなり無期限停止。base review FIFOは即時拒否。対象の破損/置換入力に対するcleanupの主要処理停止で致命的。ラベルやApprove票によらず採用 |
| `SWE-2-Max#L-1@06c16cf3f9d2`（`deepseek-v4.1-flash#L-2@06c16cf3f9d2`、`claude-opus-5-5#L-1@06c16cf3f9d2`と統合） | 対応しない | 固定projectパスは事実で、非存在projectのuv起動がexit2/stdout空になる機序を確認。ただし本runの標準Dev Container `/workspaces/reso-world` では実際のSテストを通しており、別配置だけの互換性/保守性の指摘。データ損害・標準経路の停止なし。見直し: 標準構成の失敗、新しい損害の再現、利用者の名指し |

分類は対応する2/対応しない1/解消済み0（6出典すべてを含む）。前サイクルの判断なし。初回のレビュー修正であり、同条件を以前のレビュー修正で直した履歴はないため、設計見直しトリガー1〜3は未該当。今回の追随漏れ/新設読取の回帰は初回実装の問題であり、別Issueの#419の原因とは区別する。

### 要件対応と守る条件・影響経路

要件は「必要値だけでなく保存済みレビュー/試行との対応も削除前に確定し、不正なら全対象と記録を保持する」。元Specの既存Batch検査だけではpathの対応を保証しないため、上記仕様3/6で具体化した。任意の記録修復・真正性認証・過去missing成功化は追加しない。共有する入力→読取→照合→削除→復旧の統合担当はcontroller。実装担当と自己レビュー/fix-checkへ同じ条件・原指摘・証拠を渡す。

| 守る条件 | 経路 | 判定 | 観測する結果/検証 | 実行結果・証拠 |
|---|---|---|---|---|
| 削除対象は同じ保存済みrunner/batch/試行に属する | Spec cleanup→batch→remove_attempts→runner rmtree | 修正する | 別runner/別worktreeを最初の副作用前に拒否し、全bytes/mode/link/登録/HEAD-statusとvictimを保持。元入力復元後に通常CLI回収/no-op | 修正前head/base双方で誤削除を確認。70c5f8cbの境界10件/追加canonical負例で全状態不変拒否・復元回収を確認 |
| 同じ条件をdesignでも保つ | review_design.cleanup→共通cleanup | 修正する | designも同じ拒否/正常対照 | 70c5f8cbのdesign境界と既存共通委譲Sに成功。独立実装を追加していない |
| 正規failed/fallback/prepare失敗を誤拒否しない | batch=None/nullable attempt fields/存在しない準備失敗path | 既存挙動を維持 | 正規生成される状態と新しいpath条件が両立。nullableな記録と実体不在を混同しない。既存synthetic fixtureは実runnerの保存形式へ合わせ、拒否・復旧assertionを弱めない | 70c5f8cbの19ケースと正規prepare-failed＋fallback回収/no-opの追加実行に成功 |
| 記録読取は特殊ファイルで待ち続けない | request読取→review.json/spec.md→metadata検査 | 修正する | FIFO/device/symlinkを待たず拒否し、通常regular fileの回収を維持 | 修正前headのFIFO待ちとbaseの即拒否を確認。70c5f8cbではreview/spec FIFO・device・symlink-FIFOを待たず無変更拒否し、復元回収/no-opに成功 |
| 成功証拠・JSONL再追記・private/common-dir・停止未確認・missingの守り | 既存receipt/evidence読取・lock→削除callback・再実行 | 既存仕様を維持 | 既存Sを変更せず検証。fixtureの偽pathだけは正規化が必要、実害assertionは削らない | 元HEAD1488件、修正後835件/関連135件と再開後41件・19matrixに成功。証拠なしmissing拒否/JSONL復旧等のSを維持 |
| 任意の一貫した偽造・同時手編集を真正性検査する | 複数記録を同時に整合するよう改ざん | 対象外 | 署名/悪意ある同時変更の新境界は要求外。単一不正入力の対応検査で境界を保つ | 元の除外範囲のまま |

方針: 点の削除後例外捕捉ではなく、cleanupの共通読取/対応検査で必要条件を最初の副作用前に揃える。runner本体・一般implement cleanupへ新しい責務を広げる案や、PR保証を狭めて誤対象を残す案は選ばない。追加恒久テストは誤対象削除を防ぐ独立Sの代表だけ、正常側と復元/no-opを併記。FIFOの待ちは明白な停止としてL、一時検証で確認し恒久テストを増やさない。新たなpathガードにより既存の不整合なsynthetic fixture（artifact_dirが固定/tmp、work_dirがrunner外）を正規runner配置へ合わせる場合も既存Sの拒否/復旧内容を弱めない。

### 現行HEADでの実行証拠と残作業

- 再現はPR headとbaseの隔離worktreeに限定。実runner＋fake /usr/bin/true、正常対照・別絶対runner・別登録worktree・review/spec FIFO・固定project失敗機序を確認。全体scriptはhead/baseともexit0（不具合の観測をassertした意味）。
- 原因はpath対応未検査（preexisting）と新規の非regular記録読取（introduced）で別々。正常識別子のまま1つだけpathを変えた負例、ファイル1つだけFIFOにした負例で、別の拒否に隠していない。
- 保存ログ: `/workspaces/reso-world/tmp/agents/issue-420.xlpq2lqf/cycle1-head-repro.log`、`cycle1-base-repro.log`、`cycle1-reproduce-review-findings.py`、`cycle1-statements.txt`。全4変更ファイルの全文と関連runner/cleanupはread-only sp-reconが精読、controllerが新規境界と実行経路を照合。隔離head/base worktreeは登録から外して親領域も回収済み。
- 実装担当は利用者指定pi_openai-codex_gpt6-terra_xhigh、self-review/fix-checkは既定self、fallback=[]。run_roles.pyで指定割当を維持。自己レビューはこの段階では未実施。最大1回の予約後に入口で停止し、利用者の明示回復許可で同じ予約枠を再開した結果は下記に記す。未完了を成功にしない。

### 修正実装・自己レビュー前の検証

- run_roles implementはrequested/actualとも指定担当、実測openai-codex/gpt-6.1-terra/xhigh、elapsed936.797秒、全停止確認済み、sensitive_paths/outside_changes=[]。worker commit `0cb06e871fa5e8985a04589af53996addfdffad9` の3変更ファイルを確認し、専用worktreeへ`70c5f8cb9eb6b653a40ad26640568427ae60452b`として取り込み。一般runner/implement cleanup本体は変更なし。worker worktreeは停止/cleanを確認して登録から外し、roles/logは保持。
- 追加S代表はrunner_dirだけを別directoryへ変えた誤削除防止1件。workerでRED1→GREEN、途中のsynthetic fixture整合不足1件を修正後、関連135件が2回exit0。既存Spec/design fixtureは正規runner領域に合わせ、Sの拒否/復旧assertionを維持。任意ruffは未導入でexit2（未検証、必須ではない）。
- controllerの修正後境界10ケースはexit0/12.57秒。正常側、runner/attempt/request_pathの各単独不一致、fallback、design、review/spec FIFO、device symlink、symlink FIFOを確認。負例9件でfixture全体のbytes/mode/link種類/参照先/link数/directory構成・Git登録とCODE_ROOTを比較し不変。正規入力復元後の別CLI回収/no-opも成功。過去の元matrix19件もexit0/24.645秒で再確認した。
- 一時検査初回は、work_dirを意図して別値にした負例のretainedへ元の不明pathまで要求するfixture側の誤りで失敗。実装は読める破損記録が指すpathと元runner領域を保持しており、全状態不変は成立。対象を推測しない元仕様に合わせて一時assertionだけを訂正し上記10件を実行した。コードをこの失敗に合わせて緩めていない。
- 中心のrunner一致ガード1つだけを外した隔離worktreeで、追加S代表がexit1（誤対象削除を検出）。正規修正版では同テストexit0。対照worktreeは登録から外して削除済み。FIFOはLとして一時検証のみ、恒久Sを増やしていない。
- controller必須検証: shell27本/98.69秒、layout、`uv run --project /workspaces/reso-world --locked pytest tests/skills .agents/skills -q` 835件/803.95秒、diff checkすべてexit0。検証したコードHEADは70c5f8cb、Specのみ未commitで不変を確認。Specは自己レビューの後に一度だけcommitする。
- 実行証拠: `/workspaces/reso-world/tmp/agents/review-fix-planning-pr428.tbrt__6a/` の `implement-run/roles.json`、`implement-verification-excerpts.jsonl`、`boundaries.log`、`matrix19.log`、`mutation-guard-off.log`、`new-guard-green.log`、`fix-verify-1.log`〜`fix-verify-4.log`、`fix-validation.json`。経路表の修正後未実施欄はこの結果で更新する：Spec/designの対応検査/非regular拒否/正常互換/既存ガードを70c5f8cbの実行で確認済み。別原因の全組合せ網羅や任意の一貫した偽造まで保証したとはしない。

### 停止記録（自己レビュー入口）

run_roles.pyの自己レビュー枠を1回予約し、self-review/fix-checkともselfとして開始した。controllerがpr-review prepareへ`--model-name openai-codex/gpt-6.1-sol`を渡したが、この入口は`PI_MODEL=gpt-6.1-sol`単体と照合するため、`--model-name does not match this runtime's PI_MODEL`でexit1。レビューstate/attempt/run_recordは未作成、レビュー未開始。これはモデル未観測ではなく呼出し側の識別子形式の誤り。pr-reviewのprepare再実行禁止と自己レビュー最大1回の規則に従い、自動で別指定を試さず結論3で停止した。fix-checkは未完了。自己レビュー成功や修正push/マージを記録しない。

Specはdraftの未commit変更として専用worktreeに保持。非Specの修正commitが既にPR未反映で存在するため、停止規則に従いSpecだけも取り消さない。ローカルHEADは`70c5f8cb9eb6b653a40ad26640568427ae60452b`、公開PR HEADは`06c16cf3f9d2d9874c04b562358a81863706cffd`。追加修正は公開未実施。状況コメント: https://github.com/usaturn/create-reso-world/pull/428#issuecomment-6845856720 。loopは1サイクル/stopped/ended_by=outcome/merged=falseでfinishし、ロック解放、retained=[]。PR/IssueはOPENのまま確認した。self-reviewの再予約・別名のplanning.jsonによる上限迂回はしない。この停止時点では明示的な回復判断を必要とし、通常の自動継続がreadyであるとは扱わなかった。

### 明示的な復旧とサイクル1の修正完了

- 利用者の「制限を解除します。作業を続行してください。」を、失敗したprepareの再実行と既に予約したself-review/fix-checkの再開を許可する指示として2026-11-13T07:24:05Zに記録。旧失敗・停止handoff・planningの予約行は削除せず、run_rolesを再起動せず同じ枠を使用した。安全境界、採否済みのskip、対象PR/branch、秘密情報検査、finalize経由のマージ条件は解除していない。
- pr-review入口へ観測した`PI_PROVIDER=openai-codex`と`PI_MODEL=gpt-6.1-sol`を用い、指定commit70c5f8cbのPR全体をprepare→精読/検証→complete。成功、active_findings=0、Approve、cleanup=success、retained_paths=null。prepare開始から624.693秒。保存先は`reviews/usaturn/create-reso-world/#428-fix-issue-420-cleanup-preflight/gpt-6.1-sol-commit-70c5f8cb9eb6b653a40ad26640568427ae60452b.md`と対応するfindings JSON。新しい要対応指摘なし。
- fix-checkはcontroller self（openai-codex/gpt-6.1-sol / pi）、同じ70c5f8cbの隔離worktreeで実行。先に固定した主張4件・変更3ファイル・文書候補108件を判定し、holds=4、passed=3、consistent=17/unrelated=91、unchecked/新規指摘=0。独立stagingでvalidateしてから同じ内容を既存review directoryへコピー。`verified/70c5f8cb9eb6.fix-check.json`と`.statement-candidates.json`、要約へ保存した。実測680秒、利用者の再開許可で記録した1800秒の期限内。
- 再開時の新規実行: 境界10件/10.813秒、元matrix19件/18.305秒、正規prepare-failed＋fallbackと非正規attemptの2件、全3変更Python構文、関連Spec/design41テスト/8.81秒、diff checkが全てexit0。実runner＋fakeだけを使用。必須の未確認なし。任意ruff未導入は未検証のままで、成功に含めない。
- 自己レビュー入口が管理する隔離worktreeはcompleteが回収し、追加fixtureも自身の一時領域から回収済み。旧/tmp6登録には触れていない。実行記録は`/workspaces/reso-world/tmp/agents/review-fix-planning-pr428.tbrt__6a/`の`recovery-authorization.json`、`self-pr-prepare-recovery1.json`、`self-pr-complete-recovery1.json`、`fix-check-*.log`と、元の失敗/stop記録を保持。
- 修正の実装・必要検証・同じ予約枠の自己レビュー/fix-checkを完了し、既存PRへscan付きpushする。公開後の次のサイクルとfinalizeはこの記録時点では未実施で、マージ成功を先に記録しない。旧サイクル1の停止コメントは同じ番号で復旧結果へ更新し、終了済みloopの記録は過去のstoppedとして保持する。
