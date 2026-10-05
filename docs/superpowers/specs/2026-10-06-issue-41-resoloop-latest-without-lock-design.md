# Issue #41: ResoLoop の版のロックを廃止し、常に最新の公開版を使う 設計

- 文書管理／対象リポジトリ: `usaturn/create-reso-world`
- 対象: Issue #41「ResoLoop の版のロック（.devcontainer/resoloop.lock）を廃止し、常に最新の公開版を使う」
- 基準: `main` の `e6edcf8`（PR #38 のマージ後）
- 経路: brainstorming の architectural 経路（Issue の「進め方」の指定）
- 状態: draft（内容の明示承認はまだ無い）
- 実行許可: 2026-10-06 に利用者が「#41 に着手せよ。推奨案で進めて、途中で止めずに PR まで作成せよ」と指示した。この指示を、この Spec の推奨案で Plan の作成・実装・検証・push・PR の作成まで止まらずに進める許可として扱う。内容の確認は PR で受ける。マージは指示に含まない
- 関連 Plan: `docs/superpowers/plans/2026-10-06-issue-41-resoloop-latest-without-lock.md`
- PR: #45（未マージ。内容の確認をこの PR で受ける）
- 作成: 2026-10-06

## 1. 目的と前提

ResoLoop は常に NuGet の最新の公開版を使う。版を固定するロック（`.devcontainer/resoloop.lock`）と、それを読む仕組みを撤去する。Issue #41 の決定事項 1〜4 を前提とする。

1. 導入する版は NuGet の最新の公開版。公開されているのは `0.1.0-preview.N` のプレリリースだけなので `--prerelease` を付ける
2. rebuild のとき（postCreate）に最新を入れる。rebuild せずに最新へ上げる 1 行のコマンドを README に書く。postStart では更新しない
3. fork モードは、ロック無しの一時的な上書きとして残す。次の rebuild か、決定 2 の手動のコマンドで最新の公開版に戻る
4. 同梱スキル（`resonite-*`）の同期は手動のまま。postCreate は各プロジェクトの `resoloop skills sync --check` の結果を表示するだけで、差分があっても失敗しない

## 2. 調べた事実

この環境（dotnet `10.0.401`、SDK `10.0.201` と `10.0.401`）で、`--tool-path` の一時ディレクトリを使って確かめた。

| # | 事実 |
| --- | --- |
| F-1 | `dotnet tool update ResoLoop --prerelease --allow-downgrade` は、未導入なら最新を導入し、最新が導入済みなら「既にインストールされています」で 0 を返し、公開版より大きい版（`0.1.0-preview.17.fork.20261006.abc1234` に詰め直したパッケージ）が導入済みなら最新の公開版 `0.1.0-preview.17` へ戻す |
| F-2 | 同じ状態で `--allow-downgrade` を付けないと、「要求されたバージョン 0.1.0-preview.17 は、既存のバージョン … を下回っています」で 1 を返し、版は変わらない。Issue の「版を指定しない update では公開版に戻らないおそれ」は実際に起きる |
| F-3 | NuGet の版一覧（`v3-flatcontainer/resoloop/index.json`）は unlisted の版も返す。`dotnet tool` の最新の解決は unlisted を除く |
| F-4 | `resoloop skills sync --check` は、新しい版で同梱スキルが変わっただけなら `SKILL_SYNC_REQUIRED`、プロジェクト側で手を入れた同梱スキルがあれば `SKILL_SYNC_CONFLICT` を出す。終了コードはどちらも 6（`ValidationFailed`）。preview.17 では、4 プロジェクト（MyResoniteProject・akichi・slum02・slum03）すべてが `SKILL_SYNC_REQUIRED` になる |
| F-5 | 上流は、リリースの後に `src/RLoop.Cli/RLoop.Cli.csproj` の `<Version>` を次の版へ上げる（タグ `v0.1.0-preview.17` の時点では `0.1.0-preview.16`、上流 `main` では `0.1.0-preview.17`）。リリースは `-p:Version` で版を渡す |
| F-6 | `global.json` に合う SDK が無いと、そのディレクトリでの `dotnet --version` は 155 で終わる（`rollForward: latestPatch` の解決は dotnet 自身が行う）。`external/resoloop` では `10.0.201` を返す |

