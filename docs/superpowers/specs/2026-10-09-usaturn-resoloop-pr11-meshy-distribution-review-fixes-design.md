# usaturn/resoloop PR #11: Meshy 実行基盤の同梱のレビュー修正要否

- 文書管理リポジトリ: `usaturn/create-reso-world`（文書用ブランチ `docs/issue-56-meshy-distribution`、文書 PR #61）
- 対象リポジトリ・PR: https://github.com/usaturn/resoloop/pull/11（`feat/meshy-distribution` → `main`）
- 関連 Issue: usaturn/create-reso-world#56（PR 本文で Refs。自動 close なし）。本文で言及: create-reso-world#50（実機受入は対象外）
- 関連文書: `docs/superpowers/specs/2026-10-08-create-reso-world-issue-56-meshy-distribution-design.md`、`docs/superpowers/plans/2026-10-08-create-reso-world-issue-56-meshy-distribution.md`
- 検証したコード HEAD: `29ab002a4e9a671448e661b66831f91934bd6a56`（base `main` = `8bcef8a14e4b36167058df3f5c4af95ee895f9cf` は head の祖先）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning https://github.com/usaturn/resoloop/pull/11` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-56-meshy-docs`（既存の文書用 worktree を clean・origin 一致の条件で再利用）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-56-meshy`（PR head を checkout 済みの既存 worktree を clean・HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`external/resoloop/reviews/#11-feat-meshy-distribution/` の 4 ファイル。対象 HEAD はすべて `29ab002a4e9a` で、`pull/11/head` の取得結果と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `SWE-2-High.md` | Approve | Low 2・Info 2 |
| `claude-opus-5-5.md` | Approve | Low 1（未検証候補 2） |
| `deepseek-deepseek-v4.1-flash.md` | Approve | Low 1・Info 1 |
| `grok-4.7.md` | Approve | Low 1 |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | SWE L-1、DeepSeek L-1、Grok L-1 | CI の `linux-offline-python` が `tests/meshy/test_meshy_process_output.py` を実行しない | 対応しない。CI の網羅の不足で、現行 HEAD の挙動は誤っていない（同ファイルの 12 件は下の検証で成功）。`docs/MESHY-VALIDATION.md` は Linux CI の範囲を workflow/doctor と書いており、CI が実行すると説明していない。将来の回帰に備える保険 |
| R2 | SWE L-2 | `safe_path` が project より上位の祖先の symlink まで拒否し、symlink を含む `--project` では全コマンドが `symlink_forbidden` になる | 対応しない。再現した（祖先に symlink がある `via/proj` は拒否、実パスの `base/proj` は成功）。拒否は何も書かずに止まる fail-closed で、誤った結果やデータの変更は無い。`SKILL.md` は `PROJECT` に対象プロジェクトの**実パス**を渡す手順で、実在するワールド（`MyResoniteProject`・`akichi`・`slum02`・`slum03`）のパスと `content/`・`.resoloop/` に symlink は無い。journal guard は `MESHY_CONFIG_DIR` と Node 側の書込先の文字列を比べるため、project のパスに symlink が無いこと（論理パスと実パスの一致）を前提にしており、範囲を狭めると guard の前提が崩れる。仕様の論点（祖先の symlink を許すか）は残す |
| R3 | Opus L-1 | meshy-cli の失敗 envelope（`ok: false`、`result: null`）を `_cli` が出力不正として扱い、CLI の `error.code` が `cli_output_or_spawn_failed` に置き換わる | 対応しない。再現した（fake の `meshy` で `_cli` は `cli_output_or_spawn_failed`、同じ envelope を `_error()` に渡すと `auth_invalid`）。影響は失敗時の診断だけ: `status`・`wait`・`attach`・`list`・`balance` は状態を変えずに失敗し、`submit` は `unknown` に倒れて再送しない、`download` は `succeeded` のまま同じ task で再取得できる。誤った成功・重複課金・データの消失は起きない |
| R4 | SWE I-1 | 破損した GLB（20 バイト未満、壊れた JSON chunk、範囲外の animation の node）が名前付きの拒否 report にならず、generic な `resoloop_conversion_failed` になる | 対応しない。コードで確認した（`meshy_blender.py` の `__main__` は `Rejected` だけを捕まえ、`convert_operation` は report が無いと元のエラーを返す）。変換は拒否され、出力は公開されない（fail-closed）。診断性だけの問題 |
| R5 | SWE I-2 | 存在しない operation への `status` などで、空の `content/generated/meshy/<name>/` と `.lock` が作られる | 対応しない。再現した。残るのは空のディレクトリとロックファイルだけで、その後の同名の `plan` は成功した（`operation.json` を `O_EXCL` で作るため妨げにならない） |
| R6 | DeepSeek I-1 | `pyproject.toml` の追加後に `uv run --group dev pytest` を実行すると、未追跡の `uv.lock` が残る | 対応しない。再現した（`?? uv.lock`）。テスト用の任意の依存の lock の方針の論点で、配布物・init/sync の挙動に影響しない |
| R7 | Opus 未検証候補 1 | `uv run --no-project` が 3.12 未満の Python を選ぶと、要件外の Python で wrapper が動く | 対応しない。隔離した managed Python 3.10 で確かめた: `--help`・offline `plan` は動作し、`doctor` は `python` check を失敗（`Use uv with Python >=3.12.`）として報告した。`submit` は `--confirm-paid` なしで送信前に止まった。runbook の手順 2 は `uv python install 3.12` を案内している |
| R8 | Opus 未検証候補 2 | 8k の MR texture の分離で大きなメモリを確保する | 対応しない。8k は利用者が明示した場合だけ（既定 2k）。変換は offline で、Blender の異常終了・時間切れは `resoloop_conversion_failed` になり出力を公開しない（`test_resoloop_timeout_stops_process_tree`・`test_failed_export_is_not_published` で固定）。データの消失は起きない |
| R9 | 自己確認（検証環境） | この Dev Container では、offline テストが 5 秒の subprocess 上限（`Harness.run`）で時々 `TimeoutExpired` になる | 対応しない。下の「検証」のとおり、同じプロセス内の `plan` でも最大 7.8 秒止まる一方、Python の起動だけなら常に 20 ms 以内で、停止はファイルシステム操作中に時間的にまとまって起きた（VM 全体の書き込みと I/O 待ちが多い状態）。失敗するテストは実行ごとに変わり、同じテストは再実行で成功した。公開 CI（ubuntu-latest）は成功している。テスト環境の制約で、wrapper の挙動の誤りではない |

