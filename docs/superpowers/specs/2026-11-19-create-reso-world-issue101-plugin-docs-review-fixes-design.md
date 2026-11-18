# usaturn/resoloop#32 プラグイン文書のレビュー修正 設計

## 管理・実行許可

- 状態: `completed`
- 対象 PR: https://github.com/usaturn/resoloop/pull/32（`feat/create-reso-world-issue-101-plugin-docs` → `feat/plugin-v2`）。関連 Issue: usaturn/create-reso-world#101（PR は Refs で参照し、close しない）
- 元の設計: `docs/superpowers/specs/2026-11-18-create-reso-world-issue101-plugin-docs-design.md`、計画: `docs/superpowers/plans/2026-11-18-create-reso-world-issue101-plugin-docs.md`（どちらも文書専用 PR usaturn/create-reso-world#469）
- 実行許可: 利用者が 2026-11-19 に `/pr-review-fix-loop https://github.com/usaturn/resoloop/pull/32 --assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_xhigh,pi_opendesign-go_deepseek4-flash_max,pi_alibaba_qwen4-max_max` を起動した。設定に無い `pi_opendesign-go_deepseek4-flash_max` は、利用者の回答で `pi_opencode-go_deepseek4-flash_max` に直した。PR 修正ループは review-fix-planning の完遂（この PR の承認済み実装修正、修正不要なら `usaturn/resoloop` の open で draft でない PR のマージ）を許可する。内容の承認（`approved`）ではない
- PR 修正ループ: run `0670efc4e5c145849606df697bc64186`、サイクル 1（判断の記録のサイクル 1。PR に前の記録は無い）
- planner: `claude-opus-5-5`（ランタイム claude-code）

## レビュアーの構成

| レビューファイル | モデル | ランタイム | agent_id | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `SWE-2-Max.md` | SWE-2 Max | devin | `devin_swe2_max` | `5b1a179c419c` | はい | Approve |
| `gpt-6.2-sol.md` | gpt-6.2-sol | pi | `pi_openai-codex_gpt6-sol_xhigh` | `5b1a179c419c` | はい | Needs manual verification |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash | pi | `pi_opencode-go_deepseek4-flash_max` | `5b1a179c419c` | はい | Approve |
| `qwen4-max-preview.md` | qwen4-max-preview | pi | `pi_alibaba_qwen4-max_max` | `5b1a179c419c` | はい | Approve |

- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/resoloop/#32-feat-create-reso-world-issue-101-plugin-docs/`
- 確認済みの一覧: `verified/5b1a179c419c.json`（mode cycle、confirmed 4・not_reproduced 0・unverified 0、coverage.remaining なし）
- 工程の記録: `verified/5b1a179c419c.planning.json`
- 修正と自己レビューの担当（`run_roles.py` の割り当て。雛形の既定のまま）: implement `self`、self-review `self`、fix-check `self`。自己レビューは `run_roles.py --phase self-review` の 1 回

## 全指摘と分類

