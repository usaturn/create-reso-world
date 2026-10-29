# ResoLoop プラグイン Issue ボード再計画 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 承認済み設計に従って親 #95 と子 Issue の担当・依存・開始手順を更新し、文書専用 PR と復元可能な記録を残す。本体コードは実装しない。

**Architecture:** 既存ボードを再利用し、最新上流起点の基盤 F と CLI 統合 I だけを新設する。1つの直接先行データから本文・台帳・図・native relation を揃え、親の固定 ref 予約下で調整役が順次更新する。各子の実装には別の Spec・Plan・handoff と実行許可が必要。

**Tech Stack:** Git、GitHub REST API（gh）、Markdown、JSON、uv 経由の Python による使い捨ての構造検証。新しい常設ツールやテストコードは作らない。

**Spec:** `docs/superpowers/specs/2026-10-29-create-reso-world-issue95-plugin-replan-design.md`。承認済み内容の commit は `d009286968a21c916bafb39b2308ebaa09d40c4c`。

## 管理・承認・今回の範囲

- 文書・ボード: `usaturn/create-reso-world`、親 https://github.com/usaturn/create-reso-world/issues/95、database id `5871216931`、board key `resoloop-plugins-board`。
- 状態: **approved**。内容承認の対象は `3a4fc1b8213555ea88502265592cefa7b8ae01dc`。そのPlanの確認依頼と公開範囲の提示、実行方式の説明を受けて、利用者が「提案どおりにサブエージェント方式でお願いします。」と指示した（2026-10-29 UTC）。Spec の承認だけから推測したものではない。
- 実行許可: 上記の「提案どおり」の対象は、確認依頼で示した Issue の作成・本文/状態/依存の更新、親の予約 ref の作成と条件付き削除、文書ブランチの通常 push、同テーマの文書専用 PR 1件の作成または再利用まで。マージ、本体実装、fork 側への push、上流投稿は含めない。
- 選択された実行方法: **直列 subagent-driven-development**（`/sp-implement subagents` 相当）。利用者の明示選択に従いNative推奨から切り替えた。各Taskを新しい担当へ依頼し、子は読み取り・下書き・検証を行う。予約ref・GitHub書込み・push・PRは調整役が実行する。Taskごとのレビューと最後の全体レビューを行い、並列実行はしない。これは指定された実行方式の反映であり、設計・操作対象を広げる変更ではない。
- 独立サブシステムである F・#98・#99・#100・I・#101 等を、この親 Plan で一括実装しない。各子は先行の実コード/API が対象ブランチで利用可能になってから独立した Spec・Plan を作る。
- `PARENT_ROOT=/workspaces/reso-world`、`DOC_ROOT=/workspaces/reso-world/.worktrees/resoloop-plugins-replan`、文書 branch `docs/resoloop-plugins-replan`。
- コードの将来の統合先は `usaturn/resoloop:feat/plugin-v2`。現状はローカルだけで、worktree は `/workspaces/reso-world/external/resoloop/.worktrees/plugin-v2`、HEAD は `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`。
- 実行時の SESSION は `uv run --no-project python .agents/scripts/agent_tmp.py mkdir issue95-board` で新規作成する。ここでいう `snapshot/`・`payload/`・`restore/`・`board.json`・`claim.json` は全て SESSION の下。worktree 内へ非追跡の作業物を置かない。

## Global Constraints