分類: **解消済み 0 / 対応する 0 / 対応しない 9**。

仕様の論点として残すもの: R2（`--project` の祖先の symlink を許すか。許す場合は journal guard の書込先の比較も実パスに揃える必要がある）、R6（`uv.lock` をコミットするか ignore するか）。

## 確認の範囲

- 変更ファイル 29 件の全文: wrapper（`meshy.py`・`meshy_workflow.py`・`meshy_conversion.py`・`meshy_blender.py`・`meshy_doctor.py`・`meshy_cli_guard.mjs`）、`SKILL.md`・`references/runbook.md`・`references/licenses.md`、`BundledSkillManager.cs`・両 csproj の差分、`ProjectInitializerTests.cs` の追加分、`.github/workflows/ci.yml`、`pyproject.toml`、README 3 種・`docs/BLENDER.md`・`docs/MESHY-VALIDATION.md`、既存スキル 3 件と `build-handoff.md` の差分。Python テスト 4 ファイルはハーネスと各テストの意図・境界を読み、全件を実行した
- 関連処理: `ProjectInitializer` の配置（改行の正規化）、`BundledSkillManager.Sync` の競合判定（`missing`・`untracked-conflict`）と lock の移行
- 状態遷移の確認: `submit` の `planned`→`submitting`→`submitted`/`unknown`、`submitting` の再実行で `unknown` へ倒すこと、`query` の attach の識別ガードが保存前に働くこと、`download` の失敗が `succeeded` に戻ること、`convert` の公開とロールバック
- 既存ワールドへの影響: 4 つのワールドの `.agents/skills/` に `meshy-resoloop` は無く、`skills sync` では `missing` として追加される（競合で停止しない）。create-reso-world のルートの `.agents/skills/meshy-resoloop` はワールドの配置先と別で、この PR の範囲外
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった

