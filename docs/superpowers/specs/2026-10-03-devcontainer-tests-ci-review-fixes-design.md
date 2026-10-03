# PR #15 レビュー指摘の修正方針（devcontainer-tests の flaky な失敗の残存）

- 対象 PR: usaturn/create-reso-world #15（`fix/devcontainer-tests-ci`）
- 現行 HEAD: `e2a5995e93162d14d37843be9e5855f2a7265577`
- 入力: `reviews/#15-fix-devcontainer-tests-ci/`
  - `claude-opus-5-5.md`（対象 HEAD `e2a5995e9316`、Low 1 件）
  - `openai-codex-gpt-6.1-sol.md`（対象 HEAD `e2a5995e9316`、Medium 1 件）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（対象 HEAD `e2a5995e9316`、指摘 0 件）
- 経路（brainstorming の判定）: bounded。既存のテストスクリプト 1 本の中で、同じ形の箇所を置き換えるだけで、CLI や他のテストとのインターフェースは変わらない
- 承認: ユーザが「推奨案で修正を進めてプッシュまで」と事前に承認した

## 背景

PR #15 は #10（`test-herdr-agent-task.bash` の SIGPIPE による flaky な失敗）を閉じるため、`test_title_truncation_under_c_locale` で CLI の出力をいったん変数に受け、`printf '%s\n' "$out" | rg -m1` で抽出する形に直した。2 モデルのレビューは、この形にも同じ競合が残ると指摘した。`rg -m1` / `rg -q` は一致した時点で終了する。bash の `printf` ビルトインはパイプへ 1 行ずつ書き込むため、一致行より後ろの行を書く時点で読み手がいなければ SIGPIPE で落ちる。テストは `set -euo pipefail` で動くので、代入や検査が終了コード 141 になり、スクリプトが失敗する。

## 現行 HEAD での再現

レビュー対象 HEAD の隔離 worktree で、各形を `set -uo pipefail` のもとで 16 並列 × 500 回（計 8000 回）実行した（8 コア、bash 5.3.9、ripgrep 15.1.0）。

| 形 | 対応する行 | 失敗 / 8000 回 | 失敗時の終了コード |
| --- | --- | --- | --- |
| C ロケールの CLI 出力を `printf \| rg -m1` で抽出（PR の形） | 147-148 | 5 | 141 |
| ASCII タイトルの CLI 出力を `printf \| rg -m1` で抽出 | 121（136 も同じ形） | 1 | 141 |
| `printf \| rg -q` で一致行（3 行目、後ろに 5 行）を検査 | 65 ほか | 3 | 141 |
| C ロケールの抽出を here-string で渡す | （修正案） | 0 | — |
| `rg -q` の検査を here-string で渡す | （修正案） | 0 | — |

## 指摘の一覧と振り分け

分類: 解消済み 0 / 対応する 4 / 判断保留 0 / 対応しない 1

| ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| F1 | Claude L-1 本体、Codex M-1 | 148 行目の `printf '%s\n' "$out" \| rg -m1` で SIGPIPE の競合が残る | 対応する (a) | 現行 HEAD で 8000 回中 5 回、終了コード 141 を再現 |
| F2 | Claude L-1 付随 | 146 行目のコメントが、CLI を直接つながなければ SIGPIPE は起きないと読める | 対応する (b) | F1 の再現により、変数に受けても後段のパイプで SIGPIPE が起きることを確認。コメントの前提が事実と異なる |
| F3 | Claude L-1 付随（差分外） | 手本とした 121・136 行目も同じ形 | 対応する (a) | 121 行目と同じ形で 8000 回中 1 回、終了コード 141 を再現。136 行目は CLI への入力が違うだけで、パイプの形は同一 |
| F4 | Claude L-1 付随（差分外） | 同じファイルの `printf '%s\n' "$out" \| rg -q` 検査も、一致行が最終行でなければ同じ競合を持つ | 対応する (a) | 65 行目と同じ形で 8000 回中 3 回、終了コード 141 を再現 |
| F5 | Claude L-1 根拠 | PR 本文の「修正後の形は 300 回中 0 回」は試行回数が少なく、残存率を検出できていない | 対応しない | リポジトリ内の記述ではない。修正後の再検証結果は PR へのコメントで示す |

DeepSeek のレビューは指摘 0 件で、本文で「SIGPIPE の窓を塞いでいる」としている。F1 の再現により、この判断は採らない。

## 修正方針

対象は `.devcontainer/test-herdr-agent-task.bash` だけである。CLI 本体（`.devcontainer/herdr-agent-task.bash`）は変更しない。

1. **F1・F3・F4**: ファイル内の `printf '%s\n' "$out" | rg …` をすべて `rg … <<<"$out"` に置き換える。here-string は `printf '%s\n'` と同じく末尾に改行を付けるので、`rg` が受け取る入力は変わらない。bash は here-string の内容を `rg` の起動前に書き終える（小さい入力はパイプに一括で書き込み、大きい入力は一時ファイルを使う）ため、`rg` が先に終了しても書き手が SIGPIPE を受けない。
   - 一致行が最終行の箇所（`assert_label_on_every_status` の `unknown` キーなど）と、否定検査（94 行目）は単独では競合しにくい。しかし、ファイル内に `printf | rg` の形を残すと、今後の追加で同じ形が写される。そのため同じ置換をそろえて適用する。94 行目の否定検査は、退行で `state_label` 行が混入した場合に、`printf` が 141 で終わると `if` が偽になり、検査をすり抜ける経路もある。
   - `printf '%s\n' "$out" | wc -l`（161 行目）は `wc` が入力を最後まで読むため競合しない。変更しない。
2. **F2**: 146 行目のコメントを削除する。代わりに `run_dry` の直後に、出力の検査を here-string で渡す理由（`rg -q` / `-m1` が早期に終了するため、CLI も `printf` もパイプでつながない）を 1 か所だけ書く。

## 検証方法

| 対象 | 方法 | 期待結果 |
| --- | --- | --- |
| F1–F4 | `bash .devcontainer/test-herdr-agent-task.bash` を単発で実行する | `OK test-herdr-agent-task (task2)` |
| F1–F4 | `rg -n "printf '%s\\\\n' \"\\$out\" \\| rg" .devcontainer/test-herdr-agent-task.bash` | 0 件 |
| F1・F3・F4 | 修正後のテストスクリプト全体を 16 並列で繰り返し実行する（手元のみ。確率的な検査なので CI には入れない） | 失敗 0 件 |
| 環境の変更 | `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` | PASS |

## 範囲外

- `.devcontainer/test-*.bash` と `tests/scripts/*.bash` にある、ほかの「生成側コマンド → `grep -q` / `rg -q`」のパイプ。Claude のレビューが確認したのは `test-readme.bash:21`、`test-resonite-feature.bash:7`、`test-check-layout.bash` の `PASS: check-layout` 検査だけで、書き込みが 1 回で終わるか一致行が最終出力であるため対象外と判断した。`test-herdr-status.bash` と `test-pi-openai-codex.bash` にある `printf '%s\n' "$out" | rg -q` / `grep -q` の形は、この選別では確認しておらず、第2回のレビューで同じ競合が再現した。対応は `docs/superpowers/specs/2026-10-03-devcontainer-tests-ci-round2-review-fixes-design.md` に記録した。
