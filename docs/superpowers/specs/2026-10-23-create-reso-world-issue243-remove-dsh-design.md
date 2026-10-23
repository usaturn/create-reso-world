# Issue #243: DSH 担当の撤去

- 文書管理: `usaturn/create-reso-world`
- 対象: `usaturn/create-reso-world#243`
- 着手時のコード: `7cf60715caf0026f7a4c95c72cdc2527e8075e2c`
- 状態: `completed`。レビュー修正サイクル 3 の設計と検証を記録した。内容の承認を受けた記録ではない
- 実行許可: 利用者の「`$issue-to-pr https://github.com/usaturn/create-reso-world/issues/243 --merge`」。推奨案で設計・実装・検証・PR 作成・指定のレビュー修正ループまで進める指示として扱う
- 追加指示: 利用者の「廃止したことについて、テストを書かないこと。TDD で実装しないこと。」を優先する

## 目的と範囲

使っていない DSH の担当と、そのためだけの親入力・bundle・隔離・成果照合・導入処理を撤去する。既定の `review.inspect` から `dsh-ccd` を外し、既存の `pi-deepseek` を使う。共通のレビュー保存、書き込み監査、停止確認、他のランタイムの挙動は維持する。

対象は `tools/agent_runner/`、`pr-review`、`pr-review-fix-loop`、`review-fix-planning`、Dev Container の設定・導入・現行の運用説明である。DSH 専用のテストと fixture は、対応する機能と一緒に削除する。共通の安全性テストは、残る機能の検証に必要なものを保持・整理する。

過去の `docs/superpowers/` の Spec・Plan、保存済みの PR レビュー結果、利用者の個人設定と資格情報は変更しない。現行ファイルに残る過去の評価入力・移植比較の DSH 専用記述は縮約し、元の詳細は Git 履歴で参照できるようにする。過去に別の担当を使ったと書き換えない。DSH 以外の adapter、Pi 経由の DeepSeek、Codex に対する既存の拒否規則は維持する。Dev Container の再構築、既存環境のアンインストールは行わない。

## 設計

### agent_runner と設定

`Runtime`、adapter の登録、`dsh.py` と `dsh_*.py`、専用の write path と receipt の処理を撤去する。`confined_writes` に基づく限定監査をなくし、起動前と実行後はすべての登録済み checkout を監査する。監査不能なら外部担当の起動前に拒否する。共通の停止・秘密情報除去・成果受け取り・後片付けの保証は残す。

個人設定の agent 定義に `runtime = "dsh"` が残る場合、設定の読み込み時点で DSH を撤去したことが分かるエラーにする。別のランタイムへ暗黙に置き換えない。古い `finalize-parent` hook や担当・fallback の移行は、最小限の案内として文書に残す。個人設定は自動編集しない。

### PR レビューと修正ループ

`prepare-parent`、`finalize-parent`、`pr_review_parent.py`、親からの bundle を使う private clone、DSH の観測 identity と staged 成果の親保存を撤去する。通常の checkout を使う prepare・complete・保存・cleanup は維持する。浅い checkout でも元の Git の shallow 境界・ref・FETCH_HEAD を書き換えずに PR 全体をレビューできるよう、必要な履歴は使い捨ての所有領域へ直接取得する。修正ループの DSH 用プロンプト、書き込み例外、成果照合、失敗分類、run_roles の DSH 拒否を撤去する。Codex の拒否と他のレビュアーの判定は維持する。

### Dev Container と文書

`install_beforehand.bash` の DSH 導入、対応する導入テスト、README の headless 手順を撤去する。雛形の `[agents.dsh-*]` と `finalize-parent` hook を外す。Dev Container の既存の bubblewrap など他用途の設定は残す。過去の Spec・Plan と保存済みの PR レビュー結果を変更せず、現行の評価資料と移植記録から DSH 専用の入力・旧手順を整理する。評価の日時と結果を別の構成で実施したと読み取れる表現にはしない。

## 決定記録

