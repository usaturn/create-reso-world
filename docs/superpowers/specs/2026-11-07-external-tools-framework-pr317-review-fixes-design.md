# PR #317 外部ツール共通管理基盤のレビュー修正の判断

- 状態: completed
- 対象 PR: https://github.com/usaturn/create-reso-world/pull/317（`docs/emission-repo-management` → `main`）
- 判断した HEAD: `ff50f4340ce2f11c81d1f512d2561f609318c161`
- サイクル: 1（PR 修正ループ run `3b889f294d9145c6adb8524e414a58d0`）
- planner: `claude-opus-5-5`（ランタイム: claude-code）
- 実行許可: 利用者が `/pr-review-fix-loop https://github.com/usaturn/create-reso-world/pull/317` を明示して起動した。review-fix-planning の完遂（この PR の承認済み実装修正と、結論 2 のマージ・関連 Issue の更新）の実行許可として扱う。ほかの PR・リポジトリ、Emission Editor の repo 作成・clone・移行・公開への許可には広げない
- 関連する文書: 設計 `docs/superpowers/specs/2026-11-06-emission-editor-repository-management-design.md`、実装計画 `docs/superpowers/plans/2026-11-06-external-tools-framework.md`（この PR が追加した。同じテーマの review-fixes の Spec は無いので、この文書を新しく作った）

## 1. レビュアーの構成

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `Grok-4.7.md` | Grok 4.7 | cursor | `cursor_grok4_xhigh` | `ff50f4340ce2` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | `devin_swe2-max_default` | `ff50f4340ce2` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | `pi_commandcode_deepseek4-flash_max` | `ff50f4340ce2` | はい | Request changes |

- 3 人とも loop の判定は `accepted`（`rejected` なし）。前のサイクルの判断の記録は無い（PR のコメントは 0 件）
- 修正と自己レビューの担当（loop の割り当て）: implement `claude-code_opus_default`、self-review `self`、fix-check `self`。結論 2 のため、いずれも起動していない。自己レビューの回数は 0
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#317-docs-emission-repo-management/verified/ff50f4340ce2.json`（review-verify の cycle モード）。工程の記録: 同じディレクトリの `verified/ff50f4340ce2.planning.json`

## 2. 指摘の一覧と分類

解消済み 0 / 対応する 0 / 対応しない 5。確認済みの一覧（review-verify）は 5 件とも confirmed（事実として確認）だが、下の理由で致命的に当たらない。

| 指摘 | 重大度 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `Grok-4.7#M-1@ff50f4340ce2` issue-to-pr の手順が `ci=disabled` を台帳の値だけで CI 確認の対象外にする（`.agents/skills/issue-to-pr/SKILL.md:125`） | Medium | 対応しない | 文言は実在し、`AGENTS.md` の「GitHub Actions」と `docs/external-tools-workflow.md` の実設定照合と食い違う。ただし害が出るのは、台帳が `ci=disabled` の登録済みツールで Actions が実際には有効になっている誤設定のときだけである。登録先の repo は未作成で、作成時に `enabled=false` を確かめる手順（設計 6 章の 4）がある。通常ツールは手動マージで、issue-to-pr は PR を作るだけなので、誤ったマージにはならない。規約の `AGENTS.md` が照合を求めている |
| `deepseek-deepseek-v4.1-flash#H-1@ff50f4340ce2` clone と managed cleanup が `GIT_ASKPASS`・`GIT_SSH`・`GIT_SSH_COMMAND` を落とす（`tools/external_tools/clone.py:76`、`.agents/skills/repo-cleanup-after-merge/SKILL.md:39`） | High | 対応しない | 環境変数が渡らないことは事実だが、影響は環境変数だけで認証する private の通常ツールに限られる。この環境の GitHub 認証は `credential.helper`（設定ファイル）で、`GIT_ASKPASS`・`GIT_SSH*` は設定されていない（2026-11-07 に確認。値は読んでいない）。登録済みの Emission Editor は公開 repo の予定で、取得に認証は要らない。失敗した場合も `git_failed` で止まり staging を残すので、気付かない損害にはならない |
| `deepseek-deepseek-v4.1-flash#M-1@ff50f4340ce2` clone の checkout が `submodule.recurse=true` で submodule を初期化しうる（`tools/external_tools/clone.py:209`） | Medium | 対応しない | 報告の条件（global の `submodule.recurse=true` だけ）では再現しない。clone と同じ手順（`init --template=` → `fetch --no-recurse-submodules` → `-c core.hooksPath=/dev/null -c core.fsmonitor=false` の `checkout --detach`）を submodule 付きのローカル fixture で実行すると、終了コード 0 で submodule の中は空、`status --porcelain=v1 --untracked-files=all --ignored` も空だった（Git 2.55.0。Grok の確認と同じ）。review-verify は、`submodule.active` も設定すると checkout が終了コード 128 で止まることを確かめた。その場合も clone は `git_failed` で止まって staging を残すので気付かない損害にならず、submodule の取得も起きない。この環境には `submodule.recurse` も `submodule.active` も無い |
| `deepseek-deepseek-v4.1-flash#L-1@ff50f4340ce2` managed tool の review-fix の worktree が親の `.worktrees` に作られる（`.agents/skills/review-fix-planning/SKILL.md:161`） | Low | 対応しない | resolver は同じ common-dir の linked worktree を受け付けるので動作は正しい。ResoLoop fork の review-fix でも同じ置き方をしている既存の挙動で、配置と片付けの整理の問題（保守性）に当たる |
| `deepseek-deepseek-v4.1-flash#I-1@ff50f4340ce2` loop のエラーメッセージが通常ツールを対象外と述べる（`.agents/skills/pr-review-fix-loop/scripts/loop.py:861`） | Info | 対応しない | 表示の文言だけで、判定と動作は変わらない |