- Spec の4機能（外部コマンド、スキル、UIX レシピ、doctor）と D-1〜D-6 を維持する。
- upstream 基準は `a7be2dd4a5e4df9f152c8908e51a853d3af6bb74`。fork main の reset・force push・削除・作り直し、旧 fork 専用機能の混入は禁止。
- 親 checkout、ローカルワールド、既存の texture-transfer worktree、外部 checkout の未追跡 `reviews/` を変更しない。
- #91・#96・#97・usaturn/resoloop#18 の completed と旧 Spec/Plan・PR の履歴を残す。#104 だけを理由付き not_planned で閉じる。#110〜#112 は F の実装検証前に閉じない。
- 生 argv の受け渡し、スキルの別記録、`<plugin-name>:<recipe-name>`、`uix-plugin--<plugin-name>--<recipe-name>--<caller-key>` は承認済み仕様。ボードの更新中に再設計しない。
- 予約名は `refs/heads/agent-claims/issue-95`。UUID・UTC時刻・最新 main の tree/parent を持つ一意な空コミットから新規 ref を作り、自分の保存済み SHA の時だけ削除する。
- すべての外部書き込み前に、対象 owner/repo・id・予約所有・最新本文を確認する。未知の親・依存・別の予約を変更しない。
- 単なるパス・文言・一覧を写すテストは追加しない。ボードの誤対象・所有・復元・不完全公開は実データの構造検証と読み戻しで検出し、成功条件を満たすまで operational と報告しない。
- Code の build/test・Resonite 接続・グローバルツール導入は実行しない。private の create-reso-world の CI は確認不要で、新しい Actions は作らない。

## Review Focus

1. 同じ番号の別 repo（特に create-reso-world#18 と usaturn/resoloop#18）を操作しない: Task 1/3 で `(repository, number, database id)` の組を全件照合する。
2. 新規 Issue 作成の応答が失われても重複を作らない: Task 3 で body の stable key・公開台帳・全ページの repo Issue 一覧から既存作成を回収する。
3. 関係者の本文・#90 の知見・旧完了履歴を全体置換で失わない: Task 1/3 で管理範囲外のバイト列を保存・比較し、差分があれば公開を止める。
4. 追加と削除の途中や文章だけ更新された状態を ready と誤報しない: Task 3/4 で置換先 blocker を先に追加し、全 native relation と台帳を再取得して照合する。
5. ローカルパスや PR URL だけを復元可能と誤認しない: Task 4 で公開済み内容だけを空の restore/ に取り出し、SHA-256・byte数・JSON・承認/未実装状態を照合する。

---

## 受け入れ基準

### 動作環境

本 Dev Container の Linux、git・gh・uv・Python、認証済みの create-reso-world への Issue/content 書き込み権限。通常の文書 push 前にリポジトリ所定の Gitleaks が成功すること。公開先は同 repo の main 宛て文書 PR と #95 の記録だけで、ResoLoop/Meshy/上流のコード・設定には書き込まない。将来のプラグインは Linux/Windows 対象だが、この親 Plan はどちらの実装受け入れも実行しない。

### 実入力

- GitHub から再取得した複数ページの Sub Issues・comments・blocked_by。日本語・改行・バッククォート・引用・コメント中のシェル断片を含む本文を、シェルコードに埋め込まず JSON/ファイルとして扱う。
- #90 の元の知見一覧と managed marker の外側。#104 の過去の判断。外部 repo の #18。
- F/I が未採番の下書きと、作成済みだが応答・台帳追記が途中の回復ケース。

### 防御範囲・完成条件

- F/I を1件ずつ追加し、既存16子を残す。native Sub Issues は合計18件。#104 は historical/not_planned、従来の4完了子は completed のまま。
- active な先行表は下記 JSON の16辺。#104 の従来2辺は historical として残すため、native の管理辺は合計18辺。未知の追加辺は勝手に削らず未完了とする。
- 本文の許可/禁止ファイル・先行・対象 branch が親と子で一致し、共有 API の所有者が明記されている。`Program.cs` の変更は I だけ。
- 実装子は planning: not-started / implementation: not-started。既に有効な成果物や進行中作業が見つかった場合はリセットせず停止・再調整する。親設計の公開だけで子を planning: ready としない。
- 文書 PR は同テーマで1件、親から承認済み Spec と現行 Spec/Plan を読める。公開した handoff pair と manifest を復元・照合済み。
- 最後に自分の親予約だけを条件付き解放し、ref の不在を確認。本体コード・fork/main・利用者所有部分に差分なし。
- 対象外の反例: 他の利用者が新たに加えた関係の削除、他人の予約の解除、closed predecessor だけで未公開コードを利用可能とみなすこと、過去の API 例の実行、文書 PR のマージ。

## データとファイルの担当

### 直接先行の唯一の入力（Task 1 で board.json に取り出す）

`active` が現行実行マップ。`historical` は残す過去の関係。本文・図・辺数・API差分を別の手書き表から作らない。

