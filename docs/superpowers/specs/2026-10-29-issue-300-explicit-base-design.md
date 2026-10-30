# issue-to-pr の明示 base 指定

## 管理・実行許可

- 状態: draft（実行許可と設計内容の承認は別）
- 対象: usaturn/create-reso-world #300
- 利用者の指示: `/skill:issue-to-pr #300 --assign inspect=claude-opus,devin-swe,pigod --merge`
- 許可範囲: 推奨案による設計・実装・検証・commit・push・PR、指定したレビュー修正ループの finalize によるマージ。
- この run の repository / remote / base: `usaturn/create-reso-world` / `origin` / `main`
- 取得した base SHA: `5dc093cc2ed6855fb15353d70c1e8bb3b12d2151`
- 作業場所: `/workspaces/reso-world/.worktrees/issue-300-explicit-base`
- 実装担当の検査結果: `assignment={agents:[self],fallback:[]}`, `self=true`（既定の適用）。
- ループ設定: 利用者指定 `inspect=[claude-opus,devin-swe,pigod]`、既定 `max_cycles=3`、fix implement は `claude-opus`、self-review / fix-check は `self`、fallback はすべて空。template は `.devcontainer/agent-runner.toml`、check-options の config は null。

## 意図と受け入れ条件

Issue の実装対象の `origin` に存在するブランチを `--base <branch>` または `--base=<branch>` で明示し、そのブランチの取得済み SHA から分岐して同じ base 宛てに PR を作る。未指定時は main。親 Issue / handoff が別 base を要求する場合は明示指定を必須にし、不一致では外部書き込み前に止まる。

Linux Dev Container、uv、Git、偽 gh とローカル bare remote で検証する。main と分岐した `feat/plugin-v2`（非 ASCII branch も代表例を確認）を用意し、main だけの内容が混入せず、base 固有の内容を失わないことを確認する。任意 remote・tag・commit 式への解釈、異なる checkout、base の移動、古い検証結果による公開・マージを防ぐ。

## 設計

### 入力と base helper

`resolve_issue.py` は `base`（未指定時 main）と `base_explicit` を既存の出力に追加する。Issue の参照の前後・等号形式を扱う。Git の branch 規則を使い、option、refs 名前空間、revision 式を branch として解釈しない。シェルの eval は使わない。

新規 `scripts/resolve_base.py` は `--checkout ROOT --repo OWNER/REPO [--base BRANCH] [--required-base BRANCH ...] [--expected-sha SHA]` を受け付ける。呼び出し側は base_explicit が真のときだけ --base を付ける。親・handoff にある required base をすべて渡す。repository の指定も矛盾していないことを呼び出し側が先に確認する。親 Issue / handoff の「統合先」「PR の向き先」「base」等の明示記述を controller が全文から意味で読み取り、根拠となる URL またはファイルと指定値を記録する（自然文の自動抽出 helper は作らない）。関連例・過去の記録を今回の指定と混同せず、複数の指定が矛盾する、または確定できない場合は停止する。

helper は追跡対象 checkout のルート、対応 repository と origin の fetch/push URL の一致を検証し、Git の環境変数による別 checkout 選択を避ける。GitHub の認証値を出力しない。完全な `refs/heads/<branch>` を取得し、remote の観測と取得した commit が一致した場合だけ `{repo, remote, branch, ref, sha}` を返す。remote は origin 固定。--expected-sha は捕捉済み SHA と違う場合に失敗する。ブランチ・worktree・PR を作る helper にはしない。

### 分岐・検査・公開

SKILL.md は helper が確定した SHA をコード用 worktree の分岐元とし、差分もその SHA を基準にする。worktree 直前・検証前・push 直前・PR 作成直前に repository / origin / branch / SHA を再確認する。base が移動したら未検証の組み合わせで続けず停止する。自動 rebase / reset / fork main 同期はしない。

`scripts/scan-before-push.sh` に任意の `--expected-base-sha SHA` を追加する。取得した base が指定 SHA と違えば検査成功を返さず、検査後にも remote の同じ heads ref が動いていないことを確かめる。既存の Gitleaks の設定・除外禁止・版検査・未公開範囲・成功時 HEAD SHA だけを返す仕様は維持する。既定の呼び出しとの互換性を保つ。

