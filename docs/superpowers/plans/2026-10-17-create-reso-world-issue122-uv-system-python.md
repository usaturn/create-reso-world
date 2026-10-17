# Issue #122 リビルド後の配置修復 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** uv 設定反映後に残った、移設したワールドの起動パスと非ワールドの誤ったレイアウト検査を直す。

**Architecture:** 未指定のプロジェクトは従来どおり world として検査する。検査ルートのローカル設定 `.check-layout-projects.json` に明示された assets/items のみ、用途別の要件で検査する。親checkoutのローカル配置は限定修復し、成果物・独立リポジトリ・既存環境の再作成には触れない。

**Tech Stack:** Bash、jq、uv、pytest。

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue122-uv-system-python-design.md`（今回の変更はD-7〜D-12）

## 管理・実行許可

- 状態: draft。元の設定・説明はPR #129で実装済み。このPlanは同じIssueの残課題として更新する。
- 利用者のissue-to-pr依頼と、ローカル配置修復・非ワールドを区別する検査仕様変更への「OK」を実行許可として扱う。内容承認のSHAは記録されていない。
- コード・文書: `usaturn/create-reso-world`、基準 `76f1098af9f07388f4c10d55786ea9d726654171`。
- DOC_ROOT/CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-122-local-layout`、branch `fix/issue-122-local-layout`。PARENT_ROOT: `/workspaces/reso-world`。
- 実行方式: executing-plans（inline）。2 Taskの小さい変更で、checkerとローカルでの実検証が逐次依存するため。独立調査はsp-debug、設計builder checkと最後のブランチ全体のレビューは読み取り専用sp-reviewに委譲する。

## Global Constraints

- Spec D-1〜D-6のuv設定を再実装しない。requires-pythonは変更しない。
- `.venv`再作成、消失した3.12の再導入、別リポジトリの編集、Resonite操作、有料API、ダミー雛形追加、マージは禁止。
- 追跡ファイルはworktreeだけで編集。ローカル設定と検証ログ・バックアップはPARENT_ROOT側の所定位置に置く。
- ローカル設定のキーは収集済みプロジェクトの完全一致だけ。未指定worldの検査を緩めない。
- テスト/検証はforegroundで同期実行し、終了コード・ログを確認してから次へ進む。

## Review Focus

- configの壊れた型・不正JSON・未知profile・外部/深いパス・存在しないキーはFAIL（Task 1のfixtureで検証）。
- assetsが標準ワールドの欠落を隠さないよう、設定なしと明示worldは厳格な既存検査を維持（Task 1）。
- itemsで共有リンクやuv.lock検査を失わない（Task 1）。
- assetsではresoloop同期を呼ばず、共通の追跡禁止検査は継続（Task 1）。
- ローカルでのuv実行が3.12環境の再作成を誘発しない（Task 2でsystem3.14の実在を事前確認）。

## 実行予算

- 全体の能動時間55分（前回の調査8分は完了済み別区間）。準備/Spec・Plan10分、コード/TDD15分、ローカル修復・全体検証15分、レビュー/PR15分。
- ledger: `/workspaces/reso-world/tmp/agents/issue-122.8evpv7k0/budget.jsonl`、実装進捗は同じsessionの `progress.md`。worktree内へ未追跡workspaceを作るスキル補助scriptは使わず、brief・BASE・実行結果もこの進捗ファイルで管理する（リポジトリの保存先規則を優先）。
- 同期サブエージェントはAPI上停止できないため強制終了しない。設計/最終レビューは各5分目安・保存予約1分・無進捗3分を報告の目安にし、終了まで待つ。時間で停止できるworkerは起動しない。
- 同じ信頼性の失敗は再試行1回まで。安全の失敗は再試行せず停止。検証・実装を時間でkillしない。
- checkpoint: phase境界、予算50%/100%、worker失敗直後。100%で未完なら停止報告。
- contingency: 既存worldに新しい競合があればその修復を停止・報告する。検査で同期警告だけなら既定どおり許容。真の失敗はsystematic-debuggingで調査し、機能を無条件skipして通さない。

