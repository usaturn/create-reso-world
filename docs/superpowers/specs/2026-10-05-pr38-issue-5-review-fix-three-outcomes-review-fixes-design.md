# PR #38 issue-5-review-fix-three-outcomes のレビュー指摘の選別と修正

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/38
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `feat/issue-5-review-fix-three-outcomes`
- 指摘を検証した HEAD: 1 回目 `9685ca60b09bfcd9186dea0e28eee76625d7549e`、2 回目 `e344d2c12e810f5fce5019a4b670fa8c545a1d70`
- 入力: `reviews/#38-feat-issue-5-review-fix-three-outcomes/` 配下の全ファイル（1 回目 4 ファイル、2 回目 5 ファイル）
- 作成日: 2026-10-05
- 結論: 1 回目は **1（修正が必要）**。致命的な指摘 2 件（C-H1、O-M2 と同じ原因の D-L2）を直し、既存 PR へ push した。2 回目は **2（修正が不要）**。`e344d2c` に対するレビューに致命的な指摘は無く、修正せずにマージする（9 章）
- 状態: completed（2026-10-05。2 回目の選別・検証まで完了。push・状況コメント・マージ・Issue 更新の結果は PR のコメントに書く）
- 実行許可: 2026-10-05 の利用者の依頼（1 回目・2 回目とも同じ文面）。PR とレビュー結果を確認して修正要否を三択で確定し、修正が必要なら推奨案で修正・検証・PR 全体の再レビュー（自己レビューは 1 回まで。複数のサブエージェントに別々の観点で同時に担当させてよい）を経て push する。修正が不要なら確認・検証を完了し、最終の状況コメントを投稿してマージし、関連 Issue を更新する。致命的な指摘だけを直し、同じ原因の箇所は PR の差分外も直す。`pr-review` は使わず、専用の worktree で作業する
- 作業場所: 既存の worktree `.worktrees/issue-5-review-fix`（PR の head ブランチを checkout 済み、未コミットの変更なし、HEAD が PR の head と一致）を専用の worktree として使った（1 回目・2 回目とも）
- 関連: 設計 `docs/superpowers/specs/2026-10-05-issue-5-review-fix-three-outcomes-design.md`
- 構成: 1〜8 章は 1 回目（`9685ca6`）の記録、9 章は 2 回目（`e344d2c`）の記録

## 1. レビュー入力

| ファイル | 対象 HEAD | 指摘 | 判定 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `9685ca60b09b` | Medium 2・Low 1 | Approve |
| `SWE-2-Max.md` | `9685ca60b09b` | Medium 1・Low 3・Info 3 | Approve |
| `deepseek-deepseek-v4.1-flash.md` | `9685ca60b09b` | Low 2 | Approve |
| `openai-codex-gpt-6.1-sol.md` | `9685ca60b09b` | High 1 | Request changes |

対象 HEAD はすべて、選別時点の PR の head（`gh pr view 38 --json headRefOid`）と同じである。base（`origin/main`）は `a6e2c41` で、PR の分岐点から進んでいない。

## 2. 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 3（C-H1、O-M2、D-L2。O-M2 と D-L2 は同じ指摘） |
| 対応しない | 10 |

判定は、致命的かどうか（秘密情報の露出、データの消失、了承の無い操作・誤った対象への操作、手順どおりで誤った結果・主要な処理が止まる、セキュリティ）と、現行 HEAD での確認で行った。重大度ラベル・票数・Approve では決めていない。