PR 作成には確定した branch 名を `--base` に渡し、作成後の `baseRefName`・base の SHA を確認する。GitHub 上の他者の更新をローカル操作と一括でロックできるとは保証しない。各境界で観測した移動は停止として報告し、PR 後のマージには後段の finalize の検証を必ず使う。PR 作成後に移動を見つけても PR を自動で閉じたり branch を消したりせず、公開済み URL と観測した差異を報告して停止する。

外部コードの文書は独立して create-reso-world / origin / main の SHA を取得する。文書用 worktree・scan・PR へコードの base を流用しない。同一 repository の場合はコードと文書を同じ PR に含める。

### マージと停止条件

後段は実 PR の base を取得する既存 review-fix-planning / finalize を維持する。HEAD 一致、base 移動、merge 第1親、CI の守りを弱めない。統合ブランチを使う代表テストでこの経路を確かめ、既存 base 移動等のテストを重複して増やさない。

main 以外への PR の `Closes` は GitHub が default branch へのマージ時のみ自動 close する点を明記し、未指定 --merge の終了範囲を変えない。既存 Refs / Closes の選択条件は維持する。

## 決定記録（Approaches）

| 項目 | 選択した案 | 検討した別案 | 理由 / 委任・停止条件 |
|---|---|---|---|
| base 確認 | 対象決定後の専用 helper | Issue resolver 内で fetch、手順文だけ | Issue repository とコード repository を混同しない。通常設計の委任による選択 |
| base 移動 | 固定 SHA との照合で停止 | 自動取り込みと再検証 | 対象の差し替えや未検証マージを避ける。停止は安全境界 |
| scan | optional expected SHA を追加 | 別の scan 実装を複製 | 検査範囲・設定を一元化し既存呼び出しを保持 |
| 後段ループ | 実 PR base の既存 guard を再利用 | 要求 base を全 helper に重複保持 | 既存実装は branch 非依存。代表テストで確かめる |
| 実行 | SDD、3 Task を同期で直列実行 | すべて inline | 入力 helper・scan・統合手順の責務を分けてレビュー可能 |
| スキル検証 | 旧手順と新手順の実行シナリオ比較 | 有料モデルでの pressure テスト | Issue は有料モデルのテスト起動を禁止。ローカル Git と偽 CLI に限定し、モデルの行動評価と称さない |

## 対象外・禁止

- 統合ブランチ新設、fork main の同期/reset/force push/削除、他者 worktree 変更。
- プラグイン機能 #98〜#100、キュー #242、ワールド cwd 対応、対象 repository / remote 拡大。
- テスト目的の実 GitHub 書き込み、実際の別 Issue 実装、有料モデル起動、新規 Actions。
- 今回の PR 自身の指定されたレビュー修正ループはテストではなく公開後の作業として実行する。

## 検証

恒久テストは S の対象取り違え・未検証公開・秘密検査範囲に限る。単なる argparse / 文言 / 一覧の固定照合は追加しない。既存正常対照と安全テストを再利用する。README の非ワールド検証3入口、diff check、最後のブランチ全体レビューを行う。

## 実行記録（2026-10-30、公開前）

- 実装: `c8a681d`（入力/base helper）、`e3e6a36`（scan pin）、`50d6d24`（手順統合）。Task 3 のレビューで別シェルのfail-fast欠落を実Git/偽CLIで再現し、`350d78a`で修正・限定再レビュー合格。
- 全体レビュー: `5dc093c..350d78a`。4件を`e3fb308`で1回の修正にまとめ、限定再レビューですべて対応済み、新規不具合なし。GIT_*を除いたhelperと継承するpushの環境差は、ローカルbareの誤送信先refで再現した。各手順の隔離環境を一致させ、代表Sテストでコード/文書両方の正しい送信先・PR照合と誤送信なしを観測。
- 保存/再開: 実手順を新しいBashで実行し、正常系成功・base移動時停止・公開済み資源保持を確認。runner用IMPLEMENT_SESSIONとrun全体のSESSIONの参照/削除範囲を構造確認。文言の固定テストは追加していない。
- 入力/対象: 実Gitのmain/非ASCII統合branchと独立したSHA/内容を比較。origin不一致・required base矛盾・別ref・移動・GIT_*による取り違えを拒否する既存Sテストと正常対照が通過。allowlistを確認できていなかった重複ケースは削除。
- 検査/公開: 実Git範囲と偽Gitleaksの記録、実行手順からの偽gh PR作成・読取で同じbase/SHAを確認。外部コードの統合branchと文書mainを独立に観測。scan前/scan中/PR前の移動と作成後base不一致の停止を確認。finalize代表正常例を非mainに変更し、既存拒否ガードを再実行。
- 最終修正のcovering141・全pytest1255はexit0。記録は親checkoutの`tmp/agents/issue-300.vmbh4kha/`内のtask/branch report・ログ。最後の文書commit後のREADME3入口はcontrollerが続けて実行し、HEAD/argv/exit/logとchecks-fileを保存する。push/PR/指定ループは未実施で、内容承認は記録しない。
- 本run自身は開始時のmain向けissue-to-pr手順を維持し、親checkoutのscanner/loopを使用する。開発した新手順をこのrunの公開に遡及適用しない。ここまでは公開前の記録。公開結果は次節に追記する。

