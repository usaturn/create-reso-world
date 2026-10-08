# Meshy 実行基盤の ResoLoop 同梱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 任意機能の Meshy 実行基盤を ResoLoop の init / skills sync で自己完結して配布する。

**Architecture:** 既存の埋め込みリソースと許可リスト型ハッシュ同期を拡張し、skill 配下に全モジュール・手順を隣接配置する。既存 wrapper の安全条件を維持し、ローカル doctor と Linux platform gate を追加する。依存導入・認証は利用者の明示手順に分離する。

**Tech Stack:** .NET 10 / C#、Python >=3.12 / uv / pytest、Node.js >=22.12.0、meshy-cli 0.4.0、Blender / NumPy、ResoLoop exporter。

**Spec:** `../specs/2026-10-08-create-reso-world-issue-56-meshy-distribution-design.md`（内容コミット `0bacce7b1a9d89c930917bf83d18abda9617e7fe`）

- 文書管理: `usaturn/create-reso-world`、Issue #56
- 実装対象: `usaturn/resoloop`、基準 HEAD `8bcef8a14e4b36167058df3f5c4af95ee895f9cf`
- 状態: completed
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-56-meshy-docs`
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-56-meshy`
- 実行方式: 推奨の subagent-driven。Task は直列、レビューは読み取り専用。
- 実行許可: ユーザーの「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」により、内容の承認待ちは省略する。内容が個別レビュー済みという意味ではない。Plan の内容 SHA を後で記録する。

## Global Constraints

- wrapper の生成・変換は Linux のみ。Windows native / macOS は未対応。Windows の init / sync と bundle 適用は別。
- Python >=3.12、Node.js >=22.12.0、Meshy CLI 0.4.0。通常 ResoLoop は最新の NuGet 公開版（prerelease を含む）。
- init / sync で依存インストール・認証・API を呼ばない。doctor はローカル・短 timeout・無書込み・sanitized env。
- API キーは環境変数のみ。有無だけ確認し値を表示/保存しない。credentials fallback しない。
- 全同期競合を更新前に検出する。operation / journal / 生成物 / blend / state を管理範囲へ入れない。
- Build Handoff 承認と paid / image送信 / live適用の承認を分け、`not-authorized-at-preproduction-stage` を実行許可にしない。
- submitting / unknown は再送禁止。素材の拒否と source culling の個別承認を維持する。
- source create-reso-world を変更しない。Spec/Plan は create-reso-world にのみ保存する。
- 有料・画像外部送信・認証・live 操作、マージ、上流 PR、NuGet 公開を行わない。

## Review Focus

1. 空白のあるプロジェクト/配置先でも兄弟 import と Node guard の preload が動くこと（Task 1/2 の再配置テスト）。
2. 別ファイルの欠落と script の手編集が同時に起きても sync が一つも変更しないこと（Task 1 の snapshot）。
3. dependency probe の出力/timeout に secret が混入しても doctor が漏らさず、送信前に版違いを止めること（Task 2）。
4. Meshy / Node がなくても offline plan が動き、Windows help は POSIX import で落ちないこと（Task 2）。
5. pack/install の配布 ENTRY と移設した bundle で実変換/validate が成立し、fixture が skip で通過しないこと（Task 2/3）。

---

### Task 1: 自己完結配置と同期の挙動

**Files (CODE_ROOT relative):**
- Create: `skills/codex/meshy-resoloop/{SKILL.md,references/runbook.md,references/licenses.md,scripts/meshy.py,scripts/meshy_workflow.py,scripts/meshy_conversion.py,scripts/meshy_blender.py,scripts/meshy_cli_guard.mjs}`。
- Modify: `src/RLoop.Core/BundledSkillManager.cs`, `src/RLoop.Core/RLoop.Core.csproj`。
- Test: `tests/RLoop.Tests/ProjectInitializerTests.cs`。
- Create: `tests/meshy/test_meshy.py`, `tests/meshy/test_meshy_conversion.py`, `tests/fixtures/meshy/create_fixture.py`（移植元の実行可能テスト・fixture）。
- Create: `pyproject.toml`（任意の test dependency group、通常 init に無関係）。