---

### Task 1: 明示profileで用途別レイアウトを検査する

**Files:** Modify `scripts/check-layout.sh`、`tests/scripts/test-check-layout.bash`、`.gitignore`、`README.md`。

**Interfaces:** `.check-layout-projects.json` は `{"worlds/<name>": "assets"}` 等のobject。値はworld/assets/itemsだけ。設定が無ければ追加依存なし。設定があればjqを要求し、不正設定はFAIL。assetsは通常ファイル `.resoloop.json` のみ、itemsはworldのroot flux設定を実ディレクトリitemsに置換、それ以外はworldと同じ。

**テストの要否:** 必要。入力の型/パス拒否、profile分岐、外部コマンド呼び出し範囲、標準worldの安全条件という実行ロジックを守る。READMEの文言やローカルの固有名は照合テストにしない。

- [x] Step 1: 一時git fixtureでassets/items成功、未指定world欠落失敗、items共通リンク/lock不足失敗、不正JSON/型/profile/パス/未収集キー/設定symlink/jq不足、共通追跡禁止とassets同期回避の挙動テストを追加する。
- [x] Step 2: `bash tests/scripts/test-check-layout.bash` を実行。Expected: 新profileのfixtureだけFAIL（RED）。baselineは同じworktreeで成功済み。
- [x] Step 3: checkerに設定の検証・profile分岐を追加。ローカル設定をgitignoreし、READMEに各profileの意味・例・未指定の既定値・エラー条件・移設した起動パスの注意を書く。
- [x] Step 4: 同じテストを再実行。Expected: PASS。`bash -n scripts/check-layout.sh tests/scripts/test-check-layout.bash` と `git diff --check` も成功。
- [x] Step 5: 明示した4ファイルだけstage/commitする。

### Task 2: ローカル配置を限定修復し、全体検証・PRを行う

**Files:** PARENT_ROOTのローカル設定、worlds/{MyResoniteProject,akichi,slum02,slum03}の共有リンク、worlds/{akichi,slum02}/.venv/binの旧パスを含む通常テキスト、worlds/LumenAbyss_Astra/uv.lock。進捗をこのPlanとSpecに記録する。

**Interfaces:** Task 1のcheckerを `--root /workspaces/reso-world` で実行。local configは assets=asakusa01-meshy、items=reso-workshopを指定し、これら2プロジェクト自身には書かない。

**テストの要否:** ローカル設定/リンク/生成物の修復だけなので新テスト不要。差分、旧値確認、バックアップ、実コマンド結果で検証する。