## PR #301 レビュー修正・第1サイクル（2026-10-30）

### 入力・実行許可・採否

PR: https://github.com/usaturn/create-reso-world/pull/301 。レビュー対象は `dbfa04ed299919b0511f246dd4a3ced8e6b0aabe`、base は `5dc093cc2ed6855fb15353d70c1e8bb3b12d2151`。公開前の clean HEAD に対する README 3入口は24 scripts PASS、layout PASS、1255 passed、diff check exit 0。親 scanner が検査した同じ SHA を push 済み。証拠は既存 SESSION の controller-verification.json/checks.json と controller-final-*.log。

元の `--merge` 指示に基づく完遂であり、設計内容の承認とは扱わない。planner は `openai-codex/gpt-6-astra` / pi。loop run は `907057843bcf4fc8948eba3b8d627918`。実装は設定の `claude-opus`、自己レビューと fix-check は `self`、fallback は空。自己レビューはまだ0回、上限1回。

| レビューファイル | モデル / runtime | HEAD / 再実行 | loop の判定 |
|---|---|---|---|
| deepseek-v4.1-flash.md | deepseek-v4.1-flash / pi | dbfa04ed2999 / true | accepted |
| SWE-2-Max.md | SWE-2 Max / devin | dbfa04ed2999 / true | helper が指定した1回の再実行後 accepted |
| claude-opus-5-5.md | claude-opus-5-5 / claude-code | dbfa04ed2999 / true | rejected: awaiting_approval、exit 0、停止確認済み。保存成果は照合後に入力として読むが成功レビューとは扱わない |

全8指摘を5件に統合。解消済み0、対応する2件（出典3件）、対応しない3件（出典5件）。重大度や票数ではなく、現行 HEAD の事実と review-fix-planning の採否基準で決めた。

| 出典（すべて @dbfa04ed2999） | 区分 | 根拠・見直す条件 |
|---|---|---|
| deepseek-v4.1-flash#M-1、SWE-2-Max#L-1 | 対応する | (a) 認証用 GIT_SSH_COMMAND に依存する対応 origin の通信が停止する。ローカル SSH transport を使う同じ Git の直接操作は成功、helper は exit 2。秘密情報や実ネットワークは使わず再現。既存 review_target の remote 認証保持と同じ利用経路を守る |
| claude-opus-5-5#H-1 | 対応する | (a) Dev Container の zsh で手順が初手から bad substitution、worktree 未作成。bash 対照は同じ入力で公開まで成功。主要手順の停止 |
| claude-opus-5-5#M-1 | 対応しない | main の前進も安全停止するのは選択済みの設計。未検証の組み合わせの成功を避ける要求を維持する。自動追従や再捕捉はこの修正で追加しない。利用者が移動時の方針を明示変更したときに見直す |
| claude-opus-5-5#L-1、SWE-2-Max#I-1 | 対応しない | 記録項目の明示漏れであり、SESSION の確定値と実操作の base は保持される。記録の列挙だけを理由とする変更は採否基準の対象外。記録欠落による誤操作が再現するか、利用者がこの指摘を名指しで依頼したときに見直す |
| deepseek-v4.1-flash#L-1、claude-opus-5-5#I-1 | 対応しない | 旧 eval の停止理由の期待は不一致だが、現行手順の停止位置・公開対象は誤らない。現在の主要手順を止めるものではない。実際の採点誤りが主要処理を妨げると再現するか、名指しの依頼で見直す |