```json
{
  "active": {
    "plugin-core-refresh": [],
    "plugin-commands": ["plugin-core-refresh"],
    "plugin-skills": ["plugin-core-refresh"],
    "plugin-recipes": ["plugin-core-refresh"],
    "plugin-cli-integration": ["plugin-commands", "plugin-skills", "plugin-recipes"],
    "plugin-docs": ["plugin-cli-integration"],
    "upstream-proposal": ["plugin-docs"],
    "meshy-finish": ["plugin-repo", "open3d-devcontainer"],
    "meshy-plugin": ["meshy-finish", "plugin-cli-integration"],
    "meshy-switch": ["meshy-plugin"],
    "plugin-install-symlink-path": ["plugin-core-refresh"],
    "plugin-link-remove": ["plugin-core-refresh"],
    "plugin-package-link": ["plugin-core-refresh"]
  },
  "historical": {
    "plugin-core": [],
    "plugin-repo": [],
    "open3d-devcontainer": [],
    "meshy-unbundle": [],
    "preproduction-meshy-route": ["meshy-plugin", "meshy-unbundle"]
  }
}
```

既存キー→番号は親台帳と各 Issue の最新 GET から結び付ける。F=`plugin-core-refresh`、I=`plugin-cli-integration` だけが新設。既知の parent id は上記のとおりだが、実行時に再照合する。新規の number/id/node_id/html_url は API 応答を保存して初めて使う。

### 子へ渡す編集範囲

この表は**将来の子の編集権限**であり、今回これらのファイルを編集する指示ではない。記載以外が必要なら調整役が採否を決め、子の Spec/Plan を先に更新する。

| 所有者 | 許可する主なファイルと責務 |
| --- | --- |
| F | `src/RLoop.Core/Plugins/` の `SemanticVersion.cs`・`PluginNames.cs`・`PluginErrors.cs`・`PluginManifest.cs`・`PluginInstallRecord.cs`・`PluginRegistry.cs`・`PluginInstaller.cs`・`PluginGit.cs`・`PluginPathPolicy.cs`・`PluginProjectLock.cs`。`tests/RLoop.Tests/Plugin{Manifest,Registry,Installer}Tests.cs` と `tests/fixtures/plugins/core/`。Core/Plugins 全体を独占する指定にしない |
| #98 | `src/RLoop.Core/Plugins/PluginCommandRunner.cs`・`PluginRuntimeEnvironment.cs`・`PluginToolProbe.cs`、`src/RLoop.Cli/PluginCommandDispatch.cs`・`PluginDoctorChecks.cs`・`BuiltinCommandCatalog.cs`、`PluginCommandTests.cs`・`PluginToolProbeTests.cs`、fixtures/plugins/commands。F のファイル・Program.cs は禁止 |
| #99 | `src/RLoop.Core/Plugins/PluginSkillManager.cs`、`BundledSkillManager.cs`・`ProjectInitializer.cs`、`PluginSkillSyncTests.cs`、fixtures/plugins/skills。F・#98・レシピ・Program.cs は禁止 |
| #100 | `src/RLoop.Core/Plugins/PluginRecipeResolver.cs`、`UixRecipes.cs`・`ApplyDocumentCompiler.cs`・必要な `ApplyDocument.cs`、`PluginRecipeTests.cs`、fixtures/plugins/recipes。F・スキル配布・Program.cs は禁止 |
| I | `src/RLoop.Cli/Program.cs`・必要な `CommandLine.cs`・新設 `PluginManagementCommands.cs`、`tests/RLoop.Tests/PluginCliIntegrationTests.cs`、fixtures/plugins/integration。先行の API の無断変更は禁止 |
| #101 | resoloop の `docs/PLUGINS.md`、README.md/README_JA.md/README-DETAILS.md のプラグインの節、`skills/codex/resonite-build/SKILL.md` の影響箇所、`examples/plugins/` の最小例。機能コードは変更しない |
| #90 | resoloop-meshy の仕上げ・UV・素材・計測・描画ツール、`skills/` の本文・参照文書、依存定義と対応テスト。移植元ワールドは読取のみ。manifest・CLI入口・導入READMEは #102 に残す。具体的な移植先はこの子の Spec で固定し、推測で移植しない |
| #102 | resoloop-meshy の manifest、コマンド入口、tools/skills の宣言、README の導入・使用方法と対応テスト。仕上げ本体・スキル本文・依存定義は #90 の成果を使い、無断変更しない |
| #103 | 最新本文の許可リストを維持。create-reso-world の Meshy API scripts/skill/docs/installer の撤去とREADME等の案内に限定。ローカルワールド・過去文書・基本apt行は禁止 |
| #110〜#112 | F の結果・代表テストの証拠と当該 Issue の記録のみ。F と重複するコード変更・テストを新たに割り当てない |
| #105 | 上流提案文・分割案の準備。上流投稿は別途利用者確認。Meshy完成を依存に戻さない |

