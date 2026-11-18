# Issue #101 プラグイン4機能の文書と最小例 設計

## 管理・実行許可

- 状態: `draft`（コミットしただけで `approved` にしない。内容の承認は記録していない）
- 対象 Issue: usaturn/create-reso-world#101（実装対象 `usaturn/resoloop`、base `feat/plugin-v2`）。親は create-reso-world#95（ボード `resoloop-plugins-board`、子のキー `plugin-docs`）
- 設計の定義元: `docs/superpowers/specs/2026-10-29-create-reso-world-issue95-plugin-replan-design.md` の D-1〜D-6（承認済みの内容 `d009286968a21c916bafb39b2308ebaa09d40c4c`）
- 利用者の指示（2026-11-18）: `/issue-to-pr #101 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review devin_swe2_high --implement claude-code_sonnet_xhigh --assign implement=claude-code_sonnet_xhigh --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh`
- 同じ run での利用者の回答（2026-11-18）: base について「feat/plugin-v2 で進める」を選んだ。`--base feat/plugin-v2` を明示したものとして入力を解決し直した
- 実行許可の範囲: この Spec・Plan の作成とコミット、`usaturn/resoloop` の作業ブランチでの文書・最小例の実装、Gitleaks の検査を通した SHA の push、`usaturn/resoloop:feat/plugin-v2` 宛ての fork 内 PR と `usaturn/create-reso-world:main` 宛ての文書専用 PR の作成、C6 の別 Issue の起票（下の決定 C6）。Issue #101 の「コードの push・fork 内 PR の作成は、着手時に利用者の実行許可を得る」は、この `/issue-to-pr` の指示で満たしたものとして扱う
- 設計レビューの後の続行: 設計レビューの `decide` は、採用して反映した blocking 3件を理由に `next: stop` を返した。`wrong_approach`・利用者への質問・`needs_judgment`・作るものを変える採用はどれも無いので、2026-11-15 の利用者の指示（Issue #427 の run で「現在止まっていることは許可されていません。必ず推奨案で進めることがスキルで規定されている」。この挙動は #455 で追跡中で、2026-11-18 の時点で open）に従って Spec を commit し、Spec レビューへ進んだ
- 実行しないこと: マージ（`--merge` は base が `main` でないため適用しない）、PR 修正ループ、上流 `orange3134/resoloop` への PR、NuGet への公開、グローバルの `resoloop` の入れ替え
- 先行: I #298 は closed・`state_reason=completed`。コード PR usaturn/resoloop#31 が `feat/plugin-v2` に merge `cae50506401577f840fb22d81ea5aa87d5fa9c2b` として取り込まれている（2026-11-18 に `git ls-remote` で先端が同じ SHA であることを確認）
- コード base: `usaturn/resoloop` `refs/heads/feat/plugin-v2` @ `cae50506401577f840fb22d81ea5aa87d5fa9c2b`。文書 base: `usaturn/create-reso-world` `refs/heads/main` @ `10fbef1e31a4b86674196b51318b4b167b696b08`
- 予約: `refs/heads/agent-claims/issue-101` = `7f16b7b04ff53bb5ea19aface86b1de84ec508d1`（session `e27c7ebe-3e7e-4946-b67a-17769e79e6bf`、着手コメント https://github.com/usaturn/create-reso-world/issues/101#issuecomment-6980459900 ）

## 1. 目的と現状

`usaturn/resoloop:feat/plugin-v2` には、プラグインの4機能（外部コマンド・スキルの配布・UIX レシピ・doctor）と `plugin install`・`plugin list`・`plugin remove` が入っている。使い方と作り方を説明する文書と最小例は無い（`docs/PLUGINS.md`・`examples/plugins/` は無く、README 3種と `skills/codex/resonite-build/SKILL.md` に `plugin` を含む行は 0 行）。仕様は create-reso-world の5本の Spec（#297・#98・#99・#100・#298）とコードに分かれていて、利用者・作者・#105 で上流の PR を読む人は、それらを読み合わせないと manifest の書き方や `plugin remove` が消すデータを知ることができない。

この Issue では D-1〜D-6 と4機能を、統合先のコードと実際の help・出力に合わせて文書にし、4機能を全部使う最小例を足す。後続の #105（上流への PR）、#328（プラグインの新規開発の手順）、#329（プラグインのリポジトリの雛形）は、この文書と最小例を前提にする。

コードを読んで分かった現状（`cae50506` の時点）は次のとおりである。