### 2.1 全指摘一覧

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| C-H1（Codex High） | 手順 2 が祖先の確認でリポジトリを 1 件に絞るため、rebase の後に別リポジトリの同番号 PR を選び得る | **対応する** | 誤った対象への push・マージ。一時リポジトリで再現した（上流 PR の rebase 後に fork の別 PR だけが条件を満たす。逆向きでは上流 PR が選ばれ、結論 1 でその head へ push する）。発生条件の実例もある: 上流 #4 と fork #4 は番号が同じで履歴が重なる、レビュー後に `fix/slot-snapshot-dedup` が作り直された。PR の URL を渡さない `#N` 指定は「第1引数の解決」で支える使い方である |
| O-M2（Opus Medium） | 結論 3 で draft の Spec を PR の head ブランチにコミットすると、以後の完遂がその PR で毎回結論 3 になる | **対応する** | 主要な処理が止まる。一時リポジトリで再現した: Spec を書いた後の結論 3（head の更新、または一時的な API 障害）で Spec のコミットがローカルブランチに残り、2 回目以降は「専用の worktree」の手順 3 の `merge-base --is-ancestor` が失敗して止まり続ける。既存の worktree を再利用した場合（この PR 自身の配置）は、持ち主の push で draft の Spec が PR に入る。この環境では GitHub API の TLS タイムアウトが実際に起きている（このセッションと Codex のレビュー） |
| D-L2（DeepSeek Low） | 結論 3 の draft Spec のコミットで次回も結論 3 になる | **対応する** | O-M2 と同じ |
| O-M1（Opus Medium） | 要約・取捨選択の相談だけの依頼でも完遂に入り、マージまで進む | 対応しない | 仕様の是非。設計 D-1 で利用者が「計画で止めることを明示した依頼以外は完遂」と決めており、設計 9.3 でもこの点を対応しないとした |
| O-L1（Opus Low） | rebase 前の HEAD を対象とするレビューが残っていると、URL を渡しても手順 2 で止まる | 対応しない | 安全側の停止で、理由（レビューと PR の対応を確かめられない）を報告する。誤った操作は起きない。C-H1 の修正後も、`PR_REPO` を決めた後の照合として残す |
| S-M1（SWE Medium） | `allowed-tools` が Write/Edit を Spec の場所に限るため、コード編集で権限確認が出る | 対応しない | Claude Code の `allowed-tools` は事前承認だけでツールを制限しない（公式文書 "It does not restrict which tools are available"）。確認が出ても承認すれば進む。この行は PR で変わっていない |
| S-L1（SWE Low） | `gh pr checks` が check 0 件で exit 1 を返す場合の扱いが無い | 対応しない | usaturn/resoloop は fork で Actions が一度も動いておらず（`actions/runs` 0 件）、結論 2 では毎回この分岐に入るが、結果は「CI 基盤の障害として結論 3」か「従来どおり check 0 件でマージ」のどちらかで、誤った操作は起きない。resoloop の PR の head は結論 2 の途中で変わらない（Spec は create-reso-world 側に置く） |
| S-L2（SWE Low） | eval 8〜10 が実在リポジトリの近い PR 番号を使う | 対応しない | 選別中に usaturn/create-reso-world の PR #40（Issue #39 の対策、open）が作られ、eval 8 の番号は実在するようになった。それでも、前置きで実行・変更・GitHub への操作を禁じており、eval を自動で走らせる仕組みはリポジトリに無い。eval 8 のレビューディレクトリ `reviews/#40-docs-example/` も存在しない |
| S-L3（SWE Low） | 専用 worktree の再利用がメイン checkout を拾い得る | 対応しない | 再現したが、PR の head ブランチへの正しい操作で、片付けの対象にもならない |
| S-I1（SWE Info） | 結論 1 の「手順 2 をやり直す」が全体の手順 2 と紛らわしい | 対応しない | 表記の問題。誤読しても HEAD の再特定をやり直すだけ |
| S-I2（SWE Info） | Spec を completed でコミットした後にマージが失敗すると記録が不正確になる | 対応しない | 記録の書き方。操作の誤りは起きない |
| S-I3（SWE Info） | 設計 Spec の状態が approved のまま | 対応しない | 記録の書き方 |
| D-L1（DeepSeek Low） | head ブランチ名が `main` のときローカル main が動き得る | 対応しない | 動き自体は再現したが、実在の PR（create-reso-world 25 件、usaturn/resoloop 6 件、orange3134/resoloop 3 件）に head 名が `main` のものは無く、fork の main は上流の写しで差分のある PR を作れない |

## 3. 守る条件と影響経路

### 3.1 C-H1: 操作する PR はレビューした PR と同じであること

守る条件: 完遂で push・マージ・投稿する PR（`PR_REPO` と `PR_NUMBER`）は、レビューディレクトリが対象とした PR と同じであることが、URL などの識別情報で確定している。

