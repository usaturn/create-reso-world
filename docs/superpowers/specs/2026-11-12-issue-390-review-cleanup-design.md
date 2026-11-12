# #389 / #390: 実装出力先の事前検査と review cleanup の復旧

## 管理・実行許可

- 状態: `completed`。内容承認ではなく issue-to-pr と review-fix-planning の実行許可に基づく実装・検証・選別の完了。マージ結果は後続の最終化で確認する。
- 取りまとめ: https://github.com/usaturn/create-reso-world/issues/390
- 共同実装: https://github.com/usaturn/create-reso-world/issues/389
- 利用者指示: `#390 --merge --spec-review pi_opencode-go_deepseek4-flash_max --implement pi_opencode-go_deepseek4-flash_max --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_default`。
- 許可範囲: 両 Issue の共同実装・検証・commit・push・1 本の main 向け PR、指定レビュー修正ループの finalize によるマージ。内容を approved と記録しない。
- 「途中でメインがマージされたら追随」の指示は、捕捉 base の移動で停止する上位規則と両立しないため適用しない。捕捉値は origin / refs/heads/main / `c3a8e113c3af010fac94820266b93e107d6dbfaf`。

## 意図・現状

#389 は起動前の出力先 leaf 検査と起動後の worktree 分類が不一致で、`..`・祖先 symlink を含む出力先で実装を終えた後に拒否される。#390 は worktree 削除後の receipt 追記失敗で成功証拠が残らず、実 runner の request.json が残るため、再実行で missing の拒否から回復できない。さらに callback 失敗後の試行と runner-dir が報告一覧から落ちる。

対象コードは `.agents/skills/issue-to-pr/scripts/implement_task.py`・`review_spec.py`、design は `review_design.py` の共通 cleanup 委譲。実 runner は `tools/agent_runner/runner.py` が worktree 外へ request.json を保存する。既存分類を緩めて解決しない。

## 方式の比較・決定記録

| ID | 選択した案 | 検討した別案 | 理由・委任または停止条件 |
|---|---|---|---|
| D1 | #389 を最初の独立実装コミットにする | 両修正を一括実装 | Issue の明示順序。実装担当は利用者指定の pi_opencode-go_deepseek4-flash_max、fallback=[]、self=false（helper check 済み） |
| D2 | 起動前に正規絶対パス・symlink 構成要素を検査し拒否 | resolve して黙って受理 | 後続監査と同じ入力条件にし、許可するパスを広げない。実行後の再検査は維持 |
| D3 | 削除成功後、独立した成功証拠を保存・fsync し、その後既存 JSONL へ追記 | missing 全件を回収済みにする／削除予定と不在だけで成功とする／JSONL だけでリトライ | 実際の削除成功を別 CLI で照合でき、既存の不明消失拒否を保つ。証拠保存自体の失敗は停止 |
| D4 | 成功証拠を review ledger 内の追記専用 sidecar とする | runner 内に置く／既存 review.json を更新 | runner 回収後も証拠を保持し、既存記録を改変しない |
| D5 | callback 失敗後は削除せず、残り全試行と runner-dir を列挙 | break だけ／処理を続けて削除 | 中断後の全保持対象を明示する。削除済みパスと未処理パスの理由を区別 |
| D6 | #389 は一時検証、#390 は誤回収・証拠欠落の S テストだけを恒久追加 | 明示拒否の L や文言 F テストを追加 | AGENTS.md と #389 の受け入れ条件。D 重複を増やさない |
| D7 | Spec レビューのみ指定担当で実行、設計レビュー・builder check は行わない | 設定上のレビューも追加 | 利用者は --spec-review だけを指定。明示 agent、fallback=[]、self=false。再レビューは important 採用時の 1 回のみ |
| D8 | Task ごと runner へ直列依頼、controller が統合・Task review | self へ切替／同時書込 | --implement の明示を維持。同じファイルを変更し、起動元 helper は親 checkout を使う。失敗を理由に self へ切り替えない |
| D9 | PR 後の 3 サイクル上限の指定 inspect レビューで最終全体レビューを代替 | PR 前にも全体レビュー | --merge の規則。max_cycles=3 は既定、inspect の 3 担当と fix implement は利用者指定。self-review/fix-check=self は既定、fallback はすべて空 |