F-4 のため、`scripts/check-layout.sh` の検査 7（同期ずれを FAIL にする）を今のまま残すと、最新版を導入した時点で check-layout が失敗する。Issue の完了条件（check-layout が通る）と注意（同期は別の運用作業）を両立させるため、D-13 で検査 7 を変える。

## 3. 設計判断

### 導入（`.devcontainer/install_resoloop.bash`）

- **D-1 最新版の求め方**: 導入済みかどうかにかかわらず、`dotnet tool update --global ResoLoop --prerelease --allow-downgrade` を 1 回実行する（F-1）。`--allow-downgrade` は、fork の上書き（D-5 の版は公開版より大きくなり得る）から公開版へ戻すために要る（F-2）。NuGet の版一覧は読まない（F-3。最新の判断は dotnet に任せる）
- **D-2 NuGet に届かないとき**: update が失敗したとき、導入済みの版があれば `WARN` を出して続ける（その版のまま postCreate を通す）。導入済みの版が無ければ失敗させる。失敗の理由（ネットワークか、それ以外か）は区別しない
- **D-3 導入後の照合**: `~/.dotnet/tools/resoloop --version` の版が、`dotnet tool list --global` の ResoLoop の版と一致することを確かめ、導入した版（と更新前の版）を表示する。期待版を固定値で持たないので、照合の相手は dotnet が記録した導入済みの版にする。fork モードの分岐は外す

### 検証（`.devcontainer/verify-resonite-tooling.bash`）

- **D-4**: .NET 10 SDK があること、`resoloop --version` が動いて空でない版を表示すること、Blender が画面無しで動くことだけを確かめる。NuGet の最新とは比べない（ネットワークに依存させない。最新の導入は D-1 が担う）。確かめた版を表示する

### fork の一時的な上書き（`scripts/resoloop-fork.sh`）

- **D-5 上書きの版番号**: `<checkout の csproj の Version>.fork.<コミット日（UTC、YYYYMMDD）>.g<短い SHA>`。csproj の `<Version>` にプレリリースの部分が無ければ `.fork.` の代わりに `-fork.` を付ける。例: `0.1.0-preview.17.fork.20261006.gabc1234`
  - `fork` を含むので、公開版と区別できる（`status` はこれで fork のビルドかどうかを表示する）
  - コミットの SHA を含むので、コミットごとに変わる。日付はビルドした日ではなくコミット日なので、同じコミットからは同じ版になり、導入済みなら作り直さずに済む
  - SHA の前に `g` を付けるのは、数字だけの SHA（`0123456` など）が SemVer の「先頭が 0 の数値の識別子」になって不正な版になるのを避けるため
  - 基準を csproj の `<Version>` にするのは、上流がリリースの直後に次の版へ上げるため（F-5）。上流の `main` から作ったブランチは、最新の公開版より大きい版になることが多い。小さい版になっても、導入と戻しはどちらも `--allow-downgrade` を使うので困らない