| 経路 | 判定 | 確かめる方法 |
| --- | --- | --- |
| 手順 2: `external/resoloop/reviews/` で PR の URL が無い | 修正する: 祖先の確認で候補を絞らず、停止して URL を求める（完遂では結論 3） | SKILL.md の手順 2 の文面。一時リポジトリの再現（祖先の確認では誤った候補が 1 件だけ残る）に対し、新しい文面は候補の絞り込み自体をしない |
| 手順 2: ルートの `reviews/` で PR の URL が無い | 既に満たす: ルートの `reviews/` は usaturn/create-reso-world の PR のレビューだけを置く（`pr-review` の SKILL.md 82 行） | `pr-review` の保存先の規定を読んだ |
| 手順 2: PR の URL がある | 既に満たす: `PR_REPO` は URL から決まり、ディレクトリ名の番号との食い違いは「第1引数の解決」で止まる。祖先の確認は照合として残す | SKILL.md の「第1引数の解決」の最後の段落 |
| その他のリポジトリ（`CODE_ROOT`） | 既に満たす: 明示の `CODE_ROOT` と一致する remote 1 件が要る（ルート `AGENTS.md` の「リポジトリ境界」） | 共通 context helper の `select_remote` |
| `#N` がルートと `external/resoloop/` の両方に一致 | 既に満たす: 複数一致で停止する（「第1引数の解決」） | 実データで `#9` が 2 件に一致して止まることを確認した |
| 計画のみの流れ | 修正する: 同じ手順 2 の文面が適用される | 手順 2 は流れによらず共通 |
| 結論 2 の `--match-head-commit` | 対象外: 選んだ PR の head を照合するだけで、PR の同一性は手順 2 で担保する | — |
| `pr-review` のディレクトリ名にリポジトリが入らない | 対象外: `pr-review` は変えない。review-fix 側で URL を求めて担保する | — |

### 3.2 O-M2 / D-L2: 結論 3 の後にスキル自身の状態を残さないこと

守る条件: 結論 3 で止まった後、このスキルが作った状態（Spec だけのコミット、作ったローカルブランチ）が PR の head ブランチに残らず、次の完遂を止めたり、再利用した worktree の持ち主の push で PR に入ったりしない。ただし push していない修正は捨てない。

| 経路 | 判定 | 確かめる方法 |
| --- | --- | --- |
| 結論 3 一般（Spec を書いた後の停止。API 障害・権限・範囲外など）、create-reso-world の PR、修正なし | 修正する: Spec をコミットせず、変更を取り消して報告に分類と停止理由を書く | 一時リポジトリで新しい手順どおりに止め、2 回目の手順 3 が「ローカルブランチも無い」分岐に入ること |
| 結論 2 の手順 6 で Spec をコミットした後の reject | 修正する: commit 直後に記録した Spec のコミットが HEAD で、親が `HEAD_SHA`、作業ツリーが clean だと取り消す直前に確かめたときだけ `reset --keep "$HEAD_SHA"` で取り消す | 一時リポジトリで reject を起こし、取り消し後に `worktree remove`（`--force` なし）と `branch -D` が通ること |
| 結論 2 の手順 6 の commit 後の確認に失敗した（持ち主・別のセッションのコミットや stage が混ざった） | 修正する（自己レビューで追加）: 取り消さずに残して報告する | 一時リポジトリで持ち主のコミットの上に Spec をコミットし、条件が取り消しを拒むこと |
| `git add` 済みの新規の Spec をコミット前に止めた | 修正する（自己レビューで追加）: `restore --staged --worktree` で index と作業ツリーから戻す | 一時リポジトリで `status --porcelain` が空になること |
| 片付けのローカルブランチの削除条件 | 修正する: コミットを足さずに止まったときは、作成時の head と同じなら消す | 範囲外の PR の結論 3 の後に PR を rebase し、2 回目が止まらないこと |
| 再利用した worktree（持ち主がいる） | 修正する: 上の 2 経路で Spec のコミットを残さないので、HEAD が `HEAD_SHA` で未コミットの変更が無い状態に戻る | 一時リポジトリの再利用の構成で、停止後に `git status --porcelain` が空で HEAD が元の head であること |
| create-reso-world の PR で push していない修正がある | 修正する（報告）: 修正は捨てず、報告にブランチ・`status`・`log` と、次の完遂が止まる理由を書く | SKILL.md の結論 3 の文面 |
| 「Spec のコミットと確認用コピー」の完遂の項 | 修正する: 結論 3 の扱いを参照する形にした | SKILL.md の文面 |
| create-reso-world 以外の PR | 既に満たす: `DOC_ROOT` は文書用ブランチで、手順 3 は head ブランチだけを見る | SKILL.md の「Spec のコミットと確認用コピー」の手順 1 |
| 手順 3 の 2 番目の分岐（元からあるローカルブランチを fast-forward） | 対象外: このセッションが作ったブランチではないので消さない。rebase の後に止まるのは、このセッションの前から同じ | — |
| 計画のみの流れの draft コミット | 対象外: 承認後の実装で同じブランチから push される前提の別の流れである | — |

