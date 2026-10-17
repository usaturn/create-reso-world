# Issue #117: pi-lens を Pi の拡張の導入対象から外す

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/117
- 検証した基準 HEAD: `eee9434adf017909770d61e9393129d802a332db`（`origin/main`）
- 状態: completed（2026-10-17 JST、利用者の指示（Spec・Plan を completed にする文書 PR の作成とマージ）による。文書の内容に対する利用者の明示承認は記録していない。完了の根拠は Plan の「完了」）
- 関連 Plan: `docs/superpowers/plans/2026-10-17-create-reso-world-issue117-retire-pi-lens.md`
- 実行許可: 2026-10-17（JST）、利用者が「#117 に対応してください。途中で止めずに推奨案で PR まで実行してください」と指示した。推奨案での実装、隔離 worktree、commit、push、create-reso-world への PR の作成まで許可されている。マージと rebuild は利用者が行う。下の判断は確認を取らずに決めたエージェントの判断である

## 意図

pi-lens を共有の `~/.pi` から外す決定（usaturn/agent-workspace#684、2026-10-17）に合わせ、reso-world の Dev Container が `npm:pi-lens` を再登録しないようにする。既に登録済みの `~/.pi` からは、既存の廃止拡張（`pi-distill` など）と同じ仕組みで、バックアップを取ってから撤去する。

## 確認した事実（2026-10-17）

- `npm:pi-lens` を入れているのは `.devcontainer/install_beforehand.bash` の拡張の一覧（327 行）だけ。`docs/` 以外で `pi-lens` を参照する追跡ファイルは、ほかに `.pi-lens.json` だけ
- `.devcontainer/cleanup_pi_mcp.py` は、postCreate で拡張の導入より前に実行される（`install_beforehand.bash` 247 行）。`PACKAGES` の各パッケージについて、`settings.json` の登録、pi が管理する npm マニフェスト、`npm/node_modules/<name>` の実体を調べ、残りがあればバックアップを取ってから `pi remove` で撤去し、撤去後の実体で成否を判定する。2 回目の実行では何もしない
- `.devcontainer/tests/test_pi_mcp_cleanup.py` のテストの多くは、`REMOVED`（`PACKAGES` と同じ一覧）を回して、宣言の形（文字列・版の固定・オブジェクト）、マニフェストだけの残り、バックアップ、再実行、プロビジョニング後の再登録の無さを確かめる。偽の pi（`.devcontainer/tests/fake_pi_packages.py`）は、`FAKE_PI_REQUIRE_CLEAN=1` のとき、廃止した拡張が登録されたまま `pi install` が呼ばれると失敗する
- 今の共有 `~/.pi`（Pi 1.3.0）には `npm:pi-lens`（4.4.3）が登録され、`npm/package.json` の `dependencies` と `npm/package-lock.json` の `node_modules/pi-lens` にもある。pi-lens は unscoped の名前で、ほかの pi パッケージを別に登録しない

## 判断

- **D-1 撤去の方法**: `cleanup_pi_mcp.py` の `PACKAGES` に `pi-lens` を足す（Issue の「着手するときに決めること」1 の推奨）。導入をやめるだけの代案は、登録済みの `~/.pi` に pi-lens が残り続け、agent-workspace#684 の撤去と扱いがそろわないので採らない
- **D-2 導入の停止**: `install_beforehand.bash` の拡張の一覧から `npm:pi-lens \` を外す
- **D-3 テスト**: 新しいテスト関数は作らず、既存のテストの一覧に pi-lens を足す。`test_pi_mcp_cleanup.py` の `REMOVED` と `seed_packages` の `npm/package.json`、`fake_pi_packages.py` の `retired` に `pi-lens` を足す。既存の一覧を回すテストが、登録済み・マニフェストにだけ残った・未登録の 3 つの状態、バックアップ、2 回目の実行、プロビジョニングが pi-lens を入れないことを、cleanup とインストーラの該当部分を実行して確かめる。一覧は撤去の対象（削除してよい範囲）を決める固定値なので、`AGENTS.md` の「テストの採用基準」で使ってよい固定値にあたる
- **D-4 README**: `.devcontainer/README.md` の「pi の旧拡張・MCP 設定の移行」の、導入しない拡張の一覧に `pi-lens` を足す。撤去は同じ `~/.pi` を使うほかのコンテナの拡張の実体も消すので、rebuild や手動の cleanup の前に、ほかのコンテナ・ホストで動いている pi を終了する旨を同じ節に足す
- **D-5 `.pi-lens.json`**: 削除する。pi-lens が読む設定で、ほかに参照するファイルは無い
- **D-6 過去の記録**: `docs/` の過去の Spec・Plan・移植の記録は、当時の記録なので変えない
- **D-7 PR と Issue**: PR の本文は `Refs #117` にし、マージで #117 を自動で close しない。受け入れ基準の「作り直した Dev Container で `pi list` に `npm:pi-lens` が無い」は、利用者の rebuild の後にしか確かめられないため

## 範囲外

- 既存の worktree に残った `.pi-lens-probe-home/` の片付け、pi-lens の代わりの lint の導入（Issue の「対象にしない」）
- コンテナ内の `~/.pi-lens`（bind mount の対象外で、rebuild で消える）
- ローカルのワールドのプロジェクト（git の追跡対象外）に残る `.pi-lens.json`
- 共有の `~/.pi` に残る他の廃止拡張（今の `npm:@upstash/context7-pi` など）。既存の cleanup の対象であり、この変更で挙動は変わらない
- usaturn/agent-workspace#684・usaturn/xrift-poc#16 の実装
- この作業の中で実機の共有 `~/.pi` に cleanup を実行すること。ほかのコンテナの Pi の実体を消すため、利用者が Pi を止めてから rebuild で行う
