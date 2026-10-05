# PR #45 issue-41-resoloop-latest-without-lock のレビュー指摘の選別と修正

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/45
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `feat/resoloop-latest-without-lock`
- 指摘を検証した HEAD: `ee9b728a0d0947bf7c89545975d77df034c07750`
- 入力: `reviews/#45-feat-resoloop-latest-without-lock/` 配下の全ファイル（4 ファイル）
- 作成日: 2026-10-06
- 結論: **1（修正が必要）**。致命的な指摘 1 件（X-M1）を直し、既存 PR へ push する
- 状態: completed（選別・修正・検証・自己レビューまで完了。push・状況コメントの結果は PR のコメントに書く）
- 実行許可: 2026-10-06 の利用者の依頼（`/review-fix-planning #45`。計画で止める指定は無い）。スキル `review-fix-planning` の完遂として、PR とレビュー結果を確認して修正要否を三択で確定し、修正が必要なら推奨案で修正・検証・自己レビュー（1 回まで）を経て既存 PR へ push する。修正が不要なら確認・検証を完了し、最終の状況コメントを投稿してマージし、関連 Issue を更新する
- 作業場所: 既存の worktree `.worktrees/issue-41-resoloop-latest`（PR の head ブランチを checkout 済み、未コミットの変更なし、HEAD が PR の head と一致）を専用の worktree として使った
- 関連: 設計 `docs/superpowers/specs/2026-10-06-issue-41-resoloop-latest-without-lock-design.md`、計画 `docs/superpowers/plans/2026-10-06-issue-41-resoloop-latest-without-lock.md`

## 1. レビュー入力

| ファイル | 対象 HEAD | 指摘 | 判定 |
| --- | --- | --- | --- |
| `openai-codex-gpt-6.1-sol.md` | `ee9b728a0d09` | Medium 1 | Approve |
| `SWE-2-Max.md` | `ee9b728a0d09` | Low 1・Info 1 | Approve |
| `claude-opus-5-5.md` | `ee9b728a0d09` | Info 3・未検証候補 1 | Approve |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `ee9b728a0d09` | Low 1・Info 1 | Approve |

対象 HEAD はすべて、選別時点の PR の head（`gh pr view 45 --json headRefOid`）と同じである。base（`origin/main`）は選別の開始時点で `e6edcf8`（PR の分岐点）だった。commit 前の fetch では `4cea90a`（PR #40 のマージ。`pr-review` スキルとその文書だけの変更）に進んでいたが、この PR と同じファイルは変えておらず、`git merge-tree` で競合が無いことを確かめた。結論 1 なので base は取り込まない。

## 2. 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 1（X-M1） |
| 対応しない | 9（レビューの 8 件と、自己レビューの T-1。T-1 は 6 章） |

判定は、致命的かどうか（秘密情報の露出、データの消失、了承の無い操作・誤った対象への操作、手順どおりで誤った結果・主要な処理が止まる、セキュリティ）と、現行 HEAD での確認で行った。重大度ラベル・票数・Approve では決めていない。

### 2.1 全指摘一覧

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| X-M1（Codex Medium） | `resolve_ref` が `origin/HEAD` を origin のブランチとして先に解決し、`checkout HEAD`・`install HEAD` が今のコミットではなく origin の既定のブランチを取り出す | **対応する** | 手順・ツールのとおりに使うと誤った結果になる（(a) 再現した誤動作）。スクリプトの使い方の説明と Spec D-6 は「origin に同名のブランチが無い名前は git がそのまま解決する」と定めており、`HEAD` はその名前に当たる。`resoloop-fork.sh clone`（`git clone`）が作る checkout には必ず `refs/remotes/origin/HEAD` があり、push していないコミットを試す場面（`docs/resoloop-fork-workflow.md` の「上流へ PR を出すときの流れ」の 6）で到達する。一時リポジトリで再現した: ローカルのブランチ `local-fix` の `7533999` から `checkout HEAD` を実行すると、終了コード 0 で `4e53088 (origin/HEAD, detached)` に移った。`install HEAD` は同じ `do_checkout` を通るので、別のコミットから版を作ってビルド・導入し、成功と表示する |
| S-L1（SWE Low） | `report-resoloop-skills.bash` で `git ls-files` が失敗すると `no projects found.` と表示する | 対応しない | 発生条件は index の破損で、サポートしている構成ではない。表示だけのスクリプト（常に 0 で終わる仕様）で、git の `fatal:` は stderr にそのまま出る。誤った操作は起きない |
| S-I1（SWE Info） | 旧形式の fork 版（`.prN.`）を `status` が `NuGet release` と表示する | 対応しない | 移行期だけの表示のずれ。公開版への戻し（`--allow-downgrade`）は版の形式に依存せず動く |
| O-I1（Opus Info） | `docs/integration.md` の手順 7 が「すべて `ok`」を求めたまま | 対応しない | `warn:` が出ても `PASS: check-layout` は表示され、同じ文書の「Rebuild 後に確かめること」と PR の説明（範囲外）が `warn:` を説明している。誤った操作は起きない |
| O-I2（Opus Info） | `install_beforehand.bash` の cleanup のコメントが「唯一の意図的なベストエフォート」のまま | 対応しない | コメントの表記。動作に影響しない |
| O-I3（Opus Info） | Spec の D-9・D-10 の `install` の手順順序が実装と違う | 対応しない | 記録の書き方。実装（導入済みなら SDK を確かめずに照合だけ）の方が緩く、運用文書とテストは実装と一致している |
| O-U1（Opus 未検証候補） | NuGet の HTTP キャッシュで、リリース直後に最新が見えないかもしれない | 対応しない | 起きても `(unchanged)` と表示され、時間を置いて再実行すれば済む使い勝手の問題で、致命的でない |
| D-L1（DeepSeek Low） | Spec の F-5（上流の版の上げ方）が実際のタグ・main と一致しない | 対応しない | 事実誤りは確認した（タグ `v0.1.0-preview.17`＝`99c59be` の csproj は既に `0.1.0-preview.17` で、版の更新はリリースコミット自体に含まれる）。ただし D-5 の結論（`.fork.` の接尾辞と両方向の `--allow-downgrade`）は成り立ち、実装・運用は変わらない |
| D-I1（DeepSeek Info） | 旧 Spec（2026-09-26）に後継注記が無い | 対応しない | 記録の書き方。現行の手順は `docs/resoloop-fork-workflow.md` と新しい Spec にあり、旧 Spec を読んで操作する経路は無い |

