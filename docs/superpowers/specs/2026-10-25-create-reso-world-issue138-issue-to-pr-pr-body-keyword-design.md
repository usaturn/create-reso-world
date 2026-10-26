# Issue #138: issue-to-pr の PR 本文で、マージの後の確認が残る Issue とボードの子を `Closes` で閉じない

- 状態: completed
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
3. ボードの子の close と親の更新はマージの後に調整役が行うことを書く（5 章のボードの子の項ではなく、1 の対応の行に書いた）
4. 5 章の「`--merge` のとき」の結果の表の `no_fix_needed` に、`Refs #N` にした Issue の扱いを足す → 評価で振る舞いが外れなかったので書かなかった（D5）
5. 2 章の 6 の止まる条件に、同じ Issue のマージ済みの PR があり、本文・コメントから PR にする作業が残っていないと分かる（残りがマージの後の確認だけ、など）場合を足す。その PR の URL と残りの確認を報告する。「停止時の報告」の停止条件にも足す

`.agents/skills/issue-to-pr/evals/`: `scenarios.json` に (pa)〜(pe) を足し、`validation.md` に評価の結果を書く。

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
2. (pd) `--merge` で、rebuild の後の確認が残る Issue のループが `no_fix_needed` でマージまで終わったとき、Issue を開いたまま残し、最終報告と Issue のコメントに残りの確認を書く。(pe) 別のリポジトリが実装の対象で、マージの後の確認が残る Issue は、`Refs <Issue の URL>` のまま（`Refs #N` にしない）で、確認の項目を書く（どちらも比較の版で 3/3）
3. PR #136 の (a)〜(j) の結果が変わらない（Issue の受け入れ条件 2）。(a)〜(h)・(j) は今の `evals/scenarios.json` の期待どおり 3/3。(i) は変更の内容 5 で、期待どおり 3/3 を目指す（今の版では分かれる。着手時の確認 6）

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | PR 本文の Issue の指定を、別のリポジトリ → `Refs <URL>`、同じリポジトリでマージの後の確認が残るかボードの子 → `Refs #N`、ほかは `Closes #N` の対応にする（変更の内容 1） | (a) 同じリポジトリでも常に `Refs` にし、確認の後に閉じる。(b) `Closes` のまま、マージの後にコメントするか開き直す | Issue の直し方の案のとおり。(a) は、`--merge` で `finalize.py` が通常の Issue を閉じなくなり、`--merge` の無い run は PR の作成で終わるので、通常の Issue を閉じる人がいなくなる。(b) は、開き直すまでの間に Issue が completed に見え、ボードでは後続の子が選ばれうる。`Refs #N` なら、`finalize.py` も閉じない（着手時の確認 3） | 委任: `/issue-to-pr #138 --merge --max-cycles 3` の推奨案での決定 |
| D2 | 条件を「マージの後でなければ確かめられない項目が受け入れ条件・検証に残る」にする（rebuild・実機・`resoloop` の導入は例） | Issue の文面どおり「マージの後の確認がある」 | 問題は、確認が済む前に閉じることである。この run の中で済ませた確認（worktree の版での実機の確認など）は残らないので、閉じてよい。別のリポジトリの Issue と条件が重なるときに `Refs #N` が別のリポジトリの番号を指さないよう、条件は `TARGET_REPO` にある Issue に限る | 委任: 推奨案での決定 |
| D3 | 残りの確認は、PR 本文・最終報告と、run の最後（`--merge` のときはループの終了の後）の Issue のコメントに書く。Issue の指定に関係なく書く | Issue の文面どおり、最終報告と Issue のコメントだけ | PR 本文に `Refs #N` の理由が無いと、レビュアーと利用者が指定の誤りと見分けられない。直近の PR（#106・#107 など）も本文に理由を書いている。ループの後に書くと、マージの結果と一緒に記録できる（#251 のコメントと同じ形）。評価では、対照は自分の判断でコメントを書いたが、指定の規則を明示した版は 3 回とも書かなくなった（規定が無いため）ので、REFACTOR で文面にした | 委任: 推奨案での決定 |
| D4 | ボードの子は `Refs #N` にし、close と親の更新はマージの後に調整役が行うと 5 章のボードの子の項に書く。この run は閉じない | `Closes #N` のまま、調整役がマージの後に親を更新する | `Closes` だと、調整役が確かめて親を更新する前に、後続の子の着手条件（`state_reason=completed`）が満たされる | 委任: Issue の直し方の案 |
| D5 | `--merge` の結果の表と 1 章の `--merge` の説明は変えない | (a) 表の `no_fix_needed` に、`Refs #N` の Issue は開いたまま残り、その理由を書くことを足す（着手時の案）。(b) 1 章の説明も直す | 比較の版の評価で、3 回とも `Refs` の Issue を読み直して open と書き、最終報告から抜けなかった（2 回は表の文面が当てはまらないと指摘しただけ）。writing-skills の「対照が失敗しなければ文面を書かない」に従う。1 章の「関連 Issue の更新」は `finalize.py` の挙動のとおりで、直さなくても誤らない | 委任: 推奨案での決定（Plan の Task 3 の Ruling） |
| D6 | 2 章の 6 に、マージ済みの PR があり PR にする作業が残っていない Issue で止まる条件を足す（変更の内容 5） | (a) 変えずに、別の Issue にする。(b) helper がマージ済みの PR を API で探して止める | D1 で、マージ済みの `Refs` の PR が残した open の Issue が普通になる（着手時の確認 6）。司令塔のセッションや利用者がその Issue で issue-to-pr を起動すると、今の文面では worktree を作ってから残りを整理しうる。(a) はこの PR が増やす場面を残す。(b) は、残りが確認だけかを本文とコメントから判断する必要があり、helper では決められない | 委任: 推奨案での決定。PR #266 の作業が、この Issue で扱うために #138 に記録した |
| D7 | `finalize.py`・pr-review-fix-loop・review-fix-planning・`planning-parallel-issues` は変えない | merge commit の照合で止まったときの扱い（3.5 節の既知の制限）も、この Issue で直す | 着手時の確認 3〜5 のとおり、今の挙動と文面で `Refs` を扱え、照合で止まったときの自動の close は pr-review-fix-loop の最終報告が既に扱う。Issue の反映先は `.agents/skills/issue-to-pr/SKILL.md` だけ | 委任: Issue の反映先 |
| D8 | pytest のテストは書かない | 文面の照合テスト | 変更は `SKILL.md` の文面だけで、コードを変えない。文面の照合は `AGENTS.md` の F に当たる。振る舞いは行動比較で確かめる | `AGENTS.md` の「テストの採用基準」 |
| D9 | 行動比較は、Claude Code の Agent ツールで起動した新しいサブエージェント（model `sonnet`）で、1 回の起動で 1 回答。(pa)〜(pe) は対照（`origin/main` の `c1fdc56` の `SKILL.md`）と比較（変更後）で各 3 回。(a)〜(j) は PR #266 の評価と同じ指示文（ファイルのパスだけ変える）で、比較の版で 3 回。(a)〜(h)・(j) のどれかが外れたら、切り分けのために対照でも 3 回取る | (a)〜(j) も最初から対照と比較で取る。回数を増やす | Issue の直し方の案と受け入れ条件のとおり。(a)〜(j) の今の版の結果は `validation.md` の #137 の節に記録済みで、その評価の後の `SKILL.md` の変更（`7da85d7`）は 2 章の 6 に触れていない。本物のモデルを起動する確認なので、回数は Plan に書いた分に限る（`AGENTS.md` の「エージェント運用」） | 委任: 推奨案での決定 |
| D10 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3 は利用者の指定。雛形 `/workspaces/reso-world/.devcontainer/agent-runner.toml`、`config` は null、`assign` は空。inspect は `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正の implement は `claude-opus`、self-review と fix-check は `self`（fallback はどれも空）で、どれも雛形と個人設定の既定の適用 | ループ用のオプションを足す | 利用者が書いたループ用のオプションは `--max-cycles 3` だけで、ほかは足さない | 委任: `/issue-to-pr #138 --merge --max-cycles 3`。`check-options` は終了コード 0 |
| D11 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`（雛形 `/workspaces/reso-world/.devcontainer/agent-runner.toml`、個人設定 `/home/vscode/.config/agent-runner/config.toml`）。雛形の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #138 --merge --max-cycles 3`。`check` は終了コード 0 |