| 項目 | 現状 |
| --- | --- |
| help | `resoloop help` に `plugin install SOURCE [--ref GIT_REF] [--project DIR] [--json]`・`plugin list [--project DIR] [--json]`・`plugin remove NAME --yes [--project DIR] [--json]   (also deletes the plugin's data/ directory)`・`resoloop [--project DIR] PLUGIN_COMMAND [ARGUMENTS...]`・`uix recipe describe NAME [--project DIR]   (plugin recipes: PLUGIN:RECIPE)` の行がある |
| manifest | `resoloop-plugin.json`。欄は `schemaVersion`（1 のみ）・`name`・`version`・`resoloop`（`minVersion` 必須、`maxVersionExclusive` 任意）・`description`・`commands`・`skills`・`recipes`・`tools`。未知の欄と重複した欄は拒否する（`src/RLoop.Core/Plugins/PluginManifest.cs`） |
| 名前 | 先頭は英小文字、小文字の英数字を1つのハイフンで区切る、2〜40文字（`PluginNames.IsValid` の `\A[a-z][a-z0-9]*(-[a-z0-9]+)*\z`）。プラグイン・コマンド・スキル・レシピ・tools の名前に同じ規則を使う。スキル名の `resonite-` と組み込み名は予約 |
| コマンドの呼び出し | `program` はコマンド名か `./` で始まる package 内のパス。`args` の `${pluginRoot}`・`${pluginData}` だけを置き換え、利用者の引数をその後ろに変えずに足す。環境変数 `RESOLOOP_PLUGIN_NAME`・`_COMMAND`・`_ROOT`・`_DATA`・`_PROJECT_ROOT`・`_HOST_ARGV`・`_HOST_VERSION` を渡し、`PYTHONPYCACHEPREFIX` と `UV_PROJECT_ENVIRONMENT` を `data/` の下へ向ける（`PluginRuntimeEnvironment.cs`） |
| 導入元 | ローカルのディレクトリ（Git の作業ツリーのルートか Git 外）と、Git URL（`http`・`https`・`ssh`・`git`・`file`、scp 形式）＋`--ref`。ルートでない Git の下位ディレクトリは `PLUGIN_SOURCE_INVALID`（`PluginGit.cs`） |
| テキスト出力 | `init`・`skills sync` はプラグインのスキルを配るが、テキスト出力にはプラグインの結果が出ない。`--json` の `plugins` に出る。`SKILL_SYNC_REQUIRED` のメッセージは同梱スキルを前提にした文言（決定 C6） |
| doctor | Resonite に接続できないと本体の項目が失敗し、`ready: false` のまま終了コード 0 を返す。プラグインのツールの項目は `plugin:<plugin-name>:<tool-name>` |
| 公開版 | `src/RLoop.Cli/RLoop.Cli.csproj` の `<Version>` は 0.2.0。NuGet の 0.2.0 にプラグイン機構は無い。csproj は `README.md`・`README-DETAILS.md`、`docs/` の一部のファイル（`QUICKSTART.md` など名前を挙げたもの）、`src/` と `skills/codex/`（`source/` の下）を pack する。csproj を変えないので、`docs/PLUGINS.md`・`docs/PLUGINS.ja.md`・`examples/plugins/` は NuGet のパッケージに入らない |

## 2. 範囲と禁止

変えてよいもの（Issue 本文の「範囲と禁止」の所有範囲）:

- `docs/PLUGINS.md`（新規、英語）と `docs/PLUGINS.ja.md`（新規、日本語）。`.ja.md` は既存の `docs/RESONITELINK-IMPORT-ISSUES.ja.md` と同じ名付け方で、決定 A1 の併記のために足す（Issue の所有範囲 `docs/PLUGINS.md` の日本語版として扱う）
- `README.md`・`README_JA.md`・`README-DETAILS.md` のプラグインの節（新設）
- `skills/codex/resonite-build/SKILL.md` のプラグインに触れる段落（新設）
- `examples/plugins/hello/` の最小例（新規）

変えないもの:

- 機能コード（`src/`）、テスト（`tests/`）、`RLoop.Cli.csproj`
- 上の節以外の文書の節。上流 main で変わった `README-DETAILS.md` の 196〜237 行目付近と 373 行目付近、`SKILL.md` の 47〜62 行目付近の行（決定 C3）
- 旧 preproduction・Meshy 専用機能の持ち込み、Meshy プラグイン（#102）
- fork の `main`、上流 `orange3134/resoloop`

記載外の編集が必要になったら、編集せずに止まって報告する（親 #95 の調整役が裁定する）。

## 3. 決定記録

「利用者の決定」は利用者が決めたこと、「エージェントの判断」は推奨案としてこの run で決めたことである。A1〜C6 は 2026-11-18 に利用者が別のセッションで決め、ローカルの下書き `docs_draft/issue-101-decisions.md`（git の追跡外）に記録したもので、この Spec に内容を写した。Issue の本文とコメントには書かれていない。

