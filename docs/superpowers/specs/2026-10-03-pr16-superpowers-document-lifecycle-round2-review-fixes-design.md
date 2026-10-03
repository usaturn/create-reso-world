# PR #16 第2回レビュー指摘の修正方針

- 日付: 2026-10-03
- 状態: completed（ユーザの「進めてください。」で R9 を明示承認。後続の「推奨案で問題を解消してください。また#15マージ済みです。」に従って検証阻害要因を解消し、実装と必須検証を完了。公開先は既存 PR #16）
- brainstorming 経路: bounded
- 文書管理リポジトリ: `usaturn/create-reso-world`
- 対象リポジトリ・PR: [usaturn/create-reso-world #16](https://github.com/usaturn/create-reso-world/pull/16)
- 対象ブランチ: `docs/superpowers-document-lifecycle`
- 検証したコードの HEAD: `ab28ff527f1331b2fabed008b6f292b723e0bba8`
- 入力ディレクトリ: `reviews/#16-docs-superpowers-document-lifecycle/`
- 前回の判断: 対象 HEAD にコミットされている `docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-review-fixes-design.md`
- 関連する運用設計: `docs/superpowers/specs/2026-10-03-superpowers-document-lifecycle-design.md`

## 1. 目的と制約

指定ディレクトリのレビューだけを、現行 PR HEAD のコミット済み内容で再検証する。実際の誤動作、事実誤認、理由なく削除された回帰ガード、名指しの修正依頼に該当するものだけを修正対象にする。既存の対応範囲を広げる設計論点や、将来の保険となる文書・テスト追加は採用しない。

今回の成功条件は、create-reso-world の linked worktree を cwd にした pr-review が、helper で後から失敗するのではなく、resolver 内で fetch 前に明確な案内と終了コード 66 を返すことである。main checkout の通常経路と、既存の `CODE_ROOT` 検査は維持する。

計画フェーズの依頼は指摘の選別・修正計画であり、実装の承認ではなかった。本 Spec を提示して停止した後、ユーザの「進めてください。」で R9 が明示承認された。PR 内に記録された過去の包括的実行指示は、今回の実装許可として流用していない。

## 2. 入力と検証の範囲

次の3ファイルを全文読んだ。いずれも冒頭の対象 HEAD は `ab28ff527f13` で、Review history は初回 `821e82de7652` と更新 `ab28ff527f13` を記録している。

| ファイル | 現行の指摘 | 解消済みとして記録された指摘 | 未検証候補 |
| --- | --- | --- | --- |
| `openai-codex-gpt-6.1-sol.md` | M-1、M-2 | M-3 | なし |
| `deepseek-deepseek-v4.1-flash.md` | L-1、L-3、I-1 | L-2 | allowed-tools の相対パターン |
| `claude-opus-5-5.md` | L-2、I-1 | L-1 | allowed-tools の相対パターン |

検証対象の source/test は `git show ab28ff527f1331b2fabed008b6f292b723e0bba8:<path>` で取得した blob を読んだ。挙動検証には、一意な一時ディレクトリ配下に同 SHA の detached worktree とフィクスチャを作成した。既存 checkout の未コミット source/test や、他の worktree の差分は根拠にしていない。

文書の整合性調査は読み取り専用の調査役にも委譲した。最初の委譲はコマンド実行ツールがなく固定 HEAD を読めなかったため、暫定報告を検証根拠にせず、調整役が `git show` で取得した blob を渡して再調査した。最終分類と挙動検証は調整役が行った。

## 3. 全指摘の分類

**重複を統合した10項目: 解消済み2 / 対応する1 / 判断保留0 / 対応しない7。**

本書の R1〜R10 は今回のローカル ID で、前回 Spec の F 系 ID とは別である。同じ問題を報告した2モデルの指摘と、共有の未検証候補はそれぞれ1項目へ統合した。Claude L-2 に含まれる remote-less の論点は R3 と重複するが、当該指摘全体の分類は R4 に保持する。

以下の行番号はすべて検証 HEAD のコミット済みファイルを指す。`pr-review`、`review-fix-planning` のスキルは `.agents/skills/<name>/SKILL.md` を指す。

| ID | 出典 | 内容 | 区分 | 根拠・理由 |
| --- | --- | --- | --- | --- |
| R1 | Claude L-1、DeepSeek L-2（Resolved findings） | linked worktree の `CODE_ROOT` を resolver が通し、helper が拒否する | 解消済み | `pr-review:140–146` に main checkout 検査があり、親 cwd から linked `CODE_ROOT` を渡すと終了66と `CODE_ROOT is a linked worktree` を返す。現行の回帰テストも成功した。 |
| R2 | Codex M-3（Resolved findings） | 別 checkout の `DOC_ROOT` を使うと Spec の作成先とコミット先が不一致になる | 解消済み | `review-fix-planning:57,62–64,183` が作成・更新・コミット先を `DOC_ROOT` に統一している。別の文書 checkout に新規文書をコミットしてコピーし、更新後に旧SHAを `--replace-from` へ渡す操作が両方終了0。コピーと blob が一致し、親 checkout は未変更だった。 |
| R3 | DeepSeek L-1 | remote のない checkout に関する AGENTS.md の文言と exact-one-remote 検査が食い違う | 対応しない | `AGENTS.md:70` は明示指示を必要条件とし、同時に一致 remote 1件を要求する。remote 0件では終了66を再確認した。前回 Spec F3 と同じ、ローカル専用 checkout を許可するかの仕様論点で、現行方針を変更しない。 |
| R4 | Claude L-2 | 任意 `CODE_ROOT` の経路を2スキルに限定する規約と、Spec・planning・handoff の前提が食い違う | 対応しない | `AGENTS.md:70` が経路を pr-review と review-fix-planning に限定し、他の作業では停止する。運用 Spec §3.1 と各スキルの想定をどちらへ揃えるかは設計論点。前回 Spec F4 の対象外判断を維持する。 |
| R5 | Codex M-1 | コピー先の検査と `mv -f` の間に別コピーや編集を上書きできる | 対応しない | `scripts/superpowers-review-copy.sh:93–115` の競合2ケースを再現した。ただし前回 Spec F5 が対象外にした、同一名の同時実行・実行中の編集を保護範囲へ加える論点である。未修正だが「解消済み」にはせず、ロック・公開方式変更・注意書き追加も今回行わない。 |
| R6 | Codex M-2 | 外部 checkout の cwd が TOPLEVEL・helper 配置元として採用される | 対応しない | 外部 cwd の3ケースで resolver は終了0、TOPLEVEL は外部 checkout、指定式の helper は不存在だった。一方、親 cwd では正常な明示 `CODE_ROOT` を解決し、remote 2件を拒否する。`pr-review:123,169` と前回 Spec F6 の親 cwd 前提を維持し、外部 cwd 対応を追加しない。 |
| R7 | DeepSeek I-1 | 歴史的 Plan が後続レビュー修正を反映していない | 対応しない | Plan `:777,779` の旧記述は残るが、`docs/superpowers/README.md:45` と運用 Spec §7 は Plan を実装過程の記録と定める。前回 Spec F7 の判断どおり、過去手順を現行スキルへ同期する追記・テストはしない。 |
| R8 | Claude・DeepSeek の Unverified candidates | 相対 allowed-tools と別パスの DOC_ROOT が一致しない可能性 | 対応しない | `review-fix-planning:4` の相対パターンは確認したが、Claude Code の許可照合で実際に誤動作する根拠はない。前回 Spec F8 と同じ未検証の互換性懸念で、潜在バグの数行修正だとも確定していない。 |
| R9 | DeepSeek L-3 | linked worktree の cwd が TOPLEVEL 経路を通り、helper が後から拒否する | 対応する (a) | create-reso-world の linked cwd・`CODE_ROOT` 空で `pr-review:123` は終了0、MAIN_ROOT に linked worktree を返した。同じ値でコミット済み helper の `create --repo` を実行すると終了2、`repo must be the main checkout, not a linked worktree`。CODE_ROOT の早期拒否だけではこの経路を覆わない。 |
| R10 | Claude I-1 | Spec の包括指示による approved と、実施済み Plan の状態・未チェック項目 | 対応しない | 運用 Spec `:4,263` は包括指示で承認と扱う例外を明記し、Plan `:6` もその指示を記録する。この扱いの是非は設計論点。未チェック43・チェック済み0は確認したが、approved は未実施を断言する状態ではなく、PR は既知の検証失敗も報告しているため、全完了という事実へ書き換える根拠にしない。Info級の状態追跡補足として今回対象外にする。 |

レビュー内の Test suggestions は別の修正指示ではない。R9 を固定する回帰テストだけを採用する。R1・R2 の追加補強、R3〜R8・R10 の文書追記やテストは採用しない。前回 Spec にのみあるテスト補強候補を今回の指摘として持ち込まない。

## 4. 現行 HEAD の再現結果

最小再現はコミット済み resolver ブロックと helper を変更せずに実行した。

| ケース | 観測結果 |
| --- | --- |
| create-reso-world linked cwd、CODE_ROOT 空（R9） | resolver: 0、MAIN_ROOT は linked worktree。helper create: 2、main checkout 要件で拒否 |
| 親 cwd、linked CODE_ROOT（R1） | resolver: 66、fetch 前の linked worktree 拒否 |
| 親 cwd、remote 0件の CODE_ROOT（R3） | resolver: 66、`has 0 remotes ...; exactly one is required` |
| 外部 cwd、CODE_ROOT 空・明示・一致remote 2件（R6） | 3ケースとも resolver: 0。helper 配置元は外部 checkout |
| 親 cwd、外部 CODE_ROOT の対照（R6） | 正常なremote 1件: 0、一致remote 2件: 66 |
| 親とは別の文書 checkout の新規・更新コピー（R2） | `created:` / `replaced:`、両方0。親の文書に変更なし、コピーは committed blob と一致 |
| コピーAを mv直前で止め、異なる文書Bを同名へコピー後にA再開（R5） | BもAも0。Bの成功済みコピーがAに置換された |
| 旧版コピーの照合後、mv直前に注記を加えて処理再開（R5） | 0。注記が消えた |

R9 の再現手順は次のとおり。全フィクスチャを一意な一時ルート配下に置く。

1. 検証 HEAD の隔離 worktree を作り、HEAD 一致を確認する。`git show <HEAD>:.agents/skills/pr-review/SKILL.md` の手順2から、PR_URL の代入で始まる bash resolver ブロックをそのまま抽出する。
2. 別の一時 Git リポジトリを初期化し、空でない初回コミットと origin `https://github.com/usaturn/create-reso-world.git` を設定する。そのリポジトリから detached linked worktree を作る。
3. linked worktree を cwd とし、`PR_JSON` の url を `https://github.com/usaturn/create-reso-world/pull/16`、`CODE_ROOT` を空にして、`set -euo pipefail` と抽出ブロックを実行する。ブロック後に MAIN_ROOT・PR_REMOTE を表示する。現行 HEAD は終了0で linked worktree を返す。
4. コミット済み `pr_review_workspace.py` に `create --repo <linked worktree> --pr-number 16 --commit <フィクスチャHEAD> --head-branch fixture --model-name repro --temp-root <一時ルート>` を渡す。環境に `CODEX_THREAD_ID` があればこのフィクスチャ実行時だけ外す。終了2と linked worktree 拒否を確認する。既存テストを失敗させるための対象ファイル編集は不要。

R5 の同期には外部の PATH 上の mv ラッパーと FIFO を使い、時間依存の sleep や対象スクリプトの編集は行っていない。ネットワーク fetch や予約 ref の作成は再現に不要で、実施していない。

関連する現行テスト:

```text
.agents/skills/pr-review/tests/test_pr_review_skill_contract.py
.agents/skills/review-fix-planning/tests/test_review_fix_planning_skill_contract.py
51 passed in 5.78s
```

最初の `uv run --no-project pytest` は pytest が PATH にないため起動失敗した。依存を追加せず、既存の親 `.venv` の interpreter を `uv run --no-project --python /workspaces/reso-world/.venv/bin/python python -m pytest` で指定して再実行した。テスト本体は検証 HEAD の隔離 worktree にあるものを使用した。

最小再現11ケースは約4.2秒。検証の一時ファイル、フィクスチャ、ログはすべて一意な一時ルートに閉じ込め、検証終了時に worktree remove 成功後、親の一時ルートも削除した。Spec 作成・承認待ちへは残していない。保存前に PR HEAD が上記 SHA のままであることを再確認した。

## 5. R9 の修正方針

### 推奨案: TOPLEVEL 経路で早期拒否する

変更対象を次の2ファイルに限定する。

- `.agents/skills/pr-review/SKILL.md`
- `.agents/skills/pr-review/tests/test_pr_review_skill_contract.py`

1. resolver の `pr_repository == origin_repository` 分岐で、TOPLEVEL の git-dir と git-common-dir を絶対パス・実パスで比較する。既存の CODE_ROOT 検査と helper の `require_main_checkout` と同じ基準を使う。
2. linked worktree なら、create-reso-world の main checkout を cwd にするよう促すメッセージと対象パスを stderr に出し、終了66で停止する。MAIN_ROOT を後続へ正常値として返さず、helper・fetch の前に止める。
3. 手順2の本文に、同リポジトリの TOPLEVEL 経路も main checkout を要求することを短く示す。helper の安全要件は変更しない。
4. 回帰テストでは、create-reso-world の origin を持つフィクスチャから linked worktree を作り、そこを cwd にして CODE_ROOT を空で実行する。終了66、linked worktree と main checkout の案内、正常な MAIN_ROOT 出力がないことを確認する。
5. 同じ origin の main checkout を cwd にした対照ケースは、従来どおり終了0・MAIN_ROOT=main checkout・PR_REMOTE=origin となることを確認する。

既存の外部 CODE_ROOT 分岐、resoloop fork 分岐、remote 判定、helper、予約 ref の方式は変更しない。テストでは実際のネットワーク fetch をしない。resolver ブロックが終了66を返すことで、ブロック後に記載された fetch に到達しないことを固定する。

### 採用しない代案

git-common-dir から main checkout を自動解決する案は、作業先の自動切替という挙動変更を含む。今回必要なのは、指定した linked worktree が helper の要件を満たさないことを早期に知らせる修正だけなので採用しない。

## 6. 承認後の検証と反映

R9 のテストを先に追加し、現行 HEAD で失敗することを確認してから修正する。

| 検証 | 合格条件 |
| --- | --- |
| `uv run pytest .agents/skills/pr-review/tests/test_pr_review_skill_contract.py` | 新規 linked cwd ケースが66、main cwd の対照ケースと既存 CODE_ROOT・既知リポジトリのケースが成功 |
| `uv run pytest tests/skills .agents/skills` | スキル変更の検証がすべて成功 |
| `bash .devcontainer/run-tests.bash` | 環境変更に必要な検証が成功 |
| `bash scripts/check-layout.sh` | 配置検査が成功 |

今回の計画フェーズでは重い一括検証を実施していない。PR 説明は main 由来の test-instructions・slum03 の失敗を記録しているが、今回それらの一括再現や修正は行っていない。承認後の必須検証が失敗した場合は commit・push せず、原因と範囲外の障害を報告する。本書を根拠に未報告の問題を修正範囲へ追加しない。

検証が成功したら origin を fetch して既存 PR の先端を確認し、`docs/superpowers-document-lifecycle` にだけ commit・push する。現在の親 checkout の別ブランチへ実装修正を載せず、新規 review-fixes ブランチ・第二PRも作らない。push 後は指定 helper で同じ PR に分類・判断・結果の日本語コメントを作成または更新する。正確なモデル識別子は投稿時に pi-model-name の手順で取得する。

## 7. 対象外の設計論点

- R3・R4: remote-less checkout や他リポジトリの実装へ適用範囲を広げるか。今回規約を変更しない。
- R5: 同名コピーの同時実行・実行中編集を保護対象にするか。再現はしたが、今回保護範囲を再設計しない。
- R6: 外部 cwd からの pr-review 起動を支えるか。親 cwd 前提を維持する。
- R10: 包括指示を指定版への承認と扱う方法、歴史的 Plan の状態追跡をどこまで補うか。今回定義変更・状態補完をしない。

## 8. 初回実装と検証停止の記録

R9 は承認後に対象ブランチの既存 worktree `/workspaces/reso-world/.worktrees/superpowers-document-lifecycle` で実装した。初回検証時点ではコード変更は §5 の2ファイルだけで、HEAD は `ab28ff527f1331b2fabed008b6f292b723e0bba8` のまま、未コミットだった。以下は阻害要因解消前の結果であり、後続の結果は §9 に記録する。

| 検証 | 実測結果 |
| --- | --- |
| 追加した linked TOPLEVEL 回帰テスト（修正前） | `DID NOT RAISE ResolverStopped` で1件失敗。誤動作を捉えることを確認 |
| pr-review 関連テスト（修正後） | 37 passed |
| `uv run pytest tests/skills .agents/skills` | 284 passed, 1 skipped |
| `bash .devcontainer/run-tests.bash` | 26件中24件成功、2件失敗 |
| `bash scripts/check-layout.sh` | slum03 のスキル同期1件で失敗 |
| 読み取り専用タスクレビュー | Spec compliance・R9 task quality は Approved。必須検証ゲート未通過を別途指摘 |

失敗した `tests/scripts/test-instructions.bash` は `.pi/APPEND_SYSTEM.md lacks: async: false`、`tests/scripts/test-check-layout.bash` と配置検査は `resoloop skills sync --check failed for slum03` を報告した。これらの入力ファイルとテスト・スクリプトに R9 による差分はなく、PR説明にも記録されている既知の阻害要因と一致した。初回の承認範囲では修正せず停止した。

LSP の能動チェックは指摘0だったが、サーバーの coverage が inconclusive であり、clean 確認済みとは扱わない。テストによる検証結果とは区別する。

初回は必須検証が成功しなかったため §6 の停止条件を適用し、commit・push・PRコメント投稿を行わなかった。本書も当時はローカル・未コミットだった。初回の保存ログは対象 worktree の `tmp/pr16-r9-implementation/` にある。後続の明示承認と解消結果は §9 に記録する。

### 作業記録

- 着手: 2026-10-03 22:18頃 JST。
- 入力・PR・規約確認: 約4分。
- 文書調査委譲、挙動11ケースの再現、関連51テスト、teardown: 約7分。
- 分類・bounded設計・Spec作成と自己確認: 約5分。
- 全体: 約16分（計画フェーズのみ）。
- 上記は経過区間の概算であり、モデルの生成時間や委譲単体の正確な計測ではない。

## 9. 追加承認による阻害要因の解消と再検証

ユーザの「推奨案で問題を解消してください。また#15マージ済みです。」で、以下の阻害要因の解消が追加承認された。§3 のレビュー分類と R9 の設計は変更しない。

1. GitHub で #15 が MERGED であることを確認し、そのマージコミット `9699e94a56798a5d148d464825b57e426c155695` を先端とする `origin/main` を既存 PR ブランチに取り込む。検証前のコミットを避けるため `git merge --no-commit --no-ff origin/main` を使用した。競合はなく、R9 のパッチが取り込み前後で完全一致することを確認した。親 checkout や別 worktree の未コミット変更は取り込まない。
2. 差分を確認済みの `slum03` で `resoloop skills sync --update --json` を実行する。更新対象は `slum03/.agents/skills/resonite-build/SKILL.md` と `slum03/.agents/skills/.resoloop-bundled.json` の2ファイルだけだった。手順書には保存・再読み込み後のアセットURL移行の安全な扱いが1段落追加され、配布ハッシュが更新された。
3. `slum03` の `resoloop skills sync --check --json` を再実行し、終了0、`synchronized: true`、全19ファイル `current` を確認した。CLIと版ロックはともに `0.1.0-preview.15` のまま。Resoniteへの接続・ワールド変更・stateファイル変更は行っていない。

#15 の取り込みにより、旧 `async: false` の存在を要求するテストは、現行の同期 role API の指示を検査し、旧形式を禁止するテストになった。指示本文へ古い引数を戻す回避策は採用していない。

### 最終検証

すべて対象 worktree で同期実行し、終了を確認した。`slum03` の pytest はそのプロジェクトを cwd にした。

| 検証 | 結果 | 実行時間 |
| --- | --- | --- |
| `uv run pytest .agents/skills/pr-review/tests/test_pr_review_skill_contract.py` | 37 passed、終了0 | 約2秒 |
| `uv run pytest tests/skills .agents/skills` | 284 passed, 1 skipped、終了0 | 約13秒 |
| `bash tests/scripts/test-instructions.bash` | PASS、終了0 | 1秒未満 |
| `bash .devcontainer/run-tests.bash` | 26件すべて成功、終了0 | 約58秒 |
| `bash scripts/check-layout.sh` | PASS、終了0 | 約2秒 |
| `slum03` の `uv run pytest` | 538 passed、終了0 | 約117秒 |
| `git diff --check` と `git diff --cached --check` | 終了0 | 1秒未満 |

保存ログ・実測時間・R9の保全パッチは対象 worktree の `tmp/pr16-r9-blocker-resolution/` にある。阻害要因の解消と再検証は追加承認の範囲だけで行い、対象外とした R3〜R8・R10 は修正しなかった。実装と検証は完了し、本書・R9修正・スキル同期を既存 `docs/superpowers-document-lifecycle` ブランチにコミットして PR #16 へ反映する。公開コミットと push の結果は同 PR の review-fix-planning コメントに記録する。

### 追加作業の所要時間

- PR状態・受信コミット・承認範囲の確認、未コミットマージ、R9差分保全、スキル更新: 約2分。
- 関連テスト・環境検証・プロジェクト検証: 約192秒。
- 結果記録と公開処理: PRの作業結果コメントおよびローカルの公開ログに記録する。