**Interfaces:**
- Consumes: `BundledSkillManager.Sync(string targetDirectory, bool update)`、`ProjectInitializer` の既存 init。
- Produces: 配置済み `scripts/meshy.py --project PROJECT COMMAND`、Task 1 の8ファイル（Task 2 で doctor を加え計9ファイル）の v2 lock。既存の CLI / sync API は不変。
- Python テストは `RESOLOOP_MESHY_ENTRY` で配置済み ENTRY を選択できる。未指定時は target `skills/codex/.../scripts`。テスト内の直接 module import も同じ ENTRY の隣接パスを使う。

**テスト要否:** 必要。同期の安全条件・ファイルの配置・wrapper の実行/入出力を確認する。文書・ライセンス本文や一覧を写した文字列テストは作らない。

- [x] **Step 1:** C# テスト `MeshySyncPreservesUserDataAndCheckIsReadOnly`、`MeshySyncRefusesEditedScriptBeforeRestoringMissingFile`、`MeshySyncInstallsIntoPreMigrationLock` を追加する。実 init/sync を呼び、配置 script を開けること、check 前後 snapshot 一致、operation/journal/blend/state 保持、欠落＋手編集時の `SKILL_SYNC_CONFLICT` と bytes/lock 不変、解決後の復旧を検査する。
- [x] **Step 2:** `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj -c Release --filter FullyQualifiedName~MeshySync`。未登録により FAIL を確認する。
- [x] **Step 3:** source 5 scripts を隣接配置して移植し、skill と runbook の repository root / Dev Container 参照を除去する。ライセンス・外部依存の説明も配置する。Files/Names と explicit EmbeddedResource を登録する。新 installer/sync schema は作らない。
- [x] **Step 4:** source の wrapper テストと Blender fixture を target へ移し、ROOT/ENTRY/兄弟 module の参照だけ target 用に変更する。API モック・guard 実行・path 保護などの検証内容は維持する。
- [x] **Step 5:** C# focused tests と `uv run --group dev pytest tests/meshy/test_meshy.py -q` を実行し PASS を確認する。Node guard を空白を含む移設先で実行する回帰も加える。
- [x] **Step 6:** `git diff --check`、diff を確認しコード側でコミットする。

### Task 2: 任意依存の診断、対応環境、制作導線、配布物テスト

**Files:**
- Create: `skills/codex/meshy-resoloop/scripts/meshy_doctor.py`。
- Modify: 同 `meshy.py`, `meshy_workflow.py`、`BundledSkillManager.cs`, Core csproj（doctor 登録）。
- Test: `tests/meshy/test_meshy_doctor.py`, 既存 `tests/meshy/test_meshy*.py`。
- Modify: 同 `SKILL.md`, `references/runbook.md`、`skills/codex/resonite-model-preproduction/{SKILL.md,references/build-handoff.md}`, `skills/codex/resonite-build/SKILL.md`, `skills/codex/resonite-blender/SKILL.md`, `README.md`, `README_JA.md`, `README-DETAILS.md`, `docs/BLENDER.md` の関連箇所。
- Modify: `.github/workflows/ci.yml`（Linux の非 live Python テスト。Windows pack smoke を維持）。

**Interfaces:**
- Consumes: Task 1 の配置済み ENTRY / `RESOLOOP_MESHY_ENTRY` / wrapper。
- Produces: `meshy_doctor.diagnose(project: Path) -> dict` (`ok`, `checks`, `key_present`) と `meshy_doctor.require_cli_compatibility() -> None`（名前付きエラー）。doctor CLI は `ok` に応じた exit 0/1。help/platform gate を通過するまで POSIX module を import しない。

**テスト要否:** 実ロジックは必要。fake PATH / dependency version / timeout / secret / 無書込み、送信ゼロ、任意依存なし plan、配布 ENTRY を検査する。文書変更には文字列テストを作らず、リンク先・構文・diff を検査する。