## PR #270 のレビュー修正の判断（2026-10-26）

- 状態: completed（レビュー修正の判断とマージ前の検証を完了。内容が利用者に approved されたという意味ではない）
- 実行許可: 利用者の明示した `/skill:pr-review-fix-loop #270`。既存 PR のレビュー・必要な修正・push・条件を満たした場合のマージと関連 Issue の更新までを行う。新しい PR は作らない
- 司令塔: `openai-codex/gpt-6.1-sol`（pi）。loop のサイクル 1、PR 全体の判断の記録は round 2
- 対象 HEAD: `63884d8af6a9cc407e426a3a127dee802a9559f0`。前の判断は [round 1 の状況コメント](https://github.com/usaturn/create-reso-world/pull/270#issuecomment-6394574228)。同じ HEAD の全 10 判断（元の指摘は 11 件）を引き継ぎ、skip を変える新しい根拠は無かった
- 結論: **2 修正不要**。対応する 0、対応しない 9、解消済み 1。前回の停止は base `08255caa1acb076111326f2a961c1ec19c64a993` の mount の不整合で、今回の検証した base `7b9380075e9bae9617f5a6a441aafc3ddffedf14` との一時マージでは解消している
- 元の実装内容・D1〜D11 の設計判断は変更しない。今回は Spec だけに確認結果を追記する

### レビュアーの構成と確認済みの一覧

`reviews/usaturn/create-reso-world/#270-fix-issue-138-pr-body-keyword/` の全レビュー・候補一覧・確認済みの一覧・実行記録を入力にした。loop は `mode: reuse` で、レビュアーの追加起動・却下・失敗は無い。次の「同じ HEAD」は記録の `rerun: true` を意味し、今回の新規起動を意味しない。

| レビューファイル | 実際の担当 | モデル / ランタイム | レビュー HEAD | 同じ HEAD / 今回の起動 |
| --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus | claude-opus-5-5 / claude-code | `63884d8af6a9` | はい / 再利用 |
| `SWE-2-Max.md` | devin-swe | SWE-2 Max / devin | `63884d8af6a9` | はい / 再利用 |
| `deepseek-deepseek-v4.1-flash.md` | pi-deepseek | deepseek/deepseek-v4.1-flash / pi | `63884d8af6a9` | はい / 再利用 |
| `Grok-4.7.md` | cursor-grok47 | Grok 4.7 / cursor（runner の観測は Grok 4.7 256K Extra High） | `63884d8af6a9` | はい / 再利用 |

- 確認済みの一覧: 同ディレクトリの `verified/63884d8af6a9.json`（confirmed 9・not_reproduced 1・unverified 0）。PR・HEAD・4 件の入力との一致、各 JSON の validate とレビュー本文との check-pair を再確認した
- 工程の記録: 同ディレクトリの `verified/63884d8af6a9.planning.json`。以前の実行と時間の記録を残し、今回の判断・検証の時間を追記する
- 独立した読み取り専用の補助調査も行い、新しい致命的な欠陥は無かった。補助担当が全文を読まなかった evals は司令塔が全文を読んだ。PR の変更 5 ファイル、関連する Issue の参照・close・ボードの着手条件とテストを確認した
- `run_roles.py`: 未実行（修正不要）。設定の割り当ては implement=claude-opus、self-review=self、fix-check=self。実装・自己レビュー・修正の確認の役割は起動していない。修正後の自己レビューの回数は 0（修正が無いため）、設計の見直しも無し

### 全指摘の採否

| 指摘の参照 | 判定 | 根拠 |
| --- | --- | --- |
| `SWE-2-Max#M-1@63884d8af6a9` | 対応しない・引き継ぎ | 手順が無いことは確認した（確認済みの一覧 V-2）。ボードの子を Refs #N にして調整役が閉じるのは Issue #138 の直し方の案（利用者の指定した設計）で、子が開いている間は planning-parallel-issues の選択が先行の子を阻害要因として挙げるので、気付かずに誤った操作に進むことはない。手で閉じるまで後続が止まるのは設計の帰結で、子を閉じる手順の追加は Issue の反映先（issue-to-pr の SKILL.md）の外。致命的ではない |
| `deepseek-deepseek-v4.1-flash#M-1@63884d8af6a9` | 対応しない・引き継ぎ | 文面の事実は確認した（確認済みの一覧 V-1）。残りの確認は 207 行で Issue のコメントと最終報告に残るので、調整役はそれを読んで閉じる時期を決められる。この重なり（ボードの子でマージの後の確認もある）でも、base はマージの時に Closes で閉じていたので、変更前より早く閉じることはない。致命的ではない |
| `deepseek-deepseek-v4.1-flash#M-2@63884d8af6a9` | 解消済み・引き継ぎ | finalize の結果に Refs #N の Issue が入らないことは確かめた（closing_issues が [] を返す）が、SKILL.md:207（63884d8）が、マージの後の確認が残るときは Issue の指定に関係なくその項目を最終報告に書かせる。(pd) の行動比較 6/6（02e1bcb・db6c107）が、Issue が開いたままであることと確認の項目を最終報告に書いた。最終報告が落とす結果は現行 HEAD で再現しない（確認済みの一覧 V-8） |
| `deepseek-deepseek-v4.1-flash#M-3@63884d8af6a9` | 対応しない・引き継ぎ | 食い違いは確認した（確認済みの一覧 V-9）。受け入れ条件 2 を回帰が無いことと読むか、結果が同じことと読むかの仕様の判断。(a)〜(h)・(j) は 3/3 のままで、(i) は分かれていた結果が期待どおりになった（改善）。Issue のコメント（PR #266 の記録）は、この Issue が Refs を増やすので (i) をここで扱う前提を書いている。Spec の D6 と受け入れ条件 3 に判断を残した。マージしても誤った操作・結果は起きない |
| `claude-opus-5-5#L-1@63884d8af6a9` | 対応しない・引き継ぎ | 規則の組み合わせは確認した（確認済みの一覧 V-3）。照合が狭まって漏れが残るのは、Spec と PR 本文が Issue の受け入れ条件を落としたときだけで、issue-to-pr は受け入れ条件を整理して Spec に書き（4 章の 1）、create-reso-world の PR は Spec を載せてレビュアーが PR の主張として読む。手順どおりに進めた場合に誤った結果にはならない。要設計判断で、致命的ではない |
| `SWE-2-Max#L-1@63884d8af6a9` | 対応しない・引き継ぎ | 対応の範囲は確認した（確認済みの一覧 V-4）。この repo の commit の書き方（<種別>: <要約> (#N)）と issue-to-pr の Plan の commit message は keyword を #N に続けないので、手順どおりに進めた場合には起きない。致命的ではない |
| `SWE-2-Max#L-2@63884d8af6a9` | 対応しない・引き継ぎ | 重なりは確認した（確認済みの一覧 V-5）。同じ Issue に似たコメントが 2 件並ぶだけで、どちらも Issue を閉じず、誤った操作・結果にならない。致命的ではない |
| `deepseek-deepseek-v4.1-flash#L-1@63884d8af6a9` | 対応しない・引き継ぎ | 期待の不足は確認した（確認済みの一覧 V-10）。比較の 3 回は残りの確認も報告した。評価の期待の書き方で、スキルの振る舞いは変わらない。致命的ではない |
| `claude-opus-5-5#I-1@63884d8af6a9`（`SWE-2-Max#I-1@63884d8af6a9`を含む） | 対応しない・引き継ぎ | 食い違いは確認した（確認済みの一覧 V-6）。実装の位置は同じ Spec の変更の内容 3 と Plan の Task 2 の Ruling に書いてある。記録の書き方の指摘で、致命的ではない |
| `claude-opus-5-5#I-2@63884d8af6a9` | 対応しない・引き継ぎ | 理由の誤りは確認した（確認済みの一覧 V-7）。(i) は 2 章の 6 で止まり 5 章に進まないので、取り直さない結論は変わらない。記録の書き方の指摘で、致命的ではない |

### 検証と要件の照合

検証は 2026-10-26T06:33:26Z〜06:49:25Z に実行した。検証時の専用 worktree は HEAD `63884d8` で clean。一時マージは同じ HEAD に base `7b93800` を merge したツリーで、競合は無かった。merge は push せず、隔離 worktree とその親ディレクトリは検証後に削除した。

| 対象 | 実行コマンド | 終了コード・観測結果 |
| --- | --- | --- |
| HEAD 単体 | `bash .devcontainer/run-tests.bash` | 0、23 PASS |
| HEAD 単体 | `bash scripts/check-layout.sh` | 0 |
| HEAD 単体 | `uv run pytest tests/skills .agents/skills -q -p no:cacheprovider` | 0、685 passed |
| HEAD + base `7b93800` | `bash .devcontainer/run-tests.bash` | 0、23 PASS |
| HEAD + base `7b93800` | `bash scripts/check-layout.sh` | 0（前回失敗した mounts の整合も通る） |
| HEAD + base `7b93800` | `uv run pytest tests/skills .agents/skills -q -p no:cacheprovider` | 0、685 passed |

- 同じ隔離ツリーで `finalize.closing_issues` の正常な対を実行し、空の closing 参照は `[]`、同じリポジトリの #138 の closing 参照は `[138]` になった。GitHub への書き込みはこの確認では行っていない
- scenarios.json の JSON 解析と 50 場面の ID の一意性、変更全体の `git diff --check` を確認した
- 要件の観測は既存の行動比較（(pa)〜(pe) は最終版で各 3/3、(a)〜(h)・(j) は 3/3、(i) は改善して 3/3）と文書・関連処理の照合を使う。実モデルを追加で起動していない。今回変えるのは本 Spec の記録だけで、評価した SKILL.md は変わらず、既存の行動比較の前提を変えない
- 未実施: REFACTOR 後の (a)〜(j) の取り直し、`Refs` の PR で pr-review が照合範囲を狭めるかの行動比較、実際のボードの子 × マージ後確認・`--merge` 等の組み合わせ、他ランタイムの行動比較。文書とコードで確かめた事実・採否と、これらの実運用の未確認を区別する
- テストの追加はしない。本 Spec の記録を固定文言で照合するテストは AGENTS.md の F。既存テストの実行・構造と参照の確認で代える。変更した安全ガードは無いのでガードの対照検証は対象外
- 公開直前に base と PR の head を読み直す。Spec だけのコミットを検査付きで push し、`finalize.py --spec-commit` によって同じ base と head を照合して最終化する。push・マージ・Issue 更新の結果と今回の正確な所要時間は、状況コメントと loop の記録に残す
