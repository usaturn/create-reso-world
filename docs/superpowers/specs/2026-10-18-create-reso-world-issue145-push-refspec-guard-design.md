# push の refspec を `${SHA:?}` にする

## 管理・実行許可

- 文書管理・変更対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/145
- 状態: `draft`（内容の明示承認は受けていない）
- 調査時 HEAD: `2deb900`
- 利用者の指示: Claude Code のセッションで `/issue-to-pr #145`
- 実行許可: issue-to-pr の委任範囲に従い、通常の判断を推奨案で決め、検証・commit・push・PR 作成まで進める。マージ、他のリポジトリの変更、remote の実在の branch を使った検証は含まない
- 作業場所: `/workspaces/reso-world/.worktrees/issue-145-push-refspec-guard`、branch `fix/issue-145-push-refspec-guard`（`origin/main` `2deb900` から作成）
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue145-push-refspec-guard.md`

## 意図と範囲

`AGENTS.md` の「push の前の秘密情報の検査」と、それに従う手順は、push の refspec を `"${SHA}:refs/heads/<branch>"` と書いている。1 回のシェルの呼び出しでは `[ -n "$SHA" ]` が空の SHA を止めるが、検査と push を別の呼び出しに分けると、2 回目の `SHA` は空になる（Claude Code の Bash は呼び出しをまたいで変数を保たない）。refspec が `:refs/heads/<branch>` になり、remote の branch が消える。PR の head なら GitHub はその PR を close する。fork の branch なら上流の PR も close される。

refspec を `"${SHA:?}:refs/heads/<branch>"` にして、SHA が空・未設定なら push の前にシェルが止まるようにする。PR #144 が issue-to-pr の 5 章だけに入れた形（`c3db9c5`）を、基準の `AGENTS.md` と、ほかの手順に揃える。

変更は次の 5 か所と、この Spec・Plan に限る。

- `AGENTS.md`（「push の前の秘密情報の検査」の push の形と注意）
- `.agents/skills/review-fix-planning/SKILL.md`（「実装後」の手順 5）
- `docs/resoloop-fork-workflow.md`（fork へ push する手順 5）
- `docs/resoloop-meshy-workflow.md`（push の手順 5）
- `scripts/scan-before-push.sh`（使い方のコメント）

検査のスクリプトの動作、issue-to-pr、claim ref の削除、`scripts/resoloop-fork.sh` は変えない。

## 必要な挙動

1. 5 か所の refspec を `"${SHA:?}:refs/heads/..."` にする。`[ -n "$SHA" ]` は残す（1 回の呼び出しでは、こちらが先に止める）
2. `AGENTS.md` に「SHA が空だと refspec が branch の削除になるので、呼び出しを分けるときも `:?` を外さない」を 1 文で書く（issue-to-pr の 5 章と同じ書き方）
3. zsh の注意（`$SHA:r` を修飾子として展開する）は、`${SHA:?}` の形に合わせて「波括弧で書く」に言い換える。`AGENTS.md` と `scripts/scan-before-push.sh` のコメントの 2 か所
4. 直した形は bash・zsh の両方で、SHA が空・未設定なら push の前に止まり、remote の branch が残る。SHA があれば今までどおり push する

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
|---|---|---|---|---|
| 空の SHA の止め方 | refspec を `${SHA:?}` にし、`[ -n "$SHA" ]` も残す | `[ -n "$SHA" ]` だけ（今の形）、push を関数・スクリプトに包む | Issue の指定。`:?` は refspec を作る位置で効くので、呼び出しを分けても、`[ -n "$SHA" ]` を写し忘れても止まる。スクリプトに包むと、検査した SHA と送る SHA を合わせる今の形が変わる | issue-to-pr による通常判断の委任 |
| `AGENTS.md` の注意 | push の形の後に、issue-to-pr の 5 章と同じ 1 文を足す | 理由を詳しく書く（PR の close、上流への影響） | Issue の指定。理由の詳細は Issue と、この Spec に残す（指示文は簡潔に書く） | — |
| zsh の注意の言い換え | 「`${SHA:?}` と波括弧で書く」 | 今の「`${SHA}` と書く」のまま、注意を消す | 形が `${SHA:?}` になるので、`${SHA}` と書くと形と食い違う。注意を消すと、波括弧を外して `$SHA:refs` に戻す誤りを防げない | — |
| 対象の範囲 | Issue の 5 か所 | `.agents/skills/issue-to-pr/evals/scenarios.json:108` の期待値、過去の Spec・Plan の記録も直す | Issue が対象と対象外を列挙している。`scenarios.json` は行動比較の期待値で、手順の定義ではない。PR #144 の review-fix Spec が「次に issue-to-pr の行動比較を行うときに `:?` を含める」と決めている。過去の Spec・Plan は当時の記録で、書き換えない | — |
| 対象外 | `planning-parallel-issues` の claim ref の削除、`scripts/resoloop-fork.sh:124` | 同じく `:?` を付ける | Issue のとおり。前者は削除が目的で `--force-with-lease` で SHA を照合する。後者はスクリプトの中の変数で、呼び出しが分かれない | — |
| 検証 | ローカルの bare repo で bash・zsh の再現、`README.md` の「テスト」 | 文面を照合する pytest、remote の実在の branch での確認 | 文面の変更なのでテストは書かない（`AGENTS.md` の「テストの採用基準」）。止まるかどうかはシェルの展開で決まるので、コマンドを実行して確かめる。実在の branch では削除の危険がある | — |
| 行動比較 | 行わない | writing-skills の無し/ありの比較 | review-fix-planning の変更はコードブロックの refspec 1 つで、エージェントの判断ではなくシェルの展開で止まる。効果は再現の実行で確かめられる。新しいスキルを作る変更でもない | — |

## 検証と受け入れ条件

ローカルの一時ディレクトリに bare repo（`origin.git`）と作業用の clone を作り、`fix/x` を push した後に、次を bash と `zsh -f` のそれぞれで実行する。

| 場面 | 形 | 期待する結果 |
|---|---|---|
| A. SHA が未設定の別の呼び出し | `git push origin "${SHA:?}:refs/heads/fix/x"` | push の前にシェルが止まる（終了コード 0 以外）。origin の `fix/x` が残る |
| B. SHA が空文字列 | 同上（`SHA=` を設定してから） | A と同じ |
| C. 対照（今の形） | `git push origin "${SHA}:refs/heads/fix/x"`（SHA 未設定） | origin の `fix/x` が消える（Issue の再現と同じ。確かめた後に作り直す） |
| D. 検査を通した 1 回の呼び出し | `AGENTS.md` の形そのまま（`scripts/scan-before-push.sh` を実行し、`"${SHA:?}:refs/heads/fix/x"` で push） | 終了コード 0。origin の `fix/x` が作業用の clone の HEAD と同じ |

あわせて `README.md` の「テスト」のコマンド（ワールドの行を除く）を実行する。`bash -n scripts/scan-before-push.sh` で構文を確かめ、`git diff --check` で空白の誤りが無いことを確かめる。

## 検証の結果

再現（2026-10-18、`3ca8214`、bash 5.3.9・zsh 5.9・gitleaks 8.30.1）。各場面ごとに新しい bare repo を作り、`SHA` を `env -u SHA`（B は `env SHA=`）で外した新しいシェルで実行した。

| 場面 | bash | `zsh -f` |
|---|---|---|
| A. 未設定・`${SHA:?}` | 終了コード 127、`SHA: parameter null or not set`。`fix/x` は残った | 終了コード 1、`SHA: parameter not set`。`fix/x` は残った |
| B. 空文字列・`${SHA:?}` | A と同じ | A と同じ |
| C. 未設定・`${SHA}`（今の形） | 終了コード 0、` - [deleted] fix/x`。`fix/x` が消えた | bash と同じ |
| D. `AGENTS.md` の形を 1 回の呼び出しで | 終了コード 0、検査は `no leaks found`、`fix/x` が作業用の clone の HEAD と同じ | bash と同じ |

zsh は空文字列のときも `parameter not set` と出すが、push の前に止まる点は同じ。