子本文の検証欄には、resoloop 子では専用 worktree を cwd に `dotnet build ResoLoop.slnx`・`dotnet test ResoLoop.slnx --no-build`、Meshy 子では専用 worktree で `uv run pytest`、#103 では create-reso-world の専用 worktree で `bash scripts/check-layout.sh`・`bash .devcontainer/run-tests.bash`・`uv run pytest` を記載する。実機や実GLBが必要な子は、その子の Spec/Plan で原本と出力先・排他・未実行時の状態を明示する。今回これらの検証を実行したと書かない。

F は検証済みパッケージ/記録/予約名入力を持つ registry API、#98 は起動・終了・doctor の仕様と名前 catalog、#99 はスキル記録、#100 は resolver をそれぞれ所有する。具体的な型・シグネチャはその所有子が Spec で固定してから消費側に渡す。I が結線を専有する。未固定 API を、このボード更新 Plan で実装済みのインターフェースとして捏造しない。

## 実行予算

親 #95 の**ボード更新 run**の能動時間を90分とする。過去の設計約26分と今回の Plan 作成は別記録、子のコード実装はこの予算に含めない。Task 1=20分、Task 2=15分、Task 3=35分、Task 4=20分を目安とする。

- 実行開始時に SESSION/budget.jsonl を `issue_budget.py start --budget-minutes 90` で開始。各 Task 境界・50%・100%・失敗直後に show と checkpoint を記録。利用者待ちは await-user/resume で除く。
- controller が foreground で gh を順次実行する。外部書き込み・git push を timeout で途中停止する worker は起動しない。直列SDDでは各Taskの読取・下書き担当 sp-implementer を1件ずつ（計4件）、Taskレビュー sp-review を各1件（計4件）、最終全体レビューを1件予定する。修正はSDDの修正サイクル上限と全体90分の双方に従う。レビューには同じ受け入れ基準・brief・証拠差分を渡す。単一担当は目安5分、報告整理を含め残り10分未満なら新しい担当を起動せずpartialにする。pi の同期 subagent は途中監視・強制停止ができないので、期限付き停止を実装したと主張せず戻るまで待つ。予算超過なら返却後に追加作業を止める。
- 同じ reliability 失敗の再試行は1回まで。ただし作成・更新の応答が不明なら、再試行前に既存結果を読み戻す。安全の失敗・権限拒否の回避・予約所有喪失は全体停止、同じ操作を別手段で通さない。
- 100%で停止し、残りを partial と記録して自分の予約を解放する。文書公開だけ済み・relation未完了などの状態を隠さない。予算延長・追加Issue・設計縮小は自分で決めない。
- 完了時は要約を Plan/PR/handoff に転記して ledger の end を記録。watch が無いこと、または全対象停止を確かめて、自分の SESSION だけを `${SESSION:?}` ガード付きで削除。引継ぎ時は SESSION と ledger を残す。

## contingency（代替策）

