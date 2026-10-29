# Issue #95: 最新上流から ResoLoop のプラグイン機構を再計画する

## 管理・状態・許可

- 文書管理: `usaturn/create-reso-world`。対象ボード: https://github.com/usaturn/create-reso-world/issues/95
- 実装対象: `usaturn/resoloop`。上流: `orange3134/resoloop`。Meshy の後続対象: `usaturn/resoloop-meshy`
- 状態: **completed**（親設計・ボード更新・PR #296 のレビュー判断まで。プラグイン機能と子の計画・実装は未完了）。2026-10-29 UTC、コミット `d009286968a21c916bafb39b2308ebaa09d40c4c` を示した確認依頼に、利用者が「OK」と回答した。この内容承認は実装・公開の実行許可とは区別する。PR レビューの記録は第9章。
- 利用者の指示: 古くなったプラグイン Issue 群を、最新上流を基準に計画し直す。既存 fork・履歴を残し、新しい上流起点ブランチを使う提案に「基本的にOK」、既存案の仕様・作成・配布・導入方法を説明した後に「OKです。作業を続行してください」。これは調査・再計画の続行許可であり、未提示の設計の承認、本体の実装・push・PR・マージの許可にはしない。
- 今回の区切り: 設計の保存、独立した builder check、ローカルコミット、確認用コピーの提示。承認後に `writing-plans` で計画し、既存ボードの更新へ進む。本セッションでは GitHub の Issue 本文・状態・依存関係は変更しない。
- この新規文書を作る理由: 利用者が最新上流からの再設計を明示したため。旧 #97 の completed な設計・計画は当時の実装記録として残し、本書を親 #95 の再計画の定義元にする。旧文書を書き換えて現在の実装と見せかけない。
- 旧基盤の記録: [#97](https://github.com/usaturn/create-reso-world/issues/97)、[usaturn/resoloop#20](https://github.com/usaturn/resoloop/pull/20)、`2026-10-16-create-reso-world-issue97-resoloop-plugin-core-design.md`。当時の制限は `2026-10-16-usaturn-resoloop-pr20-plugin-core-review-fixes-design.md`。
- Plan: `../plans/2026-10-29-create-reso-world-issue95-plugin-replan.md`（ボード更新の実行計画。作成時点では draft、内容承認・実行許可は別途確認する）。

### 基準と作業場所

2026-10-28 18:59 UTC に fetch・確認した値。版を運用で固定する指定ではなく、再計画の調査基準である。

| 対象 | 基準・場所 |
| --- | --- |
| 上流 `upstream/main` | `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`、ResoLoop 0.2.0 |
| fork `origin/main` | `ff77b91d1f17c7dba861416d82f1a6c8929f2805`。上流との差は fork 側1・上流側2コミット |
| create-reso-world `origin/main` | `6733fc25d945d5b1b7c0ea9dc831d516453d7843` |
| `PARENT_ROOT` | `/workspaces/reso-world`。上記 origin/main の detached HEAD、追跡ファイル clean |
| `DOC_ROOT` | `/workspaces/reso-world/.worktrees/resoloop-plugins-replan`、`docs/resoloop-plugins-replan` |
| コード元 checkout | `/workspaces/reso-world/external/resoloop`。`4077350` の detached HEAD、未追跡 `reviews/` あり。切替・削除しない |
| 新しいコード worktree | `/workspaces/reso-world/external/resoloop/.worktrees/plugin-v2`、`feat/plugin-v2`。上流の基準 SHA から作成、コード無変更 |

fork の削除・再作成、main の reset・force push はしない。fork main は通常の同期スクリプトの fast-forward 条件を満たさない。必要な開発基点は新ブランチで確保する。既存 texture-transfer worktree とローカルワールドも対象外。

## 1. 目的と成功条件

ResoLoop 本体に、特定サービスに依存しないプラグインの入口を設ける。プラグインの作者は通常の外部ツールと manifest を作り、Git で配布し、利用者はプロジェクト単位で導入する。後からプラグインを増やすたびに本体へ専用コードを足す必要をなくす。

完成時には次の4機能をすべて使える。調査担当が提案した「スキル・レシピ・doctor を v1 から外す」という縮小案は、利用者へ説明した範囲と異なるため採らない。

1. `resoloop <plugin-command> ...` による外部コマンドの実行。
2. `init`・`skills sync` によるプラグインスキルの配布。利用者のファイルを保護する。
3. `uix recipe list|describe|export` と `$recipe` からのプラグインレシピの利用。
4. `doctor` による必要な外部ツールの確認。不足の検出を成功と報告しない。

Meshy は機構の一部ではなく後続の利用例とする。汎用機構の完成・上流提案は Meshy の実モデルや Blender/open3d の仕上げ処理の完成を待たない。

### 対象外・失敗とみなすこと

- `plan`・`apply`・`test` の任意処理へ割り込む実行フック、.NET アセンブリの本体内ロード。
- 自動更新、依存ツールの自動インストール、マーケットプレイス、専用レジストリ、ZIP 配布、開発用リンク導入、SDK・雛形生成コマンド。
- 既存インストールの自動移行、全ローカルワールドへの一括導入・削除。
- Meshy API、Tripo、旧 fork 専用の preproduction 機能の再導入。
- ハッシュ照合を署名検証やサンドボックスと呼ぶこと。プラグインは利用者と同じ権限で動く。
- 最新の NuGet 公開版の運用を古い fork ビルドへ恒久的に置き換えること。

## 2. 調査した現在の構造

- 上流基準と fork main に `src/RLoop.Core/Plugins/` はない。旧 #97 の完了と PR #20 のマージは歴史的事実だが、後続が利用できるコードが現在の対象ブランチにある証拠にはならない。
- `src/RLoop.Cli/Program.cs` は冒頭で `ParsedArguments.Parse` を実行する。未知名が最終分岐まで進むと、その前に ResoniteLink へ接続する。
- `src/RLoop.Cli/CommandLine.cs` の既存パーサは `--` を拒否し、未知のオプションに続く引数を消費し、`--help` などを本体の指定として処理する。この解析後の値からプラグインの生引数は復元できない。
- `BundledSkillManager` の `.agents/skills/.resoloop-bundled.json` は同梱ファイル専用で、更新時に同梱ファイル一覧から作り直す。プラグインの記録を混ぜない。
- `UixRecipes.Catalog` は埋め込みの同梱レシピ一覧で、同梱スキルの配布にも使う。実行時のプラグインをこの静的一覧に混ぜない。
- `ApplyDocumentCompiler.Compile(path)` は `$recipe` を `UixRecipes` から展開する。プロジェクト別の解決文脈が必要で、static な可変グローバル状態にしてはならない。
- `ProjectInitializer` は既存の生成ファイルに内容差があると全体を止める。プラグイン用 ignore のために既存 `.resoloop/.gitignore` のテンプレートを変更しない。
- create-reso-world の `scripts/new-world.sh --apply` は `.agents/skills/` の各実ディレクトリに対応する `.claude/skills/` のリンクを補う。既存の仕組みを使い、ResoLoop 本体にこのリポジトリ固有のリンク処理を入れない。

## 3. 検討した進め方

| 方式 | 利点 | 採らない理由・採用理由 |
| --- | --- | --- |
| 旧 fork main に上流をマージし、旧 PR をまとめて戻す | 過去のコードを使いやすい | fork 専用機能と旧前提を持ち込み、上流提案の差分が膨らむため不採用 |
| 最新上流の新ブランチへ必要な設計・コードだけを移す | 差分をプラグインに限定でき、過去の履歴も保てる | **採用**。利用者がこの進め方を了承。過去のコミットは参考にし、無条件に cherry-pick しない |
| 本体は変更せずラッパーだけ作る／`plugin run` のみに縮小する | 本体への影響が小さい | 既存案の直接コマンド、skills sync、レシピ、doctor の統合を満たさないため不採用 |

以下の具体的な仕様は設計時のエージェント提案を含む。方式への了承だけから承認を推測せず、上記のコミット済み内容への「OK」を承認根拠として記録した。

## 4. 作者・配布・導入の仕様

### D-1 パッケージと manifest

ルートに `resoloop-plugin.json` を置く。旧 #97 の v1 の欄（`schemaVersion`、`name`、`version`、`description`、`resoloop`、`commands`、`skills`、`recipes`、`tools`）と型・上限・SemVer 比較を引き継ぐ。未知欄・重複欄は拒否する。対応版の例は 0.2.0 を基準に書き直し、旧例の `maxVersionExclusive: 0.2.0` をコピーしない。

プラグインの記述は外部プログラム、スキル、JSON レシピ、必要ツールの宣言であり、4種類すべてが必須ではない。動く最小例を文書タスクで用意し、SDK・生成コマンドは作らない。依存環境の準備方法は作者が文書に書く。

### D-2 導入元と保存先

- ローカルディレクトリ、または Git URL＋明示的な `--ref` から導入する。Git では実際のコミットを記録し、導入後に自動追従しない。
- Git からの配布では manifest がリポジトリのルートにある。手動 clone は不要。private リポジトリの認証は Git の既存機構を使い、URL の資格情報を記録しない。
- `<project>/.resoloop/plugins/<name>/{install.json,package/,data/}` に保存する。`--project DIR`、または cwd から上への `.resoloop.json` の探索で対象を特定し、見つからなければ作らない。
- コピー方式で、導入時にプラグインのコードを実行しない。言語の依存パッケージの取得も install 自体では行わない。
- Git の作業ツリールートにあるローカル導入元は、追跡ファイルと ignore されていない未追跡ファイルを対象とする。Git 外のディレクトリは `.git` を除く通常ファイルを対象とする。Git 管理かどうかの確認失敗を「Git 外」と見なして全部コピーしてはならない。
- コピー元の実パスと Git の最上位を比較し、リンクを経由した指定でも ignored ファイルを取り込まない（#110）。Git の操作は親プロセスの `GIT_DIR`・`GIT_WORK_TREE` 等で別リポジトリに向かないよう隔離する。必要な credential helper の認証は維持する。
- 導入先 `plugins/.gitignore` を installer が管理し、`package`・`data`・記録・staging を Git へ誤追加しにくくする。既存の異なるファイルは上書きせず停止する。プロジェクト既存の `.resoloop/.gitignore` は変更しない。

### D-3 安全な導入・削除・照合

旧 #97 の全ファイル照合、staging からの確定、件数・容量制限、名前の衝突拒否を引き継ぎ、#110〜#112 を基盤の受け入れ条件に含める。

- `.resoloop`・`plugins`・対象プラグイン・`package` と配布先の経路について、書き込み・読み込み・削除で外部のリンク先を操作しない。symlink/junction を拒否し、子リンクを辿らない。
- manifest の参照パスだけでなく `install.json` のファイル名も検証し、`..`・絶対パス・大小文字差での衝突等を使った範囲外操作を防ぐ。
- 同一プロジェクトの導入・削除は排他する。名前の照合から確定までに別プロセスが入って衝突した導入を成功させない。OS のプロセス終了で解放されるロック方式とし、経過時間だけで他の処理のロックを削除しない。
- 導入に失敗しても既存の導入物・記録は変えず、自分の staging だけを片付ける。
- `package/` 全体を利用前に照合する。内容変更・追加・欠落・リンクの差し替えを検出したプラグインは使わない。`data/` は照合対象外。
- `plugin list` は壊れたプラグインも問題付きで表示する。`remove NAME --yes` は記録が壊れていても、安全な実ディレクトリだけを削除できる。
- remove が消すのは指定名の導入ディレクトリ（`data/` を含む）のみ。配布済みのスキル・外部の記録・利用者の成果物は消さない。更新は remove＋install のままとし、データを保持する更新機能は追加しない。データ削除の注意を help と文書に記載する。
- ハッシュは意図しない差分の検出であり、`install.json` を同じ権限で書き換えられる相手への防御や、配布者の信頼の保証ではない。悪意ある同一ユーザによる競合差し替えへの完全な防御は対象外。

## 5. 4機能の統合

### D-4 コマンドと doctor（#98）

既存の組み込みコマンドの構文・出力を変えず、プラグイン呼び出しだけを既存パーサより前に分離する。

- プラグイン呼び出しの構文は `resoloop [--project DIR] <plugin-command> [arguments...]` とする。`--project=DIR` も同じ意味。ホストが解釈する指定はコマンド名より前の `--project` のみ。
- プラグイン名より後のトークン（`--help`・`--version`・`--json`・`--`・空文字・空白・非 ASCII を含む）は順序・値を変えずプラグインへ渡す。引数を文字列へ連結してシェルで実行しない。
- 組み込み名を常に優先し、導入時と実行時の予約名判定を共通化する。0.2.0 で増えた `bundle`・`import` 等も含む。大文字小文字の比較を本体と一致させる。
- コマンドの解決・照合は ResoniteLink 接続前に行う。本体は外部コマンドのためだけに接続しない。必要ならプラグインが明示的に本体コマンドを呼ぶ。未登録名も接続前に `UNKNOWN_COMMAND` とする。
- cwd はプロジェクトルート。manifest の `${pluginRoot}`・`${pluginData}` と、プロジェクトの場所・本体の呼び戻し方を渡す。接続情報を渡す場合も、発見・接続を暗黙に実行しない。
- 子の stdout/stderr はそのまま転送し、通常終了では子の終了コードを保持する。`--json` を子へ渡す場合は作者が JSON 出力を実装する。本体が子の JSON を二重に包まない。起動前のエラーは本体のエラーとして stderr に報告する。
- manifest の `timeoutSeconds`、省略時は本体の `commandTimeoutSeconds` を使用する。期限・キャンセルで成功を返さず、子孫の停止を確認する。実行時の Python キャッシュや uv 環境は `data/` に向け、`package/` を変更しない。
- doctor の tools 検査は明示的な doctor 実行時だけ行う。検査プログラムにも期限を設け、required 不足・検査失敗をプラグイン名とともに示す。プラグイン無しの結果・必須判定は維持する。確認だけで、導入や修復は行わない。

具体的な環境変数名、呼び戻し argv の表現、エラーコード、キャンセルの停止手順は #98 の Spec で固定する。これらは上の意味を保つ実装上の判断として残し、#102 は確定した仕様だけを使う。

### D-5 スキル（#99）

- 同梱の `.resoloop-bundled.json` は同梱専用のままにする。プラグインの配布記録は別の `.agents/skills/.resoloop-plugins.json` に持つ。
- `init`・`skills sync --check|--update` で、照合済みのプラグインが宣言する `skills/` の通常ファイルを `.agents/skills/<skill-name>/` へ配る。`resonite-` と同梱名は予約する。
- 同梱・全プラグインの競合を事前確認してから書き込みを始める。利用者が編集したファイル、所有の記録がない既存ファイル、リンク先へは書かない。失敗後に未配布のファイルを配布済みとして記録しない。
- アンインストール後も配ったファイルと、その保護に必要な記録は残す。再導入時は最後に配った内容との比較で利用者の編集を保護する。
- プラグイン無しの既存 init・sync の成果物や同梱の記録形式を変えない。既存の生成ファイルをプラグイン導入の都合で書き換えない。
- create-reso-world の利用者は sync 後に既存の `scripts/new-world.sh --apply <world>` で Claude 用リンクを補う。汎用 ResoLoop は `.claude/` を操作しない。

### D-6 UIX レシピ（#100）

- 組み込みの `UixRecipes.Catalog` と既存名・生成キーは変更しない。プロジェクトのプラグインレシピは別の読み取り専用 resolver で合成する。
- 外部で使う名前は `<plugin-name>:<recipe-name>`。manifest の `recipes[].name` はローカル名のままとする。プラグインの裸のレシピ名を暗黙に探索しない。
- `uix recipe` は選択プロジェクトの resolver、宣言ファイルの `$recipe` は主入力ファイルの場所から探索したプロジェクトの resolver を使う。cwd や include 先の都合で別ワールドのプラグインを選ばない。プロジェクトを参照しない既存の組み込みレシピ利用は維持する。
- プラグインの生成キーは `uix-plugin--<plugin-name>--<recipe-name>--<caller-key>` を基点とする。各ローカル名は連続する `--` を含まない旧名前規則を使い、組み合わせの境界を曖昧にしない。同じ入力から同じ展開を得る。
- 宣言が要求するプラグインが未導入・不整合なら、ワールドを変更する前に停止する。レシピは JSON の展開であり、プラグインの実行フックにはしない。

## 6. Issue の分割と所有権（更新案、未公開）

新規 Issue はまだ作っていない。以下の `F`・`I` はキーであり、Issue 番号ではない。番号を推測して本文や native relation に書かない。

| キー / Issue | 成果と主な所有ファイル | 直接の先行 |
| --- | --- | --- |
| F: `plugin-core-refresh`（新設） | `src/RLoop.Core/Plugins/` の manifest・記録・installer・registry・排他・パス保護と対応テスト。D-1〜3、#110〜112 の再発防止を含む | なし |
| #98 `plugin-commands` | `PluginCommandRunner.cs` 等の実行コード、新設 CLI helper・組み込み名 catalog・doctor helper と対応テスト。`Program.cs` は変更しない | F |
| #99 `plugin-skills` | 新設 `PluginSkillManager.cs`、`BundledSkillManager.cs`、`ProjectInitializer.cs` と対応テスト。`Program.cs` は変更しない | F |
| #100 `plugin-recipes` | `UixRecipes.cs`・`ApplyDocumentCompiler.cs`・必要な `ApplyDocument.cs` の resolver 伝搬と対応テスト。`Program.cs` は変更しない | F |
| I: `plugin-cli-integration`（新設） | `Program.cs`・必要な `CommandLine.cs` の変更を専有。install/list/remove、コマンド、init/sync、レシピ、doctor を接続し、4機能を一時プロジェクトで通す | #98、#99、#100 |
| #101 `plugin-docs` | `docs/PLUGINS.md`、短い英日 README・README-DETAILS、影響する同梱スキル、最小の作者向け example | I |
| #105 `upstream-proposal` | 上流への相談文・PR の分け方と、利用者確認後の投稿 | #101 |
| #90 `meshy-finish` | Meshy 側の知見と仕上げの道具。既存の範囲を維持 | #96、#91 |
| #102 `meshy-plugin` | Meshy リポジトリの manifest・入口・スキル・必要ツール | #90、I |
| #103 `meshy-switch` | create-reso-world の API 連携撤去と利用案内 | #102 |
| #110・#111・#112 | F の結果と各不具合の対応を記録する。別実装・重複テストは足さない | F |

F が manifest・検証済みパッケージ・導入記録・予約名を受け取る registry API を固定する。#98〜#100 はその API を勝手に変更しない。名前 catalog は #98、CLI への結線は I が所有する。共有 API の変更が必要なら親 #95 の調整役が裁定し、各担当の Spec・Plan を先に更新する。I が最終統合を担当する。

コードの統合先は上流起点の `feat/plugin-v2` とする。将来、push・PR・マージが許可された段階で、子はこのブランチから分岐して同ブランチ宛ての fork 内 PR でレビューする。fork の `main` を子 PR の base にせず、旧 fork 専用変更を取り込まない。上流へ提案するブランチにもこのプラグイン系列だけを含める。現時点では統合先はローカルにのみ存在し、remote branch・PR は作らない。

既存ボードの公開台帳は削除せず、過去の関係を履歴として識別できる形で更新する。native な子・依存関係はこの直接先行表から生成する。F 後の3機能だけを並行に進め、I は3件の完了と対象ブランチでの利用可能性を待つ。

### 旧 Issue・完了記録の扱い

- 親 #95 を再利用する。#91・#96・#97・usaturn/resoloop#18 の completed は履歴として残す。#97 を reopen して新実装を混ぜない。
- #98〜#100 の #97 依存を F に差し替える。旧 #97 の closed だけで着手可能と表示しない。
- #110〜#112 は F に統合するが、設計時点で解決済みにしない。新コードで防御を検証した結果を各 Issue に記録してから completed にする。
- #104 は fork 専用 preproduction を対象とし、新基準に対象ファイルがない。ボード更新時に「この再計画には含めない」旨を記録し、not planned で閉じる案とする。旧 fork のコードを持ち込んで達成しない。
- #105 の Meshy 完了待ちと #110〜#112 の個別修正待ちは外し、#101 を待つ。安全条件は F と I の受け入れに含まれる。
- #103 の usaturn/resoloop#18 待ちは外す。今回の上流基準に Meshy 同梱はないためで、create-reso-world 側の API 撤去が済んだと見なす意味ではない。

## 7. 受け入れ基準と検証方針

### 動作環境

Linux の本 Dev Container、.NET は上流 `global.json` に従う。Windows も利用対象で、argv・パス・プロセス・junction の OS 差を扱う。Windows の実行確認をしていない状態を実機確認済みと報告しない。Git は一時的なローカルリポジトリ、外部プログラムは偽のツールを使う。通常の検証に Resonite・Blender・Meshy・認証情報は不要。

### 実入力

- 空白・日本語を含む `作業 ワールド` とプラグインディレクトリ。引数の空文字、改行を含む文字列、`--help`、`--json`、`--`、`;`・`$()` を含む値を、偽の子の受信 argv と照合する。
- Git の追跡外だが ignore されていないファイルと、ignore した偽の機密ファイルを含む開発リポジトリ。直接パスとリンク経由の同じ入力に対する同じ守りは代表ケースに絞る。
- 利用者編集済みのスキル、所有記録のない同名ファイル、取り外したプラグインの旧スキル。
- プラグインレシピを使う主入力と include、cwd とは別のプロジェクト、同じローカル名を持つ別プラグイン。

### 防御範囲と対象外の反例

削除・上書きの範囲、導入後の意図しない差分、誤ったプロジェクト選択、Git 環境による導入元の取り違え、衝突、失敗の成功報告、実行時データとパッケージの混同を防ぐ。許可例も必ず残し、何でも拒否する実装にしない。

同一ユーザの悪意あるプロセス、導入元コードの信頼判定、ファイル・ネットワークのサンドボックス、署名・鍵の配布は対象外。Windows と Linux の差を偽の path 文字列だけで検証したことにしない。

### テストの採用

| 守り | 区分と方法 |
| --- | --- |
| 範囲外削除・リンク先操作、Git の誤ったコピー・資格情報の記録、競合、失敗で既存の記録を失う | S。F のモジュールで実行テスト。旧 #110〜#112 の代表再現を含む |
| 子への引数の変形・シェル解釈、組み込みの乗っ取り、失敗・時間切れを成功扱い | S。#98 と I に責務を分け、同じ守りを重複させない |
| 利用者のスキルを上書き・削除する、書き込み失敗を配布済みとして記録する | S。#99 で代表ケース |
| 別プロジェクトのレシピを選ぶ、展開結果・キーを取り違える、未導入のままワールド変更が進む | S。#100 で入力から展開・拒否を確認 |
| manifest や公開 CLI の不正入力が明示的なエラーになるだけの経路、構文・型・help | L。通常の実行・静的検査で確認。安全境界を通してしまう場合は S として扱う |
| 文書・モデル名・固定一覧・版・ファイルの存在だけの照合 | F。追加しない。既存の履歴保護・権限の F∩S は維持 |

本セッションは設計文書だけのため、テストを追加せず、本体の build/test や実機受け入れを実行したと報告しない。文書差分・リンク先・保存コピーとコミットの一致を確認する。将来の各 Task のテストの要否と正確な検証コマンドは Plan に記載する。

## 8. 実行・公開の境界と次の手順

1. この draft をローカルコミットし、`scripts/superpowers-review-copy.sh` で確認用コピーを公開する。`docs_draft/superpowers/specs/` にも同じ内容を置く。
2. コミット済み内容の承認後に `writing-plans` を使う。受け入れ基準・防御範囲・動作環境、各 Task のテスト採否、実行予算・contingency を記した Plan を提示する。
3. ボードを更新する段階で最新の本文・全コメント・全 native relation・予約 ref を読み直す。権限・ruleset・Actions を確認して親 #95 を固定 ref で予約し、調整役が既存本文の管理範囲・公開台帳を更新する。F・I を作って実 ID を保存し、直接先行表と native relation の一致を再取得で検証してから予約を解放する。
4. 子ごとの Spec・Plan・handoff と復元検証が終わるまでは planning: ready としない。今回の親設計だけで全子を ready にしない。
5. 実装は別の許可後に、上流起点の feature branch／各 Task の worktree で行う。fork main に独自実装を蓄積する運用へ戻さない。新規コードは秘密情報検査後にだけ push する。
6. 上流への投稿文は #105 で利用者に提示し、投稿の確認を取る。設計承認から投稿の許可を推測しない。コードの統合先・PR の構成はその Plan と実行許可で固定する。

### 初回設計セッションの成果状態（2026-10-28 UTC）

- 新しい上流起点の branch/worktree: 作成済み、コード無変更。
- 設計: draft。独立した sp-review の builder check は「nothing important left」。文書以外を変更せず、ローカルコミットとコピーの照合後に提示する。
- Plan・Issue 更新・本体実装・push・PR・上流投稿: 未実施。
- GitHub 公開: **公開未実施**。確認用コピーはローカル閲覧用で、遠隔の復元元ではない。

### 独立確認の記録

- Issue 調査担当は旧完了記録と現行 tip の不一致、#104 の対象不在を確認した。単一行 JSON が読み取り上限に当たった #91 のコメントは調整役が Markdown に整形して補足確認した。
- コード調査担当は raw argv・接続前の分岐・同梱スキルの記録・レシピ resolver の問題を確認した。提案に含まれた4機能の縮小と古い予約名リストへの評価は、そのまま採用せず調整役が実コード・旧文書と照合した。
- builder check の初回依頼はロール指定不足で NEEDS_CONTEXT。`Review scope: task` と受け入れ基準を付けた再依頼で文書全体を確認し、「nothing important left」。コードのテストを実行したという意味ではない。
- 調査・設計・独立確認は 2026-10-28 18:59〜19:21 UTC（約22分）。以降は文書の保存・確認コピー・引き継ぎの整備。

## 9. PR #296 のレビュー判断（2026-10-29 UTC）

### 対象・許可・結論

- 対象: https://github.com/usaturn/create-reso-world/pull/296 。判断対象 HEAD は `c87c34b605da88ceecab18fa783cfca2d01dc35b`、検証した base は `6733fc25d945d5b1b7c0ea9dc831d516453d7843`（HEAD の祖先）。差分は本書と同テーマ Plan の2文書だけ。
- 実行許可: 利用者による `pr-review-fix-loop #296 --assign inspect=claude-opus,devin-swe,pigod` の明示起動。今回の文書 PR のレビュー判断・必要な修正・検証・通常 push・修正不要の場合の最終化を含む。以前の設計・ボード作業に対するマージ禁止は当時の範囲であり、この別の明示指示と区別する。子の計画・本体実装・fork への push・上流投稿には広げない。
- planner: `openai-codex/gpt-6-astra`（pi）。サイクル1、loop run `f1ebb608a04c460b8530604624c1641b`。
- 結論: **2 修正不要**。5出典を4判断にまとめ、解消済み0・対応する0・対応しない4（出典数では5）。事実としての文書の不足と、現行構成で到達する致命的な欠陥を区別した。以下は採否・検証の完了記録であり、push・マージ・Issue更新の実施結果はPRの状況コメントと完了報告に残す。
- 同テーマの既存Specは本書だけであるため本書を更新した。承認済みのD-1〜D-6・所有範囲・Planの操作は変更していない。過去の状態表現は当時の記録として残す。

### レビュアーと確認成果

レビュー保存先は `reviews/usaturn/create-reso-world/#296-docs-resoloop-plugins-replan/`。全員 `accepted`、失敗・入力除外なし。全ファイルの最終レビューHEADは `c87c34b605da`、modeはInitial、このサイクルで再実行済み。

| ファイル | 実担当 / モデル | runtime | active指摘 | Merge recommendation |
| --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | claude-opus / claude-opus-5-5 | claude-code | 2 | Approve |
| `SWE-2-Max.md` | devin-swe / SWE-2 Max | devin | 0 | Approve |
| `deepseek-v4.1-flash.md` | pigod / deepseek-v4.1-flash | pi | 3 | Approve |

確認済み一覧: 同保存先の `verified/c87c34b605da.json` と `.md`。工程記録: `verified/c87c34b605da.planning.json`。判断に重大度・票数・Approveの数は使っていない。補助のsp-researchはGit/GitHub実行・保存ツール不足でNEEDS_CONTEXTを返し、成果を判定に使わず司令塔が静的確認を実施した。

### 全指摘の採否

各参照の検出HEADは `c87c34b605da`。

| 出典 | 分類 | 確認した事実・理由 | 見直す条件 |
| --- | --- | --- | --- |
| `claude-opus-5-5#L-1` | 対応しない | 上流 `a7be2dd` に `ApplyDocument.cs` はなく、`ApplyDocument.Load` は `ApplyWorkflow.cs:28` にある。#100本文にも誤記がある。ただしPlanの編集範囲節と#100は、記載外の編集を親調整役の裁定・子Spec/Plan更新で解決する手順を既に持つ。本PRは実装を許可せず、ファイル一覧の誤りだけから無許可編集・主要処理の停止とは判定しない。 | #100の子設計で実ファイルの範囲を確定するとき、または誤記による具体的な誤操作・実装停止が確認されたとき。 |
| `claude-opus-5-5#L-2`、`deepseek-v4.1-flash#M-1` | 対応しない（同一判断） | D-2はGitルート内部の非ルート導入元の扱いを明記していない。ただし漏えいは、将来の実装が全コピーへフォールバックする仮定に依存する。現基準にPlugins実装はなく、D-2はGit確認失敗時の全コピーを禁止し、旧コードの無条件移植も禁止している。子#297の独立設計・検証・実装許可を省かず、現時点では設計の選択として扱う。実際の漏えいを再現したという意味ではない。 | #297で非ルートのコピー/拒否規則を決めるとき、または到達可能な秘密混入の実挙動が確認されたとき。 |
| `deepseek-v4.1-flash#L-1` | 対応しない | 予算節に独立した無進捗打切り値はなく、引用された続行指示だけでは30分の決め手は分からない。一方、親#95のコメント `6487878180` は再開前に追加30分程度を提示し、`6488017101` はその上限での再開を記録する。引用1行だけから無許可延長だったとは断定しない。completedな過去Planの記録であり再実行指示ではない（`docs/superpowers/README.md`）。このマージで予算延長の操作は起こらない。 | 新しい実行計画として再利用する場合、または無許可実行の具体的な新証拠が出た場合。 |
| `deepseek-v4.1-flash#I-1` | 対応しない | 本書には設計時点の未公開/未作成の語が残るが、後続Planの完了節と親IssueはF#297/I#298の公開を記録する。最新Issue・依存を読み直す開始ゲートがあり、設計の履歴を現在の作成手順と見なさない。現在時点を読みやすくする説明の問題で、主要動作を誤らせる欠陥ではない。 | 本書単独を最新ボードの操作手順として公開する場合、または重複作成の実経路が確認された場合。 |

「対応する」がないため修正方針・修正経路表・設計見直しの対象はない。直さない論点を直したことにはせず、子の着手前に必要な設計判断として区別する。

### 要件との対応・検証結果

共有する前提は、ボード完成と本体機能完成を混同しないこと。統合担当は今回のplannerで、PRの約束とSpec/Plan、GitHub状態、復元データを照合した。

| PRの約束・制限 | 観測結果・根拠 | 今回の扱い |
| --- | --- | --- |
| 文書のみ、4機能は将来の実装対象 | HEADの全変更2文書を全文確認。機能コード・テスト差分なし。各子に独立したSpec/Plan・許可が必要。 | 実装修正なし。機能完了や実機成功を報告しない。 |
| 18子・18依存、#104のみnot_planned、旧完了履歴維持 | GitHubから全18子・18parent・blocked_byを読み直し、Plan JSONのactive13子/16辺・historical5子/2辺と照合。歴史4件はcompleted、#104はnot_planned。 | 構造・状態は一致。過去の操作順序を現在値で遡及証明しない。 |
| activeの子は未計画・未実装 | 全13active本文のplanning/implementationがnot-started、Issueはopen。#100は先行F待ちで、記載外の変更は親裁定を要する。 | 所有表の誤記を未承認のコード編集権限として使わない。 |
| 公開4資料を復元可能 | #95のmanifest `6488294559` にある4コメントだけからbase64を復元し、全SHA-256・byte数、handoff JSON解析、Spec/Planと固定commit `fc8edddd2519b953051b95dbe2a00aac4aac90a7` のバイト一致を確認。 | 復元元は固定版のまま保持。本章追加後の文書と固定版を混同しない。 |
| 承認記録と履歴を維持 | Specの承認SHAからの差分を確認。Planの承認SHA・実行方式変更の明示指示・終了記録を全文確認。 | 今回は状態・レビュー記録のみ追記。新たな内容承認を捏造しない。 |

実行した検証（いずれも終了コード0）:

- `git diff --check 6733fc25d945d5b1b7c0ea9dc831d516453d7843...HEAD`（専用worktree、判断対象HEAD）。
- 一時検証 `uv run --project /workspaces/reso-world --locked python <SESSION>/check-docs.py <専用worktree>`。Plan JSON解析/DAG、全子のrepo/id/parent/先行集合/状態、公開4資料の復元を上表のとおり確認。SESSIONは `tmp/agents/pr296-review-fix.gnja3lxl/`。恒久テストではなく、結果を本章へ転記後に回収する。
- 候補3組を `review_findings.py validate` / `check-pair`、確認済み一覧を同validate、判断を `review_records.py validate` で検査。
- `bash scripts/scan-before-push.sh -C /workspaces/reso-world/.worktrees/resoloop-plugins-replan --base origin/main`。判断対象HEADまで8commit、検出なし。最終push前にもその時点のcommitを再検査する。
- `git ls-tree` / `git show` で上流 `a7be2dd` の `ApplyWorkflow.cs`、`BundleAnalysis.cs` と同表の他の既存ファイルを確認。親#95全コメントの本文・時点を照合し、親予約refは0件。

文書・固定一覧の一致だけを恒久テストにするのはF/Lに当たるため追加しない。機能コードがなく、dotnet build/test・Windows実機・Resonite接続は対象外。過去の1113検査の全実行履歴や操作途中の順序を再現したとはしない。

修正の実装・修正後自己レビュー・fix-checkは未実施（修正対象0件、`run_roles.py`呼出し0回）。設定の割り当てはimplement=claude-opus、self-review=self、fix-check=selfだが、実行済み担当として記録しない。レビュー工程は05:52:20〜06:11:37 UTC（約19分17秒）、判断・独立確認は06:11 UTC以降。最終の所要時間はloop記録と状況コメントに記録する。
