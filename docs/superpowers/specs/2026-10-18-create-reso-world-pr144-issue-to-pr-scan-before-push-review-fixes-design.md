# PR #144: issue-to-pr の push 前検査（Issue #139）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/144（`fix/issue-139-scan-before-push` → `main`）
- 関連 Issue: #139（`closingIssuesReferences`。本文の `Closes #139`）
- 関連文書: `docs/superpowers/specs/2026-10-17-create-reso-world-issue139-scan-before-push-design.md`、`docs/superpowers/plans/2026-10-17-create-reso-world-issue139-scan-before-push.md`（どちらも draft のまま。この文書では変えない）
- 検証したコード HEAD: `1b7be50a0b3cd0affdc373b5a8ee5c4340dc62fd`。base `main` は PR の分岐点 `50e4a6b` から進んでいない
- 状態: completed
- 実行許可: 利用者が 2026-10-18（JST）に `/review-fix-planning #144 --hold-action skip` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う。`--hold-action` は review-fix-planning に定義の無いオプション（issue-to-pr の移植元のオプション名）で、止まらずに進める指示と読み、完遂の扱いを変えない
- 結論: 2（修正不要でマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-139-scan-before-push`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#144-fix-issue-139-scan-before-push/` の 4 ファイル。対象 HEAD はどれも `1b7be50a0b3c` で、取得した `pull/144/head`（`1b7be50`）と同じ。

| ファイル | 対象 HEAD | 判定 | 指摘 |
| --- | --- | --- | --- |
| `Grok-4.7.md` | `1b7be50a0b3c` | Approve | なし |
| `SWE-2-Max.md` | `1b7be50a0b3c` | Approve | なし |
| `claude-opus-5-5.md` | `1b7be50a0b3c` | Approve | Info 1 件（I-1） |
| `deepseek-deepseek-v4.1-flash.md` | `1b7be50a0b3c` | Approve | Low 1 件（L-1） |

## 分類

| ID | 出どころ | 内容 | 分類と根拠 |
| --- | --- | --- | --- |
| I-1 | claude-opus-5-5（Info） | シナリオ (k) の `expected` が `"${SHA}:refs/heads/..."` のままで、最終版の `SKILL.md` が求める `${SHA:?}` を合格の基準に含めていない | 対応しない。`scenarios.json:108` はそのとおり（現行 HEAD で確認）だが、評価の期待値であり、スキルの手順の挙動には影響しない。`SKILL.md:109-115` は `${CODE_SHA:?}`・`${DOC_SHA:?}` と「呼び出しを分けるときも `:?` を外さない」を書いており、`validation.md` は最終版の 3 回答すべてが `:?` を付けたと記録している。次の行動比較で `:?` を落とした回答を合格にし得るという将来の保険の論点で、マージ・利用で誤った操作に進む経路は無い |
| L-1 | deepseek-v4.1-flash（Low） | Plan の「実行予算」の worker の行に、予約枠と無進捗の打ち切りが無い（`AGENTS.md` の SDD 実行運用、`.agents/execution-budget.md:53`） | 対応しない。Plan の 43 行目に `予約`・`無進捗` が無いことは現行 HEAD で確認した。ただし Plan は実行を終えた記録で（「完了」の節）、評価のサブエージェントは打ち切りに達していない。記録の網羅の指摘で、直さずにマージしても誤った操作・データの消失には至らない |

分類: **解消済み 0 / 対応する 0 / 対応しない 2**。

仕様の論点として残すもの: Plan の Global Constraints（20 行目）と Spec の決定記録（39 行目）にも `"${SHA}:refs/heads/<branch>"` の形が残り、決定記録の 42 行目（`${SHA:?}`）と揃っていない。どちらも `c3db9c5` の修正の前に書いた記録で、手順の定義は `SKILL.md` だけが持つため直さない。次に issue-to-pr の行動比較を行うときに、(k)(l)(o) の期待値に `:?` を含める。

同じ条件の再発と設計の見直し: 当たらない（「対応する」が 0 件）。

## 確認の範囲

- PR の変更 5 ファイルの全文: `.agents/skills/issue-to-pr/SKILL.md`・`evals/scenarios.json`・`evals/validation.md`、PR の Spec・Plan
- 関連: `scripts/scan-before-push.sh`（この PR では変えていない。`-C`・`--base` の既定 `origin/main`・終了コード 0/1/2・成功時は標準出力に SHA の 1 行だけ・installer の解決は `BASH_SOURCE` 基準）、`SKILL.md` の 2 章の `PARENT_ROOT` の求め方（31 行目）と対象ごとの作業ルート・remote の表（50〜52 行目）、`AGENTS.md` の「push の前の秘密情報の検査」と「SDD 実行運用」、`.agents/execution-budget.md`
- 自己確認:
  - 5 章のコマンド列は、検査の失敗（終了コード 0 以外）と空の SHA のどちらでも、`&&` の連鎖と `[ -n ]`・`${VAR:?}` の二重のガードで push の前に止まる。create-reso-world が対象で `DOC_SHA` の 2 行を除いた形も、行末の `\` が残らず成り立つ（Grok・deepseek のレビューが bash・zsh と使い捨ての bare repo で実行して確認済み）
  - `SCAN` は `PARENT_ROOT` のスクリプトで、usaturn/resoloop・usaturn/resoloop-meshy の worktree でも、`-C` で渡した checkout の `origin/main` を base にする。2 章の表のとおり、どの対象も push 先は `origin`（usaturn の fork・リポジトリ）で、上流の orange3134/resoloop へは向かない
  - 再 push（(o)）でも範囲は `origin/main..HEAD` で、PR の branch の全 commit を検査し直す
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった
- PR と関係しない既存の問題で致命的なものは無い

## 検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| PR head `1b7be50`（専用の worktree） | `bash .devcontainer/run-tests.bash` | `PASS: 32 test(s)`、終了コード 0 |
| PR head `1b7be50` | `bash scripts/check-layout.sh` | `PASS: check-layout`、終了コード 0 |
| PR head `1b7be50` | `uv run pytest tests/skills .agents/skills -q` | 589 passed（180.45 秒）、終了コード 0 |

base `main` は PR の分岐点 `50e4a6b` のままで（`git merge-base --is-ancestor origin/main 1b7be50` が成功）、base を merge した一時的なツリーの検証は不要。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）ので、check の確認は対象外。検証は clean な専用の worktree で行い、この文書の下書きは worktree の外（`tmp/agents/`）に置いた。検証の後も worktree の `git status --porcelain` は空だった。

## PR の説明への追記

「対応しない」とした 2 件は記録の網羅の指摘で、PR の説明の保証（5 章の push の挙動・停止条件）と食い違う実在の制約ではないので、PR の本文は変えない。

## 自己レビュー

修正が無いので行わない（結論 2）。

## 所要時間

着手（2026-10-18 02:05Z ごろ）から Spec の記録まで約 13 分。レビューと PR の読み込み 約 2 分、指摘の確認と変更ファイル・関連の読み込み・自己確認 約 4 分、検証（PR head で `run-tests.bash`・`check-layout.sh`・pytest）約 8 分（Spec の下書きと並行）。