- 最新 upstream が基準から変わった: 新コードにプラグイン基盤・関連変更があるか読取で確認し、意味が変わる場合は Spec の再承認へ戻る。コード worktree や承認済み SHA を黙って移動しない。
- 権限・ruleset が不明、別予約、未知の parent/relation がある: claim/更新を始めず、下書きと具体的 blocker を残す。文章だけの依存に格下げしない。
- 作成/更新が timeout: 全ページの Issue・台帳・relation を再取得し、stable key と返却 ID で既実施を確定してから続行。二重作成を避け、無差別な rollback はしない。
- 本文に新しい利用者編集: 管理範囲外を維持して下書きを再構成する。承認済み仕様と矛盾する新指示なら判断を求める。
- push/秘密情報検査が失敗: Task 2 で止まり、Issue の依存更新へ進まない。除外・force push で回避しない。
- 一部 relation の更新だけ失敗: 台帳に成功/未実施を分けて保存し、board: incomplete。全体を更新前へ強制的に戻さない。自分の予約を保持したまま利用者待ちに入らない。
- 文書量が comment 上限を超える: UTF-8安全な分割か base64 分割を使い、manifestに順序/encodingを記録。要約やローカルパスだけで代用しない。

---

### Task 1: 最新状態の取得と公開下書きの作成

**Files:** SESSION/snapshot/、SESSION/board.json、SESSION/payload/ の親・子本文と relation差分。追跡コードは変更しない。

**テストの要否:** 恒久テストは不要。文書・GitHub記録の操作であり、機能コードを新設しない。誤対象・本文消失・誤ったグラフを防ぐ事前ゲートとして実入力の構造・範囲を検査する。API操作を常設ツール化する変更はこの Plan の対象外。

**Interfaces:** Consumes: 承認済み Spec と上記直接先行 JSON。Produces: 各キーの `(repository,number,id,node_id,url)`、保存した本文/updated_at、許可された差分、F/Iが未採番の下書き、循環のない board.json。

- [ ] **Step 1:** PARENT_ROOT/DOC_ROOT と remotes、git status/worktrees、Spec/Plan の承認 SHA と実行許可を確認。origin/main と upstream/main を fetch し、旧コードと同じならその事実を記録する。変更があれば contingency を適用。
- [ ] **Step 2:** #95 の本文・全コメント・全子、全子の本文/全コメント/blocked_by、関係PR、全 claims を `gh api --paginate --slurp` で保存する。外部子の #18 は `repos/usaturn/resoloop/issues/18` を使う。ページごとに取得できていることを記録する。
- [ ] **Step 3:** repo/default branch/permissions、rulesets、main protection、Actions を再取得。Issue/content書込みが必要。プラン上使えないことを明示する403だけは非適用の証拠として扱い、不明な403/404は停止。claim対象のworkflow制限も確認する。
- [ ] **Step 4:** 全 Issue 一覧から stable key の重複/既存F/Iを確認。parent台帳・最新本文・native parent の3点で管理対象を確定し、board.jsonへ実IDを入れる。F/I は見つからない時だけ number/idを未確定にする。
- [ ] **Step 5:** 親の map/ledger marker を再利用し、古い基準・所有表・開始手順等のボード運用部分を承認済み仕様へ更新する下書きを作る。古い利用者決定・関連リンク・コメントは残し、変更理由と後継仕様を追加する。#90は既存 child marker 内だけを更新し、元の本文・知見はバイト単位で保持する。その他の子は既存の親/キーを根拠に managed child marker を設け、無関係な追記は外へ残す。
- [ ] **Step 6:** 下書きには「親bodyの7必須節」「子bodyの目的/範囲・禁止/先行・入力/API/受け入れ/検証/成果物/状態・反映先」を満たす。開始手順は `.agents/skills/planning-parallel-issues/references/issue-board.md` の全文7段を日本語で埋め込み、対象repo/絶対checkout/文書保存先/子のclaim/復元/未実装を明記する。`N` は選択した子番号というパラメータとして定義し、F/Iの未採番リンクを公開しない。
- [ ] **Step 7:** Pythonの一時的な検査で、全キーの一意性・先行参照・DAG・active/historical辺数・repo/idの対応・許可/禁止範囲の非重複・管理外本文の同一性を確認する。Expected: active13子/16辺＋historical5子/2辺、F/Iを除くID解決済み、未知の関係なし。異なる実データは固定数へ強引に合わせず停止する。

### Task 2: 親の予約と文書 PR の公開