### 進め方

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- | --- |
| R1 | base | `usaturn/resoloop:feat/plugin-v2`（利用者の回答） | fork の `main` | Issue と親 #95 が反映先を `feat/plugin-v2` と定め、fork `main` を base にしないとしている | 利用者の回答「feat/plugin-v2 で進める」。base の移動を観測したら issue-to-pr の前進追随の条件の範囲で追随し、条件の外なら止まる |
| R2 | `--merge` | 適用しない。PR を作った時点で終える | ループを回す | issue-to-pr の規則で、base が統合用 branch のときは `--merge` を適用しない（`merge-disabled.txt`）。ループ用の `--assign` も使わない | なし。最終のブランチ全体のレビューは省かない |
| R3 | planning handoff と復元 manifest | 作らない。決定と経緯は Spec・Plan・Issue のコメントに残す | 親 #95 の開始手順どおり handoff の2ファイルと manifest を作る | 2026-11-14 の利用者決定「全て issue-to-pr で進めるので handoff は不要」。#101 の本文の handoff の記載は、その決定の時点で修正を見送った旧書式の残件 | 利用者の決定。予約 ref は親の手順どおり使う |
| R4 | 予約の解放の時点 | PR を作り、結果を Issue にコメントした後に、保存した SHA の lease で解放する | Spec・Plan の公開後すぐに解放する | 同じ run で実装と PR まで進めるので、実装中に別のセッションが同じ子を選ばないようにする。#356・#357 の issue-to-pr の run と同じ扱い | 予約の SHA が変わっていたら書き込みを止め、消さずに報告する |
| R5 | PR の分け方 | コードの PR 1本（`feat/plugin-v2` 宛て、docs・examples・README・SKILL.md を含む）と、create-reso-world の文書専用 PR 1本（Spec・Plan） | 規模 L を複数のコード PR に分ける | 利用者の決定 C4。文書と最小例は互いの出力例で結びつき、分けると照合をやり直すことになる | なし |
| R6 | 実装の担当 | 各 Task を agent-runner の `claude-code_sonnet_xhigh` に1つずつ順に依頼する。fallback は個人設定の値（空） | このセッションが自分で実装する | 利用者の指定 `--implement claude-code_sonnet_xhigh`（`implement_task.py check` が `self: false` を返した） | 失敗しても担当を暗黙に替えない。`failed` と上限に達した再試行では止まる |
| R7 | レビュー | 設計レビュー `pi_openai-codex_gpt6-sol_xhigh`、Spec レビュー `devin_swe2_high`（どちらも fallback は個人設定の値で空）。builder check は Spec レビューが代わる | builder check だけを行う | 利用者の指定 `--design-review`・`--spec-review` | issue-to-pr の Spec・設計レビューの停止条件に従う |
| R8 | 日本語の推敲 | 日本語の成果物（`docs/PLUGINS.ja.md`・`README_JA.md` の節・`README-DETAILS.md` の節）と、この Spec・Plan・PR・Issue に書く日本語を yomiyasu の手順で推敲し、検査ツールで意味の変わるおそれのある箇所を確かめる | 推敲しない | Issue #101 の「決定済みの事項」にある 2026-11-18 の利用者決定 | 実装担当が yomiyasu を使えない場合は、司令塔が Task のレビューで検査ツールを実行し、結果を指摘として修正担当に返す |

### 文書（利用者の決定 A1〜A6）

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- | --- |
| A1 | 言語 | 併記。`docs/PLUGINS.md` は英語、`docs/PLUGINS.ja.md` は日本語。`README.md` は英語版、`README_JA.md` と `README-DETAILS.md` は日本語版へリンクする | 英語だけ、日本語だけ | 利用者の決定。上流の読者（英語）と、この開発環境の利用者（日本語）の両方に向ける | なし |
| A2 | 構成 | 概要 → クイックスタート → 利用者向け → 作者向け → 安全と制限 → エラー | 機能ごとの章立て | 利用者の決定 | なし |
| A3 | README | `README.md`・`README_JA.md` に4〜6行の節と詳細へのリンク。`README-DETAILS.md` に簡潔なコマンド表とリンク | README に詳細を書く | 利用者の決定。resoloop の `AGENTS.md` は利用者向けの README を短く保ち、詳細を `README-DETAILS.md` か別の文書に置くと定めている | なし |
| A4 | 出力例 | install・list・remove・doctor の短い実出力を貼り、「0.2.0 の feat/plugin-v2 で確認」と注記する。長い JSON は抜粋する | 出力例を載せない | 利用者の決定。Issue の目標「文書の例と実際の動作の食い違い 0 件」を照合できる形にする | 実出力と違う例を載せない |
| A5 | エラー表 | よく出る `PLUGIN_*` と対処の短い表 | 全コードの一覧 | 利用者の決定 | なし |
| A6 | 英日の対応 | 2つの文書の見出しと内容の対応を、README の英日と同じように確かめる | 対応を確かめない | 利用者の決定 | なし |

### 最小例（利用者の決定 B1〜B5）

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- | --- |
| B1 | 範囲 | 4機能すべて（コマンド・スキル・UIX レシピ・tools） | コマンドだけ | 利用者の決定 | なし |
| B2 | 実装 | Python + uv。`pyproject.toml` と `uv.lock` を置き、`uv run --project ${pluginRoot} --locked` で起動する | シェルスクリプト、`dotnet` のプログラム | 利用者の決定。本体が `UV_PROJECT_ENVIRONMENT` と `PYTHONPYCACHEPREFIX` を `data/` に向けるので、`package/` を変えずに動く | なし |
| B3 | 題材 | `hello` プラグイン。コマンドは受け取った argv と `RESOLOOP_PLUGIN_*` を表示する。スキル `hello-guide`、レシピ `hello-card`、tools `uv` | 実用的な題材 | 利用者の決定 | なし |
| B4 | 導入経路 | ローカルディレクトリと Git URL（`--ref`）の両方を文書にする。実演はコピーしたローカルディレクトリで行う | 片方だけ | 利用者の決定 | なし |
| B5 | 置き場所 | `examples/plugins/hello/` に一式を置く。resoloop リポジトリの下位ディレクトリなので、そのままでは導入できない。クイックスタートでは別のディレクトリへコピーしてから導入する。Git URL の例は一時リポジトリで確かめる | 別リポジトリ | 利用者の決定 | なし |