- [x] **Step 1:** fake tools による doctor テストを書く。キーなしでもローカル依存が揃えば成功、node旧版/meshy新版/欠落/timeoutは非0、APIサブコマンド呼出しゼロ、envの key/NODE_OPTIONS 除去、出力の sentinel secret 不在、project snapshot 不変を検査する。非対応 platform は help 成功・操作拒否を検査する。版違い submit は operation を submitting にせず create が0回。
- [x] **Step 2:** `uv run --group dev pytest tests/meshy/test_meshy_doctor.py -q`、未実装による FAIL を確認する。
- [x] **Step 3:** doctor と platform/lazy import gate を実装する。probe の出力はそのまま表示しない。Meshy `--no-update-check` を使い、CLI送信経路の child_env 準備より前で版検査する。互換版の fake CLI に version 応答を加える。
- [x] **Step 4:** source 環境に依存しない手順へ仕上げる。Node/Python/uv/Blender/NumPy/exporter の導入・確認・更新、ResoLoop の非固定最新導入、承認と復旧を記載する。preproduction の Meshy「外部スキル」説明を同梱へ変更し、finishing/build の責務を維持する。
- [x] **Step 5:** Linux CI で Python/uv/Node を用意し安全条件・doctor テストを実行する。実 Blender が必須のテストを skip で成功扱いしない（ローカル mandatory 実行結果と分離する）。Windows の既存 pack/install smoke はそのまま維持する。
- [x] **Step 6:** `dotnet test ResoLoop.slnx -c Release` と Python 全テストを同期実行する。Blender/NumPy の不足は一時隔離 launcher で補い、標準環境の未検証を明記する。必要 fixture は skip 0。
- [x] **Step 7:** pack した CLI を一時 tool-path に install、新規 init、既存プロジェクトへ sync、キー・Meshy/Node 不在の通常 init/sync、配置済み help/plan を検査する。配置 ENTRY で Python 全テストを再実行する。変換 bundle を別パスへコピーして `resoloop validate`、asset の相対解決を確認する。
- [x] **Step 8:** `git diff --check`、Python 構文、相対リンク、active LSP 診断、変更差分を確認しコミットする。

### Task 3: 最終レビュー、記録、fork PR と文書 PR

**Files:** この Spec / Plan、必要な検証結果を target `docs/MESHY-VALIDATION.md` に記録する。

**Interfaces:** Task 1/2 の変更・実行結果・内容コミット SHA を消費し、相互参照する2 PR を公開する。

**テスト要否:** 文書/PRの本文は不要。代替として main controller が直近のテスト・pack/install を再確認し、読み取り専用 reviewer に全変更とテスト採用基準を確認させる。

- [x] **Step 1:** 読み取り専用 sp-review で最終ブランチレビュー。paid gate、retry、防漏洩、path保護、競合全件preflight、配布依存閉包、テスト基準を確認する。実装担当/controllerだけがテストを実行する。
- [x] **Step 2:** 根拠のある指摘を修正し該当テストと全体検証を実行する。既存source/ユーザー作業物には触らない。
- [x] **Step 3:** Spec/Plan に実行許可と内容SHA、実装HEAD、検証結果/残課題/所要時間を追記する。実施していない live/標準rebuild/Windows 実機は明記する。承認済みと推測しない。
- [x] **Step 4:** 文書と実装をそれぞれコミット・push する。`usaturn/resoloop` に Meshy の独立 PR、`usaturn/create-reso-world` に Spec/Plan の文書専用 PR を作り相互参照する。`Refs usaturn/create-reso-world#56`、自動closeなし。
- [x] **Step 5:** 公開 target の CI を確認する。create-reso-world private CI の確認は不要。forkマージ/上流PR/NuGet未公開を明記して、Herdr task を completed にする。

## 実行記録

### 実行許可と実装

- 内容コミット: Spec `0bacce7b1a9d89c930917bf83d18abda9617e7fe`、Plan `3a7d425a8b378d3f18d3b21d4bbe94535d51df0d`。ユーザーの推奨案による一貫実行許可をこの版へ適用した。内容の個別承認を得たとは記録しない。
- Task 1: `a525952`（8 files同梱、sync保護、移植テスト）、Spec PASS / quality APPROVED。
- Task 2: `1f99aff`（doctor、Linux gate、9 files、任意依存手順、CI）。Spec PASS、重大な指摘なし。軽微な2件を最終修正にまとめた。
- 最終修正: `4fd899dda9ed5b76252d2cd76f85871f522d7d4a`。不正UTF-8の後処理で診断エラーが上書きされる問題（doctor/conversion）と、NumPy欠落テストのホスト依存を修正。全体review＋scoped re-reviewで未解決指摘なし。
- 実装ブランチ HEAD（検証記録を含む）: `29ab002a4e9a671448e661b66831f91934bd6a56`。
- fork PR: https://github.com/usaturn/resoloop/pull/11 、文書PR: https://github.com/usaturn/create-reso-world/pull/61 。相互参照済み、自動closeなし。