| 論点 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 撤去の粒度 | DSH 専用経路を呼び出し元まで削除する | adapter だけ残す、または互換 stub を置く | 孤立した bundle・hook の保守を残さず、Issue の目的を満たす | Issue #243 の推奨案への委任。共通経路に用途があれば残して確認する |
| 既定 inspect | `dsh-ccd` を既存の `pi-deepseek` に置き換える | DSH を外して 3 担当だけにする | 現行の個人設定と同じ構成の DeepSeek 担当を維持できる | Issue の選択委任。重複モデルなどで設定が無効なら見直す |
| 監査 | 常に全登録を監査する | `confined_writes` を一般機構として保持する | DSH 以外に利用者がなく、限定監査の前提がなくなる | Issue #243 の決定事項。監査の安全条件が弱くなるなら停止する |
| 個人設定 | 読み込み前半で旧 runtime を明示エラーにする | 一般的な `invalid_value` に任せる、または自動移行する | 黙った変更を避け、必要な利用者操作を示せる | Issue #243 の決定事項。秘密の値をエラーへ出さない |
| 過去の評価資料 | 現行ファイルの DSH 専用記述を縮約し、詳細は Git 履歴に残す | 現行ファイルにも旧担当一覧・導入観測をすべて残す | Issue #243 は過去の Spec・Plan の保存と、検索結果を最小限の撤去説明に絞ることを指定している。評価の日時・結果と、現在の構成で実施したかの区別は残す | Issue #243 の受け入れ条件を優先する。過去の評価を別の担当で実施したと読める変更はしない |
| テスト | DSH 専用テストを削除し、新しい廃止確認テストも TDD 工程も設けない。実行・静的解析・差分で確かめる | Issue に書かれた DSH 拒否の新規テスト 1 件 | 利用者の後続の明示指示と AGENTS.md のテスト採用基準を優先する | 利用者の追加指示。共通の安全性テストは残る保証に限り保持する |
| レビュー修正ループ | 既定の最大 3 サイクル、個人設定のレビュアー・修正担当を使う | 追加の `--assign` や上限指定 | 利用者は `--merge` だけを指定した。`check-options` はこの既定構成を受理した | 利用者の指定と既定の適用を区別する。ループの停止条件に当たれば成功扱いしない |
| Plan の実装担当 | 既定の `self` | `--implement` で外部担当を指定する | `implement_task.py check` が `self=true` を返し、利用者は上書きしていない | 雛形・個人設定の既定。Task の独立性に応じて実装方式を選ぶ |

## 受け入れと確認

1. 現行コード・設定・運用説明の DSH 参照は撤去され、`git grep -il dsh` の残りは過去の Spec・Plan、この Spec・Plan、最小限の撤去・移行案内だけである。検索結果を写したテストは作らない。
2. 雛形と現行の個人設定を使う PR 修正ループを確認し、指定のレビュー修正ループを 1 サイクル以上実行して結果を観測する。実モデルの起動はループに必要な範囲に限る。
3. 一時的な設定に `runtime = "dsh"` を含めて読み込み、外部担当を起動する前に分かりやすいエラーで停止することを確認する。正常な設定の読み込みも対にして確認する。
4. README の「テスト」の入口のうち追跡対象向けの `run-tests.bash`、`check-layout.sh`、`pytest` と、関連する静的解析を通す。
5. 作業完了後、#175・#211 を理由付きで not planned として閉じ、#116 に撤去を記録する。#243 と PR の状態を再確認する。

## 制限

Issue にない別リポジトリへの反映、利用者設定の編集、追加の実モデル評価は行わない。`--merge` のマージは review-fix-planning の `finalize.py` だけが行う。

## PR #249 レビュー修正サイクル 1（計画）

- 対象 HEAD: `2b2fc1181cb798ae4d3d8f3926accc3f80aefc18`
- 確認済み一覧: `reviews/usaturn/create-reso-world/#249-feat-issue-243-remove-dsh/verified/2b2fc1181cb7.json`。元の4指摘を3原因にまとめ、すべて現行 HEAD で確認した
- 実行許可: 利用者の `--merge` 指示に含まれるレビュー修正とマージの実行。文書の内容を承認済みにする指示ではない
- 結論: 対応する指摘が2件あるため、修正して既存 PR へ push する。修正後はループで再レビューする
- planner: `gpt-6-sol` / `codex`。レビューサイクル番号: 1

| レビューファイル | レビュアー・ランタイム | 対象 HEAD | 今回の入力 |
| --- | --- | --- | --- |
| `gpt-6.1-sol.md` | `gpt-6.1-sol` / `pi` | `2b2fc1181cb7` | 再実行 |
| `SWE-2-Max.md` | `SWE-2 Max` / `devin` | `2b2fc1181cb7` | 再実行 |
| `deepseek-deepseek-v4.1-flash.md` | `deepseek/deepseek-v4.1-flash` / `pi` | `2b2fc1181cb7` | 再実行 |
| `Grok-4.7.md` | `Grok 4.7` / `cursor` | `2b2fc1181cb7` | 再実行 |