### 周辺（利用者の決定 C1〜C6）

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- | --- |
| C1 | SKILL.md | `skills/codex/resonite-build/SKILL.md` に2〜3行を足す。プロジェクトにプラグインがあれば `resoloop plugin list` で確かめ、`resoloop [--project DIR] COMMAND` で呼ぶ。詳細は `docs/PLUGINS.md` | 足さない | 利用者の決定 | なし |
| C2 | #110〜#112 | 短い既知の制約として書く。通常のディレクトリを使うよう勧める。ローカル導入元のパスは、リンクを解決した実体で判定する（リンク経由の指定も受け付け、Git のルートかどうかとコピーするファイルは実体で決まる）。これとは別に、管理領域（`.resoloop`・`plugins`・各プラグインのディレクトリ・`package`）のリンクと、コピーする導入元の中のリンクは拒否する。`data/` は照合の対象外。Issue 番号は書かない | 旧不具合として説明する。導入元のリンクを一律に拒否すると書く | 利用者の決定。修正コードは F #297 で取り込み済みで、残るのは追跡確認と記録である。open という状態だけで未修正と書かない。設計レビュー D2 を採用し、利用者の決定の意図（現行の利用条件を正確に書く）に沿って、拒否の条件を現行の実装（`PluginPathPolicy.ResolveDirectory`、`PluginInstallerTests` のリンク経由の導入の成功と管理ディレクトリのリンクの拒否）に合わせた | 拒否の条件は、文書を書く時点のコードとテストで確かめる |
| C3 | 上流との差分 | `feat/plugin-v2` のまま。上流で変わった行に触れず、追加を最小にする。#105 で小さな衝突を解消する | 上流 main を取り込む | 利用者の決定。上流への追従は Issue の対象外 | なし |
| C4 | PR | 1本（決定 R5） | 複数 | 利用者の決定 | なし |
| C5 | NuGet | 対象外。README から docs と examples へは GitHub の絶対 URL（fork の `feat/plugin-v2` を指す。例 `https://github.com/usaturn/resoloop/blob/feat/plugin-v2/docs/PLUGINS.md`）で案内する。`csproj` は変えない。#105 で上流へ移すときに URL を更新する | 相対リンク | 利用者の決定。`README.md`・`README-DETAILS.md` は NuGet に pack され、csproj を変えないので `docs/PLUGINS.md`・`docs/PLUGINS.ja.md`・`examples/plugins/` は pack されない。相対リンクは NuGet のページで切れる（Spec レビュー S1 で根拠の書き方を直した） | なし |
| C6 | テキスト出力の不足 | 現状を文書にする。`init`・`skills sync` はプラグインのスキルを配るが、テキスト出力には出ないので `--json` の `plugins` を見る。`SKILL_SYNC_REQUIRED` の文言が同梱スキル前提であることも注記する。CLI の表示の修正は別 Issue にし、この Issue の PR を作るときに `issue-authoring` の書式で起票して PR と相互にリンクする | この Issue で `Program.cs` を直す | 利用者の決定。機能コードの変更は Issue の対象外 | 起票の前に同じ目的の Issue を検索し、あれば起票せずにリンクする |

### この run のエージェントの判断