## 4. 修正内容（`.agents/skills/review-fix-planning/SKILL.md`）

- 手順 2: PR の URL が無いときに `PR_REPO` を決めてよいのはルートの `reviews/` だけにした。`external/resoloop/reviews/` で URL が無ければ停止して URL を求める。祖先の確認やディレクトリ名との一致で候補を絞らない。祖先の確認は `PR_REPO` を決めた後の照合として残す
- 専用の worktree の片付け: 手順 3 の `-b` で作ったブランチは、コミットを足さずに止まったとき（先端が作成時の head）も消す
- 結論 2 の手順 6: reject などで止まったときは、Spec のコミットを結論 3 のとおり取り消す
- 結論 3: 停止の理由に「`external/resoloop/reviews/` で PR の URL が無い」を明記し、「書き始めた Spec の扱い」を足した（create-reso-world 以外は文書用ブランチに draft でコミット。変更が Spec だけでなければ何も取り消さずに残して報告。変更が Spec だけなら、自分の Spec の変更だと取り消す直前に確かめたときだけ取り消す。報告に使う `git` の結果は片付けより前に集める）
- 結論 2 の手順 6: commit 直後に Spec のコミットの SHA を記録する（結論 3 の取り消しの条件に使う）
- 「Spec のコミットと確認用コピー」の完遂の項: 結論 3 の扱いを参照する形にした
- Red flags: 上の 2 つの規則に反する行動を足した

設計 Spec の冒頭に、この文書への参照と変わった決定事項（D-4・D-11・D-13・D-14 の結論 3 の扱い、9.3 の手順 2）を書き足した。設計 Spec の 3 章と 9 章は変更前の記録として残す。

選んだ案と他の案:

- C-H1: ディレクトリ名のブランチ部分と `headRefName` の照合、または「PR が片方のリポジトリにしか無ければそれを選ぶ」案もあった。前者はブランチ名の変換の規則を写す必要があり、上流と fork が同じブランチを使う運用（`docs/resoloop-fork-workflow.md`）では区別できない。後者は API の一時的な失敗を「PR が無い」と取り違えると誤った候補を選ぶ。URL を求めて止める案は推測の余地が無いので選んだ。利用者の通常の依頼は PR の URL を含む
- O-M2: 次回の実行で「スキル自身の draft のコミットなら合わせ直す」案もあった。他人の未 push の作業との区別を誤ると作業を消すため選ばなかった。draft を `docs_draft/` に退避する案は、`docs_draft/` を SKILL.md に書かない既存の検査（`test_spec_goes_to_docs_superpowers_specs_of_this_repository`）と、Spec を `docs/superpowers/specs/` に置く規則に反するため選ばなかった。停止した実行の Spec の内容（分類と停止理由）は報告に書く。次の実行は、中核原則どおり現行 HEAD で検証し直す

## 5. 検証

### 5.1 修正前（PR の head `9685ca6`、専用の worktree）

| コマンド | 結果 |
| --- | --- |
| `uv run pytest tests/skills .agents/skills -q` | 516 passed・1 skipped（exit 0） |
| `bash .devcontainer/run-tests.bash` | 27 本 PASS（exit 0） |
| `bash scripts/check-layout.sh` | PASS（exit 0） |

### 5.2 修正後（専用の worktree）

| 時点 | `uv run pytest tests/skills .agents/skills -q` | `bash .devcontainer/run-tests.bash` | `bash scripts/check-layout.sh` |
| --- | --- | --- | --- |
| `0f83ce5`（修正） | 516 passed・1 skipped（exit 0） | 27 本 PASS（exit 0） | PASS（exit 0） |
| `5bb5657`（自己レビュー後の修正） | 516 passed・1 skipped（exit 0） | 27 本 PASS（exit 0） | PASS（exit 0） |

各時点の前に、関連テスト `uv run pytest -q .agents/skills/review-fix-planning tests/scripts/test_superpowers_lifecycle.py` も通した（120 passed、52 subtests passed）。既存の固定文字列の検査で失敗したものは無い。新しいテストは書いていない（文面の変更で、固定値を確かめるテストは作らない方針）。

