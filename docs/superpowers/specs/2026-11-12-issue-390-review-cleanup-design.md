# #389 / #390: 実装出力先の事前検査と review cleanup の復旧

## 管理・実行許可

- 状態: `draft`。内容承認ではなく issue-to-pr の実行許可で進める。
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

- 保存先は review_dir 内の専用 sidecar 領域。新規ファイルだけを作り、既存内容を差し替えない。symlink・hardlink・非 regular file と不正な親領域は拒否する。JSONL の既存 private regular file 検査も残す。
- 証拠には成功した CleanupEvent と、その review.json のハッシュ、repository/common-dir、試行を一意に照合する batch 内の request_id・試行番号・agent_id・work_dir を記録する。runner-dir イベントは同じ batch と runner-dir に結び付ける。
- git worktree remove の終了 0 の後だけ証拠を作り、保存完了後に cleanup.jsonl へ追記する。runner-dir の削除成功も同様。削除予定は成功証拠にしない。cleanup は同レビューで直列化し、並行する削除・証拠保存を競合させない。
- 再実行では、証拠の形式・識別情報・保存済みレビューとの対応と現在の対象状態を照合する。照合済み成功証拠は JSONL と合わせ既存 collected 分類へ渡せる。JSONL に未反映なら追記し直せる。既存 JSONL・Spec・request・review・prompt・runner メタデータは変更しない。
- 既に削除された worktree は removed_worktrees に残し、実体が保持されたようには報告しない。証拠不明の消失は retained とし、完全パス・停止理由・確認すべき review/request/receipt 記録の場所を示す。callback 失敗以降の未処理全試行と runner-dir も完全パスと理由を返す。receipt の事前検査で拒否した場合も既知の保持対象を列挙する。
- 旧 JSONL の成功記録は既存の照合条件で受理する。成功証拠のない旧 missing は成功に移行しない。実体または登録の再出現、別 common-dir、symlink、private receipt 不適合、sensitive_paths、停止未確認を従来どおり拒否する。
- 保証範囲は、成功証拠を保存でき、直後の JSONL 追記だけが単発で失敗したケース。Git 削除成功から成功証拠の保存完了前の crash、証拠保存自体の障害、未知の破損や JSONL の途中書込みからの自動復旧は保証しない。それらは証拠不足として停止・報告し、失敗を成功にしない。

## 受け入れ基準

### Task 1 — #389

1. `real/sub/../run` と `alias/run`（alias は祖先 symlink）を、外部担当起動・runner 成果物作成前に拒否する。fake adapter 起動 0 回、出力先不在、参照先・既存 worktree 登録・feature HEAD 不変を確認する。
2. 正規実パスで run → accept → cleanup が成功し、実行後の worktree 差替えは拒否する。
3. fake と一時 Git だけを使用する。明示拒否の L テストは恒久追加せず一時検証、既存 S テストを維持する。

### Task 2 — #390

1. 修正後の実 runner＋fake の成功 1 試行、および失敗 primary＋成功 fallback のそれぞれで、worktree 削除成功後の cleanup.jsonl 最初の os.write だけへ EIO を注入する。初回は明示失敗し、I/O 回復後の別 CLI プロセスから通常 cleanup で残る worktree・runner-dir を回収し、さらに再実行が no-op である。各 normal 対照も確認する。
2. 同一レビュー・試行・worktree の成功証拠を用いる。証拠のない旧記録・不明消失は拒否して手動照合情報を示す。予定＋不在だけで成功としない。
3. 中断時に全未処理試行と runner-dir を削除せず、完全パスと理由を報告する。
4. 既存 Spec/ledger/runner メタデータの生バイト、無関係な登録、CODE_ROOT HEAD/status を前後比較し、不正な改変がない。
5. 予期しない消失・再出現、symlink/別 common-dir、private receipt、停止未確認の既存拒否を維持する。design の委譲も同じ仕様である。
6. 過去記録を改変しない。旧 Spec の回復可能という一般化は、元の記録を残し訂正注記を追記する。PR 説明も実装と新証拠に合わせる。

### 動作環境・実入力・防御範囲

Linux Dev Container、uv、実 Git worktree と実 agent-runner、fake adapter/CLI。複数試行・非 ASCII のパスと review 内容・複数行 JSON 入力を扱う。外部の実モデルや資格情報・実サービスをテストには使わない。実モデル起動は指定 Spec レビューと実装担当・PR ループの workflow 作業だけに限る。

対象は issue-to-pr の出力先検査と Spec/design cleanup。runner 本体の仕様変更、implement cleanup 全体の再設計、任意の破損修復、過去失敗証拠の書換え、実際の他セッションの資源回収は対象外。

## 調査・検証の初期記録

- 適用 AGENTS.md、Issue 本文、全ページコメント・timeline・依存を確認。両 Issue に parent・未完了依存・競合 PR・claim・番号一致の branch/worktree なし。PR #376 は再現元であり両修正は未実装。
- sp-debug が現行コードと再現元に対象コード差分がないこと、メモリ内再現で fault の missing 継続と旧 fixture の不足を確認。実 runner＋別 CLI は実装時に行う。
- ベースライン: 関連 pytest 56 passed / exit 0。`/workspaces/reso-world/tmp/agents/issue-390.bq1npfwa/baseline.log`。
- 正式な検証入口は README の `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。GitHub Actions は無効のまま。