## 検証

PR head と同じ SHA の隔離 worktree（`mktemp` の下、detached）で実行した。既存の専用 worktree を、`uv.lock`・ビルド出力で汚さないためである。

| コマンド | 結果 |
| --- | --- |
| `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj -c Release` | 453 passed、skip 0（exit 0） |
| `uv run --group dev pytest tests/meshy -q -rs`（1 回目、`dotnet test` と並行） | 235 passed・2 failed、skip 0。失敗 2 件はどちらも `Harness.run` の 5 秒の `TimeoutExpired`（`test_image_hash_and_explicit_texture_options`、`test_attach_rejection_preserves_entire_project[refine-...-wrong_resource]`）。実 Blender の変換テストを含め、残りはすべて成功 |
| 上の失敗 2 件の再実行 | 13 passed・1 failed（別のパラメータ `[text-...-missing_type]`。失敗の種類は未保存） |
| offline 3 ファイル（`test_meshy.py`・`test_meshy_doctor.py`・`test_meshy_process_output.py`）の再実行 ×4 | 180 passed・3 failed（失敗の種類は未保存）／183 passed（exit 0）／181 passed・2 failed（2 件とも `TimeoutExpired`）／183 passed（exit 0） |

記録した失敗はすべて `Harness.run` の 5 秒の `TimeoutExpired` で、失敗したテストは別の実行ではすべて成功した。offline 3 ファイルは 2 回、全件が成功している。実 Blender の変換テスト（`test_meshy_conversion.py`）は 1 回目の全体実行で全件が成功した。tmpfs（`/dev/shm`）に一時ディレクトリを移す方法は、`noexec` のため偽の `node`・`meshy` を実行できず、検証に使えなかった。

時間の切り分け（同じ環境）:

| 測定 | 中央値 | 最大 |
| --- | --- | --- |
| `python -c pass` の起動 ×30 | 0.017 秒 | 0.020 秒 |
| `import meshy_workflow` の起動 ×30 | 0.064 秒 | 0.082 秒 |
| wrapper の `plan` の起動 ×30（1 回目） | 0.156 秒 | 11.087 秒 |
| 同じプロセス内の `execute(plan)` ×60 | 0.017 秒 | 7.807 秒 |
| wrapper の `plan` の起動 ×30（直後） | 0.090 秒 | 0.145 秒 |

公開 CI: run 37801297304 がこの head で `linux-offline-python`（47 秒）・`windows`（3 分 44 秒）とも成功（`gh pr checks 11 --repo usaturn/resoloop`）。base `main` は head の祖先なので、base を merge した一時ツリーでの再検証は不要。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

無い。「対応しない」のうち実在する制約（R2・R3・R5・R9）は、PR 本文の保証（単一送信と復旧、パス・上書きの保護、doctor の読み取り専用など）と食い違わない。

## 作業時間

- 着手 2026-10-08T16:39Z、Spec のコミット 2026-10-08T16:59Z（約 20 分）。内訳: PR の状態・境界の確認と worktree の選定（約 3 分）、変更ファイルの精読（約 6 分）、指摘の再現（約 2 分）、テストの実行と時間の切り分け（約 7 分、一部は精読と並行）、Spec の作成（約 2 分）