**Files:** SESSION/claim.json、SESSION/payload/claim-commit.json、SESSION/payload/claim-ref.json、Spec/Planの承認・実行記録のみ。

**テストの要否:** 新テスト不要。予約所有・push先・検査SHA・PR再利用を実APIとgit出力で検証する。試しのref作成は行わず、必要な親予約だけを作る。

**Interfaces:** Consumes: Task 1の権限・下書きと実行許可。Produces: 不変の claim SHA、own ref、承認済み/現行文書のcommit URL、文書PR番号/URL。

- [ ] **Step 1:** 最新 main の commit/tree、session UUID、UTC時刻から一意な空コミットを `POST /repos/usaturn/create-reso-world/git/commits` で作る。返却SHAを claim.json に保存してから、`POST .../git/refs` で `refs/heads/agent-claims/issue-95` を新規作成する。既存refは更新しない。応答不明時は GET して保存SHAと同じ場合だけ取得済みとする。
- [ ] **Step 2:** refのSHAを再確認し、親に所有者/session/ref/SHA/目的のコメントを追加する。別の子claimが新たに見つかったら、その子を巻き込む更新を始めず停止・解放へ進む。
- [ ] **Step 3:** Spec の承認SHAを保持し、Plan の承認SHAと公開操作の許可を metadata として記録してコミットする。`git diff --check` と変更がdocsだけであることを確認する。内容変更を承認記録に混ぜない。
- [ ] **Step 4:** 文書branchを通常pushする。PARENT_ROOTで次を実行し、検査SHA以外を送らない。

```bash
SHA="$(bash scripts/scan-before-push.sh -C /workspaces/reso-world/.worktrees/resoloop-plugins-replan --base origin/main)" && [ -n "$SHA" ] && git -C /workspaces/reso-world/.worktrees/resoloop-plugins-replan push origin "${SHA:?}:refs/heads/docs/resoloop-plugins-replan"
```

- [ ] **Step 5:** 同じ head/base の既存PRを調べ、なければ `gh pr create --repo usaturn/create-reso-world --base main --head docs/resoloop-plugins-replan` で文書専用PRを1件作る。本文はファイルから渡し、`Refs #95`、Spec/Planの承認と未実装、検証結果、今回のIssue操作範囲を書く。既存PRがあれば再利用。マージしない。lost response時は再検索してから判断する。

### Task 3: 子 Issue・親本文・native relation の更新

**Files:** SESSION/payload/ の確定本文、SESSION/board.json、親の公開台帳。Issueだけを変更し、コードは変更しない。

**テストの要否:** 新テスト不要。各書込みの直前照合と読み戻し、管理外本文比較、構造検証を操作の必須ゲートとする。全体を成功と判断するのはTask 4だけ。

**Interfaces:** Consumes: own claim、公開文書、下書き。Produces: F/Iの実ID入り台帳、更新済み18子、期待したnative relation、操作ごとの成功/未実施記録。

- [ ] **Step 1:** claim・最新本文・updated_atを再照合。親の管理範囲に board: updating と今回の文書PR・承認済みSpec・操作台帳を追加して公開し、読み戻す。下書き作成後の無関係な編集を消さない。
- [ ] **Step 2:** F/Iの既存同キーを全ページから再確認し、未作成の場合だけ `POST .../issues`（JSONのtitle/body）で作る。初期本文から親#95・stable key・未実装・先行ゲートを示す。各作成の応答を保存し、**その都度**親台帳へ number/id/node_id/url を追記してGETで確認してから次のIssueへ進む。
- [ ] **Step 3:** F/Iの現在parentをGET。読めるIssueの `No parent issue found` だけは未所属と判断し、`POST .../issues/95/sub_issues` に database idを渡す。既に#95なら追加しない。未知のparentはreparentしない。今回のPlanは既存子の親変更・削除を要求しない。
- [ ] **Step 4:** 実IDを埋めた親・子の本文を更新する。#98〜#100からProgram.cs権限を外してIへ移し、#110〜#112はFの結果確認に限定する。#90の元本文・#103の利用者所有部分の禁止は維持する。子をnot-startedにする前に、有効な新成果物/進行中の証拠がないことを確認する。
- [ ] **Step 5:** #104に上流基準で対象がないこと・再導入しないこと・Specの参照を記録し、`state=closed,state_reason=not_planned` にする。他のopen子は閉じず、従来4完了子は編集しない。#104の本文・既存2依存・親関係は履歴として残す。
- [ ] **Step 6:** board.jsonから現行とのrelation差分を生成し、管理する辺に限り追加→読み戻し→旧辺削除の順に更新する。`POST .../issues/N/dependencies/blocked_by` は `issue_id`、DELETE の末尾も predecessorのdatabase id。Issue番号やnode_idを代入しない。#103の外部#18依存削除をcreate-reso-world#18に向けない。
- [ ] **Step 7:** 各子変更・relation変更ごとに親台帳へ成功/未実施を反映して読み戻す。エラー・不明応答ではexact relationを再取得し、重複したPOST/DELETEを盲目的に繰り返さない。全件反映前は board: incomplete/updating を維持する。