| 元指摘 | 区分 | 現行 HEAD での根拠と判断 |
| --- | --- | --- |
| `gpt-6.1-sol#M-1@2b2fc1181cb7` | 対応する | 旧 Pi の成功・期限切れ `BatchResult` には空の `unrelated_checkout_audit` が保存される。新しい厳格なモデルはその欄だけで4つの読取入口を拒否し、停止確認済みの資源も未確認として残す。保存済み run の再開という主要経路が止まる |
| `SWE-2-Max#I-1@2b2fc1181cb7` | 対応する（上と同じ原因） | 同じ旧結果の読取拒否を指す。別の修正を重複して作らず、上の1つの安全条件で閉じる |
| `Grok-4.7#M-1@2b2fc1181cb7` | 対応する | 外部の浅い checkout では PR レビューの Git 操作をセッション内の所有 Git で行うのに、担当への許可文は元 checkout の Git を書き込み先に列挙する。実行者に対象外の Git 変更を許す危険がある |
| `deepseek-deepseek-v4.1-flash#L-1@2b2fc1181cb7` | 対応しない | `step` 28回に対して `STEP_TOTAL=29` で最後が `[28/29]` と表示される。利用・検証・保存の主要処理は止まらず、今回の致命的な修正条件に当たらない。表示が実際の制御や失敗判定に使われると判明したときに見直す |

### 守る条件と影響経路: 保存済み結果

原因は DSH 専用欄をモデルから除いた後も、非 DSH の旧実行で保存された空欄を読み込む経路が残ったこと。**旧版の空配列だけを読み取り時に受け入れ、現行形式の出力では復活させず、空以外や未知の欄は拒否する。** 入力境界の `BatchResult` に限定した移行で、各呼出元に別々の変換を置かない。全件を許す `extra=allow` は予期しない記録の取り違えを隠すため採らない。過去の結果を一括で書き換える案は、保存済み成果を変更し失敗時の途中状態を生むため採らない。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 旧版の空欄だけ受け入れる | `tools/agent_runner/models.py` の `BatchResult` 入力境界 | 修正する | 空配列付きの旧結果を受理し、空以外・未知欄を拒否する。現行の serialize に旧欄を出さない | 独立に構成した旧/現行/不正 JSON の入出力を照合する安全性テストと実行 | `f12c400`: 旧/現行の対照10ケースが期待どおり。代表テストは正常と観測ありの拒否を確認。変換を外す対照・無条件に捨てる対照で各1件失敗。担当結果 `implement-run/roles.json` |
| 停止確認済み資源を再開時に誤って未確認としない | `pr-review-fix-loop/loop.py` の保存結果・役割結果 | 既に満たす（共通の入力境界に依存） | 旧結果を読み、停止状態を元の記録どおり扱う | 旧結果の再開と資源監査を隔離実行 | `f12c400`: 旧結果の停止済み資源は `removed`。旧欄を除いた対照と同じ結果。10ケースの隔離実行に含む |
| 保存済み結果を正しい担当に結び付ける | `pr-review/review_run_record.py`、`issue-to-pr/implement_task.py` の読取入口 | 既に満たす（共通の入力境界に依存） | 旧結果の run と担当を読める | 旧結果で各入口を実行し、空以外は拒否する | `f12c400`: loop の2入口、attach-runner、issue-to-pr の全4入口で空欄を受理し、非空・null・未知欄を拒否 |
| 現行形式の厳格さを維持する | `StrictModel` と現行 `BatchResult` 出力 | 既に満たす | 無関係な追加欄は拒否され、旧欄を出力しない | モデルの serialize と不正 JSON の対照 | `f12c400`: `model_dump_json` に旧欄なし。未知欄は4入口で拒否。`tools/agent_runner` テストを含む1725件成功 |

### 守る条件と影響経路: レビュアーの書き込み先

原因は `helper_write_exceptions` が Git の実操作先を checkout の浅さに関係なく `source_git` として説明していたこと。**許可文には実際に helper が書く Git だけを列挙し、浅い checkout では元 Git への書き込みを許さない。** 入口ごとに独自の文面を作らず、共通関数へ浅い状態を明示して呼ぶ案を選ぶ。安全性テストは許可範囲を守るために必要であり、DSH の廃止確認を目的としない。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 浅い元 Git に書き込みを許可しない | `pr-review/review_run.py` の `helper_write_exceptions` | 修正する | shallow なら source Git の worktree/refs/objects を許可しない。通常 checkout なら必要な許可を保つ | shallow/通常の両側で許可文と実操作先を独立に照合する安全性テスト | `f12c400`: 同一/別 Git × shallow/通常の4ケース成功。過大許可ガードを外す3種類の対照で計4件失敗。実 prepare/complete の一時テスト2件で書き込み先と許可文を照合 |
| ループの許可文が実操作先と一致する | `pr-review-fix-loop/loop.py` の `review_write_exceptions` | 修正する | checkout の shallow 状態が共通関数に渡り、元 Git の過大な許可が消える | 浅い外部 checkout のプロンプト生成を隔離実行 | `f12c400`: 通常と depth=1 の clone で同一/別 Git の許可文を生成。浅い元 Git 全体の許可は消え、保存ロックだけが残る |
| 自己レビューの許可文が実操作先と一致する | `review-fix-planning/run_roles.py` の `write_exceptions` | 修正する | 同じ shallow 判定が使われる | 外部担当の依頼文を隔離実行 | `f12c400`: 通常と depth=1 の clone で別/同一 Git の許可文を生成し、同じ結果を確認 |
| Git 履歴を元 checkout に書き込まない | `pr-review/pr_review_workspace.py` の shallow 分岐 | 既に満たす | 一時所有 Git に取得し、元の shallow 境界・ref・FETCH_HEAD が変わらない | 既存の浅い checkout 検証と差分を照合 | `f12c400`: 実 prepare/complete の一時テスト2件で浅い元 Git の変更は0件。既存の浅い checkout テストも含む全 Python 1725件成功 |

