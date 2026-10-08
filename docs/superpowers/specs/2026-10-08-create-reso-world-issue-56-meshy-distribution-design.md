# Issue #56: Meshy 実行基盤の ResoLoop 同梱設計

- 文書管理: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/56
- 実装対象: `usaturn/resoloop`（上流 `orange3134/resoloop`）
- 状態: draft
- 調査したコード HEAD: `8bcef8a14e4b36167058df3f5c4af95ee895f9cf`
- 移植元 HEAD: `ce597301f797e011b9313792cb5a7a5ed4e0d104`
- Plan: `../plans/2026-10-08-create-reso-world-issue-56-meshy-distribution.md`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-56-meshy-docs`
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-56-meshy`

## 実行許可と公開範囲

ユーザーは「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」と明示した。
設計・計画の各段階で回答を待つ手順に代え、推奨案の選定、文書化、自己レビュー、実装方式の選定、ローカル検証、必要な修正、コミット・push・fork PR および文書 PR の作成までを実行する。これは未作成の文書内容をレビュー済みと扱う許可ではない。状態は draft のまま内容コミットを保存し、実行許可をその版に結び付けて別記する。
有料 API、画像外部送信、認証操作、Blender / Resonite の live 操作、fork/upstream のマージ、上流統合ブランチへの反映、上流 PR、NuGet 公開は含まない。Issue #50 の実機受入も完了扱いにしない。

## 目的と成功条件

create-reso-world や Dev Container がない利用者も、ResoLoop の配布物からスキル・実行モジュール・セットアップ手順を取得できること。
Meshy を使わない利用者には Node.js / Python / Blender / API キーを要求しない。`init` と `skills sync` はファイル配置のみを行い、依存導入・認証・API 呼び出しを行わない。
実際に pack/install した CLI で新規 init・既存 sync を実行し、配置したモジュールだけで help、offline plan、fixture 変換と bundle 検証が成立すること。必要な fixture の skip は成功に含めない。

## 選択肢と採用理由

1. **採用: スキル配下への自己完結配置。** 既存の埋め込みリソース・許可リスト・ハッシュロックを拡張する。全モジュールを隣接配置し、既存の兄弟 import と `Path(__file__).with_name(...)` を維持する。新しい installer や同期仕様が不要。
2. プロジェクト直下の別 tools ディレクトリへ配置する。スキルとツールの同期管理を別に実装する必要があり、管理範囲が広がるため不採用。
3. Meshy CLI や Python / Blender をパッケージへ内包する。容量、OS 対応、更新・再配布条件の負担が増え、任意依存の方針にも反するため不採用。

## 配布単位と同期

正式な実装場所は `skills/codex/meshy-resoloop/`。配置先はプロジェクトの `.agents/skills/meshy-resoloop/`。

- `SKILL.md`: 操作の順序、承認ゲート、復旧、後工程への引き継ぎ。
- `references/runbook.md`: OS・導入・更新・運用・復旧・Windows handoff。
- `references/licenses.md`: 移植元の由来、ResoLoop のライセンス、外部依存を同梱しないことと確認元。
- `scripts/meshy.py`: CLI、platform gate、doctor の入口。
- `scripts/meshy_workflow.py`: operation / journal / CLI 認証と再開。
- `scripts/meshy_conversion.py`: offline 変換と bundle 公開。
- `scripts/meshy_blender.py`: Blender 内の検査と編集可能データ保持。
- `scripts/meshy_cli_guard.mjs`: journal の秘密情報除去と対応 CLI 版の検査。
- `scripts/meshy_doctor.py`: ローカル前提条件検査。業務 wrapper と分離する。