### Task 4: 全体照合・成果物の復元確認・解放

**Files:** SESSION/restore/、SESSION/verification.json、当該runのhandoff pair、親の最終台帳/manifest、Planの実行記録。

**テストの要否:** 新テスト不要。完成条件を実際の公開物で検証する。コードを実装していないためdotnet/pytestの実装テストは実行しない。

**Interfaces:** Consumes: Task 3の更新結果。Produces: 照合済みボード、公開から復元した4成果物、条件付き解放の証拠、未実装を明示した最終報告。

- [ ] **Step 1:** #95・18子の本文/全コメント/全parent/全blocked_by/全Sub Issuesを再取得し、board.jsonから生成した集合と照合する。DAG・所有ファイル・公開台帳・本文・historical状態も確認する。Expected: 18子、active16辺とhistorical2辺、#104だけ新たにnot_planned、他の子は未実装、#105がMeshyを待たない。未知の差分があればoperationalにしない。Taskレビューと最終レビューでは、読取専用の sp-review へ同じ受け入れ基準・brief・公開前後のsnapshot・差分・担当報告を渡し、誤対象・履歴消失・未実装の成功扱いがないか確認してもらう。レビュー子はテスト/API変更をしない。範囲外指摘は修正前に調整役が裁定する。
- [ ] **Step 2:** agent-handoffで今回のrunの`.handoff.md`とschema-version-2`.handoff.json`を作る。Spec承認SHA、Plan承認SHA、現行文書commitとPR、実装未着手、code HEAD、許可/禁止、next actionを一致させる。子ごとの未作成のSpec/Planを存在することにしない。
- [ ] **Step 3:** Spec/Plan/handoff pairの正確な中身と、role/path/SHA-256/byte数/encoding/part順/文書commit/承認SHA/出所URLを持つmanifestを#95のコメントへ公開する。handoffには「この公開回復確認と自分のclaim解放はまだpending、子実装は許可なし」と書き、成功を先取りしない。canonical Spec/Planは文書PRのコミットと同一バイトにする。
- [ ] **Step 4:** 空のrestore/へGitHubの公開物だけから4ファイルを復元し、全hash/byte数・JSON解析・相互参照・承認/実行許可の意味・実在するcheckoutを確認する。Expected: mismatchなし。ローカル原本をコピーして復元成功としない。
- [ ] **Step 5:** 親に照合結果・復元manifest・board更新完了と子のnot-startedを記録する。pending解除の実績は、固定した成果物を書き換えず別の完了コメントに残す。claimが保存SHAであることを確認し、次の形式で解放してGETでref不在を確かめる。

```bash
git -C /workspaces/reso-world push --force-with-lease="refs/heads/agent-claims/issue-95:${CLAIM_SHA:?}" origin :refs/heads/agent-claims/issue-95
```

- [ ] **Step 6:** 解放済み・検証結果・所要時間・PR番号をPlanの実行記録に追記し、このボード更新Planだけをcompletedにする。文書差分検査・秘密情報検査をやり直して同じ文書branchを通常pushする。原文復元manifestは公開したcommitに固定して残し、完了追記だけの新commitと混同しない。push失敗なら公開残作業を報告し、完了を先取りしない。
- [ ] **Step 7:** git statusで文書とコードworktree、親・共有checkoutの既存状態が保たれたことを確認し、ledger要約とhandoffを保存してセッション作業物を片付ける。次の子の着手は別の依頼で行い、今回は選択・実装へ進まない。

