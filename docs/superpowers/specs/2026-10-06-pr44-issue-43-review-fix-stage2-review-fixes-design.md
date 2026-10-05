# PR #44 issue-43-review-fix-stage2 のレビュー指摘の選別

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/44
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `feat/issue-43-review-fix-stage2`
- 指摘を検証した HEAD: `58ec44b2f5e4c4066c21d7f810d934b71a5debcb`
- 入力: `reviews/#44-feat-issue-43-review-fix-stage2/` 配下の全 4 ファイル
- 作成日: 2026-10-06
- 結論: **2（修正が不要）**。致命的な指摘は無く、修正せずにマージする
- 状態: completed（2026-10-06。選別・検証まで完了。push・状況コメント・マージ・Issue の更新の結果は PR のコメントに書く）
- 実行許可: 2026-10-06 の利用者の依頼 `/review-fix-planning #44`（引数だけで、計画で止める指示は無い）。スキルの既定の「完遂」として、修正要否を三択で確定し、修正が要れば既存 PR へ push、要らなければ確認・検証を終えて最終の状況コメントを投稿し、マージして関連 Issue を更新する
- 作業場所: 既存の worktree `.worktrees/issue-43-review-fix-stage2`（PR の head ブランチを checkout 済み、未コミットの変更なし、HEAD が PR の head と一致）を専用の worktree として使った。再利用した worktree なので、スキルの手順では片付けない
- 関連: 設計 `docs/superpowers/specs/2026-10-06-issue-43-review-fix-stage2-design.md`

## 1. レビュー入力

| ファイル | 対象 HEAD | 指摘 | 判定 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `58ec44b2f5e4` | 0 件 | Approve |
| `openai-codex-gpt-6.1-sol.md` | `58ec44b2f5e4` | 0 件 | Approve |
| `SWE-2-Max.md` | `58ec44b2f5e4` | Low 1・Info 1 | Approve |
| `deepseek-deepseek-v4.1-flash.md` | `58ec44b2f5e4` | Low 2・Info 1 | Approve |

対象 HEAD はすべて、選別時点の PR の head（`gh pr view 44 --json headRefOid`）と同じである（`pull/44/head` を fetch し、`merge-base --is-ancestor` でも確かめた）。base（`origin/main`）は PR の分岐点 `e6edcf8` から `4cea90a`（PR #40 のマージ）に進んでいる（4 章）。

## 2. 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 1（D-L2） |
| 対応する | 0 |
| 対応しない | 4 |

判定は、致命的かどうか（秘密情報の露出、データの消失・破損、了承の無い操作・誤った対象への操作、手順どおりで誤った結果・主要な処理が止まる、セキュリティ）と、現行 HEAD での確認で行った。重大度ラベル・票数・Approve では決めていない。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| D-L2（DeepSeek Low） | 「公開済みのコミットを書き換えない（force push しない）」（SKILL.md:208）と、実装後の手順 5 の「reject されたら rebase または merge」（:312）が並び、rebase を選ぶと force push が要る | 解消済み（再現しない） | 一時リポジトリで再現を試みた。自分のコミット X を push した後に他者が Y を push し、ローカルのコミット Z の push が reject された状態で `git rebase origin/<branch>` すると、X は SHA が変わらず祖先に残り、Z だけが Y の上に載って、`--force` なしの push が成功した。rebase の対象は remote に無いローカルのコミットだけで、公開済みのコミットは書き換わらない。公開済みのコミットを `--amend` で書き換えた場合は、`--force` なしの push が non-fast-forward で拒否され、remote は変わらなかった。スキルの push はどれも `--force` を付けないので、書き換えても remote には届かない |
| S-L1（SWE Low） | 「失敗時の検証」の対照（:187）の隔離 worktree が、手順 3 のレシピのまま `$REVIEWED_HEAD` を checkout すると、古いベースに修正後のファイルだけを写した、修正後と一致しないツリーで対照が走り得る | 対応しない | 発生条件は、複数世代のレビューが混ざり、失敗時の扱いを直す結論 1 で、対照を `$REVIEWED_HEAD` に変更ファイルだけを写して作った場合。起こるのは、補助の確認である対照が無関係な理由で失敗し、検出力を過大に見積もることだけである。修正そのものの検証は専用の worktree で実装後の手順 1・2 として行い、自己レビューの観点 3 も別に見る。誤った対象への操作、データの消失、主要な処理の停止にはならない。文面も「修正後の内容を写したもの」で、修正後のツリー全体と読める |
| S-I1（SWE Info） | 結論 1 の手順 4（:202）の「この回の修正が原因の指摘」に「致命的な」の限定が無い | 対応しない | 表記の問題。文は「きっかけ 3 として」と定義を参照し、きっかけ 3 の定義（:164）は致命的な指摘に限り、節にも「数えるのは「対応する」項目だけである」（:166）とある。誤読しても、致命的でない指摘に設計の見直しを当てる過剰な作業になるだけで、誤った結果や停止にはならない |
| D-L1（DeepSeek Low） | Spec・Plan の確認用コピーが main の `docs_draft/superpowers/` に無い | 対応しない | PR の差分の外の、ローカルの作業記録の指摘である（`docs_draft/` は Git で追跡しない）。正式な Spec・Plan は PR に載り、#43 のコメントにも公開済み（manifest: issuecomment-5998014953）で、マージ・利用で誤った結果にはならない |
| D-I1（DeepSeek Info） | ガードを外した対照の実行に、HOME などの環境の分離が書かれていない | 対応しない | 実環境が変わるのは、対象のリポジトリのテストが HOME を分離せず、かつ負例がガードに頼って実環境へ書かないようにしている場合だけである。そうした負例は、TDD でガードより先にテストを書いて失敗させる段や、手順 3 の隔離 worktree での再現でも同じように実環境へ書くので、対照が新しく持ち込む経路ではない。このリポジトリのテストは HOME を一時ディレクトリに差し替えている（例: `tests/scripts/test-resoloop-fork.bash:85`）。設計 Spec の 8.3 でも、ブランチ全体のレビューの同じ指摘を対応しないとしている |