## 成功証拠と復旧の仕様

- 保存先は `review_dir/cleanup-success-<key>.json`。key は UTF-8 の `event_type + "\n" + path` の SHA-256（小文字 64 桁）。event_type は `worktree_removed` または `runner_dir_removed` の種別リテラルだけで、CleanupEvent 全体・removed_at は含めない。1 イベント 1 ファイル。トップレベルの専用 prefix を列挙し、不正な名前・重複・未知スキーマ・部分書込は拒否する。新規ファイルだけを O_CREAT|O_EXCL|O_NOFOLLOW、mode 0600 で作り、fdopen のバッファ付き書込→flush→fsync→親 directory fsync を終えてから JSONL を追記する。既存証拠は上書きしない。symlink・hardlink・非 regular file と不正な親領域は拒否する。JSONL の既存 private regular file 検査も残す。
- JSON スキーマは厳密な object: `version: 1`、`event: CleanupEvent`（既存の全フィールド）、`review_sha256: str`（review.json 生バイトの SHA-256）、`repository: str`、`common_dir: str`（削除前の実 common-dir）、`request_id: str|null`、`attempt_index: int|null`（outcome 内 0 始まり）、`agent_id: str|null`。work_dir は event.path。runner-dir イベントだけ試行の 3 フィールドを null にする。他のレビュー・batch・対象へ転用できないよう、識別フィールドを保存済み request/review/batch と照合する。repository は request.repository と一致させる。common_dir は削除前に取得した実 common-dir を記録し、再実行時にも request.repository で `git rev-parse --path-format=absolute --git-common-dir` を実行した実パスと照合する。runner-dir イベントにも同じ repository の common-dir を使う。
- `on_removed(Path)` の署名は変えず、review cleanup が batch 内の path→(Result.request_id, attempt_index, Attempt) の一意な map を削除前に作る。重複 work_dir は副作用前に拒否する。implement cleanup の呼出し仕様は変えない。
- git worktree remove の終了 0 の後だけ証拠を作り、保存完了後に cleanup.jsonl へ追記する。runner-dir の削除成功も同様。削除予定は成功証拠にしない。同一 key の既存証拠は読取・照合だけ行い、JSONL に同一 event が既にあれば追記しない。不一致は拒否し、欠落した event だけ再追記する。
- 同レビューの `review_dir/cleanup.lock` を private regular file として開き、receipt/sidecar の読取前から全処理終了まで fcntl.flock(LOCK_EX|LOCK_NB) で直列化する。取得失敗は削除せず終了 2 と保持一覧を返す。fd を閉じて解放し、lock ファイルは消さず再利用する。プロセス終了で OS がロックを解放するため stale lock の手動削除は不要。並行取得拒否と通常再実行を S の代表テストで確認する。
- 再実行では、証拠の形式・識別情報・保存済みレビューとの対応と現在の対象状態を照合する。照合済み成功証拠は JSONL と合わせ既存 collected 分類へ渡せる。JSONL に未反映なら追記し直せる。欠落イベントの照合・再追記（runner_dir_removed を含む）は runner_collected の早期 return より前に行う。cleanup.jsonl の既存行は書き換えず、欠落イベントの追記だけを行う。Spec・request・review・prompt・runner メタデータは変更しない。
- `removed_worktrees` は今回の呼出しで実際に削除できた path だけ。復旧・no-op の呼出しでは過去の削除分を加えない。callback 失敗後も今回削除分を残す。`retained` は実体保持だけでなく「回収の未完了・要確認」を表し、削除済みの対象では理由に削除済み／証拠保存または JSONL 追記の未完了を明記する。成功した runner-dir 削除は `removed_runner_dir=true`、その後の記録失敗でも true とし retained に未完了理由を追加する。既存の再実行 no-op の期待と callback 失敗時の両一覧への包含は維持する。
- 証拠不明の消失は retained とし、完全パス・停止理由・確認すべき review/request/receipt 記録の場所を示す。callback 失敗以降の未処理全試行と runner-dir も完全パスと理由を返す。receipt/sidecar/lock の事前検査拒否では ReviewInputError の互換サブクラスに retained を持たせ、Spec/design 両 CLI が既存 `status:error, reason` に `retained` と `records`（照合すべき絶対パス一覧）を追加して終了 2。直接呼出しの例外互換と削除前拒否を維持し、既存 bad/shared receipt テストに情報の確認を加える。通常の中断は retained 結果の終了 1 を維持する。通常結果でも retained が非空なら、同じトップレベル `records: list[str]` を付ける。理由の種類によらず、review_dir/request.json・review.json・cleanup.jsonl、全 sidecar、batch の全 attempt.request_path、runner-dir を絶対パス・重複なしで列挙する（prepare-failed 等の request_path=None は除く）。retained が空の正常結果の形は変えない。review.json の不在・不正は、読めた request に基づく runner-dir と確定できる記録パスを付けて拒否する。request 自体が不正で対象一覧を確定できない場合の推測は対象外とし、review_dir/request.json を照合先として示す。
- 旧 JSONL の成功記録は既存の照合条件で受理する。成功証拠のない旧 missing は成功に移行しない。実体または登録の再出現、別 common-dir、symlink、private receipt 不適合、sensitive_paths、停止未確認を従来どおり拒否する。
- 保証範囲は、成功証拠を保存でき、直後の JSONL 追記だけが単発で失敗したケース。Git 削除成功から成功証拠の保存完了前の crash、証拠保存自体の障害、未知の破損や JSONL の途中書込みからの自動復旧は保証しない。それらは証拠不足として停止・報告し、失敗を成功にしない。