### 5.3 指摘の再現（サブエージェント 3 体に独立に委譲）

- C-H1・O-L1: 一時リポジトリで、上流 PR の rebase 後に祖先の確認が fork の無関係な PR だけを選ぶこと、逆向き（fork PR の rebase 後に上流 PR を選ぶ）も起きることを再現した。`gh pr list` で番号の重なりと履歴の重なりの実例（上流 #4・fork #4）を確認した
- O-M2・D-L2・D-L1・S-L3: SKILL.md の手順 2〜5 をそのままコマンドにしたスクリプトで状態遷移を再現した。O-M2 は head の更新・API 障害の両方で 2 回目以降が止まり続けること、再利用した worktree では `[ahead 1]` が残ることを確かめた
- S-L1・S-M1・S-L2: `gh pr checks` の check 0 件の終了コード、usaturn/resoloop の Actions の実行記録、`allowed-tools` の公式文書、eval の実行の仕組みを確かめた

## 6. 修正後の自己レビュー

`0f83ce5` に対して 1 回だけ行った。新しい文脈のサブエージェント 3 体に、別々の観点を同時に担当させた。各担当には、守る条件と影響経路の表（3 章）、修正の差分、実行した検証を渡した。`pr-review` スキルは使っていない。

| 観点 | 結果 |
| --- | --- |
| 反証 | 致命的 1 件: 結論 2 の手順 6 で commit 後の確認に失敗した経路でも、結論 3 が `reset --keep "$HEAD_SHA"` を無条件に指示していた。再利用した worktree の持ち主や同じ PR の別セッションのコミット・stage を消す（一時リポジトリで 3 通り再現。別セッションの例では reflog からも辿れなくなる）。旧版には無かった経路である。C-H1 側は致命的な指摘なし |
| PR 全体 | 致命的 1 件（反証と同じ指摘を独立に再現）。手順 2 の新しい文面、bash と zsh での断片、テストは問題なし |
| 検証の検出力 | 致命的になり得る 1 件: `git add` 済みの新規の Spec を「消す」だけだと index に残り（`AD`）、`-b` で作った worktree は外せず次の完遂が止まり続け、再利用した worktree では持ち主の commit で draft が PR に入る。新しい文面どおりの 8 通り（作成／再利用 × reject／コミット前の障害 × 新規／既存の Spec）は、旧版の対照で止まり、新版で止まらないことを確かめた。C-H1 は新しい文面で候補の絞り込み自体が無くなった |

判定と対応（`5bb5657`）:

- 反証・PR 全体の指摘: 対応する（データの消失）。取り消すのは、commit 直後に記録した Spec のコミットが HEAD で、親が `HEAD_SHA`、作業ツリーが clean だと取り消す直前に確かめたときだけにした。確かめられなければ何も取り消さずに残して報告する
- 検証の検出力の指摘: 対応する（主要な処理が止まる、他の worktree への混入）。追跡済みか `git add` 済みの Spec は `restore --staged --worktree` で戻し、追跡されていない新規のファイルだけを消す。取り消した後に HEAD と `status --porcelain` を確かめる
- 報告に使う `git -C "$MAIN_ROOT" log` を片付けの後に実行すると失敗する点（検証の検出力の補足）: 同じ箇所の手順どおりに進めると失敗する問題なので、「片付けより前に集める」を足した
- 対応しない（致命的でない）: 結論 3 の停止理由の一覧に「head ブランチが PR の head より古い」が無い（修正前からの止まり方で、停止は安全側）、push 済みの Spec の扱いの明記（何もしないで済むことを確かめた）、`docs/resoloop-fork-workflow.md` の「fork 内の PR はマージしない」と設計 D-12 の違い（利用者が D-12 で決めたこと）

自己レビューの後の修正（`5bb5657`）は再レビューしていない。一時リポジトリで、取り消しの 3 通り（`git add` 済みの新規の Spec、持ち主のコミットが下にある Spec のコミット、Spec だけのコミットの reject）を新しい文面どおりに実行し、それぞれ「clean に戻る」「取り消さずに残す」「clean に戻り、worktree とブランチを片付けられる」になることを確かめた。

## 7. 所要時間（UTC、作業ファイルの時刻からの概算）