SWE-2-Max は指摘 0 件。

### 自己確認

PR の変更ファイルの全文、呼出元（`scripts/superpowers_context.py` の `resolve_context`、issue-to-pr の `resolve_issue.py`・`resolve_base.py`、cleanup の手順のブロック）と関連テストを読んだ。この PR が持ち込んだ致命的な欠陥は見つからなかった。

マージ後に `resolve_context` が毎回、親の採用済み台帳を読む経路は、マージ後の状態を再現して確かめた。merge commit を detached HEAD にし、origin を `https://github.com/usaturn/create-reso-world.git`、ローカルの `origin/main` を同じ commit にした一時の常設親（`git clone --no-checkout` から作成）で、次を実行した。

| 確認 | 結果 |
| --- | --- |
| create-reso-world の `review-fix`（linked worktree、head 照合付き） | 成功。`code_root` は worktree、`base_remote`・`head_remote` は origin |
| create-reso-world の `review-workspace` | 成功。`code_root` は親 |
| 未取得の通常ツール（`usaturn/resonite-emission-editor`）の `review-workspace` | `checkout_missing` で終了コード 66。別の場所へ切り替えない |
| CLI の `list`・`check emission-editor` | `list` は終了コード 0 で採用 commit と 1 件。`check` は `missing`・終了コード 1 |
| 親を名前付き branch にした `review-fix` | `parent_not_detached` で終了コード 66 |

最後の行は、台帳を採用した後は、親が detached HEAD でないと create-reso-world 自身の PR の context も止まることを示す。`AGENTS.md` は親を常に origin/main の detached HEAD に保つと定めており、サポートしている構成では起きない。止まるときも理由付きのエラーで、誤った対象は選ばない。指摘にはしない。

## 3. 要件対応

PR 本文・設計（8 章の受け入れ基準）・実装計画の約束と、このサイクルの確認の対応。対応する指摘が無いので、修正の Task は無い。共有する条件（台帳の採用条件・common-dir の照合・手動マージの境界）の統合担当は planner で、確認の方法は下の表のとおり。