## 受け入れ基準

### Task 1 — #389

1. `real/sub/../run` と `alias/run`（alias は祖先 symlink）を、外部担当起動・runner 成果物作成前に拒否する。fake adapter 起動 0 回、出力先不在、参照先・既存 worktree 登録・feature HEAD 不変を確認する。
2. 正規実パスで run → accept → cleanup が成功し、実行後の worktree 差替えは拒否する。
3. fake と一時 Git だけを使用する。明示拒否の L テストは恒久追加せず一時検証、既存 S テストを維持する。

### Task 2 — #390

1. 修正後の実 runner＋fake の成功 1 試行、および失敗 primary＋成功 fallback のそれぞれで、worktree 削除成功後の cleanup.jsonl 最初の os.write だけへ EIO を注入する。初回は明示失敗し、I/O 回復後の別 CLI プロセスから通常 cleanup で残る worktree・runner-dir を回収し、さらに再実行が no-op である。各 normal 対照も確認する。runner-dir 削除後の JSONL 追記失敗も一時検証し、2 回目で欠落イベントが追記され、3 回目が no-op である。
2. 同一レビュー・試行・worktree の成功証拠を用いる。証拠のない旧記録・不明消失は拒否して手動照合情報を示す。予定＋不在だけで成功としない。
3. 中断時に全未処理試行と runner-dir を削除せず、完全パスと理由、照合先 records を報告する。
4. 既存 Spec/ledger/runner メタデータの生バイト、無関係な登録、CODE_ROOT HEAD/status を前後比較し、不正な改変がない。
5. 予期しない消失・再出現、symlink/別 common-dir、private receipt、停止未確認の既存拒否を維持する。design の委譲も同じ仕様である。
6. 過去記録を改変しない。`docs/superpowers/specs/2026-11-09-issue-353-review-steps-design.md` の旧 #L-3（当初339行）の回復可能という一般化は、元の行を残し訂正注記を同ファイル末尾へ追記する。同ファイルの旧 #L-2（当初338行）は関連ケースとして記録するが対象外で、implement cleanup の従来の回収挙動は変えない。PR 説明も実装と新証拠に合わせる。
7. main 向けの 1 本の PR 本文に `Closes #389` と `Closes #390` をそれぞれ記載し、両 Task の各受け入れ条件に対応する検証結果を示す。

### 動作環境・実入力・防御範囲

Linux Dev Container、uv、実 Git worktree と実 agent-runner、fake adapter/CLI。複数試行・非 ASCII のパスと review 内容・複数行 JSON 入力を扱う。外部の実モデルや資格情報・実サービスをテストには使わない。実モデル起動は指定 Spec レビューと実装担当・PR ループの workflow 作業だけに限る。