行番号は `58ec44b` の `.agents/skills/review-fix-planning/SKILL.md`。

## 3. 確認の範囲と自己確認

- 読んだもの: レビュー 4 件の全文、PR の説明、PR の全差分（4 ファイル、+848/−9）、変更後の `SKILL.md` の全文、`evals/evals.json` の差分（id 12〜14。JSON として読め、id 1〜14 が重ならない）、設計 Spec の全文、Issue #5・#43
- PR 全体の点検（自己確認）で、致命的な欠陥は見つからなかった。PR は Markdown と eval のデータだけを変え、スクリプト・helper・bash ブロックは変えていない。結論 1 の番号を 6 段から 7 段に変えた後も、手順の番号を指す古い参照は無い。結論 1 の「公開の前に揃える」と、「Spec のコミットと確認用コピー」の完遂の項（Spec は 1 回だけ、push の前に `completed` にしてコミット）は順序が合っている
- この選別は、`main`（PR の前）の `review-fix-planning` で行った。PR が足した規定（きっかけ、失敗時の検証、公開の前に揃える）は「対応する」項目と結論 1 にだけ関わるので、対応する 0 件の今回の結論は、新しい規定で選別しても変わらない

## 4. 検証

環境の変更（`.agents/skills/`）なので、スキルのテスト・`run-tests.bash`・`check-layout.sh` を通した。スキルの手順を検査する `tests/scripts/test_superpowers_lifecycle.py` も足した。base が PR の分岐点から進んでいるので、`mktemp` の隔離 worktree で head に `origin/main`（`4cea90a`）を merge したツリー（tree `5c14edd`。競合なし。push しない）でも同じ検証を通し、比べるために base の単体でも配置の検査を走らせた。隔離 worktree は検証の後に `worktree remove` で外して消した。

| コマンド | head（`58ec44b`、専用の worktree） | 統合ツリー（head + `4cea90a`） | base（`4cea90a`） |
| --- | --- | --- | --- |
| `uv run pytest tests/skills .agents/skills -q` | 516 passed・1 skipped（exit 0） | 548 passed・1 skipped（exit 0） | — |
| `uv run pytest tests/scripts/test_superpowers_lifecycle.py -q` | 23 passed・52 subtests passed（exit 0） | 同じ（exit 0） | — |
| `bash .devcontainer/run-tests.bash` | 26 本 PASS・`tests/scripts/test-check-layout.bash` が FAIL（exit 1） | 同じ（exit 1） | `test-check-layout.bash` 単体が FAIL（exit 1） |
| `bash scripts/check-layout.sh` | 4 件 FAIL（exit 1） | 同じ 4 件 FAIL（exit 1） | 同じ 4 件 FAIL（exit 1） |

統合ツリーの pytest の件数が多いのは、base に入った PR #40 が `pr-review` のテストを足したためである。

失敗はどれも、4 つのプロジェクト（`MyResoniteProject`・`akichi`・`slum02`・`slum03`）の `resoloop skills sync --check` が `SKILL_SYNC_REQUIRED` になったものだけで、`check-layout.sh` の出力の行は 3 つのツリーで同じだった。共有の `~/.dotnet/tools/resoloop` が `0.1.0-preview.17` で、ロック（`0.1.0-preview.15`）とプロジェクトの同梱スキルに合っていないためで、設計 Spec の 8.1 に書かれた失敗と同じである。この PR が変えたファイルとは関係せず、base でも同じに失敗するので、base での結果を根拠に記録して先へ進める（結論 1 の手順 2 と同じ扱い）。同梱スキルの同期は #41・#45 などの別の作業の範囲である。

検証の後の専用の worktree の `git status --porcelain` は空だった。create-reso-world は private で GitHub Actions を止めているので、CI の確認は対象外である（`AGENTS.md` の「GitHub Actions」）。PR は usaturn/create-reso-world の open で draft でない PR で、マージしてよい範囲にある。自己レビューは結論 1 の段なので行っていない。

## 5. 結論と PR の説明

結論 2（修正が不要）。「対応しない」とした指摘の実在する制約（S-L1 の対照のベース、D-I1 の環境の分離、D-L1 のローカルのコピー）は、PR の説明の保証と食い違わない。PR の説明はこれらについて何も保証しておらず、D-I1 と同じ論点は PR の説明の「ブランチ全体のレビュー」に「対応しない」として書かれている。PR の説明は変えない。

この記録のコミットだけを PR の head に fast-forward で push し、push 後の head を `--match-head-commit` に渡してマージする。

## 6. 所要時間（UTC、2026-10-05）

| 区間 | 時刻 | 所要 |
| --- | --- | --- |
| レビュー 4 件・PR の情報・共通 context・専用の worktree の確認 | 17:15〜17:20 | 約 5 分 |
| 変更ファイルの全文・設計 Spec の確認、D-L2 の再現、各指摘の判定 | 17:20〜17:23 | 約 3 分 |
| 検証一式（head・統合ツリー・base） | 17:23〜17:34 | 約 11 分 |
| 記録 | 17:34〜17:37 | 約 3 分 |