確認済み一覧: `reviews/usaturn/create-reso-world/#301-feat-issue-300-explicit-base/verified/dbfa04ed2999.json` と同名 Markdown。工程の記録は同ディレクトリの `dbfa04ed2999.planning.json`。修正セッションは `tmp/agents/review-fix-planning-pr301.kwgmhiu8/`。5件とも確認済みで未確認候補なし。挙動3件は隔離した現行 HEAD の5 probes（bash/zsh、main移動2経路、ローカルSSH）で検証、文書2件はコミット済み記述との静的照合。実 GitHub 試験書込み・他者 checkout の fetch・有料モデル行動評価は対象外のまま。

### 守る条件の設計・影響経路

今回の両問題は、前回の全体レビュー修正 `e3fb308` が追加したシェルの一律除去から生じた回帰（認証側の helper の一律除去自体は `c8a681d`）。「修正が生んだ回帰」に該当するため、7行だけを別の構文へ置換して終わらず、環境の扱いを全経路で見直す。

守る条件は「継承環境によって確認・読取・検査・書込の対象を変えず、既存の正しい transport 認証を remote 通信に保ち、bash と zsh で同じ停止・再開条件を持つ」。入力 JSON・捕捉した base/SHA・出力先 SESSION・後段の HEAD/base/第1親/CI ガードは変えない。以前の修正は読取と push の不一致だけを閉じ、認証境界とシェルの違いを経路に含めていなかった。

比較した案: (1) 7箇所と helper の個別修正は小さいが、認証方針の写しが再びずれる。(2) 環境方針を共通の定義に寄せ、各境界が同じ方針を使う案を推奨する。(3) bash 専用や認証変数非対応へ保証を狭める案は既存環境を切り捨てるため選ばない。具体的なコード構成は実装担当が決めるが、採用指摘の原文とこの条件を変えず、同期検証の観測結果を返す。

| 守る条件 | 経路 | 判定 | 変更前の挙動 | 比較する結果・検証 | 実行結果・証拠 |
|---|---|---|---|---|---|
| 正しい checkout/config の選択 | resolve_issue の Git 読取、require_tracked_cwd、branch検証、resolve_base のローカル読取 | 既に満たす・維持 | GIT_* を除去 | 既存 S の異なる GIT_DIR/CONFIG と正常対照、秘密を stderr に出さない | dbfa04e の既存関連検証は成功。6649f98 でも関連テストと全 pytest 1255 passed が成功し、fix-check で維持を確認 |
| remote 認証を保つ | resolve_base の ls-remote/fetch、前後の recheck | 修正する | 認証変数も消えて通信停止 | ローカル fake SSH/askpass の同じ入力で直接 Git と helper の成功を比較、注入された対象上書きは拒否 | dbfa04e のローカルSSHで停止を再現。6649f98 でローカル SSH の upload-pack/receive-pack と、実 Git の offline askpass の正負の対照が成功（`controller-probes.log`・`fix-check-evidence/`） |
| shell 非互換で開始不能にしない | PARENT_ROOT導出、input、capture、worktree、diff、publish、pr の7境界 | 修正する | bash のみの間接展開 | bash/zsh で同じ main/非ASCII統合branchと外部文書分離の通し手順、別シェル再開も含める | dbfa04e の bash成功/zsh停止を確認。6649f98 で bash/zsh と相互の再開を含む 15 プローブが成功。ただし再開時の scan の SHA の受け渡しの漏れを、自己レビューの M-1 で確認した（次節） |
| 検査と書込の対象を一致させる | scan subprocess、code/docs の push、gh PR作成/読戻し | 修正する・既存安全性維持 | 全 GIT_* を消すため誤送信は防ぐが認証を失う | 既存の GIT_CONFIG_COUNT 誤送信先注入 S テストと正常対照。正しいref/PRのみ、誤送信先ref無し | dbfa04e の S テスト通過。6649f98 で代表 S テスト（transport の設定の注入）と正常対照が成功し、代表ガードを外した変異で誤った SHA を検出 |
| base移動・失敗は後続公開を止める | fresh shell の recheck、scan前/中、PR前/後 | 既に満たす・維持 | 明示的な失敗伝播と strict mode | 既存の状態/副作用検証、固定base/SHAが変わらず未公開が保持される | dbfa04e のmain移動2経路はexit2/未公開。6649f98 でも同じ 2 経路が exit 2・未公開（プローブ） |
| 既存の独立した境界を保つ | review_target.git_environment、runnerの子、finalize | 対象外・変更しない | remoteのみ認証保持、runnerは独立した隔離 | これらの責務・既存ガードを今回のissue手順へ拡大変更しない | 読解で境界を確認 |