| 判断 ID | 出典 | 位置（`5b1a179c`） | 確認 | 区分 | 根拠 |
| --- | --- | --- | --- | --- | --- |
| D-1 | `gpt-6.2-sol#M-1@5b1a179c419c` | `docs/PLUGINS.md:22,688-691`、`docs/PLUGINS.ja.md:22,688-691` | V-1 confirmed（実行） | 対応する | 下の「対応する項目」 |
| D-2 | `gpt-6.2-sol#L-1@5b1a179c419c` | `docs/PLUGINS.md:53-58`、`docs/PLUGINS.ja.md:53-58` | V-2 confirmed（実行） | 対応しない | 編集済みの既存プロジェクトでは `init` が `INIT_FILE_EXISTS`（終了コード 6）で止まるが、`ProjectInitializer` は書き込みの前に衝突をすべて調べるので、プロジェクトのファイルは変わらない（前後のハッシュが同じことを実行で確認）。手順 1 は「既存のプロジェクトを使うか、新しく作る」と書いており、止まった利用者は `init` を省けば先へ進める。データの消失も誤った結果も無い |
| D-3 | `gpt-6.2-sol#L-2@5b1a179c419c` | `docs/PLUGINS.md:266`、`docs/PLUGINS.ja.md:266` | V-3 confirmed（実行） | 対応しない | 組み込みの名前の `uix recipe describe`・`export` は `--project` を読まずに成功するが、組み込みのレシピはプロジェクトに依存しない（承認済み D-6）ので、出力は正しい。398 行が「`:` の無い名前は常に本体のレシピ」と書いている。プロジェクトの検証として describe の成功を使う手順は、ガイドにもツールにも無い |
| D-4 | `deepseek-v4.1-flash#L-1@5b1a179c419c` | `docs/PLUGINS.md:745`、`docs/PLUGINS.ja.md:745` | V-4 confirmed（実行） | 対応しない | `data` がリンクのとき、`plugin remove --yes` は拒否されずに成功するが、消すのはリンクだけで、リンク先は残る（実行で確認）。745 行の「たどらない」は成り立ち、338 行の「`data/` の中のリンクはリンクとして削除する」とも合う。list・コマンド・doctor は `PLUGIN_PATH_UNSAFE` を報告する。データの消失も誤った対象への操作も無い |
| D-5 | `fix-check#V-1@348c2884eb67`（修正後の自己レビューの fix-check） | `docs/PLUGINS.md:688`、`docs/PLUGINS.ja.md:688`（`348c2884`） | fix-check の V-1 confirmed（実行） | 対応しない | D-1 の修正で足した信頼の節の文は「doctor は各 tool の `executable` を `versionArgs` 付きで実行する」と書くが、`versionArgs` が空の tool と照合に失敗したプラグインの tool は起動しない。実際より多く起動すると書く向きの差で、利用者を危険な判断に導かない（起動するのに起動しないと読める箇所は無い）。同じ文書の Doctor の節（455 行）と作者向けの tools の節（569 行）は正しく書いている。データの消失・誤った対象への操作・安全の問題に当たらない |

件数: 解消済み 0 / 対応する 1 / 対応しない 4（D-5 は修正後の自己レビューで出たもの）。前のサイクルの判断は無い（PR に記録が無い）。

「対応しない」4 件（D-2〜D-5）は、ガイドの記述が実際と食い違う事実なので、PR の説明の既知の制限に条件と回避方法を書き足す（同じ論点が次のレビューで繰り返し挙がるのを防ぐ）。

## 要件対応

PR の約束と、元の Spec・Plan の条件のうち、今回の修正が関わるもの。

| 条件（出所） | 今回の修正方針 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 文書が D-1〜D-6 と 4 機能を「コードと実行結果に合わせて」説明する（PR 本文の変更概要、元の Spec 5 章「文書の内容」） | D-1 の記述を実装に合わせる | 概要と安全の節が、プラグインに由来するプログラムを起動する入口として、プラグインのコマンドと `doctor` の tools の検査の両方を挙げる | 修正後の本文を `PluginDoctorChecks`・`PluginToolProbe`・`PluginManifest` と照合し、V-1 の再現結果（下の表）と食い違わないことを確かめる |
| 信頼・ハッシュ・サンドボックスの違いを書き、防げるものとして書かない（元の Spec 5 章「防御範囲」、4.1 の 5） | 信頼の節の対象に tools の検査を足す。保証を広げも狭めもしない | 「導入では何も実行しない」は維持し、`doctor` が tools を起動することを、信頼の確認の対象として書く | 同上。ハッシュ・サンドボックスの節は変えない（`git diff` で確認） |
| 英日の見出しの順と内容が対応する（元の Spec 5 章「英日」） | 英日の同じ行を同じ意味で直す | 見出し 34 個の順と階層が英日で同じまま。直した 3 箇所の内容が対応する | `grep '^#'` で英日の見出しを比べる。直した行を英日で読み比べる |
| 文書の固定値テストは足さない（元の Spec 5 章「テスト」、E12） | テストを足さない | テストのファイルが変わらない | `git diff --stat` |
| 上流で変わった行と所有範囲の外の節を変えない（元の Spec 5 章「防御範囲」） | `docs/PLUGINS.md`・`docs/PLUGINS.ja.md` の 3 箇所だけを直す | 変更が 2 ファイルだけ | `git diff --stat` |