同じ条件の過去のレビュー修正はこの PR の履歴に無く、設計見直しのきっかけには当たらない。修正担当は既定の `claude-opus`。隔離 worktree の commit `41c6e53` を差分・停止を確かめて `f12c400` として取り込んだ。runner の終了コードは1で、理由は別作業の checkout の変更・撤去を全登録監査が検出したこと。担当自身は終了コード0・停止確認済みで、対象 branch の差分は無かった。controller は取り込み後に `run-tests.bash` 23件、`check-layout.sh`、全 Python 1725件を完走した。Gitleaks は修正後の13 commitで検出0件。

### 修正後の自己レビューと結論

`run_roles.py --phase self-review` を1回だけ呼び、既定の `self` で PR 全体の自己レビューと fix-check を実施した。自己レビューは指定 commit `f12c400` の全体差分を対象に指摘0件で、関連テスト9件が成功した。fix-check は修正の9主張がすべて成立し、8変更ファイルの検査、文書候補181件の判定、関連テスト83件と安全性テストの変異対照を完了した。未確認は0件。結果は `reviews/usaturn/create-reso-world/#249-feat-issue-243-remove-dsh/verified/f12c400fc2e4.fix-check.json` と同じ接頭辞の要約・文書候補に保存した。レビュー後にコードを変更していないため、自己レビューを繰り返していない。

fix-check の `V-1` は `tools/agent_runner/runtimes/cursor.rst:49` の説明が、shallow checkout でも共有 Git に worktree 登録を書き込むように読めるという文書の不一致である。旧版にも同じ説明があり、修正後の helper の許可文と実際の prepare/complete は、浅い元 Git を書き換えずに動く。既存の不正確な説明ではあるが、現行の利用手順や安全境界を破る致命的な問題ではないので、このサイクルでは対応しない。文書を根拠に実際の書き込み先を広げる運用が生じた場合、または新しい証拠で操作結果への影響が示された場合に見直す。自己レビューと fix-check に新たな致命的な指摘は無く、結論は既存 PR への修正 push と次サイクルの再レビューとする。

## PR #249 レビュー修正サイクル 2（設計の見直し）

現行 HEAD `ed1c1bbb9e683ce88f30a810c95b24de7d7563d3` の4件の再レビューでは、`gpt-6.1-sol#M-2@ed1c1bbb9e68` が新しい active 指摘、ほか3件は active 指摘なし。`verified/ed1c1bbb9e68.json` は `confirmed` 1件、`unverified` 0件。M-2 は外部 checkout の自己レビューで、controller の `GIT_DIR` または `GIT_COMMON_DIR` が別の完全な Git を指すと、`run_roles.write_exceptions` の `uses_owned_history` が浅い checkout を通常の checkout と誤判定し、元 Git 全体への書き込み許可を渡すというもの。runner の子は `GIT_*` を除くため、同じ checkout を浅いと判定してセッション所有 Git に書く。これは利用者の Git に余計な権限を与える安全境界の不一致であり、前サイクルの `Grok-4.7#M-1` と同じ守る条件の2回目、かつ修正コミット `f12c400` が導入した判定の回帰である。`STEP_TOTAL` と旧 Cursor 文書の既存の `skip` 判断は、新しい影響証拠が無い限り引き継ぐ。

### 守る条件の設計

**守る条件:** 明示した checkout に対する Git の解決・浅さの判定・実操作は、controller と runner の子で同じ Git を参照する。外から渡された `GIT_*` によって別の Git へ向かわせない。その結果、通常／浅い checkout、親と同一／別 Git、準備・保存・失敗後の回収のどの状態でも、外部担当に渡す書き込み許可は helper が実際に管理する場所だけに限る。浅い元 Git は読取専用とし、必要な履歴と review 用 worktree はセッション所有 Git に置く。Git の解決に失敗したときは、過大な許可を出さず担当起動の前に止まる。

前サイクルの `f12c400` は `source_shallow` を許可文へ渡す仕組みを作ったが、判定の `pr_review_workspace.git` は controller の `GIT_*` を継承し、runner の子と同じ Git を見ている保証が無かった。`helper_write_exceptions` の純粋な分岐と、runner の `tools/agent_runner.workspace._git` の Git 環境除去だけでは、controller 側の判定と `review_target`・loop の checkout 解決が揃わない。