## 3. 守る条件と影響経路

### 3.1 X-M1: `<ref>` は origin のブランチ名と完全に一致するときだけ origin のブランチとして解決する

守る条件: `checkout <ref>`・`install <ref>` は、`<ref>` が origin のブランチ名と完全に一致するとき（symbolic ref を除く）だけ origin のブランチを使い、それ以外（`HEAD`、`~`・`^` を付けた式、SHA、タグ、ローカルのブランチ、`upstream/main` など）は git に `<ref>` をそのまま解決させる。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
| --- | --- | --- | --- |
| 同上 | `scripts/resoloop-fork.sh` の `resolve_ref` | 修正する: `git show-ref --verify -q refs/remotes/origin/<ref>` が成功し、かつ `git symbolic-ref -q refs/remotes/origin/<ref>` が失敗するときだけ origin のブランチとして扱う | `tests/scripts/test-resoloop-fork.bash` の 8 番に追加したケース（origin/HEAD がある clone で、push していないコミットを持つローカルのブランチから `checkout HEAD` → 今のコミットのまま detached）。修正前のスクリプトでは FAIL することも確かめた |
| 同上 | `do_checkout`（`checkout <ref>`） | 修正する（`resolve_ref` の修正で直る） | 同上 |
| 同上 | `do_install`（`install <ref>`）→ `do_clone` → `do_checkout` → `fork_version`（checkout の HEAD から版を作る） | 既に満たす（`do_checkout` を通るので `resolve_ref` の修正で直る。版は checkout の HEAD から作る） | 既存の 17 番（`install fix/x` が checkout を `fix_commit` に置き、その版で導入する）と、上の 8 番。自己レビュー（反証）で、モックの dotnet を使った `install HEAD` の通しの実行が、今のコミットから版を作って導入することも確かめた |
| 同上 | `HEAD~N`・`HEAD^` などの式（`refs/remotes/origin/HEAD~1` が origin/HEAD を経由して解決されていた） | 修正する（`show-ref --verify` の完全一致の確認で、式は git の解決に回る） | 自己レビュー（反証・検証の検出力）の一時リポジトリで、`checkout HEAD~1`・`checkout 'HEAD^'` が今のコミットを基準に解決されることを確かめた。回帰テストには入れていない（6 章の T-1） |
| 同上 | origin のブランチを優先する既存の挙動（同名のローカルのブランチより origin のブランチ） | 既に満たす（完全一致のブランチ名は従来どおり origin を使う） | 既存の 7・8・27 番（`checkout fix/x` が `origin/fix/x` を取り出す、同名のローカルのブランチより優先する、後から push された先端を fetch して取り出す） |
| 同上 | `docs/resoloop-fork-workflow.md` の「fork のビルドを一時的に使う」の 2、`resoloop-fork.sh` の冒頭の使い方の説明、Spec D-6 | 既に満たす（「origin に同じ名前のブランチがあればそれを使い、無ければ git がそのまま解決できる名前」と書いてあり、修正後の挙動と一致する） | 文書を読んで確認した |
| 同上 | `do_status` | 対象外（ref を解決しない） | — |

