# PR #118: pi-lens の撤去（Issue #117）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/118（`feat/issue-117-retire-pi-lens` → `main`）
- 関連 Issue: #117（本文の `Refs #117`。`closingIssuesReferences` は空）
- 関連文書: `docs/superpowers/specs/2026-10-17-create-reso-world-issue117-retire-pi-lens-design.md`、`docs/superpowers/plans/2026-10-17-create-reso-world-issue117-retire-pi-lens.md`（どちらも draft のまま。この文書では変えない）
- 検証したコード HEAD: `cd81cdefac5548895076d5d9a9136a6995e3bd2e`。base `main` は `eee9434` で、PR の分岐点と同じ（base は進んでいない）
- 状態: completed
- 実行許可: 利用者が 2026-10-17（JST）に `/review-fix-planning #118` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要でマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-117-retire-pi-lens`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#118-feat-issue-117-retire-pi-lens/` の 4 ファイル。対象 HEAD はすべて `cd81cdefac55` で、取得した `pull/118/head` と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | Approve | なし（注記 1。R1） |
| `deepseek-deepseek-v4.1-flash.md` | Approve | なし |
| `gpt-6.1-sol.md` | Approve | なし（注記 1。R2） |
| `grok-4.7.md` | Approve | なし（注記 1。R2） |

## 分類

Severity 付きの指摘は 4 ファイルとも 0 件。判断に関わる注記を次のとおり分けた。

| ID | 出どころ | 内容 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | Opus の Review coverage | `.pi-lens.json` の削除後、rebuild までの間（共有 `~/.pi` に pi-lens が残る期間）は、pi-lens の診断が Markdown などにも出る | 対応しない。`.pi-lens.json` は `ignore` だけを持ち、pi-lens の `ignore` は診断の走査にだけ効き、自動整形には効かない（Opus が導入済み 4.4.3 の文書で確認）。増えるのは診断の表示だけで、ファイルの内容・設定は変わらない。rebuild の cleanup で pi-lens 自体が外れるまでの一時的な状態である |
| R2 | GPT・Grok の Merge recommendation | 作り直した Dev Container での `pi list` の確認（#117 の受け入れ基準）は未実施で、マージの後に利用者が行う | 対応しない。PR 本文と PR の Spec D-7 が定めたマージの後の手順で、`Refs #117` により #117 は open のまま残る。確認の前にマージしても、#117 の完了の証拠がまだ無いだけで、誤った結果は残らない。下の「自己確認」のとおり、実機の共有 `~/.pi` の今の状態は cleanup の安全検査に止められない |

分類: **解消済み 0 / 対応する 0 / 対応しない 2**。DeepSeek のレビューは注記も無い。

仕様の論点として残すもの: なし。

同じ条件の再発と設計の見直し: 当たらない（「対応する」が 0 件。この PR に以前のレビュー修正は無い）。

## 確認の範囲

- PR の変更 8 ファイルの全文または該当の節: `.devcontainer/cleanup_pi_mcp.py`（278 行の全文）、`.devcontainer/install_beforehand.bash`（pi の導入から拡張の導入まで、235〜335 行）、`.devcontainer/tests/fake_pi_packages.py`（全文）、`.devcontainer/tests/test_pi_mcp_cleanup.py`（共通部と、`REMOVED` を回す撤去・プロビジョニング・再実行のテスト）、`.devcontainer/README.md`（「pi の旧拡張・MCP 設定の移行」の節）、削除した `.pi-lens.json`、PR の Spec・Plan
- 関連: `git grep` で、`docs/` 以外の追跡ファイルの `pi-lens` 参照は撤去の一覧・テスト・README だけ。`docs/` に残るのは過去の Spec・Plan・移植の記録（PR の Spec D-6 のとおり変えない）。Issue #117 の本文、usaturn/agent-workspace#684（2026-10-16 18:55Z に close、PR #688 マージ済み）、usaturn/xrift-poc#16（open、PR #17 が open）
- 自己確認（実機の共有 `~/.pi/agent` を読み取りだけで照合。cleanup は実行していない）:
  - `settings.json` の `packages` に `npm:pi-lens` が文字列で登録され、`extensions` は空、`skills` に pi-lens のパスは無い
  - `npm/package.json`・`npm/package-lock.json`・`npm/node_modules/.package-lock.json` のうち、`manifest_contains` が一致とみなすキー（`pi-lens`・`node_modules/pi-lens`・`…/node_modules/pi-lens`）は、root の `dependencies` と `node_modules/pi-lens` の項目（その中の `bin`）だけ。pi-lens を `dependencies`・`peerDependencies`・`optionalDependencies`・`devDependencies` に持つほかのパッケージは無い。`npm uninstall` の後に一致が残って cleanup が「remains after removal」で止まる経路は無い
  - `npm/node_modules/pi-lens` は symlink ではないディレクトリ。`npm/npm-shrinkwrap.json` は無いので `require_consistent_root_locks` に止められない
  - 残す `npm:` の登録 7 件（`@jc4649/notify`・`pi-safe-search`・`pi-diet-ripgrep`・`pi-simplify`・`@howaboua/pi-skill-skill-creator`・`@teelicht/pi-superagents`・`@plannotator/pi-extension`）はすべて `npm/package.json` に宣言されており、`require_retained_npm_declarations` に止められない。登録済みの `npm:@upstash/context7-pi` は既存の撤去の対象で、同じ cleanup で外れる
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった
- PR と関係しない既存の問題で致命的なものは無い
- usaturn/xrift-poc#17 が open のままなので、xrift-poc のコンテナを作り直すと共有の `~/.pi` に pi-lens が再登録され得る。PR 本文の「マージ後にお願いしたいこと」に書かれた運用の論点で、この PR のマージで誤った結果にはならない（次の reso-world の rebuild の cleanup で再び外れる）

## 検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| PR head `cd81cde` | `bash .devcontainer/run-tests.bash` | 30/30 PASS（約 152 秒） |
| PR head `cd81cde` | `bash scripts/check-layout.sh` | PASS |
| PR head `cd81cde` | `uv run pytest tests/skills .agents/skills`（#117 の確認の項目） | 1 回目は 473 passed・1 failed、2 回目は 474 passed（121 秒）。1 回目の失敗は下の注を参照 |

1 回目に落ちた `.agents/skills/pr-review/tests/test_pr_review_workspace.py::test_killed_create_reports_its_last_phase_and_leftovers` は、プロセスグループを kill した直後に、別の session で動く `git worktree add` がまだ生きているかを見るテストで、`running` のはずが `vanished` になった。PR は `.agents/` と `tests/skills/` を変えていない（`git diff --name-only` で 0 件）。同じ PR head で単体を 3 回実行して 3/3 PASS、全体の再実行でも PASS したので、一括実行の負荷でタイミングがずれる不安定なテストと判断し、この PR の欠陥としては扱わない。

base は PR の分岐点から進んでいないので、merge した一時的なツリーでの検証は不要。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）ので、check の確認は対象外。検証は clean な専用の worktree で行い、この文書の下書きは worktree の外に置いた。

## 自己レビュー

修正が無いので行わない（結論 2）。

## 所要時間

着手（2026-10-16 19:12Z ごろ）から Spec の記録まで約 13 分。レビューと PR・Issue の読み込み 約 2 分、変更ファイルと関連の読み込み・実機の `~/.pi` の照合 約 4 分（`run-tests.bash` の待ち時間と重ねた）、一括検証（`run-tests.bash`・`check-layout.sh`）約 3 分、skills の pytest 2 回と不安定なテストの単体の再実行 約 5 分。