共有条件の統合担当は controller。担当別テストの成功だけで済ませず、base JSON→検査→正しい送信先/PR の観測と既存ガードの維持を照合する。採用した原指摘の本文は改変せず実装担当へ渡す。文書2件とbase移動の仕様は実装修正に含めない。

### 修正・検証計画

- 許可する変更は issue-to-pr の環境処理・実行手順と必要な同一責務の helper に限定。既存 scanner/finalize/runner の安全規則、remote/repository の範囲、base 移動の設計を変えない。
- zsh互換性と認証失敗は L（明示エラー）なので恒久テストを増やさず、一時的な実手順実行で確認する。環境隔離の S は既存の代表例を再利用し、守りが変わる場合だけその例を更新する。新しい文言・allowlistの固定値照合や重複テストは追加しない。
- 関連検証: issue-to-pr tests と finalize tests、scan の既存テスト、bash/zsh の通し手順、diff check。共通の環境処理を変更するなら、対象上書きを防ぐガードを1箇所だけ外した隔離対照で、その守りの負例が失敗することを確かめる。
- controller の統合確認後、README3入口と親 scanner の検査を通し、設定の自己レビュー/fix-checkを1回だけ行う。自己レビューの範囲はPR全体。新しい致命的指摘は採否を先に決め、必要な修正・検証を行い、再レビューは増やさない。
- 途中の修正を先に push しない。追加 240 分の ledger を継続し、予算超過時は未完了として引き継ぐ。

### 修正・検証の結果

- 実装: 設定の implement（claude-opus、runner の success、約 1003 秒）が `d7590a9`・`6649f98` を作り、controller が成果の tree の一致を確かめて取り込んだ。継承した `GIT_*` の方針を `scripts/git_env.py` にまとめ、ローカルの Git は全部除き、remote との通信とシェルのブロックは認証の 4 変数（`GIT_ASKPASS`・`GIT_SSH`・`GIT_SSH_COMMAND`・`GIT_TERMINAL_PROMPT`）を残す。7 つのブロックは bash と zsh で同じに動く書き方にした
- 検証: clean HEAD `6649f98` で README の 3 入口（24 scripts PASS / layout PASS / 1255 passed）と diff check が exit 0（2026-10-30 06:02:29–06:09:39 UTC）。controller の 15 プローブ（bash/zsh、相互の再開、main・非 ASCII の統合 branch、コードと文書の分離、偽 SSH、push 先の注入の防止、main の移動での停止）が成功。親 scanner も同じ HEAD で成功
- 修正の確認（fix-check、controller の openai-codex/gpt-6-astra、1069 秒）: 7 主張 holds、7 ファイル passed、文書の候補 250 件を判定、新しい指摘 0（`verified/6649f98c6736.fix-check.json`）
- 自己レビュー: 予約の後、controller の prepare の `--model-name` の誤りで開始前に失敗し、このサイクルは一度 `stopped` で記録した（PR のコメント 6516711526、loop run `907057843bcf4fc8948eba3b8d627918` は stopped で終了）。利用者の明示の指示で再開した結果は次節

### 自己レビュー（再開）と M-1 の設計の見直し

予約済みの自己レビューは、前任の司令塔（pi）が prepare の `--model-name` を誤ったため開始前に失敗した（試行・成果なし）。利用者は 2026-10-30T07:17Z に、予約済みの枠のまま、引き継いだ司令塔 claude-opus-5-5 / claude-code が PR 全体の自己レビューを 1 回だけ行うこと、致命的な指摘は直して検証だけを通し、push 後に新しいループで次のサイクルへ進むことを明示し、予算 240 分の追加を許可した。`run_roles.py` の 2 回目の呼び出しや予約の削除はしていない。