| 区間 | 時刻 | 所要 |
| --- | --- | --- |
| レビュー 4 件・PR 情報・変更ファイル全文・関連処理の確認（並行して指摘の検証を 3 体に委譲、修正前の検証一式） | 13:06〜13:24 | 約 18 分 |
| 判定と修正（`0f83ce5`）、Spec の作成、検証一式 | 13:24〜13:36 | 約 12 分 |
| 自己レビュー（3 体を同時に） | 13:36〜13:46 | 約 10 分 |
| 自己レビュー後の修正（`5bb5657`）と検証、Spec の記入 | 13:46〜13:52 | 約 6 分 |

## 8. PR の説明との関係

PR の説明は、ブランチ全体のレビューで直した点として「レビューの対象 HEAD が PR の head の履歴に含まれることを確かめる」と書いている。この修正で、リポジトリの決め方を「URL が無ければ停止」に変えたので、PR の説明の該当箇所を直す。対応しない指摘のうち実在する制約（O-L1 の rebase 前のレビューでの停止、S-L1 の check 0 件）は、PR の説明の既知の制限に書き足す。

## 9. 2 回目の選別（`e344d2c`）

### 9.1 レビュー入力

| ファイル | 対象 HEAD | 指摘 | 判定 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `e344d2c12e81` | 0 件（前回の O-M1・O-M2・O-L1 を Resolved に移した） | Approve |
| `openai-codex-gpt-6.1-sol.md` | `e344d2c12e81` | 0 件（前回の C-H1 を Resolved に移した） | Approve |
| `SWE-2-Max.md` | `e344d2c12e81` | Medium 1・Low 3・Info 3（すべて前回 `9685ca6` で検出したものの継続） | Approve |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `e344d2c12e81` | Low 3・Info 1・未検証候補 2（新規。ID は CD-） | Approve |
| `deepseek-deepseek-v4.1-flash.md` | `9685ca60b09b` | Low 2（1 回目で選別済み） | Approve |

対象 HEAD はすべて、選別時点の PR の head（`e344d2c`）と同じか、その祖先である（`pull/38/head` を fetch し、`merge-base --is-ancestor` で確かめた）。base（`origin/main`）は `a6e2c41` のままで、PR の分岐点から進んでいない。

### 9.2 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 3（C-H1、O-M2、D-L2） |
| 対応する | 0 |
| 対応しない | 16 |

