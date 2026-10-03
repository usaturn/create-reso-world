# PR #15 第2回レビュー修正の方針（同じ CI ジョブに残る `printf | rg` の SIGPIPE）

- 対象 PR: usaturn/create-reso-world #15（`fix/devcontainer-tests-ci`）
- 現行 HEAD: `53f9bfc9073405d16b8f87698f0515e833847829`
- 入力: `reviews/#15-fix-devcontainer-tests-ci/`（3 ファイルとも Initial が `e2a5995e9316`、Update が `53f9bfc90734`）
  - `claude-opus-5-5.md`（現行 HEAD で Low 1 件。前回の L-1 は解消済み。未検証候補 1 件）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（現行 HEAD で Medium 1 件、Info 1 件。未検証候補 1 件）
  - `openai-codex-gpt-6.1-sol.md`（現行 HEAD で指摘 0 件。前回の M-1 は解消済み）
- 第1回の Spec: `docs/superpowers/specs/2026-10-03-devcontainer-tests-ci-review-fixes-design.md`（以下「第1回 Spec」）
- 経路（brainstorming の判定）: bounded。既存のテストスクリプト 2 本の中で、第1回と同じ here-string への置き換えをするだけで、CLI やほかのテストとのインターフェースは変わらない
- 承認: 2026-10-03 にユーザが推奨案（R2-1〜R2-3 を実装して既存 PR #15 に push）を承認した

## 背景

第1回では `.devcontainer/test-herdr-agent-task.bash` の `printf '%s\n' "$out" | rg -q` / `rg -m1` をすべて here-string に置き換えた。`rg -q` / `-m1` と `grep -q` は一致した時点で終了し、bash の `printf` ビルトインはパイプへ 1 行ずつ書き込むため、一致行より後ろの行を書く時点で読み手がいなければ SIGPIPE（終了コード 141）で落ちる。テストは `set -euo pipefail` で動くので、検査が失敗する。

第2回のレビューは、同じ形が同じ CI ジョブ（`devcontainer-tests` は `.devcontainer/run-tests.bash` で `.devcontainer/test-*.bash` をすべて実行する）のほかのテストに残っていること、そして第1回 Spec の「範囲外」がそれを確認済みの対象外と誤って記録していることを指摘した。

## 現行 HEAD での再現

レビュー対象 HEAD の隔離 worktree で実行した（8 コア、bash 5.3.9、ripgrep 15.1.0）。

| 対象 | 方法 | 結果 |
| --- | --- | --- |
| `test-herdr-status.bash`（現行） | テストスクリプト全体を 16 並列 × 40 回 | 640 回中 15 回失敗。失敗時の `$out` には探している行が含まれていた（例: `FAIL: nongit dry-run missing clock` の出力の 1 行目が `w2<TAB>clock<TAB>…`） |
| `test-herdr-status.bash`（here-string に置き換えた版） | 同上 | 640 回中 0 回 |
| `test-pi-openai-codex.bash`（現行） | テストスクリプト全体を 16 並列で約 80 回（1 回が重いため途中で止めた） | 1 回失敗（`FAIL: pigs must use its own tier config`。直前の引数の検査は同じ `$output` で成功している） |
| 71 行目の形 | `pigs` の実際の dry-run 出力（17 行中 7 行目が一致行）で `printf \| grep -Fxq` を 16 並列 × 500 回 | 8000 回中 3 回失敗。`PIPESTATUS` はすべて `141 0` |
| 71 行目の here-string 版 | `grep -Fxq … <<<"$output"` を同条件で | 8000 回中 0 回 |

## 指摘の一覧と振り分け

分類: 解消済み 3 / 対応する 3 / 判断保留 0 / 対応しない 2

| ID | 出典 | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- | --- |
| R2-1 | Claude L-2（コード）、DeepSeek M-1（コード） | `test-herdr-status.bash` の `printf '%s\n' "$out" \| rg -q` / `rg -m1` が 31 か所残り、SIGPIPE で flaky に失敗する | 対応する (a) | 現行 HEAD で 640 回中 15 回失敗を再現。失敗時の出力に一致行が含まれる |
| R2-2 | Claude L-2（Spec）、DeepSeek M-1（Spec） | 第1回 Spec の「範囲外」が、ほかのテストのパイプを「Claude のレビューが確認し、対象外と判断した」と書いている | 対応する (b) | 第1回の Claude レビューが確認したのは `test-readme.bash:21`、`test-resonite-feature.bash:7`、`test-check-layout.bash` の `PASS: check-layout` 検査だけで、`test-herdr-status.bash` は含まれない。R2-1 の再現と矛盾する |
| R2-3 | Claude・DeepSeek の未検証候補 | `test-pi-openai-codex.bash:71` の `printf '%s\n' "$output" \| grep -Fxq` も一致行の後ろに行が続き、同じ競合を持つ | 対応する (a) | 一致行は 17 行中 7 行目。最小の再現で 8000 回中 3 回（`PIPESTATUS 141 0`）、スクリプト全体でも 1 回失敗を再現 |
| R2-4 | DeepSeek I-1 | PR 本文の「変更内容」「検証」が `e2a5995` 時点のまま | 解消済み | 選別時点の PR 本文は `eac81fe`・`53f9bfc` の行と here-string の再検証結果を含む |
| R2-5 | Claude L-1（`e2a5995`） | `test-herdr-agent-task.bash` の `printf \| rg -m1` に SIGPIPE が残る | 解消済み | `53f9bfc` の同ファイルに `rg` / `grep` へのパイプは無く、here-string が 19 か所 |
| R2-6 | Codex M-1（`e2a5995`） | 出力を変数に受けても後段のパイプで SIGPIPE が残る | 解消済み | R2-5 と同じ |
| R2-7 | Claude テスト提案 2、DeepSeek テスト提案 1 | `printf '%s\n' "$var" \| rg -q` などの形が無いことを確かめる静的な検査を追加する | 対応しない | テストの追加で (a)〜(d) を満たさない。再発防止の保険にあたる |
| R2-8 | DeepSeek テスト提案 2 | 一致行が先頭で後続行がある出力に対し、書き手の EPIPE で落ちないことを固定する回帰テスト | 対応しない | 確率的な現象で CI の必須検査にできず、(a)〜(d) を満たさない |