| 守る条件 | 経路・状態・停止位置 | 変更前の挙動 | 判定 | 観測する結果・assertion | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- | --- |
| 明示した checkout を読む | `agent_tmp._git` → `review_target._git` の親解決、`superpowers_context._git` → 対象解決、remote・ref の読取 | 外部 `GIT_*` を継承し、別 Git の設定や ref を読む余地がある | 修正する | `GIT_DIR`・`GIT_COMMON_DIR` が別 Git を指しても、指定 checkout の Git ディレクトリ・remote を得る。解決不能なら停止 | 独立した Git を使う隔離再現、通常入力との対照 | `172bc8f`: `review_target.git_environment` を中心に3入口を除去。`agent_tmp` と `superpowers_context` は循環 import を避けて同じ規則を各入口で実装。担当の一時再現では親 root・対象の出力が環境なし／2種類の汚染で一致。旧版の親 root は `GIT_DIR` 下で別 checkout を返した |
| 判定と実操作が同じ Git を見る | `pr_review_workspace.git` の `uses_owned_history`、prepare の fetch/worktree、complete/save、cleanup | `uses_owned_history` が周囲の Git 環境を継承し、浅い元 Git を通常と判定し得る | 修正する | 浅い source は常に true、通常 source は false。浅い元 Git の shallow 境界・ref・FETCH_HEAD・worktree 登録は準備から回収まで不変 | 所有 Git の動作確認と、別 Git へ向けた `GIT_*` の代表例を正常入力と対で実行 | `172bc8f`: 実関数の汚染なし／`GIT_DIR`／`GIT_COMMON_DIR` が一致。旧版では2種類とも誤判定。既存の浅い prepare/complete と全 Python 1726件成功 |
| 許可の根拠が実操作先と一致する | `loop.git_output` による親/source Git パス、`uses_owned_history`、`helper_write_exceptions`、reviewer prompt | Git パスの読取と浅さの判定で環境の扱いが異なる | 修正する | shallow なら親の保存ロックだけ、通常なら実際の source Git だけを許可する。失敗時は起動前に停止 | 環境あり／なしの許可文と実操作先を照合 | `172bc8f`: 一時的な loop の実関数で浅い／通常の親・source を各3環境で実行し、許可文が一致。旧版は remote が一致する別 Git を `GIT_DIR` に置くと別 Git 全体を許可した。関連587件成功 |
| 外部 self-review の許可を狭く保つ | `run_roles.write_exceptions` の `git_common_dir`、`uses_owned_history`、runner の子、fix-check | `git_common_dir` は `GIT_*` を除くが浅さの判定だけ継承するため、同じ source の2つの解釈が食い違う | 既に満たす（共通判定の修正に依存） | 浅い外部 source で元 Git 全体の許可が無く、通常 source では必要な許可がある。子と一致 | 実 `write_exceptions` を浅い／通常と環境あり／なしで実行 | `172bc8f`: 代表の S テストは浅い／通常と汚染なし／`GIT_DIR` を対照し4件成功。ガードを外した一時変異では1件失敗。`GIT_COMMON_DIR` は一時再現で同じ結果。元 Git の過大許可0行、通常 source は必要な1行 |
| 保存と回収の範囲を保つ | `review_run.helper_write_exceptions` と `pr_review_workspace` の保存ロック・セッション削除 | 許可文の分岐は正しいが、渡される浅さ・Git パスが誤り得る | 既に満たす（入力解決の修正に依存） | 元 Git の ref・object・登録と、親の保存ロック以外を増やさない。正常 checkout で必要な作成・回収ができる | 既存の浅い checkout 検証と正常 checkout の対照、差分の静的確認 | `172bc8f`: `helper_write_exceptions` は不変。浅い／通常の一時再現で許可文と対象一致。既存の save/cleanup テストを含む587件と全1726件成功 |

**直し方の比較:** (1) `uses_owned_history` だけで `GIT_*` を除く点の修正は、`review_target._git` と `loop.git_output` のパス解決を残し、同じ判定と操作が再びずれる。(2) checkout を明示する Git 呼出の環境を共通の方法で除去し、resolver・レビュー helper・loop の各入口で使う案は、環境が渡っても Git の対象を固定できる。(3) `GIT_*` がある呼出を非対応として拒否する案は、Git hook や `rebase --exec` から使う経路を不必要に狭める。**(2) を採用**する。Git 環境の除去は agent-runner の子と同じ規則にし、各 caller が独自に浅さや許可先を推測しない。PR の分割は、同じ安全条件を複数 PR にまたがって一時的に破るため採らない。

**検証の範囲:** M-2 は廃止の有無を問う指摘ではなく、残るレビュー経路の権限を守る S の条件である。実装後に、その守りを実装する場所へ代表的な安全性テストを1件置き、浅い source と通常 source の両側を確かめる。DSH 廃止を確認するテストは追加せず、TDD もしない。ほかの caller は同じ条件を隔離実行で照合し、固定の文言やファイル一覧を写すテストは作らない。