判定の基準は 1 回目と同じ（2 章）。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| C-H1（Codex High） | 祖先の確認でリポジトリを選び、別の PR を操作し得る | 解消済み | `0f83ce5` で、`external/resoloop/reviews/` では URL が無ければ停止し、祖先の確認で `PR_REPO` を決めない形にした（SKILL.md:54）。Codex が `e344d2c` で解消を確認した |
| O-M2（Opus Medium）・D-L2（DeepSeek Low） | 結論 3 の draft の Spec のコミットで、次の完遂が止まり続ける | 解消済み | SKILL.md:140・:211-219。一時リポジトリで、取り消しの 4 通り（`git add` 済みの新規、追跡されていない新規、追跡済みの変更、Spec だけのコミットの `reset --keep`）が clean に戻り、次の完遂が手順 3 の新規作成の分岐から入れることを確かめた。負例 5 通り（他者のコミットが下にある・上にある、他者の stage、他者の追跡されていないファイル、HEAD の移動）では何も消えない |
| O-M1（Opus Medium） | 要約・相談だけの依頼でも完遂に入る | 対応しない | 挙動は変わっていない。設計 D-1 で利用者が決めた仕様である（Opus も `e344d2c` で設計判断として Resolved に移した） |
| O-L1（Opus Low） | rebase 前の HEAD のレビューが残ると手順 2 で止まる | 対応しない | 安全側の停止。PR の説明の既知の制限に記載済み |
| S-M1（SWE Medium） | `allowed-tools` が Write/Edit を Spec の場所に限る | 対応しない | 公式文書（https://code.claude.com/docs/en/skills）は "It does not restrict which tools are available" としており、範囲外の Edit/Write は通常の権限確認に戻るだけで、止まらず誤った結果にもならない。この行は PR で変わっていない（導入は `414ff2c`） |
| S-L1（SWE Low） | `gh pr checks` が check 0 件で exit 1 | 対応しない | gh 2.101.0 で、create-reso-world の #38・#40 と usaturn/resoloop の 6 件が `no checks reported`（exit 1）を返した。この分岐に入るのは usaturn/resoloop の結論 2 だけで、結果は停止か check 0 件のままのマージのどちらか（後者は従来の運用と同じ。usaturn/resoloop の #1・#9 も check 0 件でマージされている）。既知の制限に記載済み |
| S-L2（SWE Low） | eval 8〜10 が実在する PR 番号を使う | 対応しない | #40 は実在する（open）。#41 と orange3134/resoloop #12 は存在しない。eval 8〜10 は前置きで実行・変更・GitHub への操作を禁じており、指定のレビューディレクトリ（`reviews/#40-docs-example/` など）も存在しない。`evals.json` を読むのはスキルの仕様を確かめるテスト（`test_review_fix_planning_skill_contract.py` の eval 5 の静的な照合）だけで、自動で実行する仕組みは無い |
| S-L3（SWE Low） | 専用の worktree の再利用がメイン checkout を拾い得る | 対応しない | 再現するが、commit・push は PR の head ブランチへの正しい操作で、片付けの対象にもならない（誤って実行しても git が拒否する）。到達条件は、`AGENTS.md` の「ローカルは常に origin/main」に反する状態である |
| S-I1（SWE Info） | 結論 1 の「手順 2 をやり直す」が紛らわしい | 対応しない | 表記の問題。誤読してトップレベルの手順 2 に戻ると、専用の worktree の手順 3 で修正の入ったブランチが「それ以外」に当たり、結論 3 で止まる（安全側。1 回目の根拠「HEAD の再特定をやり直すだけ」をこう改める）。検証を飛ばして push するには、:255 と :270 の両方を無視する必要がある |
| S-I2（SWE Info） | completed の Spec を push した後にマージが失敗する | 対応しない | 記録の書き方。Spec にはマージの結果を書かない設計（:255）で、何も消えない |
| S-I3（SWE Info） | 設計 Spec の状態が approved のまま | 対応しない | 記録の書き方。状態行を参照する処理・テストは無い |
| D-L1（DeepSeek Low） | head ブランチ名が `main` のときローカル main が動く | 対応しない | 1 回目と同じ。3 リポジトリに head 名が `main` の PR は無い（create-reso-world 26 件、usaturn/resoloop 6 件、orange3134/resoloop 3 件）。片付けで消すのは手順 3 の `-b` で作ったブランチだけで、既存のローカル main は消えない。fast-forward しても旧先端は祖先として残り、push は head 側の remote へ行く |
| CD-L1（DeepSeek Low） | 結論 1 の push 後の状況コメントの「現行 HEAD」が push 前の値になる。実装後だけの流れでは未定義 | 対応しない | 影響はコメントの記載だけ。push 後に古い `HEAD_SHA` を使う操作は無い（片付けの削除条件は「push した head の SHA」で `$HEAD_SHA` を参照しない。結論 3 の取り消しは条件が成り立たず何も消さない。結論 1 はマージしない）。push 後の SHA はテンプレートの「commit / push」の行に入る。実装後だけの流れで未定義になるのは、PR の前からの挙動（`a6e2c41` のテンプレートも同じ） |
| CD-L2（DeepSeek Low） | create-reso-world 以外の PR の結論 2 で、Spec が文書専用 PR へ公開されない | 対応しない | Spec は create-reso-world の文書用ブランチにローカルのコミットとして残り、消える経路は無い（片付けは `external/resoloop` 側だけを触る）。push しないことは `AGENTS.md` の既定（明示の指示があるときだけ push し、ローカルだけなら「公開未実施」と書く）と一致し、状況コメントのテンプレートでも「公開未実施」と書く。公開が遅れるだけである |
| CD-L3（DeepSeek Low） | 照合が共有の `FETCH_HEAD` に頼る | 対応しない | `FETCH_HEAD` は worktree ごとだが、メイン checkout で別の fetch が同時に入れば書き換わる。:127 は `HEAD_SHA` との等値判定なので止まる。:54 の祖先照合は誤って成立し得るが、`PR_REPO`・`PR_NUMBER` はその前に確定しており、後の worktree の作成・push・マージは `gh pr view` の `HEAD_SHA` に固定される。対象の PR は変わらず、最悪でも正しい PR に対して古いレビューを入力に進むだけで、各指摘は現行 HEAD で確かめ直す |
| CD-I1（DeepSeek Info） | eval 4 の `expected_output` が致命的の基準に合っていない | 対応しない | eval の文面の不揃い。`expectations` は更新済みで、eval を自動で実行する仕組みも無い |
| CD-U1（DeepSeek 未検証候補） | `gh pr edit --body-file` が並行した本文の編集を上書きする | 対応しない | PR の本文を書き換える経路はこの手順だけで、並行して本文を編集する運用は無い。手動の編集と重なっても、旧版は GitHub の編集履歴（`userContentEdits`）に残る |
| CD-U2（DeepSeek 未検証候補） | CI の確認が Spec の push より前にある | 対応しない | Spec を PR の head に push するのは create-reso-world の PR だけで、CI の確認は不要（Actions も停止中）。CI を確認する usaturn/resoloop では Spec を create-reso-world 側に置くので、確認後に head は変わらない |