| # | 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- | --- |
| E1 | 最小例のファイル構成 | `examples/plugins/hello/` に `resoloop-plugin.json`・`pyproject.toml`・`uv.lock`・`hello.py`・`skills/hello-guide/SKILL.md`・`recipes/hello-card.json` の6ファイル。README は置かない | 例の中に README を置く | 説明は `docs/PLUGINS.md` に一元化し、導入すると `package/` にコピーされる重複を避ける | 推奨案での委任 |
| E2 | Python のプロジェクト | `pyproject.toml` は依存の無い仮想プロジェクト（`[tool.uv] package = false`）にし、ビルドの成果物を作らない | パッケージとしてビルドする | ビルドで `package/` に成果物（egg-info など）ができると、照合で `PLUGIN_MODIFIED` になるおそれがある | `uv run --locked` が `package/` に書き込むと分かったら、代わりの方法を Plan の contingency に従って選ぶ |
| E3 | `hello` コマンドの出力 | 受け取った argv（1行に1つ）と `RESOLOOP_PLUGIN_*` の値を表示し、終了コード 0 を返す。引数に `--json` があれば同じ内容を JSON 1つで出す | テキストだけ | D-4 の「`--json` を子へ渡す場合は作者が JSON 出力を実装する」を最小例で示す | 推奨案での委任 |
| E4 | スキル | `skills/hello-guide/SKILL.md` は frontmatter（`name`・`description`）と、`resoloop hello` の呼び方を書いた数行の本文 | 本文だけ | 配布先の `.agents/skills/hello-guide/` で、エージェントがスキルとして読める形にする | 推奨案での委任 |
| E5 | レシピ | `recipes/hello-card.json` に `prototypes` の1件（`hello.card`）を置き、manifest の `parameters` に必須の `key` を宣言する。Component の型名は組み込みのレシピか既存の例が使う型だけを使い、推測しない | 型名を推測して凝った UI にする | resoloop の `AGENTS.md` が型名の推測を禁じている。オフラインの `uix recipe describe`・`uix recipe export` と `validate` で確かめられる範囲にする | 型名を確かめられなければ、Slot だけの prototype にする |
| E6 | tools | `uv`（`versionArgs: ["--version"]`、`required: true`、導入方法の `hint`） | tools を宣言しない | B3 の決定。doctor の判定を `plugin:hello:uv` で示す | なし |
| E7 | 対応版 | `resoloop.minVersion` は `0.2.0`。`maxVersionExclusive` は書かない | 旧例の `maxVersionExclusive: 0.2.0` | 旧例は 0.2.0 を拒否する（Issue の受け入れ条件） | なし |
| E8 | 導入先の準備の書き方 | クイックスタートは、`examples/plugins/hello/` を Git 管理の外の作業用ディレクトリへコピーし、そのコピーを導入元にする。Git 管理下に置く場合は、コピー先で `git init` してそのルートを指定する。Git URL の例は、コピーを Git リポジトリにして `file://` URL と `--ref` で導入する | resoloop の checkout の下位ディレクトリを直接渡す | installer は Git の作業ツリーのルートか Git 外のディレクトリだけを受け付ける（Issue の受け入れ条件） | なし |
| E9 | 実行照合の場所 | feature worktree で `dotnet build ResoLoop.slnx` した CLI（`dotnet <worktree>/src/RLoop.Cli/bin/Debug/<tfm>/resoloop.dll`）を、`resoloop` という名前のラッパーで呼ぶ。導入元・ワールドのプロジェクト・一時 Git リポジトリは `mktemp -d` の Git 管理外のディレクトリに作り、ログは create-reso-world の `tmp/agents/issue-101-*` に残す | グローバルの `resoloop` を fork のビルドに入れ替える | 入れ替えは共有の資源で、親 #95 の運用ルールが専用の予約を求める。ビルドした dll で同じ CLI を確かめられる | 実行照合の出力に端末やホスト固有の値（一時パス）が出る場合は、文書では `<project>` のような置き換えを使い、置き換えたことを文書に書く |
| E10 | README の位置 | `README.md`・`README_JA.md` は「Blender modeling」の節の後、「Learn more」の前に「Plugins」の節を置き、ガイドへのリンクはこの節にだけ置く。既存の「Learn more」「さらに詳しく」は変えない。`README-DETAILS.md` は「Codex Skills」の節の後、「Tests」の前に「Plugins」の節を置く | 末尾に置く。「Learn more」にも1行足す | 上流 main が変えた行から離れた位置で、既存の読む順序（使い方 → 詳細）に合う。設計レビュー D3 を採用し、Issue の許可範囲（README 3種のプラグインの節）の外の節を変えない | 上流で変わった行に触れる必要が出たら止まる |
| E11 | SKILL.md の位置 | 「Automatic connection discovery」の節の前、手順の一覧の後に段落を1つ足す | 先頭に足す | 上流が変えた 47〜62 行目付近から離す | 同上 |
| E12 | テスト | 常設のテストは足さない。最小例と help・実出力の実行照合と、`dotnet build`・`dotnet test` で代える | 文書の固定値テスト、最小例の自動テスト | AGENTS.md「テストの採用基準」。文書の文言を写すテストは F で、最小例は文書の手順どおりの実行で照合する（Issue の受け入れ条件） | S に当たる守りが必要と分かったら、Plan を更新してから足す |
| E13 | 実行照合の範囲 | 次の代表操作を1回ずつ通す: ローカルの導入元からの install、list（テキストと `--json`）、`hello` の実行（テキストと `--json`、日本語や空文字を含む引数）、`skills sync --update` と配布先の内容、`uix recipe describe hello:hello-card` と `uix recipe export`、`$recipe` を使う宣言の `validate`、doctor（`--json`）、remove（`data/` が消え、配ったスキルが残ること）、Git URL（`file://`）と `--ref` からの install（`plugin install --json` の `commit` と `install.json` の `commit` が一時リポジトリの SHA と一致すること） | 全コマンドと全組み合わせ | Issue の受け入れ条件は代表例を一度通すことを求め、網羅は求めていない | 代表操作のどれかが文書と違えば、文書を実際に合わせる。機能コードの不具合と分かったら、文書に既知の制約として書くか止まるかを Plan の contingency で決める |

### レビューの記録

| レビュー | 担当 | 記録 | 結果と採否 |
| --- | --- | --- | --- |
| Spec レビュー（1回目） | 指定 `devin_swe2_high`（fallback なし）、実際の担当 `devin_swe2_high`、観測したモデル `SWE-2 High`（session `nutritious-lasagna`、CLI 3000.14.30821） | review_id `41479f8f00794445b11d52b4d5457bc2`、レビューした Spec の SHA-256 `7ec71d5340df368a9816a0e9181d9ee5c5b9c0763321602c03ba3e19e97dfb6b`（commit `1f7022c8`）、所要 735 秒、`outside_changes`・`unprotected_changes` なし | 7件（どれも minor）をすべて採用した。S1 は 1 の「公開版」と C5 の根拠、S2 は 6 の検証の入口、S3 は 4.1 の「Safety and limits」の利用条件の追加と網羅でないことの明記、S4 は 1 の「名前」、S5 は 4.1 の「Errors」、S6 は 4.1 の「Quick start」、S7 は 5 の「実入力」に反映した。どれも作るものの範囲は変えない |
| 設計レビュー（1回目） | 指定 `pi_openai-codex_gpt6-sol_xhigh`（fallback なし）、実際の担当 `pi_openai-codex_gpt6-sol_xhigh`、観測したモデル `gpt-6.2-sol`（provider `openai-codex`、effort `xhigh`） | review_id `07b97a6dc7f54899b286f03940368aa8`、レビューした Spec の SHA-256 `ee29c0957b66d9a3d9114f3a2b29cb37902282afe38a8d7db703cf8a43107bb7`（commit `b8adfe64`）、所要 225 秒、`outside_changes`・`unprotected_changes` なし。記録は issue-to-pr のセッションディレクトリ（commit しない） | verdict `concerns`、3件（どれも blocking）。D1（`plugin list --json` にコミットが無い）を採用し、4.1 の「Safety and limits」と E13 を直した。D2（ローカル導入元のリンクは実体へ解決して受け付ける）を採用し、C2 と 4.1 を直した。D3（「Learn more」への追記は許可範囲の外）を採用し、E10 と 4.3 を直した。どれも作るものの範囲は変えない |

