# Issue #138: issue-to-pr の PR 本文で、マージの後の確認が残る Issue とボードの子を `Closes` で閉じない

- 状態: draft
- 文書管理リポジトリ: `usaturn/create-reso-world`（`docs/superpowers/`）
- 対象: `usaturn/create-reso-world` / [Issue #138](https://github.com/usaturn/create-reso-world/issues/138)
- 検証したコードの HEAD: `origin/main` `c1fdc560696ab3ce3392b07ece3089989bf25902`（2026-10-25T04:27Z の着手時）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue138-issue-to-pr-pr-body-keyword.md`
- 関連: #114・PR #136（issue-to-pr の追加。2026-10-17 にマージ済み）、PR #227（#206。`finalize.py` の merge commit の照合）、PR #266（#137。(i) の分かれを #138 に記録）
- 実行許可: 利用者の `/issue-to-pr #138 --merge --max-cycles 3`。通常の設計判断を推奨案で決め、実装・検証・commit・push・PR の作成と、PR 修正ループ（サイクルの上限 3）、その結論に従う `finalize.py` のマージまでを許可する。本 Spec の内容の承認（`approved`）ではない

## 目的

issue-to-pr は、Issue が実装の対象と同じリポジトリにあれば PR 本文を `Closes #N` にする。`Closes` はマージの時に Issue を completed で閉じるので、rebuild・実機などマージの後の確認が残る Issue も、調整役が close と親の更新を行うボードの子も、確認や調整役の close より先に閉じる。`planning-parallel-issues` は先行の子が `state_reason=completed` で閉じたことを後続の子の着手条件にするので、ボードでは後続の子が早く着手できる状態になる。PR 本文の Issue の指定を、この 2 つの場合は `Refs #N` にし、残りの確認を記録する。

## 着手時の確認

1. Issue の「反映先」は、PR #136 に入れるか別の PR にするかを利用者が決めるとしていた。PR #136 は 2026-10-17 にマージ済みで、利用者がこの Issue を `/issue-to-pr` で指示したので、別の PR で直す
2. 今の文面で同じことが起きた: PR #253（`--merge` の run、2026-10-24）は `Closes #251, #252` で、マージと同時に 2 つとも completed で閉じた。#251 の検証には「実際の rebuild で、導入と再実行を確かめ、結果をこの Issue に記録する」があり、残りの確認は閉じた後のコメントに手で書かれた
3. `finalize.py` が閉じるのは、PR の `closingIssuesReferences`（本文の `Closes #N` などで GitHub が PR に結び付けた Issue）だけである（`closing_issues`）。`Refs #N` にすれば、`--merge` でも Issue は開いたまま残る
4. `planning-parallel-issues` は、子の close を誰が行うかを決めていない（調整役が親の実行マップと公開台帳を更新する）。ボードの運用では、子の close と親の更新をマージの後に調整役が行っている（PR #106 の本文）
5. `finalize.py` が merge commit の照合で止まったときの、`Closes` による GitHub の自動の close は、pr-review-fix-loop の最終報告（`merge_parent` の項）と review-fix-planning の `references/execution.md` の 3.5 節に書かれている（どちらも #138 を参照）。issue-to-pr の `--merge` の報告は pr-review-fix-loop の最終報告に従うので、この場合の報告は今の文面で足りる
6. PR #266 の評価で、(i)（open の Issue に、マージ済みの `Refs` の PR があり、最後のコメントが「rebuild の後に確かめる項目」の一覧）は、どちらの版でも 3/3 に届かなかった（条件付きで止まったのは `115f7c3` で 2/3、PR #266 の版で 1/3）。2 章の 6 が止まる条件にするのは open の PR だけで、マージ済みの PR が残した Issue を worktree の前に確かめる手順が無い。PR #266 の作業は、この Issue が `Refs` を増やすので、新しい Issue を作らずにここへ記録した

## 変更の内容

`.agents/skills/issue-to-pr/SKILL.md`:

1. 5 章の PR 本文の Issue の指定を、次の対応にする（`Closes` はマージの時に Issue を completed で閉じ、マージの後の確認や調整役の close を待たない）
   - Issue が `TARGET_REPO` と別のリポジトリにある: `Refs <Issue の URL>`（今のとおり）
   - Issue が `TARGET_REPO` にあり、マージの後でなければ確かめられない項目（rebuild、実機、`resoloop` の導入など）が受け入れ条件・検証に残るか、ボードの子（2 章の 7）である: `Refs #N`
   - Issue が `TARGET_REPO` にあり、どちらでもない: `Closes #N`
2. マージの後でなければ確かめられない項目が残るときは、Issue の指定に関係なく、その項目を PR 本文・最終報告と、run の最後（`--merge` のときはループの終了の後）の Issue のコメントに書く
3. 5 章のボードの子の項に、子の close と親の更新はマージの後に調整役が行うことを書く
4. 5 章の「`--merge` のとき」の結果の表の `no_fix_needed` に、`Refs #N` にした Issue は `finalize.py` が閉じないので、開いたままであることとその理由（残りの確認、ボードの子の調整役の close）を書くことを足す
5. 2 章の 6 の止まる条件に、同じ Issue のマージ済みの PR があり、本文・コメントから PR にする作業が残っていないと分かる（残りがマージの後の確認だけ、など）場合を足す。その PR の URL と残りの確認を報告する。「停止時の報告」の停止条件にも足す

`.agents/skills/issue-to-pr/evals/`: `scenarios.json` に (pa)〜(pd) を足し、`validation.md` に評価の結果を書く。

## 対象外

- `finalize.py`、pr-review-fix-loop、review-fix-planning の `references/execution.md`、`planning-parallel-issues` の変更（着手時の確認 3〜5 のとおり、今の挙動と文面で `Refs` を扱える）
- `finalize.py` が止まったときに、`Closes` で閉じた Issue を開き直すこと（helper は開き直さない。3.5 節）
- マージの後の確認を誰がいつ行い、いつ Issue を閉じるか（利用者か調整役が行う。このスキルは確認の項目を記録するだけ）
- マージの後の確認があるかを helper で機械的に判定すること
- 文書専用の PR の本文（今のとおり `Refs <Issue の URL>`）

## 受け入れ条件

1. 次の 3 つの場面で、PR 本文の Issue の指定が期待どおりになる（比較の版の行動比較で 3/3）。Issue の受け入れ条件 1
   - (pa) 同じリポジトリの Issue で、受け入れ条件・検証に rebuild の後の確認が残る: `Refs #N`、確認の項目を PR 本文・最終報告・Issue のコメントに書く
   - (pb) ボードの子: `Refs #N`、close と親の更新は調整役
   - (pc) 同じリポジトリの通常の Issue（`.devcontainer/` のスクリプトを直すが、受け入れ条件はこの run のテストで確かめられる）: `Closes #N`
2. (pd) `--merge` で、rebuild の後の確認が残る Issue のループが `no_fix_needed` でマージまで終わったとき、Issue を開いたまま残し、最終報告と Issue のコメントに残りの確認を書く（比較の版で 3/3）
3. PR #136 の (a)〜(j) の結果が変わらない（Issue の受け入れ条件 2）。(a)〜(h)・(j) は今の `evals/scenarios.json` の期待どおり 3/3。(i) は変更の内容 5 で、期待どおり 3/3 を目指す（今の版では分かれる。着手時の確認 6）

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | PR 本文の Issue の指定を、別のリポジトリ → `Refs <URL>`、同じリポジトリでマージの後の確認が残るかボードの子 → `Refs #N`、ほかは `Closes #N` の対応にする（変更の内容 1） | (a) 同じリポジトリでも常に `Refs` にし、確認の後に閉じる。(b) `Closes` のまま、マージの後にコメントするか開き直す | Issue の直し方の案のとおり。(a) は、`--merge` で `finalize.py` が通常の Issue を閉じなくなり、`--merge` の無い run は PR の作成で終わるので、通常の Issue を閉じる人がいなくなる。(b) は、開き直すまでの間に Issue が completed に見え、ボードでは後続の子が選ばれうる。`Refs #N` なら、`finalize.py` も閉じない（着手時の確認 3） | 委任: `/issue-to-pr #138 --merge --max-cycles 3` の推奨案での決定 |
| D2 | 条件を「マージの後でなければ確かめられない項目が受け入れ条件・検証に残る」にする（rebuild・実機・`resoloop` の導入は例） | Issue の文面どおり「マージの後の確認がある」 | 問題は、確認が済む前に閉じることである。この run の中で済ませた確認（worktree の版での実機の確認など）は残らないので、閉じてよい。別のリポジトリの Issue と条件が重なるときに `Refs #N` が別のリポジトリの番号を指さないよう、条件は `TARGET_REPO` にある Issue に限る | 委任: 推奨案での決定 |
| D3 | 残りの確認は、PR 本文・最終報告と、run の最後（`--merge` のときはループの終了の後）の Issue のコメントに書く。Issue の指定に関係なく書く | Issue の文面どおり、最終報告と Issue のコメントだけ | PR 本文に `Refs #N` の理由が無いと、レビュアーと利用者が指定の誤りと見分けられない。直近の PR（#106・#107 など）も本文に理由を書いている。ループの後に書くと、マージの結果と一緒に記録できる（#251 のコメントと同じ形） | 委任: 推奨案での決定 |
| D4 | ボードの子は `Refs #N` にし、close と親の更新はマージの後に調整役が行うと 5 章のボードの子の項に書く。この run は閉じない | `Closes #N` のまま、調整役がマージの後に親を更新する | `Closes` だと、調整役が確かめて親を更新する前に、後続の子の着手条件（`state_reason=completed`）が満たされる | 委任: Issue の直し方の案 |
| D5 | `--merge` の結果の表の `no_fix_needed` に、`Refs #N` の Issue は開いたまま残り、その理由を書くことを足す | 1 章の `--merge` の説明も直す | 報告で食い違うのは結果の表の「関連 Issue は finalize の結果の state を書く」だけである。1 章の「関連 Issue の更新」は `finalize.py` の挙動のとおりで、直さなくても誤らない | 委任: 推奨案での決定 |
| D6 | 2 章の 6 に、マージ済みの PR があり PR にする作業が残っていない Issue で止まる条件を足す（変更の内容 5） | (a) 変えずに、別の Issue にする。(b) helper がマージ済みの PR を API で探して止める | D1 で、マージ済みの `Refs` の PR が残した open の Issue が普通になる（着手時の確認 6）。司令塔のセッションや利用者がその Issue で issue-to-pr を起動すると、今の文面では worktree を作ってから残りを整理しうる。(a) はこの PR が増やす場面を残す。(b) は、残りが確認だけかを本文とコメントから判断する必要があり、helper では決められない | 委任: 推奨案での決定。PR #266 の作業が、この Issue で扱うために #138 に記録した |
| D7 | `finalize.py`・pr-review-fix-loop・review-fix-planning・`planning-parallel-issues` は変えない | merge commit の照合で止まったときの扱い（3.5 節の既知の制限）も、この Issue で直す | 着手時の確認 3〜5 のとおり、今の挙動と文面で `Refs` を扱え、照合で止まったときの自動の close は pr-review-fix-loop の最終報告が既に扱う。Issue の反映先は `.agents/skills/issue-to-pr/SKILL.md` だけ | 委任: Issue の反映先 |
| D8 | pytest のテストは書かない | 文面の照合テスト | 変更は `SKILL.md` の文面だけで、コードを変えない。文面の照合は `AGENTS.md` の F に当たる。振る舞いは行動比較で確かめる | `AGENTS.md` の「テストの採用基準」 |
| D9 | 行動比較は、Claude Code の Agent ツールで起動した新しいサブエージェント（model `sonnet`）で、1 回の起動で 1 回答。(pa)〜(pd) は対照（`origin/main` の `c1fdc56` の `SKILL.md`）と比較（変更後）で各 3 回。(a)〜(j) は PR #266 の評価と同じ指示文（ファイルのパスだけ変える）で、比較の版で 3 回。(a)〜(h)・(j) のどれかが外れたら、切り分けのために対照でも 3 回取る | (a)〜(j) も最初から対照と比較で取る。回数を増やす | Issue の直し方の案と受け入れ条件のとおり。(a)〜(j) の今の版の結果は `validation.md` の #137 の節に記録済みで、`c1fdc56` の後の変更は 2 章の 6 に触れていない。本物のモデルを起動する確認なので、回数は Plan に書いた分に限る（`AGENTS.md` の「エージェント運用」） | 委任: 推奨案での決定 |
| D10 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3 は利用者の指定。雛形 `/workspaces/reso-world/.devcontainer/agent-runner.toml`、`config` は null、`assign` は空。inspect は `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正の implement は `claude-opus`、self-review と fix-check は `self`（fallback はどれも空）で、どれも雛形と個人設定の既定の適用 | ループ用のオプションを足す | 利用者が書いたループ用のオプションは `--max-cycles 3` だけで、ほかは足さない | 委任: `/issue-to-pr #138 --merge --max-cycles 3`。`check-options` は終了コード 0 |
| D11 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`（雛形 `/workspaces/reso-world/.devcontainer/agent-runner.toml`、個人設定 `/home/vscode/.config/agent-runner/config.toml`）。雛形の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #138 --merge --max-cycles 3`。`check` は終了コード 0 |