- **D-6 ブランチやコミットの渡し方**: 引数で渡す。`install <ref>` と `checkout <ref>` は `<ref>` を必須にする。`origin` と `upstream` を fetch した後、`origin` に `<ref>` という名前のブランチがあればそれを使い、無ければ git がそのまま解決できる名前（コミット、タグ、ローカルのブランチ、`upstream/main` など）として解決する。解決した名前とコミットを表示する。fork のブランチ（決定 3）を名前だけで指定でき、push していないローカルのコミットもコミットの SHA で指定できる
- **D-7 remote の URL**: 固定値にする。`origin` は `https://github.com/usaturn/resoloop.git`、`upstream` は `https://github.com/orange3134/resoloop.git`（`scripts/superpowers_context.py` と同じ）。テストと特殊な運用向けに、環境変数 `RESOLOOP_ORIGIN_URL`・`RESOLOOP_UPSTREAM_URL` で差し替えられるようにする。checkout の位置の環境変数は `RESOLOOP_FORK_CHECKOUT` から `RESOLOOP_CHECKOUT` に改める（Issue の完了条件の検索パターン `RESOLOOP_FORK_` に一致するため）
- **D-8 `status` の表示**: ロックとの一致の代わりに、次を表示する。何も変更せず、ネットワークも使わない
  - 導入済みの版と、その種類（`NuGet release` か `fork build`。fork のビルドで、その SHA が checkout の HEAD と一致すれば、そのことも示す）
  - checkout の HEAD、ブランチ（または detached）、未コミットの変更の有無
  - remote が D-7 の URL と一致するか
  - fork のビルドが導入されているときは、公開版へ戻すコマンド（`bash .devcontainer/install_resoloop.bash`）
- **D-9 SDK の確認**: `require_sdk` は、checkout で `dotnet --version` を実行し、成功すれば SDK があるとみなす（F-6。`global.json` の `rollForward` の解決は dotnet に任せる）。失敗したら、`global.json` の `sdk.version` を表示し、`devcontainer.json` の `additionalVersions` に足して rebuild するよう案内して 3 で止まる。SDK は checkout の `global.json` から決まるので、`install` は clone と checkout の後に SDK を確かめる
- **D-10 その他のサブコマンド**: `clone`・`sync`・`test` の動作は変えない（URL の出どころだけが変わる）。`build` は HEAD のコミットから D-5 の版を作ってビルドする。追跡ファイルに未コミットの変更があれば 1 で止まる（版がコミットを名指すので、コミットに無い内容を同じ版で作らない）。`install <ref>` は、clone（無ければ）→ checkout → SDK の確認 → 版の算出の後、導入済みの版がその版と同じなら作り直さずに照合だけ行い、違えば build → `dotnet tool update --global ResoLoop --add-source <checkout>/artifacts/fork --version <版> --allow-downgrade` を実行して照合する。導入の後、公開版へ戻すコマンドを表示する
- 終了コードの区分（0・1・2・3・4）は今のまま。3 の「ロックの欠落・不正」は無くなる

### 共通の関数

- **D-11**: `.devcontainer/resoloop-lock.bash` を削除し、ロックと関係の無い 2 つの関数（`resoloop_installed_version`・`resoloop_version_of`）を `.devcontainer/resoloop-tool.bash` に移す。導入（D-3）と fork（D-8・D-10）の両方が 2 つとも使うので、それぞれに写すと食い違いが生まれるため、1 か所に置く。`verify-resonite-tooling.bash`（D-4）は版が空でないことだけを見るので、この関数集を読まない。関数の検査は `.devcontainer/test-resoloop-lock.bash` から `.devcontainer/test-resoloop-tool.bash` へ移す

### 同梱スキルの同期の表示

- **D-12 postCreate**: 新しいスクリプト `.devcontainer/report-resoloop-skills.bash` を、`install_beforehand.bash` の検証の手順の次の手順として実行する。各プロジェクト（`.resoloop.json` を追跡している直下のディレクトリ。`check-layout.sh` の `collect_projects` と同じ定義）で `resoloop skills sync ./<project> --check` を実行し、プロジェクトごとに「最新」「更新がある（`SKILL_SYNC_REQUIRED`）」「確認に失敗した（それ以外。手で編集した同梱スキルの `SKILL_SYNC_CONFLICT` を含む）」を表示する。後の 2 つは resoloop の出力を字下げして添え、`--update` の前に差分を見るよう案内する。スクリプトは常に 0 で終わる（resoloop が無いときも表示して 0）
- **D-13 `scripts/check-layout.sh` の検査 7**: `--check` が 6 で終わり、出力の 1 行目が `SKILL_SYNC_REQUIRED` で始まるときは、`warn:` の行と resoloop の出力を表示して、失敗には数えない。それ以外の失敗（`SKILL_SYNC_CONFLICT` など）は今までどおり FAIL にする。常に最新を入れると、上流のリリースのたびに同期ずれが起きる。それを、作業と関係の無い check-layout の失敗にしないため。手で編集した同梱スキルの検出（`SKILL_SYNC_CONFLICT`）は残す
- **D-14 `scripts/check-layout.sh` の検査 8**: ロックの検査を外す。検査 9（mount）を 8 に番号を詰める