## 4. 成果物の設計

### 4.1 `docs/PLUGINS.md` と `docs/PLUGINS.ja.md`

2つは同じ見出しの構成と同じ内容を持つ（A6）。見出しは英語版で次のとおり（日本語版は同じ順の日本語の見出し）。各章で説明することは次のとおりである。

1. Overview: プラグインでできること（外部コマンド・スキルの配布・UIX レシピ・doctor の tools）。プラグインは `feat/plugin-v2` の機能で、NuGet の 0.2.0 には入っていないこと。導入はプロジェクト単位であること
2. Quick start: 既存のワールドのプロジェクトか、`resoloop init` で作ったプロジェクトを用意する → `examples/plugins/hello/` を Git 管理外でプロジェクトとも重ならない作業用ディレクトリへコピーする → ワールドのプロジェクトで `resoloop plugin install <copy>` → `plugin list` → `resoloop hello ...` → `skills sync --update` → `uix recipe describe hello:hello-card` → `doctor` → `plugin remove hello --yes`。各手順に短い実出力を付ける（A4）
3. For users: 導入元（ローカルのディレクトリ、Git URL と `--ref`、`file://` を含む受け付ける URL、資格情報を URL に入れないこと）、対象プロジェクトの決め方（`--project DIR` か cwd から上への `.resoloop.json` の探索）、保存先 `<project>/.resoloop/plugins/<name>/{install.json,package/,data/}` と `plugins/.gitignore`、導入時にプラグインのコードを実行しないこと、Git では実際のコミットを記録して自動で追従しないこと、`plugin list`（壊れたプラグインも問題付きで表示）、`plugin remove NAME --yes`（`data/` を含む導入ディレクトリを消す注意、配ったスキルは残る）、更新は remove と install のやり直しであること、コマンドの呼び方（`resoloop [--project DIR] COMMAND [ARGUMENTS...]`。コマンド名より後ろはすべてプラグインに渡る）、スキルの配布（`init`・`skills sync --check|--update`、`.agents/skills/<skill>/`、`.agents/skills/.resoloop-plugins.json`、利用者の編集を上書きしないこと、テキスト出力に出ないので `--json` の `plugins` を見ること＝C6）、UIX レシピ（`<plugin-name>:<recipe-name>`、`uix recipe list|describe|export`、宣言ファイルの `$recipe`、主入力ファイルの場所からプロジェクトを探すこと）、doctor（明示的に実行したときだけ tools を検査、`plugin:<plugin-name>:<tool-name>` の項目、Resonite 未接続の本体の項目と分けて読むこと、終了コード 0 だけで成功と見なさないこと）
4. For authors: パッケージの構成（ルートの `resoloop-plugin.json`、4種類はどれも必須でないこと）、manifest の各欄（型・上限・必須・SemVer の比較。`schemaVersion` は 1、名前の規則、未知の欄と重複の拒否）、コマンドの取り決め（`program` の2つの形、`args` の置き換えは `${pluginRoot}`・`${pluginData}` だけ、cwd はプロジェクトのルート、環境変数 `RESOLOOP_PLUGIN_*` の一覧と意味、stdout・stderr の転送と終了コード、`--json` は作者が実装すること、`timeoutSeconds` と省略時の `commandTimeoutSeconds`、期限・キャンセルで成功を返さないこと、実行時のキャッシュを `data/` へ向けること）、スキルの置き方（`skills[].path` の下の `SKILL.md`、予約名）、レシピの置き方（`recipes[].path` の JSON の `prototypes`、`prototype`・`purpose`・`parameters`（`key` 必須）・`ports`・`requirements`、生成キー `uix-plugin--<plugin-name>--<recipe-name>--<caller-key>`）、tools（`executable`・`versionArgs`・`required`・`hint`）、対応する ResoLoop の版（`minVersion` を 0.2.0 にした例、旧例の `maxVersionExclusive: 0.2.0` を使わないこと）、Python と uv の最小例の説明（E2 の理由を含む）、依存環境の準備は作者が文書に書くこと
5. Safety and limits: 導入元の確かめ方（信頼できる配布元か、Git では `--ref` にコミットの SHA を使えること、導入した直後は `plugin install --json` の `commit`、後からは `<project>/.resoloop/plugins/<name>/install.json` の `commit` を、事前に確かめた SHA と照合すること。`plugin list` は導入状態と照合の問題を確かめるのに使い、コミットは表示しない）、記録との照合（`package/` 全体を使う前に照合し、内容の変更・追加・欠落・リンクの差し替えを検出したプラグインは使わない。`data/` は照合しない）、信頼・ハッシュ・サンドボックスの違い（ハッシュは意図しない差分の検出で、署名でもサンドボックスでもない。`install.json` を同じ権限で書き換えられる相手への防御ではない。プラグインのコマンドは利用者と同じ権限で動く。悪意ある同一ユーザへの完全な防御は対象外）、現行の利用条件（Git の導入元はルートに限る、ローカル導入元のパスはリンクを解決した実体で判定する、管理領域とコピーする導入元の中のリンクは拒否する、通常のディレクトリを使う。C2）、件数・容量の上限、同じプロジェクトの導入・削除の排他（`PLUGIN_PROJECT_BUSY`）。あわせて、Spec レビュー S3 が挙げた次の利用条件をコードで確かめて書く: 導入元とプロジェクトのディレクトリが重なると `PLUGIN_SOURCE_INVALID`（`PluginInstaller.cs` の `Overlaps`）、Git 外の導入元の中の `.git` は除外ではなく拒否（`PluginPathPolicy.EnumerateFiles` の `rejectNestedGit`）、Git の導入元では ignore されたファイルを導入しない（`ls-files --cached --others --exclude-standard`）、`init`・`skills sync` のプラグインのスキルの配布は指定したディレクトリそのものの `.resoloop.json` を見て祖先を探さない（`PluginSkillManager`）のに対し、install・list・コマンド・doctor・レシピは cwd から上へ探す、`--ref` は `file://` を含むすべての Git URL で必須（`PLUGIN_GIT_REF_REQUIRED`）、失敗した導入は自分の staging だけを片付けて既存の導入物と記録を変えない。ここに挙げたものは網羅ではない。各章を書くときは、D-2〜D-6 の各項に対応する利用条件・拒否条件を、ほかにもコードとテストで確かめる
6. Errors: よく出る `PLUGIN_*`（少なくとも `PLUGIN_PROJECT_NOT_FOUND`・`PLUGIN_SOURCE_NOT_FOUND`・`PLUGIN_SOURCE_INVALID`・`PLUGIN_MANIFEST_NOT_FOUND`・`PLUGIN_MANIFEST_INVALID`・`PLUGIN_SCHEMA_UNSUPPORTED`・`PLUGIN_INCOMPATIBLE_VERSION`・`PLUGIN_NAME_CONFLICT`・`PLUGIN_ALREADY_INSTALLED`・`PLUGIN_GIT_REF_REQUIRED`・`PLUGIN_GIT_REF_NOT_FOUND`・`PLUGIN_MODIFIED`・`PLUGIN_PATH_UNSAFE`・`PLUGIN_NOT_INSTALLED`・`PLUGIN_PROJECT_BUSY`・`PLUGIN_COMMAND_START_FAILED`・`PLUGIN_COMMAND_TIMEOUT`）と、原因・対処の短い表（A5。`PLUGIN_SCHEMA_UNSUPPORTED` と `PLUGIN_COMMAND_START_FAILED` は Spec レビュー S5 で足した）。コードと意味は、エラーを投げるコードの箇所を読んで確かめる