`BundledSkillManager.Names` / `Files` と `RLoop.Core.csproj` の EmbeddedResource を明示的に追加する。`RLoop.Cli.csproj` の既存 `skills/codex/**/*` が配布するソースも確認する。コードを取得せずに埋め込みから実行ファイルを配置できる。
ハッシュロック v2、v1 読み込み、既存 status と例外コードは維持する。全ファイルの競合確認後だけ更新する。手編集した script と欠落した別ファイルが同時にある場合も、一つも更新せず lock を保持する。読み取り専用 check は bytes / mtime を変えない。
管理対象は許可リスト内の配布ファイルだけ。operation、journal、元 GLB、生成物、編集済み blend、state およびその他の非管理ファイルを削除・同期しない。

## 初期対応環境と任意依存

- **生成・復旧・ダウンロード・変換 wrapper は Linux のみ対応。** `fcntl.flock`、`O_NOFOLLOW`、`O_DIRECTORY`、プロセスグループ停止の既存保証を変更しない。WSL2 は Linux 側で動作する。macOS / Windows native は未対応と明示し、help 以外は名前付きエラーと Linux/WSL の案内で停止する。help は POSIX モジュールを eager import しない。
- Windows は bundle の `validate` / `diff` / `apply` 側のみ。Windows 上の init / skills sync は通常どおり動く。wrapper の対応と混同しない。
- Python >=3.12、uv による `uv run --no-project <skill>/scripts/meshy.py`。通常 wrapper は標準ライブラリだけ。
- Meshy CLI は検証済み `meshy-cli@0.4.0`。Node.js >=22.12.0、推奨 Node 24。guard と版を合わせる。未検証版への自動更新はしない。
- offline plan は Meshy CLI / Node / キー不要。convert は Blender、Blender の Python が読める NumPy、ResoLoop exporter が必要で、Meshy CLI / キー不要。
- Blender は ResoLoop の `blender find/run/export` を使用。exporter の階層保持 / PBR pack に依存する。
- ResoLoop は NuGet の最新公開版（prerelease を含む）を利用し、通常セットアップでは版固定しない。ローカル pack 検証時だけ生成したパッケージ版を明示する。
- 各依存は利用者が手順を選んで導入する。npm 導入、uv/Python 導入、Blender/NumPy 導入、更新、ローカル probe を OS 制約とともに記載する。自動実行はしない。

### doctor のインターフェース

`uv run --no-project <skill>/scripts/meshy.py --project PROJECT doctor`

JSON 出力で `ok`, `checks`, `key_present` を返す。各 check に安定した名前・成否・修復方法を含める。キーは有無だけを検査し、未設定は失敗理由にしない。依存不足・版不一致・非対応 OS は非0。doctor は全任意依存の診断であり、doctor 失敗でも独立した offline plan の実行は妨げない。
Python/OS、node 版、Meshy 版、ResoLoop 版と exporter の検出、Blender 内の bpy / NumPy、隣接リソースを確認する。probe は短い timeout、sanitized env で実行し、API キー・他の MESHY_*・既存 NODE_OPTIONS を渡さない。Meshy probe に `--no-update-check` を必須とする。login / status / list / balance / create は呼ばず、設定・journal・operation を作らない。子の stdout/stderr をそのまま出力しない。
CLI submit 前にも Node / Meshy の対応版を検査し、失敗を送信不能と区別できる形で返す。検査失敗は送信前に止める。

## 安全条件と制作前計画の接続

- API キーは環境変数だけ。値の要求・表示・ファイル保存・credentials fallback を禁止する。guard、redaction、隔離 config を維持する。
- Build Handoff の承認は有料操作・外部送信・ワールドへの適用の承認ではない。`not-authorized-at-preproduction-stage` なら停止する。
- 対象、operation、送信件数、予算上限、モデル、texture / PBR / 解像度、画像外部送信の許可を実行前に確認する。`--confirm-paid` は実行ゲートだけで承認記録や予算監視の代わりにならない。
- text preview と任意 refine は別 operation。image に preview/refine を足さない。再生成には追加許可。
- submitting / unknown / 応答不明は再送しない。journal と list / 既知 task を照合し、確認した ID だけ attach。特定できなければ停止する。
- project 外入出力、symlink 逸脱、既存出力上書きを拒否する。partial download は同じ task の download で復旧する。
- convert は元 GLB・階層・個別 mesh・texture・編集済みデータを保持する。join / decimate / bake を自動で行わない。透明・transmission・rig・animation・非対応 shader を黙認しない。source culling の損失は既定拒否、個別承認の `--allow-culling-change` だけで許可する。
- `resonite-model-preproduction` → `meshy-resoloop` → `resonite-blender` finishing → `resonite-build` の順序と責務を文書に反映する。各実行ゲートを弱めない。