共有する条件: 英日の 2 ファイルが同じ前提（doctor の tools の起動）を述べる。統合担当は planner（このセッション）で、英日の読み比べと実装との照合を受け持つ。既存の Spec・Plan の不在は無い。

## 対応する項目: D-1（gpt-6.2-sol#M-1）

### 致命的である理由

(b) 事実誤認の記述で、そのとおりに進めると誤った結果になるもの。安全の説明として、ガイドの概要は「Plugin code runs only when you run one of its commands」、信頼の節は「Installing does not execute anything, but the first command does」と書く。実際は、`resoloop doctor` がプラグインのコマンドを呼ばなくても、manifest の tools ごとに `executable` を `versionArgs` 付きでプロジェクトのルートで、利用者の権限と環境で起動する。`executable` はセパレータの無いコマンド名に限られるが、`versionArgs` は任意なので、`sh -c ...` やパッケージの中のスクリプトを指せる。導入したプラグインを、コマンドを実行する前に確かめるつもりで `doctor` を実行した利用者（`resoloop init` が作るプロジェクトの `AGENTS.md` は、作業の前に `doctor` を実行するよう指示する）は、ガイドの説明に反して、確認前のプラグインのコードを動かす。発生条件は、プラグインを導入したプロジェクトで `doctor` を実行するという通常の使い方で到達できる。セキュリティ上の問題（信頼の境界の誤った説明）に当たる。

### 再現（`5b1a179c`、mktemp の隔離 worktree でビルドした CLI）

| 入力 | 結果 |
| --- | --- |
| tools を `sh -c 'pwd > doctor-ran.marker; echo probe 1.0'` にした導入元を install（コマンドは呼ばない） | install の後に印は無い。`doctor` の後にプロジェクトのルートに印ができた。`[pass] plugin:hello:probe: /usr/bin/sh probe 1.0`、終了コード 0 |
| 同じ tools を `required: false` | 印ができた |
| `versionArgs` にパッケージの中のスクリプト `.resoloop/plugins/hello/package/probe.sh` | 印ができた（プラグインのコードが動いた） |
| `versionArgs` が空 | 印は無い（パスの確認だけ） |
| `package/hello.py` を編集したプラグイン | 印は無い（`PLUGIN_MODIFIED` の項目だけで、tools を起動しない） |

### 修正方針

推奨案: 導入の保証（導入では何も実行しない）は維持し、概要と信頼の節で、プラグインに由来するプログラムを起動する入口を「プラグインのコマンド」と「`doctor` の tools の検査」の 2 つとして書く。信頼の節は、導入の前に manifest の `commands` と `tools` を読むよう案内し、権限と環境の箇条にも tools の検査を含める。

他の案: (1) 概要の「only」を消すだけ。信頼の節の「the first command does」が残り、信頼の確認の時点を誤らせる条件が残るので選ばない。(2) doctor が tools を起動しないように実装を変える。承認済み D-4（doctor の tools の検査）の仕様を変え、この PR の範囲（文書と最小例だけ、機能コードを変えない）を外れるので選ばない。

### 守る条件と影響経路