具体的な値（上限・既定値・メッセージ・出力）は、文書を書く時点の `feat/plugin-v2` のコードと実行結果から写し、Spec や Issue の要約から写さない。

### 4.2 `examples/plugins/hello/`

| ファイル | 内容 |
| --- | --- |
| `resoloop-plugin.json` | `schemaVersion: 1`、`name: "hello"`、`version: "1.0.0"`、`description`、`resoloop: {"minVersion": "0.2.0"}`。`commands` に `hello`（`program: "uv"`、`args: ["run", "--project", "${pluginRoot}", "--locked", "python", "${pluginRoot}/hello.py"]`）、`skills` に `hello-guide`、`recipes` に `hello-card`、`tools` に `uv` |
| `pyproject.toml` | 依存の無い仮想プロジェクト（E2） |
| `uv.lock` | `uv lock` が作るロックファイル |
| `hello.py` | E3 のとおり argv と `RESOLOOP_PLUGIN_*` を表示する数十行の標準ライブラリだけのスクリプト |
| `skills/hello-guide/SKILL.md` | E4 |
| `recipes/hello-card.json` | E5 |

`args` の形は例であり、実行照合で動くことを確かめた形を正とする。動かなければ Plan の contingency に従う。

### 4.3 README の節と SKILL.md

- `README.md`（英語）と `README_JA.md`（日本語）: 「Plugins」「プラグイン」の節（4〜6行）。プラグインでできることを1〜2文、`plugin install`・`plugin list` と呼び方の例、`feat/plugin-v2` の機能であることと詳細への絶対 URL。既存の「Learn more」「さらに詳しく」は変えない（E10）。英日の意味をそろえる
- `README-DETAILS.md`: 「Plugins」の節に、`plugin install/list/remove`・プラグインのコマンド・`skills sync`・`uix recipe`・`doctor` の簡潔な表と、`docs/PLUGINS.ja.md`・`examples/plugins/hello/` への絶対 URL
- `skills/codex/resonite-build/SKILL.md`: C1 の2〜3行（英語）。このファイルは NuGet に pack され、`init` で利用者のプロジェクトへ配られるので、詳細の案内は既存の段落と同じく「`docs/PLUGINS.md` in the resoloop repository」と書き、プロジェクトの中の相対パスとして読める書き方にしない

## 5. 受け入れ基準