自己レビューは `reviews/usaturn/create-reso-world/#301-feat-issue-300-explicit-base/claude-opus-5-5-commit-6649f98c6736a32dea8378e3db2996d210363ded.md` に保存した（依頼の予算 20 分・保存 5 分のうち 437 秒）。active は Medium 1 件（M-1）。テストの一部・eval・Spec・Plan の全文を予算内に読めなかったため、Merge recommendation は Needs manual verification。修正の確認（fix-check）は前任が完了済みで、7 主張 holds・7 ファイル passed・新しい指摘 0。

| 出典 | 区分 | 根拠・見直す条件 |
|---|---|---|
| claude-opus-5-5-commit-6649f98c6736a32dea8378e3db2996d210363ded#M-1@6649f98c6736 | 対応する | (a) Claude Code・pi は各ツール呼び出しが別のシェルなので、5 章の publish → Issue の再確認 → pr を手順どおりに進めると pr は新しいシェルで動く。文書の読み戻しの規則（保存 JSON）では `CODE_SHA`・`DOC_SHA` を得られず、`gh pr create` の後に照合の前で止まり、`--merge` のループへ進めない（主要な処理の停止）。現行 HEAD で bash・zsh の両方で再現した |

**きっかけ:** 1（同じ守る条件の 2 回目）。別シェルでの再開は、`350d78a`（再開時に base の守りを保つ、Task 3 のレビュー修正）と第 1 サイクルの V-2（7 つのブロックの bash/zsh と別シェル再開）で直した条件である。M-1 はその表で漏れた隣の経路（scan の SHA の受け渡し）。`350d78a` はテストのハーネスに、SKILL.md に無い `declare -p … CODE_SHA` の持ち越しを足しており、文書の再開の経路を通っていなかった。

**守る条件:** 7 つのブロックが後のブロックへ渡す値は、シェルの状態ではなく `SESSION` のファイルを出所にする。別シェルで再開しても、保存したファイルから同じ値を得て、外部への書き込み（worktree・push・PR 作成）の前後の照合を同じ値で行う。出所が無い・空のときは、外部への書き込みの前に止まる。以前の修正（`350d78a`・V-2）は、base の値（JSON に保存済み）と fail-fast と構文だけを経路に含め、publish が決める scan の SHA の出所を含めていなかった。

| 守る条件 | 経路（値: 書く所 → 読む所） | 判定 | 変更前の挙動 | 確かめる assertion | 確かめる方法 | 実行結果・証拠 |
|---|---|---|---|---|---|---|
| scan の SHA を PR の照合へ渡す | `CODE_SHA`: publish の scan → pr の `gh pr view` の照合 | 修正する | シェル変数だけ。別シェルでは未定義で、PR の作成後に `set -u` で止まる | 新しいシェルで保存ファイルだけから再開して終了コード 0。`code-pr.json` の `headRefOid` が scan の SHA（push した SHA）と一致 | bash/zsh の一時プローブ。ハーネスから `CODE_SHA` の持ち越しを外した既存テスト | `7c8a16a`（担当の `8a34576` と同じ tree）。controller の一時プローブで、新しい bash/zsh から保存ファイルだけで再開した正例が終了コード 0、`headRefOid` が `code-sha.txt`・push した branch・HEAD と一致。担当の確認では、旧 SKILL.md と新しいハーネスの組み合わせで既存テスト 3 件が `CODE_SHA: unbound variable` で失敗し、新しい SKILL.md では通過 |
| 同上（文書） | `DOC_SHA`: publish の文書の scan → pr の文書の PR の照合（外部の対象） | 修正する | 同上 | 文書の PR の `headRefOid` が文書の scan の SHA と一致 | 外部の対象の既存テスト（ハーネスから `DOC_SHA` の持ち越しを外す） | 外部の対象の正例（bash/zsh）で、文書の PR の `headRefOid` が `docs-sha.txt` と一致し、pr create はコードと文書の 2 回（controller の一時プローブ。担当のプローブでは準備・publish・pr を 3 つの新しいシェルで実行） |
| 出所が無いときは外部への書き込みの前に止まる | pr ブロックの開始時の読み込み | 修正する | 未定義のまま `gh pr create` まで進み、作成後に止まる | 保存ファイルが無い・空なら非 0 で止まり、`gh pr create` が呼ばれない | bash/zsh の一時プローブ（ファイルを置かない負例と、置いた正例） | `code-sha.txt` が無い・空、外部の対象で `docs-sha.txt` が無いとき、bash/zsh とも非 0 で止まり、pr create は 0 回、`code-pr-url.txt` は作られない（controller 6 件、担当 12 件の負例） |
| base の値の受け渡し | `CODE_BASE_BRANCH`・`CODE_BASE_SHA`（capture → worktree・diff・publish・pr・`recheck_bases`）、`DOC_BASE_SHA` | 既に満たす | `code-base.json`・`docs-base.json` に保存し、文書の規則で読み戻す | 再開後の base の移動で PR を作らない。正しい base で PR を作る | 既存の `test_resumed_shell_stops_before_pr_creation_when_base_moved`・`test_documented_flow_pins_worktree_diff_scan_and_pr` | `7c8a16a` の全 pytest（1255 passed）に含めて通過。ハーネスは base の値と関数だけを持ち越す |
| Issue の入力の受け渡し | `issue.json`（input → capture） | 既に満たす | ファイルに保存 | 同上の通し手順 | 既存テスト | `7c8a16a` の全 pytest（1255 passed）の通し手順で通過 |
| PR の URL | `code-pr-url.txt`・`docs-pr-url.txt`（pr の中） | 既に満たす | 作成の直後に保存 | 作成後の base の不一致を一致と報告しない | 既存の `test_created_pr_retarget_is_not_reported_as_matching` | `7c8a16a` の全 pytest（1255 passed）に含めて通過 |
| 関数の定義し直し | `recheck_bases`（capture で定義 → 後続で呼ぶ） | 既に満たす | 文書の規則で、capture の関数の定義だけを実行し直す | 再開した pr で base の移動を検出して止まる | 既存の再開テスト | controller の一時プローブで、capture のブロックから取り出した `recheck_bases` の定義だけを新しい bash/zsh で実行し直して通過。既存の再開テストも全 pytest で通過 |
| `PARENT_ROOT` | 最初のブロックの導出 | 既に満たす | 同じ導出の再実行で同じ値になる | ― | 読解 | 読解で確認 |
| 既存の独立した境界 | scanner・finalize・runner、base の移動の設計、記録項目の列挙、旧 eval | 対象外 | ― | ― | ― | 変更しない |

