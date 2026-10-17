# PR #136: issue-to-pr スキルと alias（Issue #114）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/136（`feat/issue-114-agent-workspace-port` → `main`）
- 関連 Issue: 本文の `Refs #114`（`closingIssuesReferences` は空）。本文で参照しているだけの Issue は #116・#115。PR のコメントの持ち越しは #137・#138
- 関連文書: `docs/superpowers/specs/2026-10-17-create-reso-world-issue114-issue-to-pr-alias-design.md`、`docs/superpowers/plans/2026-10-17-create-reso-world-issue114-issue-to-pr-alias.md`（どちらも draft のまま。この文書では変えない）
- 検証したコード HEAD: `31886c6a4ae29e25fef3b7d04e8d6cafe35d7d61`。base `main` は PR の分岐点 `20ff46c` から `61763dc`（PR #130 のマージ）へ進んでいる
- 状態: completed
- 実行許可: 利用者が 2026-10-17（JST）に `/review-fix-planning #136` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要でマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-114-agent-workspace-port`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#136-feat-issue-114-agent-workspace-port/` の 3 ファイル。対象 HEAD はどれも `31886c6a4ae2` で、取得した `pull/136/head`（`31886c6`）と同じ。

| ファイル | 対象 HEAD | 判定 | 指摘 |
| --- | --- | --- | --- |
| `SWE-2-High.md` | `31886c6a4ae2` | Approve | Info 1 件（SW-I-1） |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `31886c6a4ae2` | Approve | Low 1 件（DS-L-1） |
| `grok-4.7.md` | `31886c6a4ae2` | Approve | Medium 1 件（GR-M-1）、Low 1 件（GR-L-1） |

## 分類

| ID | 出どころ | 内容 | 分類と根拠 |
| --- | --- | --- | --- |
| GR-M-1 | Grok（Medium、確認推奨） | cwd が別の Issue の linked worktree のとき、3 章が必須とする `superpowers:using-git-worktrees` の Step 0（「既に linked worktree なら作らない」）や、権限エラー時に現在のディレクトリで作業する fallback に従い、別の Issue の branch の上で実装し得る | 解消済み（再現せず）。`evals/` と同じ方法（新しいサブエージェント、model `sonnet`、読み取りだけ、`SKILL.md` と superpowers 7.0.0 の `using-git-worktrees` の `SKILL.md` を 1 回ずつ Read）で、cwd を PR #127 の head の `.worktrees/issue-115-budget-task-watch` にして `/issue-to-pr #204` を答えさせた。3/3 が食い違いに気付いたうえで 3 章の「`origin/main` から新しい worktree」と 2 章 6 の「使い回さない」を優先し、`/workspaces/reso-world/.worktrees/issue-204-<要約>` を `origin/main` から作ると答えた。同じ状況で `git worktree add` がサンドボックスに拒否された場合も、3/3 が #115 の worktree・main checkout で編集せず、停止の報告（「必要なツール・API の失敗」）に進んだ |
| DS-L-1 | DeepSeek（Low） | origin の認証情報のマスク `(?<=://)[^/@]*@` が最初の `@` までしか効かず、パスワードに生の `@` を含む URL（`https://user:p@ssw0rd@github.com/...`）では `ssw0rd@github.com/...` が stderr に残る | 対応しない。表示は現行 HEAD でもそのとおり（`resolve_issue.py:75`、再現済み）だが、生の `@` を含む userinfo は git 自体が使えない形である。git 2.55.0 で `git ls-remote 'https://user:p@ssw0rd@127.0.0.1:9/x.git'` は `URL rejected: Bad hostname` で止まり、git が使える形（`p%40ssw0rd`）はマスクで全体が伏せられる（`https://***@github.com/...`、再現済み）。GitHub の HTTPS の認証はトークン（`@` を含まない）なので、動く checkout でこの表示に至る経路が無い。PR の説明の既知の制限に書き足す |
| GR-L-1 | Grok（Low） | userinfo を含む GitHub の origin で `#N` を渡すと、「GitHub のリポジトリではありません」という誤った理由で止まる | 対応しない。停止は意図どおりで、トークンは表示されない（再現済み）。誤るのは停止の理由の文面だけで、Issue の URL を渡せば同じ Issue を解決できる。手順のとおりに使っても誤った操作には進まない。PR の説明の既知の制限に書き足す |
| SW-I-1 | SWE-2（Info） | 位置引数を省略した呼び出し（`resolve_issue.py --`）では argparse が `usage:` を出し、`issue-to-pr:` で始まらない | 対応しない。`SKILL.md` の呼び出しは常に `-- "$INPUT"` で 1 引数を渡し、空文字列でも `issue-to-pr: Issue を 1 つだけ指定してください` で止まる（再現済み）。引数の欠落でも終了コードは 2 で、表示の形式だけの違い |

分類: **解消済み 1 / 対応する 0 / 対応しない 3**。

仕様の論点として残すもの: issue-to-pr の 3 章に、`using-git-worktrees` から適用しない手順（Step 0 の省略、作成前の同意、現在の HEAD からの branch、権限エラー時の in-place 作業）を明記するか、cwd が別の Issue の linked worktree である行動比較を `evals/` に足すか。今回の 6 回はどれも期待どおりだったので、writing-skills の「対照が失敗しなければ文面を書かない」に従い足していない。再現したら見直す。

同じ条件の再発と設計の見直し: 当たらない（「対応する」が 0 件）。

## 確認の範囲