### 文書

- **D-15 README の手動のコマンド**: rebuild せずに最新へ上げる 1 行のコマンドは `bash .devcontainer/install_resoloop.bash` とする。postCreate と同じ処理で、照合（D-3）まで行う。中で実行する dotnet のコマンド（`dotnet tool update --global ResoLoop --prerelease --allow-downgrade`）も併記する
- **D-16 README の見出し**: `## ResoLoop の版` は変えない。`tests/scripts/test-docs.bash` が README の見出しの一覧を固定値で比べており、その扱いは #36 で決めるため（Issue #41 のコメントのとおり、#36 が決まっていなければ見出しを残す）。節の本文だけを書き換える
- **D-17 `AGENTS.md`**: 「ResoLoop の版管理」節の見出しは残し（`tests/scripts/test-instructions.bash` がこの見出しを境界に使う）、本文を決定事項 1〜4 に合わせて書き換える
- **D-18 `docs/resoloop-fork-workflow.md`**: 全体を書き換える。最新の導入と手動の更新、fork の一時的な上書きと戻し方、上流へ PR を出すための fork の使い方、`tmp/` の旧 checkout の整理（ロックへの言及だけを外す）、上流への PR 候補
- **D-19 `docs/integration.md`**: 「PR のマージ後にユーザが行うこと」の 9 番（Rebuild の手順）と、「Rebuild 後に確かめること」の 2 番を新しい仕組みに合わせる。各フェーズの「実施したこと」は変えない
- **D-20 スキル `repo-cleanup-after-merge`**: 「fork の経路だけの手順」は、fork の checkout が `checkout`（引数なし）でロックのコミットに置かれていることを前提にしている。`checkout` は引数を必須にするので（D-6）、この前提と復元の手順を、checkout をそのまま残す形に書き換える。手順の構成（`sync` を先に実行する、手順 7 を実行しない）は変えない
- `.devcontainer/README.md`・`.devcontainer/devcontainer.json`（`additionalVersions` のコメントを、上流の `global.json` を基準にする書き方へ）も合わせる

## 4. ファイル別の変更

| ファイル | 変更 |
| --- | --- |
| `.devcontainer/resoloop.lock`・`.devcontainer/resoloop-lock.bash`・`.devcontainer/test-resoloop-lock.bash` | 削除 |
| `.devcontainer/resoloop-tool.bash`（新規、100755） | D-11 の 2 つの関数 |
| `.devcontainer/test-resoloop-tool.bash`（新規） | 2 つの関数の検査（ロックのテストの 7・8 を移す） |
| `.devcontainer/install_resoloop.bash` | D-1〜D-3 |
| `.devcontainer/verify-resonite-tooling.bash` | D-4 |
| `.devcontainer/report-resoloop-skills.bash`（新規） | D-12 |
| `.devcontainer/install_beforehand.bash` | 手順名の変更、D-12 の手順の追加（`STEP_TOTAL` を 26 に） |
| `.devcontainer/devcontainer.json` | `additionalVersions` のコメント |
| `scripts/resoloop-fork.sh` | D-5〜D-10 |
| `scripts/check-layout.sh` | D-13・D-14 |
| `AGENTS.md`・`README.md`・`.devcontainer/README.md`・`docs/resoloop-fork-workflow.md`・`docs/integration.md` | D-15〜D-19 |
| `.agents/skills/repo-cleanup-after-merge/SKILL.md` | D-20 |
| `.devcontainer/test-install-resoloop.bash`・`.devcontainer/test-verify-resonite-tooling.bash`・`tests/scripts/test-resoloop-fork.bash` | 新しい挙動に合わせて書き直す |
| `.devcontainer/test-report-resoloop-skills.bash`（新規） | D-12 の挙動の検査 |
| `tests/scripts/test-check-layout.bash` | 検査 7 の変更（更新は warn で通過、衝突は FAIL）。ロックの一時リポジトリを、mount の検査だけに使う形にする（衝突中・壊れたオブジェクトの検査は `initialize.bash` で行う） |
| `tests/scripts/test-docs.bash`・`tests/scripts/test-instructions.bash`・`.devcontainer/test-readme.bash`・`tests/scripts/test-file-modes.bash` | ロックへの言及を外す（ファイルの一覧から外すだけで、代わりの固定値は足さない） |

