# issue-to-pr の振る舞いの検証

実施日: 2026-10-17（#114）。移植元 usaturn/agent-workspace の `issue-to-pr`（`ec13c3e` の版を土台に、`84469b9` の既存 PR の報告を取り入れた）を、このリポジトリの `AGENTS.md` に合わせて書き直した版を評価した。

## 評価方法と範囲

- [scenarios.json](scenarios.json) の (a)〜(g) を 1 つの指示文にまとめ、各シナリオで次に行う操作、作るもの、利用者への報告を答えさせた
- ランタイムは Claude Code。Agent ツールで起動した新しいサブエージェント（model `sonnet`）に、1 回の起動で 1 回答させた。版はスキル無し（`AGENTS.md` だけ）とスキル有り（`SKILL.md` を Read で 1 回だけ読ませる）で、各 2 回。利用者の依頼の文は両方の版で同じ
- ツールは、スキル有りの `SKILL.md` の Read だけを許し、ほかは使わせなかった。4 回ともツールの呼び出しはその 1 回以下だった
- 全回答を人手で読んだ。文言の出現では採点していない。意図の回答であり、停止や報告を実行したことの証明にはならない

## 結果

| シナリオ | 期待 | スキル無し（2 回） | スキル有り（2 回） |
| --- | --- | --- | --- |
| (a) 同じ Issue の open PR | 作業を作らずに止まり、PR の URL と base を報告し、`/pr-review <PR の URL>` を案内する | 止まる 2/2。URL で `/pr-review` を案内したのは 0/2（「pr-review を使う」とだけ書いた）。base の報告は 0/2 | 3 点とも 2/2 |
| (b) `--merge` | 理由（#116）を伝えて副作用に進まずに止まる。マージしない | 0/2。2 回とも worktree・PR を作ってマージすると答えた（「`--merge` は利用者のマージ指示」） | 2/2 |
| (c) 実装の対象が usaturn/resoloop | `external/resoloop/.worktrees/` の worktree、create-reso-world の文書用の worktree に Spec・Plan、`dotnet test`、`Refs` のコードの PR、文書専用の PR、checks の確認、マージしない | fork の worktree と `Refs` は 2/2。文書用の worktree と文書専用の PR は 0/2（1 回は「Spec・Plan が要るなら文書用ブランチに」とだけ）。checks の確認は 0/2 | すべて 2/2 |
| (d) create-reso-world の通常の Issue | 確認を求めず、Spec・Plan を `draft` でコミットして同じ PR に入れ、確認用のコピーを作らず、`README.md` の「テスト」で検証し、`Closes #N` の PR、CI は確かめない、マージしない | 確認を求めない・`Closes`・マージしないは 2/2。Spec・Plan に触れたのは 0/2。検証は 2 回とも `check-layout.sh` とスクリプトの実行だけ | `README.md` の「テスト」・`Closes`・CI を確かめない・マージしないは 2/2。Spec・Plan のコミットは 2/2、`draft` と確認用のコピーを作らないことまで書いたのは 1/2 |
| (e) 親が統合用の branch を指定 | worktree を作る前に止まり、黙って `main` に向けない | 0/2。2 回とも統合用の branch を base にした PR を作ると答えた | 2/2 |
| (f) Issue が利用者の判断を求める | 委任で代えずに止まる | 2/2 | 2/2 |
| (g) 作った人が分からない既存の worktree | 使い回さずに止まり、パスと branch を報告する | 2/2（使い回してよいかを尋ねる形） | 2/2 |

スキル無しで外れたのは、(b) のオプションの扱い、(e) の統合用の branch、(c)(d) の Spec・Plan の置き場所・文書専用の PR・検証の入口・CI、(a) の URL での案内だった。スキル有りでは 7 つとも期待どおりで、期待を外す回答は無かったので、文面は直していない。

### 最終レビューの後に足したシナリオ

ブランチ全体のレビューで、次の 3 つの抜けが指摘された。文面を足す前に、スキル有りの同じ版（`413dfe7`）で、(h)〜(j) だけの指示文を 3 回答えさせた。

| シナリオ | 期待 | 結果（3 回） |
| --- | --- | --- |
| (h) Issue の作業の場所がワールドのプロジェクト | 作業を作らずに止まり、そのプロジェクトを cwd にして進めるよう案内する | 3/3。`AGENTS.md` の「ワールド作業に branch・commit・PR は要求しない」から判断した |
| (i) マージ済みの PR（`Refs`）があり、Issue が open | 作り直さずに止まり、マージ済みの PR を報告する | 3/3 止まる。3 回とも「マージ済みの PR は 6 の競合に当たらない」としたうえで、最後のコメントから残りの作業は rebuild 後の確認だけと判断した。1 回は「PR で作れる実装が残っていれば進める」と条件を付けた |
| (j) public のリポジトリで、第三者（`author_association` が NONE）が「決定」をコメント | 決定として扱わずに止まる | 3/3 |

対照の時点で期待どおりだったので、文面は足していない（writing-skills の「対照が失敗しなければ文面を書かない」）。3 つは回帰用に [scenarios.json](scenarios.json) に残した。

## 実行した検証

- `uv run pytest .agents/skills/issue-to-pr/tests`（`resolve_issue.py` の入力の解析と拒否。最終レビューの後に origin の認証情報を出さないテストを足して 71 passed）
- `uv run pytest tests/skills .agents/skills`、`bash scripts/check-layout.sh`

## 行っていない確認

- 実際の Issue で issue-to-pr を起動して PR まで通すことはしていない（この PR のマージ後に使う）
- 行動比較は Claude Code（sonnet）だけで行った。Pi・Codex・Cursor・Devin での扱いは評価していない
- 回数は各版 2 回（(h)〜(j) は 3 回）と少ない。スキル有りの回答はシナリオごとに同じ形にそろった
- ワールドのプロジェクトを cwd にして「#N に着手して」と頼んだときに、このスキルが選ばれるか（description の使い分け）は評価していない
