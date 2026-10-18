# PR #148: push の refspec を `${SHA:?}` にする変更（Issue #145）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/148（`fix/issue-145-push-refspec-guard` → `main`）
- 関連 Issue: #145（`closingIssuesReferences`。本文の `Closes #145`）
- 関連文書: `docs/superpowers/specs/2026-10-18-create-reso-world-issue145-push-refspec-guard-design.md`、`docs/superpowers/plans/2026-10-18-create-reso-world-issue145-push-refspec-guard.md`（どちらも draft のまま。この文書では変えない）
- 検証したコード HEAD: `f2137973f3618f00337202d0ad12fd639ce3afaf`。base `main` は PR の分岐点 `2deb900` から `84f417f`（PR #147 のマージ。`docs/superpowers/` の Issue #114 の Spec・Plan 2 ファイルだけ）まで進んでいる
- 状態: completed
- 実行許可: 利用者が 2026-10-18（JST）に review-fix-planning を `#148` だけを付けて指定。計画で止める指示は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要でマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-145-push-refspec-guard`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付けの対象ではない）

## 入力

`reviews/#148-fix-issue-145-push-refspec-guard/` の 4 ファイル。対象 HEAD はどれも `f2137973f361` で、取得した `pull/148/head`（`f213797`）と同じ。

| ファイル | 対象 HEAD | 判定 | 指摘 |
| --- | --- | --- | --- |
| `Grok-4.7.md` | `f2137973f361` | Approve | なし（Critical〜Info 0） |
| `SWE-2-Max.md` | `f2137973f361` | Approve | なし（Critical〜Info 0） |
| `claude-opus-5-5.md` | `f2137973f361` | Approve | なし（Critical〜Info 0） |
| `openai-codex-gpt-6.1-sol.md` | `f2137973f361` | Approve | なし（Critical〜Info 0） |

## 分類

レビューの指摘は 0 件。確認中に自分で挙げた事項（S-1）と、`SWE-2-Max.md` が取り扱いを妥当と判断した、実施者のブランチ全体のレビューの Minor 3 件（R-1〜R-3。PR の Plan の「判断の記録」）も、同じ基準で分けた。

| ID | 出どころ | 内容 | 分類と根拠 |
| --- | --- | --- | --- |
| S-1 | 自己確認 | `docs/superpowers/` の外で旧形 `"${SHA}:refs/heads/..."` が残るのは `.agents/skills/issue-to-pr/evals/scenarios.json:108` だけ | 対応しない。現行 HEAD で `git grep` して確かめた。行動比較の期待値で手順の定義ではなく、どの手順もこの行を写して push しない。PR #144 の review-fix Spec（I-1）が「次の行動比較で `:?` を含める」と決めている。マージしても誤った push に進む経路は無い |
| R-1 | 実施者のレビュー（Minor 1） | `AGENTS.md` に、`:?` で止まった後は検査から 1 回の呼び出しでやり直すことが書かれていない | 対応しない。止まった状態は安全（push されない）で、既存の「検査した commit をそのまま push する」「検査の後に変わった HEAD を push しない」でやり直しの形は決まる。記載の網羅の指摘 |
| R-2 | 実施者のレビュー（Minor 2） | Plan の Task 1 Step 2 の `grep -v '^./docs/superpowers/'` が、実施者の環境では効かなかった | 対応しない。Plan の検証手順の記録で、判定は除外して行ったと Plan に書いてある。今回 `git grep ... -- . ':!docs/superpowers'` で同じ結論（旧形は S-1 の 1 行だけ）を確かめた |
| R-3 | 実施者のレビュー（Minor 3） | `scripts/scan-before-push.sh` のコメントへの「`:?` を外さない」の追記が、Spec の必要な挙動 2（`AGENTS.md` だけを指定）と食い違う | 対応しない。コメント 1 行で動作は変わらず、Plan の「判断の記録」に理由がある。内容は `AGENTS.md` と同じで、誤った手順にはつながらない |

分類: **解消済み 0 / 対応する 0 / 対応しない 4**。

仕様の論点として残すもの: なし（S-1 の期待値の更新時期は PR #144 の review-fix Spec が決めている）。

同じ条件の再発と設計の見直し: 当たらない（「対応する」が 0 件）。

## 確認の範囲

