# PR #66 uv 経由でも Blender がシステムの NumPy を読めるようにする: レビュー指摘の選別

- 文書管理: `usaturn/create-reso-world`
- 対象 PR: https://github.com/usaturn/create-reso-world/pull/66（`fix/issue-60-uv-blender-numpy`、Closes #60）
- 状態: completed
- 対象 HEAD: `9695a1d619c71c24c533e9c10e389ab5c718402d`（レビュー 3 件とも同じ HEAD）
- 入力: `reviews/#66-fix-issue-60-uv-blender-numpy/`（`SWE-2-High.md`、`deepseek-deepseek-v4.1-flash.md`、`openai-codex-gpt-6.1-sol.md`）
- 実行許可: 依頼 `/review-fix-planning <PR URL>` による完遂（修正要否の確定、修正不要ならマージと関連 Issue の更新まで）
- 結論: 2（修正不要としてマージ）。「対応する」は 0 件
- 経路: 完遂のため brainstorming は呼ばない。PR の差分は 3 ファイル +38/−10 で、コードの修正は無い

## 指摘の振り分け

| ID | 指摘 | 区分 | 根拠 |
|---|---|---|---|
| SWE I-1 / DeepSeek L-1（両者のテスト提案 1 を含む） | `resoloop_env()` の venv 判定を Blender 無しで確かめる単体テストが無い | 対応しない | 欠陥の指摘ではない。文書の通常コマンド（`uv run`）で走らせる既存の実 fixture / 変換テストが、修正が無いと失敗する（PR 本文の RED 19 failed）。テストの追加も対応にあたり、致命的な指摘の修正に要らない |
| SWE I-2 | `pyvenv.cfg` を持たない非システムの `python3.X`（`uv python install`・conda・pyenv など）は PATH から外れない | 対応しない | サポートする Dev Container では到達しない。`uv python list --only-installed` は `/usr/bin/python3.14` だけで、conda・pyenv も無い。`uv python install` は文書で使わないとしている。PR の前から同じで、PR による回帰でもない。実在する制約なので PR 本文の既知の制限に書き足す |
| DeepSeek 未検証候補 | 文書 46 行の「`uv python install` の `~/.local/bin/python3.X` も Blender を壊す」は未再現 | 対応しない | 文書の指示は「使わない」で、そのとおりにして誤った結果になる経路が無い。DeepSeek の probe は `.venv/bin/python3.14`（実体は `/usr/bin/python3.14`）への symlink で、uv が置く単体の Python とは別の構成 |
| 自己確認 S-1 | `.devcontainer/README.md:186` に「実 fixture / exporter は一時 wrapper で確認済み」が残る | 対応しない | #50 の時点の検証記録で、手順ではない。読んでも誤った操作にならない |

Codex のレビューは指摘 0 件。件数: 解消済み 0 / 対応する 0 / 対応しない 4 グループ（上表）。

## 確認

- 全指摘に加え、PR の変更 3 ファイル（`scripts/meshy_conversion.py`・`tests/scripts/test_meshy_conversion.py`・`docs/meshy-resoloop.md`）を HEAD のコミット済みの内容で全文読んだ。
- Blender を起動する経路: 本番は `run_resoloop()` だけで、`convert_operation()` の変換・export の 2 回とも通る。`meshy_workflow._cli` は Meshy CLI を起動するだけで Blender を起動しない。`.devcontainer/verify-resonite-tooling.bash` は uv の外で `blender` を直接起動する。テストの直接起動 5 箇所（`tools`・`glbs` fixture、probe 3 箇所）はすべて `env=resoloop_env()` を渡す。fake の `resoloop` は shebang に `sys.executable` の絶対パスを使い、PATH の絞り込みの影響を受けない。
- `resoloop_env()` の実行確認（HEAD の隔離 worktree）: `pyvenv.cfg` が要素の直下・親にある要素だけが外れ、通常の要素・空の要素・重複・順序は残る。`MESHY_*` は渡らず、親の `os.environ` は変わらない。PATH が無いときも例外にならない。`uv run --no-project --with pytest` の下では `/workspaces/reso-world/.venv/bin` だけが外れ、`resoloop`・`blender`・`python3.14` は `~/.dotnet/tools`・`/usr/bin` に解決する。
- テストのモジュールでの `sys.path.insert(0, scripts)` は、`scripts/` に標準ライブラリと同じ名前のモジュールが無く、`test_superpowers_review_copy.py` も同じことをしている。
- PR が持ち込む致命的な欠陥は見つからなかった。

## 検証

環境: 既存コンテナ、Blender 5.0.1、ResoLoop 0.1.0-preview.17 系の fork build、`MESHY_API_KEY`・`RESOLOOP_BLENDER_EXECUTABLE` なし。

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| 専用の worktree（HEAD `9695a1d`） | `env -u MESHY_API_KEY -u RESOLOOP_BLENDER_EXECUTABLE uv run --no-project --with pytest pytest tests/scripts/test_meshy.py tests/scripts/test_meshy_conversion.py -q -rs`（Issue #60 の再現コマンド。PATH の先頭は `/workspaces/reso-world/.venv/bin`） | 192 passed / skip なし / exit 0 |
| 専用の worktree | `bash .devcontainer/run-tests.bash` / `bash scripts/check-layout.sh` | 28 件 PASS / PASS |
| head に base（`origin/main` = `745acd8`、PR #65 のマージ）を merge した一時ツリー（push しない。競合なし） | 上の 3 つ（meshy のテストはリポジトリのルートから一時ツリーのテストを指定し、PATH の先頭が `.venv/bin` になる条件をそろえた） | 192 passed / 28 件 PASS / PASS |

CI: プライベートの create-reso-world は CI を使わない（`AGENTS.md`）。check は報告されない。

## 守る条件と影響経路

「対応する」が 0 件のため作らない。

## 既知の制限（PR 本文に追記する）

- PATH から外すのは `pyvenv.cfg` を持つ仮想環境の `bin` だけである。`pyvenv.cfg` を持たない非システムの `python3.X`（`uv python install`・conda・pyenv など）が PATH で `/usr/bin` より前にあると外れず、同じ症状が残る。Dev Container ではこれらを入れない。

## 自己レビュー

修正が無いため行わない。