守る条件: ガイドを読んだ利用者が、プラグインに由来するプログラム（パッケージのコードを含む）がいつ起動するかを正しく判断できる。破れた前提: ガイドは「導入の後は、プラグインのコマンドを実行したときだけ起動する」と書いたが、`doctor` の tools の検査という別の入口が、コマンドの呼び出しと関係なく起動する。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 起動の入口を正しく示す | `docs/PLUGINS.md:22`（概要の「Installing does not run plugin code」の箇条） | 修正する | コマンドと doctor の tools の検査の 2 つを入口として挙げる | 修正後の本文を `PluginDoctorChecks.RunAsync`・`PluginToolProbe.ProbeAsync` と照合 | `348c2884` で「two things start programs that a plugin's manifest names: running one of its commands, and `resoloop doctor`, which runs the tools the manifest declares」と書いた。`RunAsync` が照合済みのプラグインの tools ごとに `ProbeAsync` を呼ぶこと、「Either can run code from the plugin's package」は V-1 のパッケージのスクリプトの再現（5b1a179c、コードは変えていない）と一致 |
| 同上 | `docs/PLUGINS.ja.md:22` | 修正する | 英語版と同じ意味 | 英日の読み比べ | `348c2884` で、起動するのはコマンドの実行と `resoloop doctor` の2つ、doctor は tools を実行する、どちらもパッケージのコードを実行できる、と英語版と同じ 3 点を書いた |
| 同上 | `docs/PLUGINS.md:23`（「Plugin commands run with your permissions」） | 修正する | 権限の説明に tools の検査を含める | 本文を照合 | `348c2884` で「Plugin commands and doctor's tool checks run with your permissions.」。`ProbeAsync` は ResoLoop と同じ利用者のプロセスとして起動する |
| 同上 | `docs/PLUGINS.ja.md:23` | 修正する | 英語版と同じ意味 | 英日の読み比べ | `348c2884` で「プラグインのコマンドと `doctor` の tools の検査は、利用者の権限で動きます。」 |
| 同上 | `docs/PLUGINS.md:688-691`（信頼の節の導入文と箇条） | 修正する | 導入では何も実行しないこと、コマンドと doctor の tools の検査が実行すること、読む対象に manifest の `commands`・`tools` を含めること。権限と環境の箇条に tools の検査を含める | 本文を照合。環境は `PluginDispatchContext.Current` がプロセスの環境をそのまま渡すことと照合 | `348c2884` で 4 点を書いた。「even if you have not run any plugin command」は V-1 の再現（コマンドを呼ばずに印ができた）と一致。「A tool check also runs with your environment」は `Current` がプロセスの全環境変数を写し、`ProbeAsync` が null 以外をすべて子に渡し、`PluginProcess.Start` がそのまま起動に使うことと一致（古い `RESOLOOP_PLUGIN_*` を外すとは書いていない） |
| 同上 | `docs/PLUGINS.ja.md:688-691` | 修正する | 英語版と同じ意味 | 英日の読み比べ | `348c2884` で英語版と同じ 4 点を書いた（manifest の `commands` と `tools` を読む、導入では実行しない、コマンドと doctor の2つが実行する、tools の検査も利用者として・利用者の環境で動く） |
| 同上 | `docs/PLUGINS.md:454-455`・`docs/PLUGINS.ja.md:454-455`（Doctor の節） | 既に満たす | doctor は実行したときだけ tools を検査し、`versionArgs` が空でなければプロジェクトのディレクトリで実行する、と書いている | `git show 5b1a179c:docs/PLUGINS.md` の 454-455 行と `PluginToolProbe.ProbeAsync` | 5b1a179c で照合済み（確認済みの一覧 V-1 の statement_sites） |
| 同上 | 「Trust, hash and sandbox are different things」の節 | 既に満たす | 「A verified plugin still runs with your full permissions」はコマンドに限らない一般の記述で、誤りではない | 本文の読み | 5b1a179c で照合済み |
| 同上 | 概要の機能の表の「Tool checks」の行（16 行） | 対象外 | 機能の説明で、起動の境界を述べていない。直後の概要の箇条（22 行）で起動を説明する | ― | 起動の有無を主張しない記述のため |
| 同上 | 作者向けの tools の節（675 行付近） | 対象外 | 作者に tools の宣言を求める説明で、利用者の信頼の判断の根拠ではない。起動は Doctor の節にある | ― | 起動の境界を述べないため |
| 同上 | `README.md`・`README_JA.md`・`README-DETAILS.md`・`skills/codex/resonite-build/SKILL.md` の追加分 | 対象外 | 実行の境界を述べる記述が無い | `git diff cae50506 5b1a179c` の追加行の読み | 該当する記述が無いことを 5b1a179c で確認 |
| 同上 | `examples/plugins/hello/` | 対象外 | 最小例の tools は `uv --version` で、記述ではない | ― | 文書ではないため |

設計の見直しのきっかけ: 当たらない（このサイクルが最初のレビュー修正で、以前のレビュー修正のコミットが PR に無い）。

### 検証方法