**比べた直し方:**

1. 点の修正: publish に `CODE_SHA`・`DOC_SHA` の保存を足し、2 章の 3 の読み戻しの対象に加える。再開時の読み戻しはエージェントに任せたままになる
2. 条件を 1 か所で保つ（推奨）: publish が scan の SHA を `SESSION` のファイルに書き、pr ブロックは開始時にそのファイルから読む。同じシェルでも別シェルでも値の出所は同じファイルになり、出所が無ければ外部への書き込みの前に止まる。base の値は既に JSON が出所で、文書の規則で読み戻せる
3. 保証を狭める: publish と pr を同じシェルで続けて実行することを必須にする。Claude Code・pi は呼び出しごとに別のシェルで、既存の SKILL.md が別シェルの再開を約束しているため選ばない（利用者の指示もこの変更を委任していない）

**テストの方針:** M-1 は止まるときにメッセージ付きの非 0 の終了で現れる L なので、恒久のテストは足さない。既存のハーネスの `declare -p` から `CODE_SHA`・`DOC_SHA` を外し、既存の S のテストが文書の再開の経路を通るようにする（新しいテスト関数は足さない）。出所が無い負例と正例は一時プローブで確かめる。

**検証:** issue-to-pr のテスト・finalize のテスト・scan の既存テスト、bash/zsh の一時プローブ（正例・負例）、README の 3 入口（`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`）、`git diff --check`、親の scanner の検査。自己レビューの 2 回目はしない（この修正は再レビューしていない）。

**結論と再レビューの扱い:** 結論 1（修正して push）。M-1 は設定の implement（claude-opus、runner の success、562.5 秒、`stop_confirmed: true`）が `8a34576` で直し、controller が tree の一致を確かめて `7c8a16a` として取り込んだ。clean HEAD `7c8a16a` で README の 3 入口（24 scripts PASS / layout PASS / 1255 passed）と diff check が exit 0（2026-10-30 07:46:03–07:53:30 UTC、`tmp/agents/review-fix-planning-pr301.kwgmhiu8/controller-verification-2.json`）。scan の既存テストは担当の確認と README の入口で PASS。M-1 の修正は再レビューしていない（自己レビューは 1 回まで）。このサイクルの修正は完了とし、文書全体は issue-to-pr の規則のとおり draft のままにする。
