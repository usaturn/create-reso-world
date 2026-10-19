# Issue #183: PR #182 の DSH 成果作成と親保存

- 状態: completed（利用者の実行指示に基づく修正・検証完了。事前の内容承認を意味しない）。
- 対象: usaturn/create-reso-world #183、PR #182、関連 #153 / #116。
- 実行許可: 2026-10-19 の利用者指示「Issue #183 を解決する形で、PR#182 を修正せよ」。既存PRへの実装・検証・commit・pushを行い、マージは行わない。
- DOC_ROOT = CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-153-pr-review-v2`、branch `feat/issue-153-pr-review-v2`。PARENT_ROOT: `/workspaces/reso-world`。
- 入力: #183 本文と調査コメント（6259872800、6260317641、6260903508）、PR HEAD `0d1cd19477ea00b216c3cc8f9400c3eb9afe4395`、main `5adc16c2055f4d2d7c0b2315014a37efc9d82e76`。
- 旧版: `5f33749` の本Spec/Planは公式追加root API待ちだった。今回は利用者の具体的な問題解決指示に基づき、候補B（固定outbox）とG（DSH全体のOS隔離）を採用する。旧版のAPI待ち・P-2不採用・未許可という判断を本版で置き換える。旧文書commitもPR履歴へ取り込み、別文書を二重管理しない。
- 変更範囲: pr-review helper/手順/挙動テスト、tools/agent_runnerのDSH隔離・結果回収・共通path・証跡検査と関連テスト。#153の旧tools除外はこの修正に限り変更する。PR #180の診断修正をmainから取り込み、その一般分類を広げない。

## 原因と選択

追加bash bindはnative filesystem policyへ伝わらず、reviews/.stagingをnative成果先にしたことが不具合の原因である。nativeがホスト/tmp全体へ書けること、親が子の申告pathを固定先照合前に更新することが、親への安全な受け渡しも妨げていた。

- 採用: nativeが許可する専用TMPDIR内の固定2ファイルを使う。DSHプロセス全体を外側bubblewrapで囲み、ホスト/tmpを隠してPID namespaceと専用/procを作る。
- 不採用: 公式API待ち（現行版に存在しない）、cwd変更（Request/Identityや指示ファイルの読込境界を変える）、native拒否後のbash書込切替（拒否した経路の迂回になる）、権限拡大（不要）。
- 設定・導入版・個人認証・他runtimeの仕様は変えない。tools/workspace・projects.tomlを導入しない。
- 新たな有料レビューは起動しない。実DSHの確認はlocalhost模擬providerとネットワークnamespaceによる検証を使い、#153の有料並行レビュー成功とは区別する。

## 指摘の分類

| ID | 分類 | 現行版の根拠と方針 |
| --- | --- | --- |
| F1 | 対応する | native staging書込拒否をAPIで再現。固定outboxへ変更する |
| F2 | 対応する | completeが固定draft照合前に別ファイルへ追記することを再現。すべての入力と保存先を副作用前に検査する |
| F3 | 対応する | native/tmpと共有review_dir grantが別attemptへ届く。DSH全体のOS隔離とattempt固有scratchへ変更する |
| F4 | 対応する | native拒否だけならadapterはsuccessになりうる。親昇格では拒否履歴と両成果のnative成功証跡を検査する |
| F5 | 対応する | disk receiptが成功payloadの入力になる。DSHはJSONL/sessionだけを使いdisk receiptがあれば拒否する |
| F6 | 対応しない | receiptがadapter失敗状態も上書きするという説明は不正確。現行コードはawaiting_approvalを維持。F5で成功時の差し替えだけを扱う |
| F7 | 対応しない | 新版DSHの導入・上流実装・追加有料並行レビューは今回の修正に不要。元の#153実機受入状況を成功へ書き換えない |

## 守る条件と影響経路

| 経路 | 判定 | 守る条件・実装・検証 |
| --- | --- | --- |
| Dsh.prepare→native/bash | 修正する | RWは自身のworkspace・home・state・tmp・review-scratchのみ。隔離で隠れる親snapshot/bundleと検証済parent_rootはROで復元。request/receipt/log/patch・他attempt・正式reviewsはRO。外側bwrapとfake CLIの実ファイル操作で確認 |
| output_dir→mount | 修正する | canonicalな実ディレクトリだけを起動前に受理。/tmp配置でもhost側はROで、内側private/tmpと区別する |
| child prepare | 修正する | 実Requestの親からreview-scratchと固定sessionを計算。親保存lock・正式run記録を書かず、bundleから所有Gitを作る |
| child native write/edit→complete | 修正する | attempt/dsh/tmp/exports/review.md・findings.jsonだけを成果入力とし、coverage/Request/Identityを検査してdigestを固定しstagedとする |
| parent finalize→outbox読込 | 修正する | stop/exit/secret cleanup・Request・Identity・snapshot・固定state/pathを照合。全階層nofollow、通常単一リンクfile、サイズ上限で各1回読んだ同じbytesを使う |
| parent complete→save | 修正する | draft/destinationを固定先から再計算し書込前に一致を検査。不正時は外部file・backup・共有成果へ書かない |
| tool履歴→成果採用 | 修正する | 昇格対象attemptのproducer拒否診断をtool call/result対応で識別。native write/edit成功が両outboxに無い、昇格要求、ログ欠落/不正なら採用拒否。通常のread行数エラーは拒否扱いにしない |
| run record→正式保存→cleanup | 修正する | 子記録はscratch内。親がtrusted bundleから別sessionと正式記録を作り既存save/cleanupへ接続。未採用時はrunner結果と子scratchを残し正式保存先は不変 |
| live HEAD・pair rollback・旧state・非DSH | 既に満たす | 既存の照合/ロック/rollbackを維持し、変更後の回帰で確かめる |
| 有料モデルの判断品質・#153全員並行受入 | 対象外 | localhostで運搬とnative/fs動作を検証し、レビュー品質や有料並行受入とは同一視しない |

## 受け渡し仕様

実Requestの親をattemptとする。共通関数は `tools.agent_runner.dsh_paths.review_scratch(attempt)` と `review_exports(attempt)`。前者は `attempt/review-scratch`、後者は `attempt/dsh/tmp/exports`。Git/sessionはruntimeの秘密値置換対象に混ぜず、native成果は置換対象に残す。置換でdigestが変化した成果は採用しない。

sessionは `review-scratch/pr-review-<PR>-<Request bytes sha256先頭8文字>/session.json`、子run記録はscratch内固定先とする。親はpayloadの任意pathや子のrun_recordを正式保存先として使わない。新しいattemptごとに生成し、旧失敗attemptを再利用しない。

親は全検査が済むまで取込先を変更しない。子sessionは安全に読んだJSONだけを照合し、子が変更できるGit設定・hook・.git参照先を親から実行しない。親専用の `attempt/review-promotion` にtrusted bundleから新sessionを作り、検証済みbytesと元の保存先fingerprintだけを渡す。outboxの読み直しcopyはしない。保存後の子session削除は固定pathに対してsymlinkを追わず行う。後段のI/O失敗は既存pair rollbackを使い、保存/cleanup結果と残存先を報告する。host側の/tmpへ出力を置いた場合も、外側OS隔離によりその領域をnativeからRWにしないため、/tmp一律禁止とはしない。

## 検証と公開

TDDで各不具合のRED/GREENを記録する。安全ガードは正常系を保ちつつ、異常を1つだけ入れた負例で状態全体不変を確認する。中心となるガードを隔離コピーで外した対照で検出力を確かめる。文書の文面・モデル一覧をコピーしたテストは追加しない。

関連pytest、スキル/runner回帰、shell 33系、layout、git diff --checkを実行する。実DSH/native確認は実装完了後に新しいsynthetic fixtureで行い、外部通信・有料モデルを使わない。修正後の自己レビューは反証・PR全体・検証の検出力の3観点を1回だけ行い、指摘への修正後は再レビューしない。

検証後、同じPRブランチへcommitし、scan-before-push.shで検査したSHAをpushする。PR説明と#183/#153/#116の状態報告を実結果に合わせ、未実施の有料受入を完了としない。実行証拠・自己レビュー・所要は本節へ追記する。

拒否履歴は昇格対象のattempt内を検査する。既存の明示fallbackの仕様は変更せず、以前のattemptの失敗はrunner結果に残す。実DSH/nativeの検証記録と、実行後の親cleanup・JSONL修正の検証範囲はPlanの実行記録に示す。


## 1回の自己レビューで見つかった適用漏れと設計の見直し

2026-10-19、反証・PR全体・検出力の3観点で1回実施した。以下を採用して修正する。修正後の再レビューは行わず、対象経路の検証を行う。

| ID | 判定・原因 | 変更前の挙動 | 条件と確かめるassertion |
| --- | --- | --- | --- |
| R1 | 対応する・修正による回帰 | outer private /tmpで親snapshot/bundleも不可視になる | Requestが固定した親入力をnative/bashの双方からROで読め、外側hostや兄弟へ書けない |
| R2 | 対応する・既存原因の適用漏れ | Gitを避けるためraw JSONへ変更した際、state/run_contextの型不正がAttributeErrorで親batchを中断 | 親境界ですべての必要なJSON構造を副作用前に検査し、不正attemptだけfailed、同batchの正常attemptは保存できる。外部file・正式成果・backup・記録は拒否前後で不変 |
| R3 | 対応する・修正による回帰 | 親のCODEX_THREAD_IDでDSH子Identityを再解決して誤拒否し、trusted session作成でも同じ問題になる | 子Identityの検証済み値を明示的に使い、親がCodexでもprovider/modelと正式保存名が子に一致。通常Codexのモデル照合は維持 |

守る条件は「停止した子の成果をデータとして検査し、親だけが正式保存する」。子のGitを避けるだけでなく、JSONの形・親の環境・隔離後の入力可視性まで同じ境界で成り立たせる。比較した案は、点の例外追加（AttributeErrorの一括捕捉・環境変数の一時削除・/tmp全体復元）、境界の構造化（JSON構造検査・明示Identity・固定したRO入力）、保証の縮小（Codex親や/tmp入力の非対応化）。構造化を採用する。例外だけの追加は別のネスト型を漏らし、global環境変更は並行処理へ波及する。保証の縮小は既存の有効な入口を失うため採用しない。


## 経路に対応する実行証拠

最終実装を含むこの文書のコミットが対象版。実DSH確認の主要14コードfileは起動前後のSHA256一致を検証した。再現コード・検証対象のsha256・結果メタデータはPlan記載のローカル証跡へ保存する。外部へは他モデルのレビュー本文・thinking・認証情報を転載しない。

| 経路 | 観測した結果と証拠 |
| --- | --- |
| native/bashの隔離、output_dir、親RO入力 | runner全体1016 passed、追加18件でnative/inner両方の/tmp入力可視性、write拒否、実require_parent_root、host兄弟不変。outer attempt RW化の対照1件とRO入力mount除去の対照で検出 |
| 子prepare→native→staged | 最新実DSHで/tmp snapshot read、bash prepare、本文write/read/edit、候補read/writeが全てcompleted。共有保存lockを取らない負例はhelper回帰 |
| 親file/状態検査→同bytes保存 | link/FIFO/oversize/別path/不正candidate/拒否・証跡不足で外部file・state・local記録・正式reviews不変。hardlinkは有効な同じdraft bytesで構成し、nlinkガード除去時だけ誤採用を検出。読込後差替でも捕捉済み2ファイル各1readのbytesを保存 |
| 子Gitを親から実行しない | hook/config/.git pointerの3毒入れに対し、親Git呼出しの場所と外部sentinel不変、正式pair保存成功を確認 |
| JSON構造不正・batch継続 | state/context/staged等の不正型とlocal inputs.request=nullを副作用前に拒否。先頭の不正attemptの後も正常attemptを保存。正常2attemptの対照も確認 |
| 親と子のIdentity分離 | 合成Codex親の有効rollout下でDSHのprovider/model/保存名を保持し成功。通常Codexのモデル不一致拒否も維持。最終実DSHでも親環境を変えず確認 |
| tool履歴→採用 | 証跡19 passed。通常read行数エラー/Unicode区切りは受理、producer拒否・native成果不足・不正ログは拒否。昇格対象attemptだけを評価 |
| 正式記録→save/cleanup、失敗 | 最終実DSHで正式pair・run_record・payloadすべてsuccess、子/親session・worktree・HOME不在。cleanup例外では保存済み成果とfailed_at=cleanupを保持する回帰を確認 |
| live HEAD・rollback・非DSH・旧state | 最終helper全体333 passed（368.76秒）で既存のHEAD変化拒否・draft保持/再開・pair rollback・通常shallow・fork/外部checkout・旧stateの経路を検証 |
| 有料の並行モデル受入 | 対象外のまま。#153の未完了を維持し、合成providerのnative搬送検証とは区別する |

自己レビューの重複指摘はR2へまとめ、3件すべて修正・検証済み。担当範囲の全体回帰はrunner1016/helper333、先行の全体回帰は2821 passed。先行回帰の後に変更した経路は担当範囲の全体回帰と最新実DSHで再検証し、変更していない他skill/移行ツールの証拠は引き継いだ。

最終確認: shell33 PASS、layout・実config check・Python構文・git diff --check成功。実DSHの最新確認は5.41秒、主要14コードfileの起動前後SHA256一致、watcher exit0/completed/residual_pids=[]。追加の有料並行受入は未実施、PRマージは対象外。公開結果はPR状況コメントと最終報告へ記録する。