- PR の変更 12 ファイルの全文: `.agents/skills/issue-to-pr/` の `SKILL.md`・`scripts/resolve_issue.py`・`tests/test_resolve_issue.py`・`evals/scenarios.json`・`evals/validation.md`、`.claude/skills/issue-to-pr`（symlink）、`AGENTS.md`・`.devcontainer/zshrc.txt`・`.devcontainer/README.md`・`docs/maatlog-poc-porting.md` の差分、PR の Spec・Plan
- 関連: superpowers 7.0.0 の `using-git-worktrees`（このリポジトリで有効な版。Step 0・1a・1b・Sandbox fallback）、`README.md` の「テスト」、PR のコメント（持ち越しの再調査）、Issue #114 の本文とコメント（#133 のマージ後に push 前の検査を取り込む依頼を含む）、#116・#137・#138 と PR #133 の状態
- 自己確認:
  - `resolve_issue.py` は `run_readonly` で `git remote get-url origin` と `gh issue view` だけを呼び、Git と GitHub の状態を変えない。`ORIGIN_URL` は `.git` と末尾の `/` を外して照合し、`supported` は 3 つのリポジトリの小文字の表記に揃える。応答の URL は owner/repo の大文字小文字だけを許して照合する
  - 3 章の `git -C "$TARGET_ROOT" worktree add -b <branch> .worktrees/<名前> origin/main` は、相対パスが `TARGET_ROOT` 基準になる（Grok のレビューで確認済み）。PR の push は `origin`（usaturn の fork・リポジトリ）だけで、上流の orange3134/resoloop へは向かない
  - Issue #114 のコメント（2026-10-17T13:07Z）は、PR #133（open）のマージ後に issue-to-pr の push を `scripts/scan-before-push.sh` 経由にするよう求めている。#133 は未マージで、`main` の `AGENTS.md` に push 前の検査の規則はまだ無いので、この PR の欠陥ではない。残りの作業として #114 に記録する
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった
- PR と関係しない既存の問題で致命的なものは無い

## 検証

| 対象 | コマンド | 結果 |
| --- | --- | --- |
| 現行 HEAD `31886c6` の隔離 worktree | `resolve_issue.py -- '#42'` を、origin が `https://user:p@ssw0rd@github.com/...`・`https://user:p%40ssw0rd@github.com/...`・`https://user:s3cr3t-token@github.com/...` の使い捨て checkout で実行。`resolve_issue.py --`・`-- ''` | どれも終了コード 2。表示はそれぞれ `https://***@ssw0rd@github.com/...`・`https://***@github.com/...`・`https://***@github.com/...`。引数の欠落は argparse の `usage:`、空文字列は `issue-to-pr: Issue を 1 つだけ指定してください` |
| git 2.55.0 | `git ls-remote 'https://user:p@ssw0rd@127.0.0.1:9/x.git'`（外部へ送らないよう 127.0.0.1 の閉じたポート）と、`%40` の形 | 生の `@` は `URL rejected: Bad hostname`、`%40` は接続の段階（`Could not connect to server`）まで進む |
| GR-M-1 の行動比較 | 新しいサブエージェント（sonnet）6 回。cwd を別 Issue の linked worktree にした `/issue-to-pr #204`（3 回）と、さらに `git worktree add` がサンドボックスに拒否された場合（3 回） | 前者 3/3 が `origin/main` から新しい worktree、後者 3/3 が編集せずに停止の報告 |
| PR head `31886c6`（専用の worktree） | `bash .devcontainer/run-tests.bash` | `PASS: 30 test(s)`、終了コード 0（2 分 28 秒） |
| PR head `31886c6` | `bash scripts/check-layout.sh` | PASS、終了コード 0 |
| PR head `31886c6` | `uv run pytest tests/skills .agents/skills -q` | 546 passed（147.43 秒）、終了コード 0 |
| PR head に `origin/main`（`61763dc`）を merge した一時的なツリー（push しない。`3dd02d7`、競合なし） | `bash .devcontainer/run-tests.bash` | `PASS: 30 test(s)`、終了コード 0 |
| 同上 | `bash scripts/check-layout.sh` | PASS、終了コード 0 |
| 同上 | `uv run pytest tests/skills .agents/skills .agents/scripts -q`（merge 後の `README.md` の「テスト」） | 567 passed（142.26 秒）、終了コード 0 |

base は PR の分岐点 `20ff46c` から PR #130 のマージで `61763dc` に進み、`AGENTS.md`・`.devcontainer/README.md` が重なるが、自動で merge できた。private の create-reso-world は CI を使わない（`AGENTS.md` の「GitHub Actions」）ので、check の確認は対象外。検証は clean な専用の worktree で行い、この文書の下書きは worktree の外に置いた。検証の後も worktree の `git status --porcelain` は空だった。PR 本文が記録していた pr-review の不安定なテスト（#128）は、今回の 2 回の実行では失敗しなかった。

## PR の説明への追記

結論 2 の規定により、「対応しない」とした実在の制約のうち PR の説明の保証と食い違う 2 件（DS-L-1・GR-L-1）を、PR の本文の「既知の制限」に条件と回避方法とともに書き足した。

## 自己レビュー

修正が無いので行わない（結論 2）。

## 所要時間

着手（2026-10-17 13:50Z）から Spec の記録まで約 20 分。レビューと PR・Issue の読み込み 約 3 分、指摘の再現（helper の 3 件・git の URL の解釈）と変更ファイル・関連の読み込み・自己確認 約 5 分、GR-M-1 の行動比較 約 2 分（6 回。読み込みと並行）、検証（PR head と merge したツリーで `run-tests.bash`・`check-layout.sh`・pytest）約 10 分。
