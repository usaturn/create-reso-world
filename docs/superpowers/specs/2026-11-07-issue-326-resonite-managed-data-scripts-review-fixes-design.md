# PR #327 レビュー修正 設計（Issue #326 managed data スクリプト）

## 管理

- 状態: completed（結論 1: 修正して push）
- PR: https://github.com/usaturn/create-reso-world/pull/327（head `feat/issue-326-resonite-managed-data-scripts`、base `main`）
- 元の Spec: `docs/superpowers/specs/2026-11-07-issue-326-resonite-managed-data-scripts-design.md`、Plan: `docs/superpowers/plans/2026-11-07-issue-326-resonite-managed-data-scripts.md`
- 実行許可: 利用者の指示 `/issue-to-pr #326 --merge`。issue-to-pr が PR の作成後に pr-review-fix-loop を回し、その中で review-fix-planning を完遂で行う（その PR の承認済み実装修正と、修正不要のときのマージ・Issue の更新）
- サイクル: 1（前の判断の記録なし）、レビュー対象の HEAD `5e5b6eeab5f62603aa404929a30fbb235911adb2`、base `4aa1ca04e51ec4bfe75873455e5465248edf2b81`
- planner: claude-opus-5-5（claude-code）
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#327-feat-issue-326-resonite-managed-data-scripts/verified/5e5b6eeab5f6.json`

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| gpt-6.1-sol.md | gpt-6.1-sol | pi | 5e5b6eeab5f6 | true | 下の採否で判断（票数は根拠にしない） |
| SWE-2-Max.md | SWE-2 Max | devin | 5e5b6eeab5f6 | true | 同上 |
| （なし） | pi_commandcode_deepseek4-flash_max | pi | ― | runner の timed_out（終了コード -15）で結果なし。入力にしていない | ― |

## 全指摘と分類

| 判断 ID | 出典 | 区分 | 理由 |
| --- | --- | --- | --- |
| gpt-6.1-sol#M-2@5e5b6eeab5f6 | gpt-6.1-sol#M-2、SWE-2-Max#L-1（V-1） | 対応する | (a) 再現。コピー中（Resonite の更新中）にコピー元へ DLL が増えると、一部だけの写しを終了コード 0 と `copied and verified` で報告する。README と Spec が「コピー中のコピー元の変化を見つける」と約束しているので、利用者はその写しを正しい版として使う（誤った結果） |
| gpt-6.1-sol#M-1@5e5b6eeab5f6 | gpt-6.1-sol#M-1（V-2） | 対応する | (a) 再現。Path を読めない Resonite のプロセス（権限の違う別のインストールなど）が混在すると、読めた別のインストール先を黙って採用し、別の版の DLL フォルダを WSL へ渡す（誤った対象）。Issue の「特定できない場合は勝手に選ばず明示指定を求める」に反する |
| SWE-2-Max#L-2@5e5b6eeab5f6 | SWE-2-Max#L-2（V-3） | 対応しない | 例のフォルダの直下に FrooxEngine.dll が無くても、スクリプトは終了コード 1 と理由を表示して止まり、誤った結果にならない。実際の配置はこの環境で確かめられない |
| SWE-2-Max#L-3@5e5b6eeab5f6 | SWE-2-Max#L-3（V-4） | 対応しない | 終了コード 1 で止まり、何も選ばない。表示の改善だけで致命的でない |
| SWE-2-Max#L-4@5e5b6eeab5f6 | SWE-2-Max#L-4（V-5） | 対応しない | テストの追加だけ。拒否の実装は SWE-2-Max が実行で確かめている。致命的な指摘の修正に必要なテストではない |

解消済み: 0 件。

## 要件対応

| 条件（元の Spec・Issue） | 今回の修正方針 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| D3「コピー後にコピー元の一覧を作り直して最初と一致することを確かめる（コピー中のコピー元の変化）」、Issue「コピーと照合の両方が成功した場合だけ成功を報告する」 | コピー後に直下の `*.dll` の名前の集合も作り直して比べる | 追加・削除・内容の変更のどれでも、成功を表示せず SHA256SUMS を置かない | テストの (6) に「追加」のケースを足す。既存の正常例 (1) が通る |
| D2「候補が 1 つに決まらなければ選ばない」、Issue「候補が複数ある場合や特定できない場合は、勝手に選ばず明示指定を求める」 | Path を読めない Resonite のプロセスが 1 つでもあれば、終了コード 1 で `-InstallPath` を求める。D2 の「Path が読めるもの」を改める | 混在で終了コード 1、全部読めて同じフォルダなら 0 | 一時的に導入した pwsh で Get-Process を差し替えて確かめる（コミットしない。元の Spec D4 の理由） |

共有条件: 2 つは別のスクリプトで、入力・状態を共有しない。統合担当は planner で、README の該当箇所と元の Spec の記述が修正後の挙動と一致することを確かめる。

## 守る条件と影響経路

### V-1（gpt-6.1-sol#M-2）