- [x] Step 1: 既存AGENTS・git status/worktree・interpreterを再確認し、修復対象の旧値/ファイルをsessionのbackupに保存する。akichi/slum02で通常 `uv run pytest` の旧shebang失敗を確認。Expected: 起動失敗、環境再作成なし。
- [x] Step 2: 12本のリンクを正しい深さに更新。正常な3.14環境のbin内旧パスだけを置換（symlink・binaryは除く）。Astraで `uv lock` を実行。Expected: uv.lock生成、`.venv`は無いまま。許可対象以外は触らない。
- [x] Step 3: PARENT_ROOTのローカルprofile設定を作成。変更版checkerの `--root /workspaces/reso-world`、akichi/slum02の各cwdで通常 `uv run pytest` を実行。Expected: PASS/全件成功。残る壊れた3.12環境はそのままと記録。
- [x] Step 4: 作業worktreeで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts`。`bash .devcontainer/verify-resonite-tooling.bash` も確認。Expected: すべて終了コード0。新checkerを使う親ローカル検査と、worktree自身の検査結果を区別する。
- [x] Step 5: Spec/Planの実行記録を更新してcommit。fresh sp-reviewでブランチ全体を読み取り専用レビューし、Critical/Importantのみ1回の修正passでRED→GREEN確認する。
- [ ] Step 6: Issue状態・他者との競合を再確認。scan-before-pushで検査したSHAだけpushし、base mainのPRを作成する。本文にCloses #122、決定と理由、実行方式、検証、所要時間、残る対象外を記録。マージしない。Issueへ検証結果をコメントする。
- [ ] Step 7: ログの要点をSpec/Plan/PRへ転記し、稼働中の子が無いことを確認。sessionを片付け、Herdrをcompletedにして報告する。親の旧checkerはマージ前なので未変更である旨も伝える。

## 実行結果

- Task 1: `e5058f0..85f0212`。profileの実行テストはRED（終了1）→GREEN（終了0）。複数JSON文書の入力拒否も追加のRED→GREENで確認。`bash -n` と `git diff --check` 成功。
- Task 2: akichi/slum02で通常の `uv run pytest` が旧shebangで終了2になることを確認し、共有リンク12本と生成binテキスト16ファイルだけを限定修復した。バックアップのbyte比較で意図したパス置換だけであること、pyvenv.cfgの不変、既存環境のディレクトリinodeの維持を確認。Astraはlockfileだけ生成し、`.venv`なし。
- 親のローカル設定: asakusa01-meshy=assets、reso-workshop=items。独立領域自身は無編集。未マージの親.gitignoreの代わりに同じ設定1パスだけ.git/info/excludeにも登録し、親のgit statusはclean。

| 検証 | 結果 |
| --- | --- |
| 作業worktree `bash .devcontainer/run-tests.bash` | 最終32/32、終了0 |
| 作業worktree `bash scripts/check-layout.sh` | PASS、終了0 |
| 作業worktree `uv run pytest tests/skills .agents/skills .agents/scripts` | 625 passed、終了0 |
| 変更版checker `--root /workspaces/reso-world` | PASS、終了0。ResoLoopスキルの更新警告は既存方針どおりwarn |
| `worlds/akichi` の通常 `uv run pytest` | 62 passed、終了0 |
| `worlds/slum02` の通常 `uv run pytest` | 226 passed、終了0 |
| 作業worktree `bash .devcontainer/verify-resonite-tooling.bash` | .NET/ResoLoop/Blender/NumPy確認、終了0 |

最初のshell suiteは31/32（READMEの短縮パスを実在参照と誤記）。実際のパスとローカル設定の説明へ直し、個別docs検査と最終32件すべての再実行が成功した。未実施の検証を成功としていない。

### 最終レビューと裁定

- sp-reviewが全6ファイルのBase `76f1098` → Head `1f35ffe` を確認。Critical/Important/Minorはすべて0件。テスト実行はcontrollerが担当。以後の変更は検証記録だけ。
- 裁定: スキル補助scriptが作るworktree内のworkspaceではなく、リポジトリ規則のPARENT_ROOT sessionにbrief・BASE・進捗・差分を保存した。挙動への影響なし。
- 裁定: 新しいローカル設定1件を.git/info/excludeにも登録した。親の追跡ファイルを変えずに誤stageを防ぐ。ローカル設定は意図的にcommitしない。
- レビュアーが範囲外とした3.12環境/独立リポジトリ修復は、利用者の除外範囲どおり対応しない。その3環境は後日の許可された修復まで使用不可のまま。
- レビュアーが範囲外としたpostCreateの状態表示へのprofile適用も行わない。表示は完了条件ではなく、余分なassets向け警告が残り得る。
- 予算: 最終レビューと全体検証の終了時点で能動19分21秒/55分、信頼性失敗はdocs参照1回、安全の失敗なし。phase別は準備/設計4分、実装/TDD3分、ローカル修復と検証7分、レビュー/再検証5分が目安。公開に要した時間はPR本文に記録する。