## 5. テストの方針

- テストは、モックの dotnet・resoloop と一時リポジトリで挙動を確かめる。版番号は、テストが自分で作る入力（モックが返す版）だけを使い、リポジトリの設定や NuGet の版を固定値で検査しない（`AGENTS.md` の基本方針、#36）
- `test-verify-resonite-tooling.bash` にある postCreate の手順名の固定文字列の検査（`step "Installing the ResoLoop version pinned in ..."`）は削除し、新しい手順名では書かない。postCreate が `install_resoloop.bash`・`verify-resonite-tooling.bash`・`report-resoloop-skills.bash` を呼ぶこと（配線）と、`STEP_TOTAL` と手順の数の一致は確かめる
- fork の版番号の検査は、モックの checkout の csproj とコミットから期待値を組み立てて比べる（固定の版を書かない）

## 6. 検証（Issue の完了条件）

1. `.devcontainer/resoloop.lock` と `.devcontainer/resoloop-lock.bash` が無い
2. `git grep -n -E 'resoloop\.lock|resoloop-lock|RESOLOOP_(MODE|NUGET_VERSION|FORK_)'` の結果が、`docs/superpowers/**`・`docs/maatlog-poc-porting.md`・`.agents/skills/rst-writer/evals/fixtures/**`・`scripts/superpowers_context.py` だけになる
3. コンテナ内で `bash .devcontainer/install_resoloop.bash` を実行し、NuGet の最新の公開版が入り、`resoloop --version` がその版を返す
4. fork の上書き（D-5 の版）を入れた状態から、`bash .devcontainer/install_resoloop.bash` で最新の公開版に戻る。実 fork のビルドは時間がかかるので、F-1 と同じ詰め直したパッケージで `--global` の導入を作り、そこから戻す
5. `docs/resoloop-fork-workflow.md` の手順どおりに `bash scripts/resoloop-fork.sh install <fork のブランチ>` で fork のビルドを一時的に導入できる（実際に `external/resoloop` でビルドして確かめ、4 の戻しもこの状態から行う）
6. `bash .devcontainer/report-resoloop-skills.bash` の出力に各プロジェクトの結果が出て、差分があっても 0 で終わる
7. `uv run pytest tests/skills .agents/skills`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、各プロジェクトの `uv run pytest` が通る

## 7. 範囲外とリスク

- 同梱スキルの `--update`（4 プロジェクト）は行わない。Issue のとおり別の運用作業である。最新版の導入後は、check-layout が 4 プロジェクトについて `warn:` を表示する
- `zshrc.txt` の `update()` に ResoLoop の更新は足さない（決定 2 は README のコマンドだけを求めている）
- rebuild のたびに apply の挙動が変わり得る。使っている版は `resoloop --version` で確かめる（README と `AGENTS.md` に書く）
- 実際の rebuild での確認は利用者が行う