PR 全体の点検（自己確認）でも、致命的な欠陥は見つからなかった。push・マージ・`reset --keep`・`restore`・`worktree remove`・`branch -D`・Issue の close・PR の本文の書き換えを 1 つずつ追い、誤った対象への操作やデータの消失にならないことを確かめた。致命的でない点として次を記録する（対応しない）。

- 結論 2 の手順 9 は、参照しているだけの Issue のリポジトリを限っていない。usaturn/resoloop の PR が上流の Issue を参照していれば、上流の Issue にコメントする（例: usaturn/resoloop#9 の "Refs orange3134/resoloop#5"）。実行許可の「関連 Issue の更新」の範囲内で、内容も事実どおりである
- 専用の worktree の手順 3 の fast-forward は、`HEAD_REPO` を照合する手順 4 より前に行う。手順 4 で止まっても、同名のローカルブランチは進んだまま残る（旧先端は祖先として残る）
- Red flags の「メイン checkout … で修正しようとしている」（:473）と、手順 3 の再利用（:137）の文面が食い違う。どちらに従っても、再利用か停止になる

### 9.3 検証

専用の worktree（`e344d2c`）で、スキルの変更に対する検証を通した。

| コマンド | 結果 |
| --- | --- |
| `uv run pytest tests/skills .agents/skills -q` | 516 passed・1 skipped（exit 0） |
| `bash .devcontainer/run-tests.bash` | 27 本 PASS（exit 0） |
| `bash scripts/check-layout.sh` | PASS（exit 0） |

検証後の `git status --porcelain` は空だった。base は進んでいないので、統合ツリーでの検証（結論 2 の手順 2）は要らない。create-reso-world は private で GitHub Actions を止めているので、CI の確認（手順 4）は対象外である。PR は usaturn/create-reso-world の open で draft でない PR で、マージしてよい範囲にある。

指摘の検証は、新しい文脈のサブエージェント 3 体に独立に任せた。

- git の挙動（CD-L3・D-L1・S-L3・O-M2 の解消）: git 2.55.0 の一時リポジトリで実験した
- GitHub・eval・権限（S-L2・S-L1・S-M1・CD-U1・CD-U2）: `gh` の読み取り、公式文書、GraphQL で確かめた
- 文面の流れ（CD-L1・CD-L2・CD-I1・S-I1〜I3）と、PR 全体の書き込み・削除の操作の点検

3 体とも、リポジトリと GitHub への書き込みはしていない。自己レビューは結論 1 の段なので行っていない。

### 9.4 結論と PR の説明

結論 2（修正が不要）。「対応しない」とした指摘の実在する制約は、PR の説明の保証と食い違わない（PR の説明は、状況コメントの HEAD の表記、文書専用 PR への公開、`FETCH_HEAD` の扱いについて何も保証していない）。O-L1・S-L1 は 1 回目に既知の制限へ書き足してある。PR の説明は変えない。

この記録のコミットだけを PR の head に fast-forward で push し、push 後の head を `--match-head-commit` に渡してマージする。

### 9.5 所要時間（UTC）

| 区間 | 時刻 | 所要 |
| --- | --- | --- |
| レビュー 5 件・PR の情報・共通 context・専用の worktree の確認 | 14:33〜14:37 | 約 4 分 |
| 指摘の検証の委譲（3 体を並行）、変更ファイルの全文・関連テストの確認、検証一式 | 14:37〜14:47 | 約 10 分 |
| 判定と記録 | 14:47〜14:52 | 約 5 分 |