対象は issue-to-pr の出力先検査と Spec/design cleanup。runner 本体の仕様変更、implement cleanup 全体の再設計、任意の破損修復、過去失敗証拠の書換え、実際の他セッションの資源回収は対象外。

## 調査・検証の初期記録

- 適用 AGENTS.md、Issue 本文、全ページコメント・timeline・依存を確認。両 Issue に parent・未完了依存・競合 PR・claim・番号一致の branch/worktree なし。PR #376 は再現元であり両修正は未実装。
- sp-debug が現行コードと再現元に対象コード差分がないこと、メモリ内再現で fault の missing 継続と旧 fixture の不足を確認。実 runner＋別 CLI は実装時に行う。
- ベースライン: 関連 pytest 56 passed / exit 0。`/workspaces/reso-world/tmp/agents/issue-390.bq1npfwa/baseline.log`。
- 正式な検証入口は README の `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。GitHub Actions は無効のまま。

## Spec レビューの記録

- helper `review_spec.py`、外部担当、1 回目。review_dir: `/workspaces/reso-world/tmp/agents/issue-390.bq1npfwa/2026-11-12-issue-390-review-cleanup-design.spec-review/review-1`。review_id: `2444b3d7c78644608c5becba7290aa1a`、reviewed SHA-256: `fafe03c1db37069b13b0b24415d8d32681ce29cc32c125d8c3affd082ad54469`。
- requested/actual agent はともに `pi_opencode-go_deepseek4-flash_max`（明示指定）、fallback=[]、identity は opencode-go / deepseek-v4.1-flash / max。elapsed_seconds=864.1938527860038。outside_changes=[]、unprotected_changes は旧 /tmp review worktree 6 件の監査不能で、保護対象の HEAD/status に変化なし。停止確認済み、sensitive_paths=[]。
- S1/S2 important、S3〜S6 minor をすべて採用。保存形式、今回削除と過去削除の報告、path→試行の対応、拒否時の情報、ロック、PR の close 指定を本文へ反映。実装する機能の範囲は変更なし。important 採用により同じ担当で 1 回だけ再レビューする。
- 2 回目: review_dir `/workspaces/reso-world/tmp/agents/issue-390.bq1npfwa/2026-11-12-issue-390-review-cleanup-design.spec-review/review-2`、review_id `98d0152163124772b72512fbd893bf9c`、reviewed SHA-256 `5e295a216e6b8869d396c3713726dc5a285d350b81ee8136b2db7befa1b5cceb`。helper/外部担当、requested/actual は同じ明示 agent、identity opencode-go / deepseek-v4.1-flash / max、fallback=[]、elapsed_seconds=752.4692806669918。outside_changes=[]、unprotected_changes は1回目と同じ旧 /tmp 6件。全試行停止確認済み、sensitive_paths=[]。
- 2 回目 S1/S2 important と S3〜S6 minor を採用し、通常 retained の records、旧 Spec の対象パス、JSONL の追記限定、key の種別、runner-collected 前の再追記、現在の common-dir 照合を本文へ反映。上限に従いこれ以上の Spec 再レビューは行わない。

## PR #419 レビュー修正サイクル1の結果

- 状態 completed は本Specの実装・検証と指摘選別の完了を示す。内容承認ではない。利用者の #390 --merge に基づきreview-fix-planningを完遂し、追加のコード修正は不要とした。マージ・Issue更新はこの記録の後にfinalize.pyで行い、成功を先に記録しない。
- 対象は 9eaa8eb6d8882413233a846a148ac88da61171ab、base c3a8e113c3af010fac94820266b93e107d6dbfaf。planner=openai-codex/gpt-6.1-sol / pi。コード・文書の8変更ファイルと関連経路・テストを照合済み。確認済み一覧: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#419-fix-issue-390-review-cleanup/verified/9eaa8eb6d888.json`。工程記録も同stemのplanning.jsonへ保存する。

| レビューファイル | モデル / runtime | HEAD | このサイクルで再実行 | 推奨 |
|---|---|---|---|---|
| SWE-2-Max.md | SWE-2 Max / devin | 9eaa8eb6d888 | true | Approve |
| deepseek-v4.1-flash.md | deepseek-v4.1-flash / pi | 9eaa8eb6d888 | true | Approve |
| claude-opus-5-5.md | claude-opus-5-5 / claude-code | 9eaa8eb6d888 | true | Approve |