## 移植元と権利・再配布の確認

移植元の5 scripts、skill、runbook、実行可能テスト2 files、Blender fixture を調査した。移植元 root に LICENSE はない。著作者履歴は `usaturn` で、本依頼は同じ所有者による fork への移植指示である。移植先の AGPL-3.0-or-later と由来を明示し、第三者が移植元全体を無条件で再配布できるとは説明しない。新たな第三者ソースをコピーしない。
Meshy CLI の npm metadata（2026-10-08 確認）は MIT / Node >=22.12.0 / 0.4.0。公式 LICENSE も MIT。CLI 本体・Node・uv・Python・Blender・NumPy は同梱しない。生成物の利用条件は依頼ごとに別確認する。
参照: https://github.com/meshy-dev/meshy-cli 、https://www.npmjs.com/package/meshy-cli 、ResoLoop `LICENSE`。
Context7 `/websites/meshy_ai_en` で公式 API の env-only 認証を照合したが CLI の版・ライセンス情報は得られなかったため npm metadata と公式 LICENSE を使った。

## 検証

1. C# 実行テスト: init 配置、既存 lock への追加、check の不変性、script の手編集競合、欠落＋競合で更新ゼロ、復旧、利用者データ保持。文書の固定文字列テストは作らない。
2. Python 実行テスト: 移植した wrapper の既存安全条件、doctor の不足/版違い/timeout/secret 非出力/無書込み、unsupported platform、任意依存なし offline plan、空白を含む移設先の兄弟 import / guard 起動。
3. 実 Blender fixture: 元 GLB 保持、複数 mesh / 階層 / PBR、拒否条件、bundle 検証、変換失敗の非公開。fixture の skip を検証完了に含めない。
4. pack/install: 一時 tool-path に実 nupkg を導入し、新規 init と旧 lock 相当の sync、配置先 ENTRY を使った help / plan / safety tests / 実変換。bundle を別パスへ移して validate。
5. CI: Windows の既存 build/test/pack/install は維持し、Linux で Python の非 live テストを実行する。実 Blender のローカル検証と CI の範囲を区別する。
6. 文書/設定: 相対リンク先の実在、ソース埋め込みと同期対象の一致、diff、構文、静的診断。SKILL の本文・設定値を写すテストは追加しない。

### 調査時のベースライン

- ResoLoop: `dotnet test ResoLoop.slnx -c Release`、448 + 19 成功、skip 0。
- 移植元 Meshy: 138 成功、54 fixture setup error。標準 `/usr/bin/blender` 5.0.1 の Python 3.14 に NumPy がないことを再現した。コード不具合とは扱わず、隔離した NumPy と Blender launcher で実 fixture を検証する。標準環境/rebuild の受入とは区別する。

## 配布状況と対象外

本作業は fork PR と文書 PR まで。fork main へのマージ、preproduction との上流統合、上流 PR、公開 NuGet 収録はそれぞれ未実施として記録する。fork PR の完了だけで Issue 全体の一般配布完了としない。Issue は自動 close せず `Refs` を使う。
create-reso-world の既存 Meshy コピーは Issue #50 の再現元として変更しない。将来の整理は別作業。新生成モード、Windows native wrapper、依存の自動インストール、paid/live 検証は対象外。