### 実装と検証（自己レビュー前）

既定の `claude-opus` 担当は隔離 worktree の `0c9b5de` に6ファイルをコミットした。runner は `success`・終了コード0・停止確認済みで、`outside_changes` と `checkout_audit` は空。controller は差分と親 `ed1c1bb`、clean status を確認して `172bc8f` として取り込んだ。両 commit のツリー ID は `6b2eef94e031b572cba5c4f05b819fbb01bfccb3` で一致する。担当は `run-tests.bash` 23件、`check-layout.sh`、関連587件、全 Python 1726件を完走した。controller は取り込み後の代表テスト4件と `git diff --check` を確認した。通常の Ruff と basedpyright は旧版からの指摘が残り、変更ファイルを旧版と同じ設定で比較した結果、新規指摘は0件。Gitleaks は `origin/main` からの15 commit で検出0件。DSH の廃止を確認するテストは足していない。

実モデルで不要な許可が利用された事実は確認しておらず、安全性の再現は許可文までである。

### 自己レビュー・fix-check と追加修正

`run_roles.py --phase self-review` を1回だけ呼び、既定の `self` で PR 全体の自己レビューと fix-check を進めた。自己レビューは指定 commit `172bc8f` の全体差分を対象に、保存と cleanup を完了し、active 指摘0件。fix-check は11主張と6変更ファイルを確認し、関連98件のテストと安全性テストの変異対照を通した。一方、`fix-check#V-1@172bc8ff26d5` を confirmed とした。`pr-review` の対話・非対話は直接 `review_run.py prepare→complete` を使う経路を含み、`GIT_ASKPASS` または `GIT_SSH_COMMAND` を唯一の Git 認証手段にした直接実行では、`172bc8f` がその変数まで除くため fetch が止まる。ローカルの偽 transport で両変数とも `ed1c1bb` は成功し、`172bc8f` は環境変数不足で停止した。実 private remote の認証は使わず、この条件の到達性は transport の実行とスキルの手順から判定した。これは今回の修正が作ったサポート対象の機能停止なので「対応する」とした。

同じ修正が生んだ回帰であり、自己レビュー後の指摘でもあるため、守る条件を次のように拡張して経路を見直した。**明示した checkout のローカル Git の解決・浅さ判定・書き込み先は外部の `GIT_*` に左右されない。一方、直接起動した pr-review helper は、Git transport の認証に必要な環境だけを fetch へ渡す。** runner の子は従来からすべての `GIT_*` を除いており、その経路の認証条件は変えない。

| 守る条件 | 経路・状態・停止位置 | `172bc8f` の挙動 | 判定 | 観測する結果・assertion | 確かめる方法 | `93bf88f` の結果 |
| --- | --- | --- | --- | --- | --- | --- |
| Git の対象を固定する | `review_target._git`、loop、親 root、対象 resolver | 全 `GIT_*` を除き、指定 checkout を読む | 既に満たす | `GIT_DIR`・`GIT_COMMON_DIR` が別 Git を指しても、指定 checkout の Git を読む | 既存の実関数対照と代表 S テスト | 既存の安全性テストを含む関連98件と全 Python 1726件成功。新しい `transport_auth` の既定は false で、これらの呼出元は変更しない |
| 浅さの判定と実操作先を一致させる | `pr_review_workspace.git` のローカル Git 操作、浅い prepare、save、cleanup、失敗後の abandon | Git の対象は揃うが、認証変数も除く | 修正する | local Git の対象は固定し、通常／浅い checkout の両側で所有領域だけを作成・回収する | GIT 環境が汚染された実 prepare→complete→cleanup、失敗→inspect→abandon、既存テスト | helper の Git 呼出だけ `transport_auth=True` とし、認証用4変数を許可した。`GIT_DIR`・`GIT_COMMON_DIR` は引き続き除く。修正前の fix-check で実成功3件・失敗回収1件と元 Git 不変を確認。修正後は関連98件と全 Python 1726件成功 |
| 直接実行の transport 認証を保つ | `review_run.py prepare` → head は `review_target.fetch_pull_head`、base は `pr_review_workspace.git fetch`。認証変数だけに依存する remote | `GIT_ASKPASS` と `GIT_SSH_COMMAND` が消え、準備が停止 | 修正する | 偽 transport の同じ入力で head と base の両方を取得する | 直接 prepare と2つの Git helper を分けて実行 | `93bf88f` は `pr_review_workspace.git` 単体の偽 fetch だけが成功。head の `review_target._git` は未修正で、`4ded953` の直接 prepare は SSH/HTTPS とも head fetch で停止（サイクル 3 の独立再現）。実認証サーバでの確認は未実施 |
| 外部担当への書き込み許可を増やさない | loop と run_roles の許可文、runner 子の環境 | 浅い元 Git への過大許可は解消済み | 既に満たす | shallow では元 Git への許可0行、通常では必要な1行 | 代表 S テストと修正前の fix-check の実関数対照 | 認証変数の許可は pr-review helper の直接実行だけ。loop・run_roles の環境は変更せず、代表 S テストと全 Python 1726件成功 |