- Devin初回はReview historyのHEAD不一致で却下し、helper指定の1回の再実行で受領した。失敗を指摘なしに数えていない。全員停止確認済み、retained=[]。診断はloop/cycle-1/diagnosticsに保存。

| 判断IDと出典 | 区分 | 根拠・見直し条件 |
|---|---|---|
| `SWE-2-Max#F-1@9eaa8eb6d888`（`deepseek-v4.1-flash#L-1@9eaa8eb6d888`と統合） | 対応しない | 破損/手編集されたrequestでのみ構造化報告を迂回するが、例外で削除前に止まり対象bytes・登録・HEAD/statusを保持する。通常の正規記録のcleanupとI/O復旧は成功。秘密露出・データ破損・誤対象・主要処理停止の基準に当たらず、利用者によるこの指摘の名指しもない。 見直し: 正常生成された記録から到達する再現、誤削除・成功誤報・保全喪失の新証拠、または利用者が指摘を名指ししたとき。 |
| `SWE-2-Max#F-2@9eaa8eb6d888` | 対応しない | on_removedを渡さないimplement cleanupの到達不能な報告分岐。実行時の誤削除・成功誤報・主要処理停止がなく保守性のみ。implement側へ証拠機構を追加することは本Issueの保証外。 見直し: この分岐が実際に使われる変更、実行時損害の再現、または利用者が指摘を名指ししたとき。 |
| `claude-opus-5-5#L-1@9eaa8eb6d888` | 対応しない | CLIテストは既存corrupt receiptの守りとD重複し、追加差分はLの出力検査。指摘は事実だが既存の正しい動作や安全性を阻害せず、完遂workflowは非致命的なテスト整理を追加対応しない。 見直し: この重複が検証の失敗を隠す具体的再現、または利用者がテスト整理を名指ししたとき。 |

### 要件対応・残る制限

#389の起動前拒否/正規経路と#390の実runner四対照・独立成功証拠・全未処理一覧・既存記録保全・安全境界・過去記録訂正はTask1/2と現行HEADの実行証拠で満たす。共有する入力・分類・保存/再追記/別CLI復旧/no-opの統合担当はcontroller。要件の意味は変更しない。成功証拠保存前のcrash・証拠自体の障害・任意の破損修復を保証しない境界も維持する。

不正requestの構造化報告は上記V-1で確認した既知の未達であり、正規生成された記録の受け入れ条件とは区別する。上の仕様中の「request自体が不正でもrequest.jsonを照合先へ」という記述は全入力では実装されていない。通常記録を使い、破損時はrequest.jsonを手動で照合し、自動修復/対象の推測削除をしない。到達不能なimplement報告分岐およびCLIテスト重複は実行時損害を持たない制約として残す。PR説明にも開示する。これらは本サイクルの選別であり、過去の失敗証拠を書き換えない。

### 検証・三択の結論

- 変更前後の状態を追う隔離再現: 不正JSON/mode欠落/runner_dir欠落のCLIはexit1、削除前停止・bytes/登録/HEAD/status不変。null/ledger不一致はrecords付きexit2、正常記録はexit0で回収。検査script全体はexit0。静的2指摘もコミット済み内容で確認。
- 同じclean HEADのissue-to-pr検証記録を再利用する条件を確認: `/workspaces/reso-world/tmp/agents/issue-390.bq1npfwa/validation-final.json` とchecks.json。shell27本、pytest1481件、layout、固定base差分、一時6件が全てexit0、全ログ実在、開始/終了clean、HEAD/base一致。baseはheadの祖先であり、mergeした組合せの追加検証は不要。
- 対応する0件/解消済み0件/対応しない3件（4出典）。追加実装・自己レビューは行わない（修正0件のためrun_roles呼出し0回、自己レビュー回数0）。設定はimplementが利用者指定pi_opencode-go_deepseek4-flash_max、self-review/fix-checkは既定self。設計見直しトリガーは対象となるfixがないため該当しない。
- 結論2: コードの追加修正不要。保存済み検証とbaseを再照合し、このSpecだけを直接の子コミットにして投稿・検査付きpush・finalizeへ進む。Spec/PRの文書記録を実行時検証の代用にしない。