- 文書の変更なのでテストは足さない（`AGENTS.md`「テストの採用基準」の F。元の Spec の E12）。代わりに次を行う
- 修正後の英日の 3 箇所を、実装（`PluginDoctorChecks.cs`・`PluginToolProbe.cs`・`PluginManifest.cs`・`PluginCommandDispatch.cs`）と照合する。コードは変えないので、V-1 の再現結果（5b1a179c で実行）がそのまま修正後の記述の根拠になる
- `git diff --check`、`git diff --stat`（2 ファイルだけ）、英日の見出しの比較（`grep '^#'`）
- 元の Spec の回帰（`dotnet build ResoLoop.slnx`・`dotnet test`）は、ビルドの入力（`src`・`tests`）を変えないので、`git diff --stat` で入力が変わらないことを確かめて代える（review-fix-planning の「実装後」の手順 2: 変更したプロジェクトに関連する `dotnet test` は、変更したプロジェクトが無いので対象が無い）

## 実行した検証と結果

修正の commit は `348c2884eb678b50ef132d98f3eba0343808a7c3`（`5b1a179c` の直接の子、PR の head ブランチ `feat/create-reso-world-issue-101-plugin-docs`）。修正は `run_roles.py --phase implement`（割り当て `self`）の依頼を planner が実行した（出力 `implement-run/roles.json`）。

| 検証 | 対象 | 結果 |
| --- | --- | --- |
| `git diff --check` | `348c2884` の作業ツリー | 終了コード 0 |
| `git diff --stat` | `5b1a179c..348c2884` | `docs/PLUGINS.md`・`docs/PLUGINS.ja.md` の 2 ファイル、各 5 行の変更だけ |
| 見出しの比較（`grep '^#'`） | 修正前後の英日 | 英日とも見出しは変わらず、英日の階層は一致（34/34） |
| コードブロックの比較 | 修正前後の英日 | 英日ともコードブロックの中身は変わらない |
| 実装との照合 | 直した英日の 4 箇所 | 上の経路表のとおり、`PluginDoctorChecks.cs`・`PluginToolProbe.cs`・`PluginManifest.cs`・`PluginCommandDispatch.cs`・`PluginCommandRunner.cs`（`PluginProcess.Start`）と一致 |
| V-1 の再現 | `5b1a179c` を mktemp の隔離 worktree でビルドした CLI | 確認済みの一覧の V-1 のとおり。`348c2884` はコードを変えないので、この結果が修正後の記述の根拠になる |
| `bash scripts/scan-before-push.sh -C <修正用 worktree> --base origin/feat/plugin-v2` | `cae50506..348c2884` の 8 commit | 検出なし（base に `.gitleaks.toml` が無いので Gitleaks の既定の規則） |

ビルドの入力（`src`・`tests`・プロジェクトの定義）は変えていない（`git diff --stat`）。変更したプロジェクトが無いので、`dotnet test` の対象は無い。

## 自己レビュー

`run_roles.py --phase self-review` の 1 回（工程の記録 `verified/5b1a179c419c.planning.json` に `pre_push_review` を 1 件予約）。割り当ては self-review・fix-check とも `self` で、planner がサブエージェント 2 つに同時に任せた（1 回と数える）。対象は修正後の HEAD `348c2884`。

| 役割 | 観点 | 成果 | 結果 |
| --- | --- | --- | --- |
| self-review（pr-review の非対話の入口、`claude-opus-5-5`・claude-code） | 2 PR 全体 | `claude-opus-5-5-commit-348c2884eb678b50ef132d98f3eba0343808a7c3.md`（所要 448 秒） | 指摘 0 件、Approve。起動の入口がコマンドと doctor の 2 つだけであることを、呼び出し元の列挙と PR head でビルドした CLI の実行（導入・一覧・`skills sync --check`・`uix recipe list` は何も起動しない、doctor は `versionArgs` 付きの tool をプロジェクトのルートで利用者の環境のまま起動する、照合に失敗したプラグインの tool は起動しない）で確かめた |
| fix-check（review-verify の `fix_check`、`claude-opus-5-5`・claude-code） | 1 反証・3 検証の検出力 | `verified/348c2884eb67.fix-check.json`・`.statement-candidates.json`・`.fix-check.md`（所要 579 秒） | 修正の主張 10 件のうち 9 件が成り立ち、1 件（C-4）が V-1 として成り立たなかった。文書の候補 58 件は consistent 32・inconsistent 2（688 行の英日）・unrelated 24・unchecked 0。検出力: Fix 節の検証（構造の検査と実装との読み比べ）は、`versionArgs` が空の場合を 688 行と照合しておらず、V-1 を見逃した |