### 最終検証

- controller再実行: C# **472成功**（453 unit＋19 default non-live）、配布ENTRYのPython **237成功、skip 0**。
- 実pack/install: local-only nupkg source、fresh cache/tool-path。配置DLL・scriptとnupkgの一致、bytecode非同梱を確認。
- 通常init/syncはNode/Meshy/Python/uv/キーなしPATHで成功。旧lock移行、check無書込み、手編集＋欠落時に更新ゼロ、operation/journal/GLB/blend/state/notes保持を実行。
- 配布ENTRYでhelp/plan/doctor、全実fixture54件を含む変換。最新実変換のbundleを別ディレクトリへ移し、相対asset4件を照合しinstalled validate成功。
- Pyright: 実際の任意test interpreterを指定して変更runtime4 modulesと新規test2 modulesで **0 errors/warnings**。active LSPのtest pytest未解決は隔離venv検出の問題と区別する。
- 補助ast-grep: boolean singletonのidentity警告は厳密bool検査として必要。JSON読み込みの局所try不足警告はcallerの終了処理とCLI error変換で処理されることをread_enclosingで確認。無条件に診断ゼロとは報告しない。
- 文書変更には文字列テストを追加せず、リンク/構文/差分を検査。通常手順の検証記録はtarget `docs/MESHY-VALIDATION.md`。
- controller logs: `/tmp/issue56-controller-logs/{dotnet-final.log,python-packed-final.log,pyright-final.log,bundle-relocation-final.log}`、すべてexit 0。

### 検証範囲・公開の残り

実変換はBlender5.0.1 / Python3.14.4 / 隔離NumPy2.5.3で成功。標準NumPy2.3.5のimportが作業中に確認できたが、controller/担当者は標準環境を変更しておらずbaselineとの差の原因は未確定。標準rebuild/全面変換、Windows/Resonite実機、paid/image/live/実APIの結果は未検証。Issue#50の実機受入を完了扱いにしない。
forkマージ、上流統合/PR、公開NuGet収録は未実施。公開CIは [run 37801297304](https://github.com/usaturn/resoloop/actions/runs/37801297304)、HEAD `29ab002a4e9a671448e661b66831f91934bd6a56` で **success**。Linux offline Python 47秒、Windows build/test/pack/install/init/sync smoke 3分44秒が成功。監視 `/tmp/issue56-controller-logs/public-ci.log` はexit0。Windows hosted runnerのinit/syncは実行済みだが、利用者のWindows/Resonite live受入とは区別する。private create-reso-world CIは規約どおり確認不要。

### 検証中の認証情報取扱い

初回Task2の失敗テストが広い親envをpytestのfailure表示へ含め、`COMMANDCODE_API_KEY` の値がharness履歴へ混入した。現在のfixtureは最小envを使用し、保存したdoctor-red.logはredaction済み。controllerは値を表示せず内部比較で保存ログの一致0、現セッションJSONLの一致1を確認した。過去のharness出力は削除できないため利用者へ該当キー更新・記録アクセス範囲確認を案内した。キー値は記録しない。認証情報の自動更新や過去履歴の改変はしていない。

### 所要時間

- controller着手: 2026-10-08 22:12:53 JST。
- Task1担当: 12分45秒（調査/RED 2:25、移植/GREEN 2:12、回帰/自己レビュー5:34、commit/report2:34）。
- Task2担当: 35分33秒（調査2分、RED2分、実装/GREEN5分、手順/CI5分、回帰2分、pack/install6分、最低Python/静的検証6分、review/commit4分、report約3分）。
- 最終修正担当: 18分54秒（調査/test2:51、RED1:20、fix/GREEN0:35、回帰4:35、pack/install4:37、review/commit1:48、report3:08）。
- controllerの調査/文書化/各読み取り専用レビュー/独立再検証/公開確認を含む総時間: 約2時間23分（2026-10-08 22:12:53〜2026-10-09 00:36 JST）。担当者時間の合計だけではなく同期レビュー・実検証・文書公開を含む。