- 動作環境: Linux の本 Dev Container。.NET は上流の `global.json`（SDK 10.0.201、`rollForward: latestPatch`）に従う。uv と git はコンテナのもの。Windows は実行しないので、確認済みとは報告しない。Resonite・Blender・認証情報は使わない
- 実入力: `examples/plugins/hello/` を Git 管理外の一時ディレクトリへコピーした導入元と、それを `git init`・commit した一時 Git リポジトリ（`file://` URL と `--ref`）。ワールドのプロジェクトは一時ディレクトリに `resoloop init` で作り、名前に空白と日本語を含める（例 `作業 ワールド`）。`hello` へ渡す引数には `--json`・`--`・空文字・日本語と空白を含む引数を含める。外部プログラムは `hello.py`（uv で起動）。doctor の照合は、最小例の `plugin:hello:uv` が使える状態で出ることを確かめるのに加え、導入元のコピーの manifest の `tools` に存在しない実行名（例 `resoloop-hello-missing-tool`）を1件足した一時的な導入元で、不足の項目の出方を1回確かめる。不足の出方を文書に載せるときは、この実行の出力から写す（最小例そのものには足さない。Spec レビュー S7）
- 文書の内容: `docs/PLUGINS.md` と `docs/PLUGINS.ja.md` が D-1〜D-6 と4機能を説明している。導入・一覧・削除、`plugin remove` が `data/` を消す注意、コマンドの呼び出しの取り決め、スキル・レシピの配布、manifest の書き方、導入元の確かめ方と記録との照合、信頼・ハッシュ・サンドボックスの違い、現行の利用条件（旧不具合の追跡状況と分けて書く）、C6 の現状が書かれている。`README.md`・`README_JA.md` のプラグインの節から `docs/PLUGINS.md`（日本語版は `docs/PLUGINS.ja.md`）へ辿れる
- 実行照合: E13 の代表操作を文書の手順どおりに1回ずつ実行し、文書に載せた help と出力（パスなどの置き換えを除く）が実際と一致する。スキルは配布先 `.agents/skills/hello-guide/SKILL.md` の内容が package の内容と一致すること、レシピは `hello:hello-card` の名前と出力、`$recipe` を使った宣言の `validate` が通ること、doctor はプラグインの項目 `plugin:hello:uv` の結果を本体の項目と分けて照合すること（`ready: true` は要求しない）、remove の後に `.resoloop/plugins/hello/` が無く、`.agents/skills/hello-guide/` が残ることを確かめる。使ったコミット・コマンド・結果を PR 本文に書き、ログを `tmp/agents/` の下に残す
- 防御範囲: 文書にするのは4機能と承認済みの D-1〜D-6 のそのままの仕様である（縮小・再設計しない）。ハッシュは署名でもサンドボックスでもないこと、悪意ある同一ユーザへの完全な防御は対象外であることを書き、防げるものとして書かない。対象外の例: 旧例の `maxVersionExclusive: 0.2.0` をコピーしない、ResoLoop リポジトリの下位ディレクトリをそのまま `plugin install` に渡す案内をしない、open という状態だけで旧不具合を未修正と書かない、公開版 0.2.0 にプラグインがあるかのように書かない、上流で変わった行と所有範囲の外の節を変えない
- 英日: `docs/PLUGINS.md` と `docs/PLUGINS.ja.md`、`README.md` と `README_JA.md` のプラグインの節で、見出しの順と内容（コマンド・値・注意）が対応している
- 回帰: feature worktree で `dotnet build ResoLoop.slnx` と `dotnet test ResoLoop.slnx --no-build` が成功する（文書と例だけの変更でも、ビルドの入力が変わっていないことを確かめる）
- テスト: 文書の固定値テストは足さない（E12）

## 6. 実行の方法

- 実行方式: `--implement claude-code_sonnet_xhigh` で `self: false` のため、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Plan の Task を1つずつ順に依頼する。Task ごとのレビューは司令塔が行う。`--merge` を適用しないので、最後にブランチ全体のレビューを行う
- 検証の入口: resoloop の `AGENTS.md` の `dotnet build ResoLoop.slnx`・`dotnet test ResoLoop.slnx --no-build`、E13 の実行照合。push の前の Gitleaks の検査は、create-reso-world の親 checkout の `scripts/scan-before-push.sh`（`/workspaces/reso-world/scripts/scan-before-push.sh`。resoloop には無い）を司令塔が issue-to-pr の手順で実行する（Spec レビュー S2）。CI は usaturn/resoloop の Actions の設定に従い、PR の checks があれば確かめる
- 公開: コードの PR は `usaturn/resoloop:feat/plugin-v2` 宛て（本文に `Refs https://github.com/usaturn/create-reso-world/issues/101`）。文書の PR は `usaturn/create-reso-world:main` 宛て（Spec・Plan だけ）。#101 は fork 内 PR の取り込み後に調整役が閉じる

## 7. 範囲外

- 機能コードの変更、新しい API・コマンド・SDK・生成コマンド
- C6 の CLI 表示の修正（別 Issue）
- #110〜#112 の修正と close
- 署名・サンドボックス、NuGet への公開
- 上流 `orange3134/resoloop` への PR と上流 main への追従（#105）
- Meshy プラグイン（#102）と #328・#329
- ペイン以外の Herdr の操作、ワールドのプロジェクトの変更