破れている条件: コピー元の直下の DLL の集合と内容が、コピーの前後で同じときだけ成功と報告する。前提「コピー前に集めた名前の一覧はコピー後も同じ」が、コピー中の追加という操作順で破れた。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 前後で同じときだけ成功 | 名前の列挙（names）→ コピー後の再列挙 | 修正する | 追加で終了コード ≠ 0、成功の文なし、SHA256SUMS なし、版のフォルダは残る | テスト (6) added | 3f7d4f2 で PASS。names の比較を外した対照で `FAIL: added copy: exited 0`。fix-check でフォルダの追加・名前の入れ替えも終了コード 1 |
| 同上 | 内容の変更（list_hashes の前後比較） | 既に満たす | 終了コード ≠ 0 | テスト (6) changed | 3f7d4f2 で PASS |
| 同上 | 削除（sha256sum が読めない） | 既に満たす | 終了コード 1 | 確認済みの一覧 V-1 の variants（削除で止まる） | 5e5b6ee で終了コード 1 |
| 同上 | コピー先の一覧の照合（expected と actual） | 既に満たす | 余分・欠落で止まる | 欠落はテスト (6) missing | 3f7d4f2 で PASS |
| 正常なコピーは成功する | 正常例 | 既に満たす | 終了コード 0、DLL と SHA256SUMS | テスト (1) | 3f7d4f2 で PASS。DLL 以外・サブフォルダの DLL の追加では止まらない（fix-check） |

### V-2（gpt-6.1-sol#M-1）

破れている条件: 実行中の Resonite のインストール先を 1 つに特定できないときは選ばない。前提「Path を読めたプロセスだけで全候補が分かる」が、Path が null・取得例外のプロセスの混在で破れた。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 特定できなければ選ばない | プロセスの Path の収集（null・例外） | 修正する | 混在で終了コード 1、`-InstallPath` を求める | pwsh で Get-Process を差し替え（partial-null・partial-error） | 3f7d4f2、pwsh 7.6.9: null・例外・空文字・プロパティ無し・全部読めないで終了コード 1 |
| 同上 | 読める別フォルダが 2 つ以上 | 既に満たす | 終了コード 1 | pwsh（both-readable） | 3f7d4f2 で終了コード 1 |
| 同上 | FrooxEngine.dll のフォルダが複数・読めないフォルダ | 既に満たす | 終了コード 1 | 確認済みの一覧（SWE-2-Max の再現） | 5e5b6ee で終了コード 1 |
| 正しく特定できれば選ぶ | 全プロセスが同じ読めるフォルダ | 既に満たす | 終了コード 0 | pwsh（same-folder） | 3f7d4f2 で終了コード 0。Resonite 以外の名前の読めないプロセスは対象外 |
| 明示指定は探索しない | `-InstallPath`・`-ManagedPath` | 対象外 | ― | 利用者が指定したフォルダで、プロセスを見ない | ― |

設計の見直しのきっかけ: 当たらない（サイクル 1、以前のレビュー修正なし）。

## 結論と結果

- 結論: 1（修正して push）
- 修正: commit `3f7d4f2`（実装担当 `claude-code_opus_default`、観測したモデル claude-opus-5-5、171 秒。runner の worktree で作った `244ae42` を停止の確認と差分の確認の後に cherry-pick）
  - V-1: コピー後に直下の `*.dll` の名前の集合を作り直して比べる。テスト (6) に added を足した（S。対照で検出力を確認）
  - V-2: Path を読めない Resonite のプロセスが 1 つでもあれば終了コード 1 で止まり `-InstallPath` を求める。PowerShell のテストはコミットしない（元の Spec D4）
  - README の手順 1・2 と元の Spec の D2・D3 を挙動に合わせた
- 検証（3f7d4f2）: `bash .devcontainer/test-copy-resonite-managed-data.bash` 0、対照（名前の比較を外す）で FAIL、shellcheck 0、`bash .devcontainer/run-tests.bash` 0（27 PASS）、`bash scripts/check-layout.sh` 0、pwsh 7.6.9 で Get-Process の差し替え 5 通りが期待どおり、ParseFile エラーなし、ASCII のみ、push 前の秘密情報の検査で検出なし
- 失敗時の検証: 拒否のテストは成功の文・SHA256SUMS・版のフォルダの残存・残したパスの表示を比べる。負例は追加の 1 つの異常だけ。ガードを外した対照で added が FAIL（1 件）
- 自己レビュー: `run_roles.py --phase self-review` の 1 回（self-review・fix-check とも `self`。2 つのサブエージェントで同時に実行）
  - self-review（観点 2）: `claude-opus-5-5-commit-3f7d4f253b482406be8128c4b9ab88dd9dc13091.md`、指摘 0 件
  - fix-check（観点 1・3）: `verified/3f7d4f253b48.fix-check.json`。主張 7 件のうち 6 件 holds。1 件 violates は下の fix-check#V-1
  - 自己レビューの後に修正はしていない（再レビューもしていない）
- 自己レビューで出た指摘

| 判断 ID | 区分 | 理由 |
| --- | --- | --- |
| fix-check#V-1@3f7d4f253b48 | 対応しない | README.md:391 は、Path を読めないプロセスがあるときも「候補を表示して」止まると読めるが、実際は候補を出さずに `-InstallPath` を求めて止まる。止まること・終了コード 1・明示指定を求めることは一致し、誤った結果にならない |

- 未確認: Windows PowerShell 5.1・Windows 11 の実機・実際の Resonite のプロセス（元の PR と同じく、マージの後に利用者が確かめる）
- 工程の記録: `reviews/usaturn/create-reso-world/#327-feat-issue-326-resonite-managed-data-scripts/verified/5e5b6eeab5f6.planning.json`