## 作成時点の検証・自己点検（実行結果ではない）

- 2026-10-29 02:19 UTCから読取で再確認。refsはSpecの基準と同じ、native子16件、現在の依存20辺、claimsは空。repo/default branch/管理権限は一致、Actionsは無効。rulesets/protectionの403はプラン上未提供と明示。文書PRはまだない。実行直前の再確認は省略しない。
- 既存本文のmarkerと#90の管理外知見を調整役が確認した。独立した事実抽出の子は空の結果で終了したため根拠に使わず、同じ入力を調整役が読んだ。Planの自己点検は調整役が行い、子へ委譲しない。
- Spec coverage: D-1〜D-6はTask 1/3の子本文・所有表・受け入れへ反映、履歴保護はTask 1/3、最新基準/排他はTask 1/2、公開と復元はTask 2/4。機能実装は各子へ明示的に分離。
- Step scan/type consistency: Task間の入力はboard.json・claim.json・公開台帳の同じキー/idを使用し、新規Issueの番号や未確定APIを仮定しない。Review Focusの5件は各Taskの事前/事後ゲートへ対応。恒久テスト・機能の実装コードは追加しない。
- 調整役がPlan中のJSONを実際に解析し、active13子/16辺、historical5子/2辺、循環なし、現在の16子とrepo/idの対応を検証した。作成時snapshotとの差分は追加11辺・削除13辺で、更新後は18子/18辺。実行時は最新から再計算し、固定数に合わせて未知の関係を消さない。
- 現在はPlan作成・Specの承認記録だけ。Task 1〜4は未実行、Issue・ref・push・PRの書き込みは未実施。文書はローカルコミットのみなら**公開未実施**と報告する。

## 実行記録（2026-10-29 UTC）

- 実行開始 02:55 UTC。内容承認は上記 SHA、選択方式は直列SDD。Task 1 の下書き担当は約13分、ローカル構造検証は18子/18辺・履歴保護・所有分離で成功。
- Task 1 レビューで証拠確認専用の #110〜#112 に fork 内PRを指示する矛盾を検出。担当が修正し、限定再レビューで指摘2件（反映手順・レビュー資料不足）とも解消、新しい重大な問題なし。Task 1 は review clean。
- Task 2: 親 #95 の自分の予約を取得して所有を照合した。Gitleaks は未公開4コミットを検査して検出なし、検査した `fa43a14ad0519bae36d310e593d8b4fe6326b2c5` を通常pushし、文書PR [#296](https://github.com/usaturn/create-reso-world/pull/296) を作成した。GitHubから取得したSpec/Planは同コミットのバイト列と一致。
- Task 3: 基盤 [#297](https://github.com/usaturn/create-reso-world/issues/297) とCLI統合 [#298](https://github.com/usaturn/create-reso-world/issues/298) を作成し、親#95へ追加。13件のactive本文を更新し、#104だけを理由付きnot_plannedで閉じた。11辺追加・13辺削除後、18子/18辺と全本文・状態の一致を実APIで確認した。歴史4完了子と#104本文、#90の管理外知見は保持。
- Task 3 レビューで、#104コメントの未解決リンクと操作途中のGET/着手確認/削除前ゲート不足を検出。担当が一回限りの操作補助を修正してオフライン検証し、調整役は既存コメントだけを修正してGET確認した。04:17 UTCの現状態照合は全active本文・コメント・依存で成功。ただし過去に不足した操作順序を遡って検証済みとはしない。
- **中断・未完了**: 修正後の限定再レビュー、Task 4の遠隔復元・最終全体レビューは残る。能動予算90分の残りが10分未満となり、新担当を起動しない条件に従って部分成果を引き継ぐ。ボードは incomplete であり、Planをcompletedにしない。自分の親予約だけを引き継ぎ公開後に条件付き解放する。本体実装・マージ・fork側push・上流投稿は未実施。再開には残作業の追加予算の確認を要する。