点の修正として helper だけで `GIT_ASKPASS` を戻す案は、`GIT_SSH_COMMAND` など同じ transport 経路を取りこぼす。全 `GIT_*` を戻す案は、`GIT_DIR` で別 Git へ向く元の安全問題を再発させる。直接実行の認証機能を保証から外す案は、現行の pr-review 手順と食い違う。`review_target.git_environment` の引数で transport 認証だけを許可する方式を選び、同じ関数を使う resolver と helper でローカル Git の選択規則を共有した。4変数は `GIT_ASKPASS`・`GIT_SSH`・`GIT_SSH_COMMAND`・`GIT_TERMINAL_PROMPT` に限定し、repository の向きを変える設定・環境は渡さない。

自己レビューは規定の1回だけで、`93bf88f` の後に2回目を行っていない。`93bf88f` の時点で確かめたのは `pr_review_workspace.git` 側の偽 fetch と関連98件、全 Python 1726件、`run-tests.bash` 23件、`check-layout.sh`、差分・静的確認である。直接 prepare の head fetch はこの時点で検証されず、サイクル 3 で未修正と判明した。DSH の廃止を確認する新しいテストや TDD 工程は追加していない。fix-check の元成果は `reviews/usaturn/create-reso-world/#249-feat-issue-243-remove-dsh/verified/172bc8ff26d5.fix-check.json` と同じ接頭辞の要約・文書候補に保存した。残る未確認は実認証サービスを使った private remote の fetch である。

## PR #249 レビュー修正サイクル 3

対象 HEAD は `4ded95313c51c98b857769edf64ce0c934fbacf2`。4 レビュアーの active 指摘各 1 件は、すべて直接起動した `review_run.py prepare` の PR head 取得で transport 認証用環境変数を落とす同じ原因を指す。前回の `fix-check#V-1@172bc8ff26d5` を直す目的で `93bf88f` が `pr_review_workspace.git` へ認証用変数を戻したが、`fetch_pull_head` は別の `review_target._git` を使う。独立確認 `verified/4ded95313c51.json` は4件を1件に集約し、SSH の2つの認証変数で同じ失敗を再現した。前サイクルから引き継いだ V-1 を「対応する」とし、Git の対象汚染 M-2 は解消済み、表示ずれと旧 Cursor 説明は前回の「対応しない」を引き継ぐ。

### 守る条件の設計

守る条件は、直接起動の PR レビューが、利用者の `GIT_ASKPASS`・`GIT_SSH`・`GIT_SSH_COMMAND`・`GIT_TERMINAL_PROMPT` を remote fetch に渡しながら、checkout の選択を変える `GIT_DIR`・`GIT_COMMON_DIR`・`GIT_WORK_TREE`・`GIT_CONFIG_*` は渡さないこと。ローカルの Git 解決、浅さ判定、ref 確認、書き込み許可は明示した checkout を一貫して参照する。remote fetch の失敗は明示エラーで止め、違う checkout の ref に取り違えない。runner の子は既存の全 `GIT_*` 除去を維持する。

破れた前提は「認証用変数を戻した `pr_review_workspace.git` が prepare のすべての remote fetch を担当する」というもの。実際には PR head は `create_from_target` → `review_target.fetch_pull_head` → `review_target._git`、base と浅い履歴は `pr_review_workspace.git` を通る。`172bc8f` の共通除去はローカル Git の対象を守った一方、認証も消した。`93bf88f` は後者の経路だけを直し、前者を未修正のまま残した。これは同じ条件の再発、かつ前回修正の適用漏れであり、経路を全面的に見直す。