ほかのテスト提案（Claude の提案 1、Codex の提案 1）は検証方法か既存テストの維持であり、修正の対象ではない。Claude の提案 1 は下記の検証方法に取り込んだ。

## 修正方針

CLI 本体（`.devcontainer/herdr-status-updater.bash`、`.devcontainer/pi-superagents-exec.zsh` など）は変更しない。

1. **R2-1**: `.devcontainer/test-herdr-status.bash` の `printf '%s\n' "$x" | rg …` を、第1回と同じく `rg … <<<"$x"` に置き換える（31 か所）。
   - 204 行目の `name_line="$(printf '%s\n' "$out" | rg $'w6\tgit_name\t' | head -1)"` は `name_line="$(rg -m1 $'w6\tgit_name\t' <<<"$out")"` にする。一致が無いときにスクリプトが止まる挙動は変わらない（どちらも代入の終了コードが 1 になる）。
   - 204 行目と 208 行目（入力が 1 行）は単独では競合しない。第1回 Spec と同じく、ファイル内に `printf | rg` の形を残すと今後の追加で写されるため、両レビューの推奨どおりそろえて置き換える。
   - 第1回と同じく、`run_updater_dry` の直後に here-string を使う理由を 1 か所だけコメントで書く。
2. **R2-3**: `.devcontainer/test-pi-openai-codex.bash` の 71 行目を `grep -Fxq "…" <<<"$output"` に置き換える。115 行目（一致行が出力の最終行なので単独では競合しない）も、両レビューが 71 行目と同じ扱いにするとしているため、同じファイル内の形をそろえて置き換える。68・97・150 行目の `| awk` は入力を最後まで読むので変更しない。理由のコメントは 71 行目の直前に 1 行だけ書く。
3. **R2-2**: 第1回 Spec の「範囲外」を、事実に合わせて書き直す。Claude のレビューが確認したのは上記 3 ファイルだけであること、`test-herdr-status.bash` と `test-pi-openai-codex.bash` は確認しておらず第2回で競合が再現したこと、対応は本 Spec にあることを書く。
4. **PR 本文**: push 後、「変更内容」の表に今回のコミットを足し、「検証」の表に今回の再現と修正後の結果を足す（R2-4 を再発させないため）。

## 検証方法

| 対象 | 方法 | 期待結果 |
| --- | --- | --- |
| R2-1 | `bash .devcontainer/test-herdr-status.bash` を単発で実行する | `OK test-herdr-status (…)` |
| R2-3 | `bash .devcontainer/test-pi-openai-codex.bash` を単発で実行する | `OK test-pi-openai-codex` |
| R2-1・R2-3 | `rg -n "printf '%s\\\\n' \"\\$\\w+\" \\| (rg\|grep)" .devcontainer/test-herdr-status.bash .devcontainer/test-pi-openai-codex.bash` | 0 件 |
| R2-1 | 修正後の `test-herdr-status.bash` 全体を 16 並列 × 40 回実行する（手元のみ。確率的な検査なので CI には入れない） | 失敗 0 件（修正前は 640 回中 15 回） |
| R2-3 | 71 行目の here-string 版の最小の再現（上記の表） | 8000 回中 0 回（実施済み） |
| R2-2 | 第1回 Spec の「範囲外」を読み、`test-herdr-status.bash` を確認済みとする記述が無いこと | 記述が無い |
| 環境の変更 | `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`（ResoLoop を PATH から外した、CI と同じ条件） | PASS |

## 範囲外

- `.devcontainer/test-*.bash` と `tests/scripts/*.bash` にある、早期に終了する読み手（`rg -q` / `-m1`、`grep -q`、`head`）へのパイプを現行 HEAD のコミット済みの内容で列挙した。本 Spec が直す 2 ファイル以外は `test-readme.bash:21`、`test-resonite-feature.bash:7`、`test-check-layout.bash` の `PASS: check-layout` 検査だけだった。これらは第1回の Claude レビューが「書き込みが 1 回で終わるか一致行が最終出力である」として対象外とした箇所で、本 Spec では安全性を独自に再検証していない。
- 静的な検査や回帰テストの追加（R2-7・R2-8）。