自己レビューの指摘の判定: fix-check の V-1 は D-5 として「対応しない」（上の表の根拠）。致命的な指摘は無いので、自己レビューの後の修正は無い。自己レビューの 2 回目はしない。

未確認の事項: なし（Windows での実行と Resonite 実機は #101 の受け入れ基準の対象外）。

## 結論

結論 1（修正して push）。D-1 を `348c2884` で直した。自己レビューの指摘（D-5）は致命的でないので直していない。「対応しない」4 件（D-2〜D-5）は、ガイドの記述が実際と食い違う事実なので、PR の説明に既知の制限として、条件と回避方法を書き足す。

- 修正の commit: `348c2884eb678b50ef132d98f3eba0343808a7c3`（push は状況コメントと PR の説明に書く）
- この Spec は create-reso-world の文書用ブランチ `docs/create-reso-world-issue-101-plugin-docs` に置き、文書専用 PR usaturn/create-reso-world#469 で公開する

## サイクル 2（判断の記録のサイクル 2、現行 HEAD `348c2884`）

- レビュー: PR 修正ループの `cycle-begin` が `reuse` を返した。現行 HEAD `348c2884` には、サイクル 1 の自己レビュー（`claude-opus-5-5-commit-348c2884eb678b50ef132d98f3eba0343808a7c3.md`、claude-opus-5-5・claude-code、指摘 0 件・Approve）があり、レビュアーを起動し直していない。ほかの 4 件（SWE-2-Max・gpt-6.2-sol・deepseek-v4.1-flash・qwen4-max-preview）は `5b1a179c` をレビューした古いレビュアーで、その指摘はサイクル 1 で判断済み
- 確認済みの一覧: `verified/348c2884eb67.json`（mode cycle）。古いレビュアーの候補 4 件を現行 HEAD の隔離 worktree でビルドした CLI で確かめ直した。gpt-6.2-sol#M-1 は not_reproduced（記述が挙動と一致した）、残り 3 件は confirmed（記述も挙動も変わらない。判断済みの「対応しない」のまま）
- 判断: D-1（`gpt-6.2-sol#M-1@5b1a179c419c`）を `fix` から `resolved` にした（根拠: `348c2884` の英日の 22 行と 688〜691 行、確認済みの一覧の V-1、fix-check の主張 10 件のうち 9 件が成り立ったこと）。D-2〜D-5 の「対応しない」は新しい根拠が無いので引き継ぐ。新しい指摘は無い
- 分類: 解消済み 1 / 対応する 0 / 対応しない 0（このサイクルの入力の分。引き継いだ「対応しない」は 4 件）

### 検証（結論 2 の手順 1・2）

検証したツリーは PR head `348c2884eb678b50ef132d98f3eba0343808a7c3` そのもの（base `feat/plugin-v2` の先端 `cae50506401577f840fb22d81ea5aa87d5fa9c2b` は head の祖先なので、merge したツリーは作っていない）。修正用の worktree `external/resoloop/.worktrees/create-reso-world-issue-101-plugin-docs`（未コミットの変更なし、HEAD が PR head と同じ）で実行した。

| コマンド | 終了コード | 結果 |
| --- | --- | --- |
| `dotnet build ResoLoop.slnx --disable-build-servers` | 0 | エラー 0 |
| `dotnet test ResoLoop.slnx --no-build` | 0 | RLoop.Tests 592 件・RLoop.IntegrationTests 22 件、失敗 0 |
| `git diff --check cae50506 348c2884` | 0 | 問題なし |

元の Spec の受け入れ基準の「回帰」（`dotnet build`・`dotnet test` の成功）を現行 HEAD で満たす。PR の checks（windows）は `348c2884` で成功。

### サイクル 2 の結論

結論 2（修正不要としてマージ）。CI の確認・状況の投稿・マージは `finalize.py` が行う。PR は closing Issue を持たない（create-reso-world#101 は Refs で参照しているだけ）ので、#101 にはマージの結果と残りの作業をコメントする。