| 守る条件 | 経路・状態・停止位置 | `4ded953` の挙動 | 判定 | 観測する結果・assertion | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- | --- |
| 指定 checkout の Git を読む | `review_target._git` の root・remote 設定解決、ref の `rev-parse`、`agent_tmp`・`superpowers_context` の前段解決 | 全 `GIT_*` を除く | 既に満たす | 汚染環境でも指定 checkout の root・remote・ref と一致し、別 Git を読まない | 通常・浅い checkout と別 Git を指す `GIT_DIR`・`GIT_COMMON_DIR` の実関数対照 | 偽 transport の128条件で汚染された別 Git は不変。既存の S テストと fix-check の実行対照でも指定 checkout を維持 |
| head の transport 認証を保つ | `review_run.prepare` → `create_from_target` → `fetch_pull_head` → `review_target._git fetch`、失敗時の `TargetError` | 4 認証変数も除き、直接起動の SSH/HTTPS fetch が止まる | 修正する | 認証用変数が fetch に届き、汚染された Git 選択変数は届かず、期待 HEAD を取得する。認証失敗時は別 ref を採用しない | 独立したローカル SSH/HTTP transport で prepare 全体と fetch 単体、正常・失敗・汚染環境を対照 | `92639d4` の `fetch_pull_head` だけ `transport_auth=True`。偽 transport の認証あり30条件は修正前に失敗、修正後に成功。認証なし30条件は両方失敗し、古い ref 8条件は拒否。期待 HEAD と別 Git 不変を確認 |
| base・浅い履歴の transport 認証を保つ | `pr_review_workspace.git fetch`、通常・浅い source、prepare→complete→cleanup と失敗回収 | `transport_auth=True` で 4 変数を残す | 既に満たす | base/historical fetch は認証変数に到達し、元の浅い Git の shallow 境界・ref・FETCH_HEAD・worktree 登録は変わらない | 前回の偽 transport と既存の浅い checkout 検証を、現行修正後の実経路で再実行 | 既存の helper は変更せず、偽 transport の通常・浅い source と fix-check の独立対照で元 Git 不変。関連248件、全 Python1726件成功 |
| 書き込み許可を実操作先に限る | `loop.git_output`、`run_roles.write_exceptions`、`uses_owned_history`、runner 子の環境 | ローカル Git の選択は環境除去済み | 既に満たす | shallow 元 Git の過大許可 0 行、通常 checkout は必要な許可 1 行 | 代表 S テストと同じ Git 汚染の隔離実行 | 修正は `review_target.py` のみ。既存 S テスト、fix-check の shallow・通常の対照で許可先を維持 |
| 関連する Git 呼出の環境を明示する | `review_target._git` 全呼出元、`pr_review_workspace.git`、loop、親・対象 resolver、runner の Git 呼出 | remote fetch が 2 入口に分かれ、認証の扱いが不一致 | 修正する | transport を使う fetch だけ 4 変数を残し、local 読取と安全判定はすべて除く | 各呼出元の全列挙と実行対照、差分・構文確認 | `_git` の既定は従来どおり除去。remote fetch だけ opt-in。fix-check のコード主張9件成立、自己レビューの active・未確認指摘0件 |

直し方は、(1) `fetch_pull_head` の fetch にだけ認証用の環境を戻す点の修正、(2) `review_target._git` に local と remote の用途を明示し、remote fetch が共通の `git_environment(transport_auth=True)` を使うようにする案、(3) 直接起動の認証環境を保証から外す案を比べる。(1) は別の remote Git 操作が増えた際に同じ適用漏れを起こしやすい。(3) は現行の直接レビュー手順を狭める。(2) を採り、`fetch_pull_head` の remote 操作を明示する。ローカル ref 検証は認証変数も含めて除去し、remote fetch の前後で同じ指定 checkout と期待 HEAD を照合する。`pr_review_workspace.git` は認証用変数以外を除去する現行の共通関数を使い続ける。

**テストの採用:** 今回の欠陥は正常な認証条件で prepare が明示エラーになる L であり、恒久テストを追加しない。廃止した事実のテストは追加しない。偽 transport による prepare 全体の一時検証、既存の S テスト、静的・構造検査、差分確認で確かめる。TDD は行わない。実認証サービスは使わず、その未確認範囲を PR の説明に残す。

### 実行結果とサイクルの結論

既定の修正担当は隔離 worktree に `ccfd850` を commit した。runner の終了と担当の停止を確認し、`outside_changes` と checkout 監査は空。controller は同じツリー ID の `92639d4` として取り込んだ。担当は修正前後で計128条件の偽 SSH/HTTPS prepare を実行し、関連248件、スキル1185件、tools314件、Dev Container23件と layout を確認した。controller は取り込み後に全 Python1726件、Dev Container23件、layout、`git diff --check` を成功させた。Gitleaks は取り込み時点の19 commitで検出0件。実 private remote は未検証である。

規定の自己レビューは1回だけで、`92639d4` の PR 全体差分に active・未確認指摘は0件。fix-check はコードに関する9主張すべて成立、関連217件と独立した SSH/HTTP prepare が成功した。一方、前サイクルの上の表が `93bf88f` で直接 prepare の head fetch まで成功したように記載していた点を文書不整合 V-1 として確認した。この版で head と base の検証範囲を明記して訂正した。コードの追加修正や自己レビューの再実行はない。

今サイクルの結論は修正を既存 PR に push し、規定のレビュー修正サイクル数の上限に従って終了すること。マージは次のレビューサイクルで修正不要と判定された場合に行う。DSH 廃止の事実を照合するテストと TDD は実施していない。