- PR の変更 7 ファイルの全文または差分の前後: `AGENTS.md`（「push の前の秘密情報の検査」）、`.agents/skills/review-fix-planning/SKILL.md`（実装後の手順 5、結論 2 の手順 6 からの参照）、`docs/resoloop-fork-workflow.md`・`docs/resoloop-meshy-workflow.md`（手順 5）、`scripts/scan-before-push.sh`（全文。差分は先頭コメントだけで、成功時に標準出力へ出すのは 93 行目の `head_sha` 1 行のまま）、PR の Spec・Plan の全文
- 関連: `.agents/skills/issue-to-pr/SKILL.md` の 5 章（`${CODE_SHA:?}`・`${DOC_SHA:?}` と同じ注意文。PR の形と一致）、`tests/scripts/test-scan-before-push.bash`（コメント・文書の push 行を照合しない）、`tests/skills/`
- 横断確認（現行 HEAD の `git grep`、`docs/superpowers/` を除く）: 変数で組み立てる push の refspec は、5 か所と issue-to-pr の 2 行がすべて `:?` 付き。旧形は S-1 だけ。`scripts/resoloop-fork.sh:124`（同じスクリプト内で求めた `$up`）、claim ref の削除（`--force-with-lease` で SHA を照合）、テスト内の push は、Issue と PR の Spec が対象外とした理由どおりで、呼び出しが分かれて空になる経路が無い
- 自己確認の再現（隔離 worktree を `f213797` で作り、ローカルの bare repo だけを使用。bash 5.3.9・`zsh -f` 5.9・gitleaks 8.30.1。場面ごとに新しい repo を作り、bare repo の全 ref を実行の前後で比べた）: 14/14 が期待どおり
  - A（未設定・`${SHA:?}`）・B（空文字列）・F（呼び出しを分けた 2 回目、review-fix-planning の変数名のまま）: bash は終了コード 127、zsh は 1。全 ref が変わらない
  - C（未設定・旧形 `${SHA}`、対照）: 終了コード 0 で ` - [deleted] fix/x`
  - D（`AGENTS.md` の形を 1 回の呼び出しで）・E（review-fix-planning の実装後の手順 5 のコードブロックを変数名のまま）: 終了コード 0。`fix/x` だけが作業用の clone の HEAD になり、ほかの ref は変わらない
  - G（存在しない base で検査を失敗させる）: 終了コード 1。push されず、全 ref が変わらない
  - 再現の後、隔離 worktree は `git worktree remove --force` の後に親ディレクトリごと消した
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった
- PR と関係しない既存の問題で致命的なものは無い

## 検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| PR head `f213797`（専用の worktree） | `bash .devcontainer/run-tests.bash` | `PASS: 32 test(s)`、終了コード 0 |
| PR head `f213797` | `bash scripts/check-layout.sh` | `PASS: check-layout`、終了コード 0 |
| PR head `f213797` | `uv run pytest tests/skills .agents/skills .agents/scripts -q` | 625 passed（191.18 秒）、終了コード 0 |
| head に base `84f417f` を merge した一時的なツリー `5bfe8a8`（隔離 worktree、push しない） | 上の 3 つ | `PASS: 32 test(s)`・`PASS: check-layout`・625 passed（192.13 秒）、どれも終了コード 0 |

base `main` は分岐点 `2deb900` から進んでいる（`git merge-base --is-ancestor origin/main f213797` が失敗）ので、`mktemp` の隔離 worktree で head に `84f417f` を merge（競合なし。差分は `docs/superpowers/` の Issue #114 の 2 ファイルだけ）し、同じ検証を通した。検証後、その worktree は `git worktree remove --force` の後に親ディレクトリごと消した。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）ので、check の確認は対象外。検証は clean な専用の worktree で行い、この文書の下書きは worktree の外（`tmp/agents/`）に置いた。検証の後も専用の worktree の `git status --porcelain` は空だった。

## PR の説明への追記

「対応しない」とした 4 件は、期待値の記録・記載の網羅・Plan の記録の指摘で、PR の説明の保証（空・未設定の SHA では push の前に止まり、値があれば今までどおり push する）と食い違う実在の制約ではないので、PR の本文は変えない。

## 自己レビュー

修正が無いので行わない（結論 2）。

## 所要時間

着手（2026-10-18 06:15Z ごろ）から Spec の記録まで約 20 分。レビューと PR の読み込み 約 3 分、変更ファイル・関連の読み込みと横断確認・自己確認の再現 約 5 分、検証（PR head と、base を merge した一時的なツリーで `run-tests.bash`・`check-layout.sh`・pytest）約 12 分（Spec の下書きと並行）。