旧版との挙動の差: `fix/x~1` のような「origin のブランチ名に `~`・`^` を付けた式」は、旧版は origin のブランチを基準に解決していた。修正後は git の解決に任せるので、同名のローカルのブランチがあればそれを基準にし、無ければ解決できずに 1 で止まる（`origin/fix/x~1` と書けば origin を基準にできる）。Spec D-6 と運用文書は origin を優先する対象を「同じ名前のブランチ」としており、修正後の挙動はこの記述どおりである。どちらの場合も、解決した名前（`origin/<ref>` か `<ref>`）とコミットを表示する。

## 4. 修正

- `scripts/resoloop-fork.sh` の `resolve_ref`: origin のブランチとして扱う条件を、`refs/remotes/origin/<ref>` の解決の成功から、「そのブランチの ref が完全一致で存在し、symbolic ref ではない」に変えた。それ以外は従来どおり `<ref>^{commit}` を git に解決させる
- `tests/scripts/test-resoloop-fork.bash` の 8 番: 上の回帰ケースを追加した（origin/HEAD があることを前提として確かめてから実行する）

他の案と選ばなかった理由:

- `HEAD` だけを特別扱いする: `HEAD~1` などの式が `origin/HEAD~1` に化ける問題が残る
- `git check-ref-format --branch` でブランチ名として正しいかを確かめる: `@{-1}` などを直前のブランチ名に展開するため、判定が checkout の状態に依存する

## 5. 検証

| 確認 | 結果 |
| --- | --- |
| 一時リポジトリでの再現（修正前） | `checkout HEAD` が `origin/HEAD` に移り、終了コード 0 |
| `bash tests/scripts/test-resoloop-fork.bash`（修正後のスクリプト） | PASS（3 秒） |
| 同じテストを修正前のスクリプト（`git show HEAD:scripts/resoloop-fork.sh`）で実行 | 追加した 8 番の検査で FAIL（`(origin/HEAD, detached)` に移った）。テストが欠陥を検出できる |
| `bash .devcontainer/run-tests.bash` | 28 本すべて PASS |
| `bash scripts/check-layout.sh` | 4 プロジェクトについて `warn:`（同梱スキルの更新。PR の範囲外）を表示し、`PASS: check-layout` |

## 6. 自己レビュー

修正後に 1 回だけ、3 観点（反証・PR 全体・検証の検出力）を別々のサブエージェントに同時に担当させた。各担当には、守る条件・影響経路・実行した検証・未確認の事項（`install HEAD` の通しの実行、git 2.55 以外での `show-ref --verify` の扱い）を渡した。自己レビュー後の修正は無く、再レビューもしていない。

| 観点 | 結果 |
| --- | --- |
| 反証 | 致命的な指摘なし。一時リポジトリで 14 通りの ref（`HEAD`、`@`、`HEAD~1`、origin/HEAD を別のブランチに向けた状態、`fetch --prune` で origin/HEAD がぶら下がった状態、origin/HEAD 以外の symbolic ref、`origin/fix/x`、`origin/HEAD`、`FETCH_HEAD`、`@` を含むブランチ名、同名のローカルのブランチがある `fix/x`、`fix/x~1` など）と、モックの dotnet での `install HEAD` を確かめた。origin/HEAD が symbolic ref でない通常の ref になる構成だけは旧版と同じ扱いになるが、origin に `HEAD` という名前のブランチが要り、このスクリプトの clone と fetch では作られない |
| PR 全体 | 致命的な指摘なし。削除したロックの参照残りが無いこと、実際の dotnet と NuGet（`--tool-path` の一時ディレクトリ）で未導入・最新導入済み・公開版より大きい版からの戻しが動くこと、上流のソースで `--check` がファイルを書かず `SKILL_SYNC_CONFLICT` が `SKILL_SYNC_REQUIRED` より先に判定されること、`STEP_TOTAL` と手順の数の一致、テストの隔離、文書の手順と実装の一致を確かめた |
| 検証の検出力 | 指摘 1 件（T-1）。`checkout HEAD` の検査は、修正前の版でも `symbolic-ref` の除外を外した版でも FAIL し、`HEAD` そのものの再発は検出できる。`install` の経路は `do_checkout` を通るので同じ検査で検出できる |

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| T-1（自己レビュー・検証の検出力） | 回帰テストが `HEAD^`・`HEAD~N` の形を見ていないので、将来 `show-ref --verify` の確認だけを外すと、その形が origin の既定のブランチに化ける再発を検出できない | 対応しない | 修正後のコードに欠陥は無い（自己レビューの一時リポジトリで `HEAD^`・`HEAD~1` が今のコミットを基準に解決されることを確かめた）。将来の変更への保険であり、致命的な指摘の修正と検証に要るテストではない |
