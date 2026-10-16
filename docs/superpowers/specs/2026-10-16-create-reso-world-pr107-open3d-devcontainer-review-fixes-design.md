# PR #107: open3d 用の libegl1・libgl1（Issue #91）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/107（`feat/issue-91-open3d-devcontainer` → `main`）
- 関連 Issue: #91（本文の `Refs #91`。`closingIssuesReferences` は空）、親 #95
- 関連文書: `docs/superpowers/specs/2026-10-16-create-reso-world-issue91-open3d-devcontainer-design.md`、`docs/superpowers/plans/2026-10-16-create-reso-world-issue91-open3d-devcontainer.md`
- 検証したコード HEAD: `ffaf754db5997d5ba21d51bfb4f90bceaac4a9e5`（PR の分岐点 `e7eb72a1602a`）。base `main` は `f9f13a7` まで進んでいる。#106・#108・#109・#113 の文書と `scripts/resoloop-meshy.sh`・`tests/scripts/test-resoloop-meshy.bash` で、この PR の変更ファイルと重ならない。head に merge した一時的なツリーでも検証した
- 状態: completed
- 実行許可: 利用者が 2026-10-16 に `/review-fix-planning #107` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要でマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-91-open3d`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#107-feat-issue-91-open3d-devcontainer/` の 4 ファイル。対象 HEAD はすべて `ffaf754db599` で、取得した `pull/107/head` と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `SWE-2-High.md` | Approve | なし |
| `claude-opus-5-5.md` | Approve | なし |
| `deepseek-deepseek-v4.1-flash.md` | Approve | Info 1（R1）、未検証の候補 1（R2） |
| `gpt-6.1-sol.md` | Needs manual verification | なし（rebuild の後の import が未確認という注記。R3） |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | DeepSeek I-1 | 確認用コピー `tmp/superpowers-review/create-reso-world-issue91-open3d-plan.md` が、実行の記録を追記する前の版のまま | 対応しない。事実は確かめた（コピーは `d636959` の Plan とバイト単位で一致し、`ffaf754` とは一致しない。Spec のコピーは両方と一致）。差は Plan の「実行の記録」の節の追記だけで、Task と判断は変わらない。コピーは親 checkout の追跡外の確認用のファイルで、PR とマージの結果に入らない。`AGENTS.md` は記録の追記だけの変更に再承認を求めない。古いコピーを読んでも誤った操作にはならない |
| R2 | DeepSeek の未検証の候補 1 | rebuild したコンテナで open3d の import が失敗するかもしれない | 解消済み。rebuild に相当する状態で再現しないことを確かめた。(1) `LD_DEBUG=libs` を付けて `import open3d`（0.20.0、`DISPLAY`・`WAYLAND_DISPLAY` なし）を実行し、読み込まれた共有ライブラリを dlopen の分も含めて列挙すると、open3d の配布物と uv の Python の外は 18 パッケージ（`libc6`・`libegl1`・`libgcc-s1`・`libgl1`・`libglvnd0`・`libglx0`・`libidn2-0`・`libpcre2-8-0`・`libselinux1`・`libstdc++6`・`libudev1`・`libunistring5`・`libusb-1.0-0`・`libx11-6`・`libxau6`・`libxcb1`・`libxdmcp6`・`zlib1g`）だった。(2) `/var/log/apt/history.log` と `/var/log/dpkg.log` によると、このコンテナの作成時（2026-10-09 15:47、postCreate の `apt install`）より後に入ったのは、2026-10-12 の `apt-get install -y libegl1`・`apt-get install -y libgl1`（と依存の `libegl-mesa0`）だけである。残りの 16 パッケージは、ベースイメージ（2026-08-17〜10-05 の記録）か、作成時の `apt install`（Blender の依存）で入っている。(3) head の `apt install` の行は `libegl1`・`libgl1` を指定しており、`libegl-mesa0` は `libegl1` の Depends で入る。実際の rebuild での確認は、PR と Spec D-7 のとおり、マージの後に利用者が行って #91 に記録する |
| R3 | GPT の Merge recommendation | 受入の条件である rebuild の後の `import open3d` が未確認なので、利用者の確認が要る | 対応しない。PR 本文と Spec D-7 が定めたマージの後の手順で、`Refs #91` により #91 は open のまま残る。確認の前にマージしても #91 の完了の証拠がまだ無いだけで、誤った結果は残らない。R2 のとおり、rebuild に相当する状態で欠けるライブラリは無い |

分類: **解消済み 1 / 対応する 0 / 対応しない 2**。SWE-2・Opus のレビューは指摘 0 件。

仕様の論点として残すもの: なし。

同じ条件の再発と設計の見直し: 当たらない（「対応する」が 0 件。この PR に以前のレビュー修正は無い）。

## 確認の範囲

- PR の変更 4 ファイルの全文: `.devcontainer/install_beforehand.bash`（470 行）、`.devcontainer/README.md`（794 行）、Issue #91 の Spec・Plan
- 関連: `.devcontainer/run-tests.bash`、`test-readme.bash`・`test-install-beforehand.bash`・`test-verify-resonite-tooling.bash`・`verify-resonite-tooling.bash` の該当箇所、`docs/meshy-resoloop.md:44`、Issue #91 の本文（ボードの変えてよいもの・完了の証拠）と状態のコメント、#95 のボードの #91 の行
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった。今のコンテナは 2026-10-12 から `libegl1`・`libgl1` が入った状態で Blender を使っており、この PR はその状態を Dev Container の定義に揃える。apt の設定は `APT::Install-Recommends "1"` で、作成時と同じ
- 検証は、PR head を checkout した既存の worktree と、`mktemp` の隔離 worktree（head に base を merge した一時的なツリー。push しない）で行った。R2 の確認の一時ファイルも `mktemp` のディレクトリに置き、終わったら消した

## 検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| PR head `ffaf754` | `bash .devcontainer/run-tests.bash` | 29/29 PASS（154 秒） |
| PR head `ffaf754` | `bash scripts/check-layout.sh` | PASS |
| head に base `f9f13a7` を merge したツリー（push しない） | `bash .devcontainer/run-tests.bash` | 30/30 PASS（161 秒。base で増えた `tests/scripts/test-resoloop-meshy.bash` を含む） |
| 同上 | `bash scripts/check-layout.sh` | PASS |
| 今のコンテナ | `uv run --offline --no-project --with open3d==0.20.0 python -I -c "import open3d"`（`LD_DEBUG=libs`、`DISPLAY`・`WAYLAND_DISPLAY` なし） | `0.20.0`（Python 3.12.15）。読み込んだライブラリの集計は R2 |

merge は競合しない（`git merge-tree --write-tree`）。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）ので、check の確認は対象外。

PR head の `run-tests.bash` の実行中（05:31Z ごろの約 20 秒）、この文書の下書きが未コミットのまま専用の worktree にあった。気づいて worktree の外へ移し、その後の check-layout と merge したツリーの検証は clean な状態で行った。追跡外のファイルが 1 つ増えても、失敗するはずのテストが PASS になることはない。

## 自己レビュー

修正が無いので行わない（結論 2）。

## 所要時間

着手（2026-10-16 05:25Z ごろ）から Spec の記録まで約 11 分。レビューと PR の読み込み 約 2 分、R1・R2 の確認（`LD_DEBUG` と apt の履歴）約 3 分、変更ファイルと関連の読み込み 約 2 分、一括検証 2 回 約 5 分（待ち時間に記録を下書き）。