| 約束・制限 | 観測する結果 | 確かめた方法 |
| --- | --- | --- |
| 採用済み台帳は常設親の detached HEAD の blob だけから読み、候補では操作を許さない | マージ後の親で台帳を読み、未取得のツールは停止する | 2 章の自己確認、`tools/external_tools/tests`（4 章の検証） |
| 既存 parent / fork の経路と、未登録 repo の明示 `CODE_ROOT` の review-fix を保つ | create-reso-world の context が台帳の採用後も通る | 2 章の自己確認、`tests/scripts/test_superpowers_context.py` |
| 通常ツールは手動マージ（`finalize.py` の範囲を広げない） | 範囲外の repo はネットワークの前に止まる | `test_finalize.py`（4 章の検証） |
| clone は 1 件・排他・非置換で、submodule・hook・setup を実行しない | submodule を初期化しない | 2 章の M-1 の再現、`test_clone.py` |

## 4. 実行した検証

base（`origin/main`）の先端 `447784c6c7f09e5aa3d303c5cdadac26675c04de` は head の祖先ではないので、head にそれを merge した一時のツリー `297228207e66cc6a2b52e0fd0fbbfd3fb336c8e3`（競合なし、push しない）で検証し、これを検証の記録にした。head だけのツリー（`ff50f434`）でも同じ検証を通した。どちらも `mktemp -d` の隔離 worktree で、検証の前後の `git status --porcelain` は空だった。

この PR の Plan には、テストが fake を抜けて実際の GitHub への push を試みた事故が記録されている。そのため、PR の作者と同じ境界で実行した: `env -i` の最小環境、一時 HOME・XDG・短い TMPDIR、`GIT_CONFIG_GLOBAL=/dev/null`・`GIT_CONFIG_NOSYSTEM=1`、`unshare -rn` による別の network namespace（interface は loopback だけ、外への経路なし。外部への接続が名前解決で失敗することを確かめた）、DAC override の能力の削除、`UV_OFFLINE=1`。

| コマンド | マージ後のツリー | head だけのツリー |
| --- | --- | --- |
| `uv run --no-sync pytest tests/skills .agents/skills .agents/scripts tools tests/scripts/test_superpowers_context.py -q -rs`（隔離） | 終了コード 0。1330 成功・1 skip・45 subtests 成功 | 終了コード 0。同じ件数 |
| `bash .devcontainer/run-tests.bash <25 本>`（隔離。`test-pi-superagents.bash` を除く全部） | 終了コード 0。25 本成功 | 終了コード 0。25 本成功 |
| `bash scripts/check-layout.sh`（隔離） | 終了コード 0 | 終了コード 0 |
| `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash`（隔離なし） | 終了コード 0 | 終了コード 0 |
| skip された `test_dispatch.py::test_initial_snapshot_cannot_silently_skip_an_unreadable_subdirectory`（隔離なし） | 終了コード 0 | 未実行（マージ後のツリーで確認） |

- `test-pi-superagents.bash` は、本物の HOME にある Pi の導入物を読み、user namespace の root では `cp -a` が所有者を保存できずに失敗するので、隔離の外で実行した。このテストが対象にする `.devcontainer/` と `scripts/setup_pi_*` は、マージ後のツリーと base で差分が無く、dry-run とダミーのキーで動く
- skip の 1 件は、隔離環境の euid が 0 のときに飛ばす権限のテストで、隔離の外で実行して成功した
- 最初の隔離（1 版）では、TMPDIR が長く UNIX ソケットのパスの上限を超えた、loopback が DOWN だった、の 2 つの環境の原因で 4 本が失敗した。直した 2 版で通った。失敗はどれも PR の変更と関係しない

## 5. 結論

結論 2（修正不要としてマージ）。対応する指摘は 0 件で、全指摘・PR の変更ファイルの全文・関連する処理とテストを確認し、マージ後のツリーで検証が通った。自己レビューは結論 1 だけの工程なので行っていない。

対応しない 5 件のうち、実際に起こる 2 つの制約（環境変数だけの認証、`submodule.active` と `submodule.recurse=true` の併用）は、PR の説明の「既知の制限」に条件と回避方法を書き足した。

この PR のマージは、常設親への台帳（Emission Editor の項目）の採用に当たる（`docs/external-tools-workflow.md` の「採用するには、別途許可された親 PR のレビュー・マージ」）。利用者が明示して起動した PR 修正ループの結論 2 として行う。登録先の repo の作成・clone・移行・公開は、引き続き別の許可が必要である。
