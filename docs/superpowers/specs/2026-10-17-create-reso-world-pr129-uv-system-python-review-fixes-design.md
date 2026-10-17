# PR #129: uv の Python をシステムに固定する（Issue #122）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/129（`feat/issue-122-uv-python-system` → `main`）
- 関連 Issue: #122（本文の `Refs #122`。`closingIssuesReferences` は空）
- 関連文書: `docs/superpowers/specs/2026-10-17-create-reso-world-issue122-uv-system-python-design.md`、`docs/superpowers/plans/2026-10-17-create-reso-world-issue122-uv-system-python.md`（どちらも draft のまま。この文書では変えない）
- 検証したコード HEAD: `7283789b67814c9cd9d71f5db33636452b900479`。base `main` は `cd602e6` で、PR の分岐点と同じ（base は進んでいない）
- 状態: completed
- 実行許可: 利用者が 2026-10-17（JST）に `/review-fix-planning #129` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要でマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-122-uv-python-system`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#129-feat-issue-122-uv-python-system/` の 3 ファイル。対象 HEAD はすべて `7283789b6781` で、取得した `pull/129/head` と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | Approve | なし（注記 1。R1） |
| `deepseek-deepseek-v4.1-flash.md` | Approve | なし |
| `grok-4.7.md` | Approve | なし（注記 1。R2） |

## 分類

Severity 付きの指摘は 3 ファイルとも 0 件。判断に関わる注記を次のとおり分けた。

| ID | 出どころ | 内容 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | Opus の「未実施の検証」 | README の「旧版で互換性を確かめる場合」の block を再実行していない（実行環境の安全チェックで拒否） | 対応しない。DeepSeek と Grok のレビューが同じ block を 2 つの設定の下で実行し、`uv python install --no-bin 3.12` が `manual` でも成功し、共有の `~/.local/share/uv` と `~/.local/bin` に Python が残らないことを確かめている。PR 本文の作成者の検証も同じ結果である |
| R2 | Grok の Merge recommendation（Opus・DeepSeek の「未実施の検証」も同じ） | 作り直した Dev Container と Herdr のペインでの受け入れ確認は未実施で、マージの後に利用者が行う | 対応しない。#122 の受け入れ基準そのもので、PR の Spec D-6 のとおり `Refs #122` にして #122 を open のまま残す。確認の前にマージしても、#122 の完了の証拠がまだ無いだけで、誤った結果は残らない。設定は rebuild まで効かないので、マージしただけでは既存のコンテナの挙動も変わらない |

分類: **解消済み 0 / 対応する 0 / 対応しない 2**。DeepSeek のレビューは注記も無い。

仕様の論点として残すもの: なし（`requires-python` をそろえるかは PR の Spec D-3 と PR のコメントで決着済み）。

同じ条件の再発と設計の見直し: 当たらない（「対応する」が 0 件。この PR に以前のレビュー修正は無い）。

## 確認の範囲

- PR の変更 4 ファイルの全文: `.devcontainer/devcontainer.json`、`.devcontainer/README.md`（追加した「uv の Python 実行環境」の節と前後の節）、PR の Spec・Plan。PR の本文と、作成者の「持ち越し候補の再調査」のコメント、Issue #122 の本文
- 関連する処理:
  - `devcontainer.json` を読むもの: `.devcontainer/mounts.bash`（`source=` の mount の行だけを読み、`//` で始まる行を飛ばす）、`.devcontainer/test-readme.bash`、`.devcontainer/test-initialize-mounts.bash`、`scripts/check-layout.sh` の mount の検査。`containerEnv` の行とコメントは対象にならない
  - uv の呼び出し: `git grep` で、追跡しているファイルの uv の呼び出しは `uv run --no-project`（postCreate の `cleanup_pi_mcp.py`、テスト用スクリプト、`scripts/superpowers-review-copy.sh`、`scripts/meshy.py`）と、プロジェクトの `uv run`・`uv sync`（`scripts/new-world.sh`）だけ。`uvx`・`uv tool`・`uv python` は無い。postCreate の `uv run --no-project` は、apt で `blender`・`python3-numpy` を入れた後に走る
  - MCP の設定（`.mcp.json`・`.cursor/mcp.json`・`.pi/mcp.json`）は `npx` と HTTP だけで、uv を使わない
  - 版の固定: 追跡しているファイルに `.python-version` と PEP 723 のメタデータは無い。`requires-python` はルートと雛形が `>=3.12`、`rst-writer` の評価用 fixture が `>=3.14,<3.15`（システムの 3.14.4 で満たす）。`external/resoloop-meshy` も `>=3.12` で、`.python-version` は無い
  - Blender: `templates/world-project/blender-system-python` は uv の Python の探索を使わない。`docs/meshy-resoloop.md` のとおり Blender は自分の版の `python3.X`（3.14）を PATH で探すので、uv の hint に従って `~/.local/bin/python3.12` ができても影響しない（PR のコメントの 3 と同じ結論）
- 自己確認: README の「既存コンテナの移行」の手順 3 の確認の block を README から抜き出し、`UV_PYTHON_PREFERENCE=system UV_PYTHON_DOWNLOADS=manual` を渡した bash で実行した。`preference=system downloads=manual`、通常の実行は `3.14.4`、`--python 3.12` は `No interpreter found for Python 3.12 ...` と `Python downloads are set to 'manual'` の hint で失敗し、block の終了コードは 0
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった
- PR と関係しない既存の問題で致命的なものは無い

## 検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| PR head `7283789` | `bash .devcontainer/run-tests.bash` | 30/30 PASS（12:50〜12:58Z、約 8 分） |
| PR head `7283789` | `bash scripts/check-layout.sh` | PASS（mount の一致を含む） |

PR はスキル（`.agents/skills/`・`tests/skills/`）を変えていないので、`uv run pytest tests/skills .agents/skills` は反映の条件にしない。base は PR の分岐点から進んでいないので、merge した一時的なツリーでの検証は不要。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）ので、check の確認は対象外。検証は clean な専用の worktree で行い、この文書の下書きは worktree の外に置いた。

## 自己レビュー

修正が無いので行わない（結論 2）。

## 所要時間

着手（2026-10-17 12:47Z ごろ）から Spec の記録まで約 14 分。レビュー・PR・Issue の読み込みと共通 context の確認 約 3 分、変更ファイルと関連の読み込み・README の確認の block の実行 約 4 分（`run-tests.bash` の待ち時間と重ねた）、一括検証（`run-tests.bash`・`check-layout.sh`）約 9 分、Spec の記録 約 1 分。
