# Issue #85: Meshy GLB の tangent normal UV 指定を安全に正規化する

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/85
- PR: https://github.com/usaturn/create-reso-world/pull/88
- レビュー選別したコード HEAD: `42f1b997baa2fdd4401afd94dd9ee031a73d6fb5`
- マージ組合せを検証した base: `fe328c71db79f48f031c4da3323543af4593d322`
- 参考: https://github.com/usaturn/resoloop/issues/17
- 調査したコード HEAD: `8f7594a85636c26c719abe51eb932e8516abf398`
- 状態: completed（実装・レビュー・offline 検証完了。内容の個別承認は未取得）
- 関連 Plan: `docs/superpowers/plans/2026-10-11-create-reso-world-issue-85-meshy-normal-map.md`
- 実行許可: ユーザーの「途中で止めずに推奨案で完了する」により、質問・Spec/Plan 承認待ちを省略し、下記の狭い修正を実行する。承認済みと推測しない。
- 公開: https://github.com/usaturn/create-reso-world/pull/88 （base main、head fix/issue-85-meshy-normal-map）。追加指示「PRしてくださ。」により push・PR 作成を許可。merge・Issue close は未実施。
- `PARENT_ROOT`: `/workspaces/reso-world`
- `DOC_ROOT` / `CODE_ROOT`: `/workspaces/reso-world/.worktrees/issue-85-meshy-normal-map`

## 目的と原因

Blender 5.0.1 の glTF importer は、単一の既定 UV を使う法線マップにも
`Normal Map.uv_map = "UVMap"` を設定する。`scripts/meshy_blender.py` は非空の
指定をすべて拒否しており、Meshy の PBR refine が変換できない。
導入済み ResoLoop exporter も非空を拒否するため、検査だけを外しても直らない。
素材と全メッシュの UV の対応を検証し、安全に同じ UV を使う指定だけを空に戻す。

調査で実 GLB → import → convert の拒否を2回再現した。メモリ内で安全な名前だけを
空に戻す実験では保存・export が成功し、PBS_Metallic の NormalMap、NormalScale、
normal texture の pixels を確認した。API・課金・実ワールド操作は行っていない。

## 変更する仕様

1. 接続された tangent Normal Map の `uv_map == ""` は、これまでどおり許可する。
   空指定に新しい単一 UV 制限を加えない。
2. 非空の名前は、その素材を使う変換対象の**全メッシュ**に UV がちょうど1つあり、
   active UV が存在し、その名前が元の `uv_map` と同じ場合だけ許可する。
   任意の実際の UV 名を比較し、`UVMap` の固定 whitelist は使わない。
3. 非空なのに mesh user が不明・0件、別名、複数 UV、UV 不在、共有素材の一部だけ
   不一致なら `Rejected(material.name, "tangent_normal_active_uv_required")` とする。
4. 共有ノードの元の名前で全ユーザーを検査してから、既存の normal image 検査を通し、
   `node.uv_map = ""` に正規化する。途中で空にして後続の不一致を隠さない。
5. graph の既存制約（TANGENT、定数 Strength、Color 出力、Non-Color、直接画像、
   unlinked Vector、Flat/Repeat/Linear）を維持する。画像・強度・UV 座標を変えない。
6. material の利用先は converter の scene mesh/material slots から集める。
   `material.users` の数や最初のメッシュだけを安全判定に使わない。
7. `adapt_material(material, defaults, cache, *, mesh_users=())` とし、
   `mesh_users` はこの素材を使う `bpy.types.Mesh` の列。
   既存の3引数呼び出しは空指定では動き、非空指定は利用先不明として安全に拒否する。
8. `convert()` は既存の active/render UV 同期を維持し、各素材の全 mesh user を渡す。

## 受け入れと検証

- 法線マップ付き・単一 UV の実 GLB を wrapper の convert → export → offline validate
  で通し、saved blend の空指定と packed Non-Color normal image、
  apply bundle の PBS_Metallic.NormalMap / NormalScale、texture provider の IsNormalMap、
  texture asset の実在と画像 pixels を確認する。
- UV の不一致、名前が同じでも複数 UV、共有素材の一部の不一致を実 bpy で拒否し、
  拒否で元の名前が消えないことを確かめる。
- 任意の一致名、共有素材、空の既存経路と graph safety を実 bpy で確認する。
- normal UV の検査を緩めるオプションは追加しない。既存の
  `--allow-culling-change` は normal と独立した明示同意であり、既存の安全条件を
  保つため fixture の full convert でも引き続き必要。culling gate の回帰も保つ。
- normal fixture は既存の2メッシュ・共有素材に asymmetric 2×2 normal image と
  非既定 Strength 0.65 を加える。実行時に GLB を生成し、binary はコミットしない。
- 文書だけを照合するテストは追加しない。runbook の検証済み範囲を更新する。

## 対象外と制約

ResoLoop checkout / 導入済み exporter / world の同梱写しの更新、UV bake、複数 UV の
対応拡大、material copy、オブジェクト結合、API・課金、live apply、Windows 実機確認、
culling 仕様の変更、無関係な既存テストの修正は行わない。
Issue #17 と安全条件を揃えるが、他リポジトリへの変更許可とは解釈しない。

既存 baseline: configured pytest は 481 passed / 1 failed / 1 skipped。
失敗は `tests/skills/test_legacy_references.py::test_tracked_files_do_not_refer_to_the_migration_source`
が既存 `.devcontainer/test-initialize-mounts.bash:20` の履歴コメントを検出するもの。
skip は他 Git process の cwd を読めない環境条件。既存 conversion suite は54 passed。
新規失敗と混同せず最終結果で明記する。

## 担当側の選択

既存の3引数 APIを保つ keyword-only context と、結合された1タスクを採用する。
TDD の失敗理由は現在の named-UV 拒否であることを記録する。
複数 UV の空指定の既存挙動を変えず、名前付きの安全性だけを拡張する。
詳細な test helper の構成は実装担当に任せ、関係ない構造変更はしない。

## 完了記録（2026-10-11）

- 実装 commit: `cdcf6da9a8f623c8abcf3bd65a4d7c8568a518a5`。最終文書修正: `d5e3809ab0198b879cab00f59666f5a2cb7bb7c4`。コードの実行対象は前者から不変。
- Task review: Spec compliant / Task quality Approved。Final branch review: Ready to merge Yes、Critical/Important なし。文書の UV 不在時のエラー説明を1回修正し、scoped re-review で ADDRESSED・新規問題なし。
- 実 conversion suite: 83 passed、必要な Blender/ResoLoop 検証 skip 0。法線 GLB の convert/export/validate、normal provider と pixels/Strength、UV/階層/素材共有、27 real-bpy safety ケースを実行。
- controller の最終 scripts suite: 282 passed + 144 subtests、skip 0（257.79秒、exit 0）。初回の無変更 CLI setup に cli_timeout が1件あり、該当ケース単独と全 suite の再実行では再現しなかった。原因未確定としてログを残した。
- controller の configured repository suite: 482 passed / 1 failed、skip 0（239.28秒、exit 1）。冒頭の既存 legacy-reference failure が残る。全体テスト成功とは扱わない。
- ruff、diff-check、check-layout は exit 0。active LSP は host の bpy/mathutils 不在、runtime の動的 import、旧 fixture の tuple 推論等の9診断あり。既存 baseline 6診断と比較し、LSP clean とは報告しない。実 bpy 実行と lint の結果は区別する。
- Evidence: `tmp/issue-85-investigation/report.md`、`tmp/issue-85-task-1/implementation-report.md`、`tmp/issue-85-controller/controller-report.md`、同ディレクトリの review と実行 logs（作業 worktree 内のローカル資料）。
- 所要: 調査24分47秒、実装19分18秒、Task review約5分、controller test commands13分05秒、Final review約10分、文書fix1分37秒、re-review約2分。セッション全体は約85分（計画・記録・統合確認を含む）。
- Final review の対象外判断を確認: 空指定の追加制限は上記互換性判断を維持し、公開版/latest・rebuild・Windows/live・課金 API の保証は追加しない。任意の converter-level shared mismatch テスト追加提案は、現実装が正しく既存のadapter+E2E検査があるため今回追加しない。
- PR 作成前はローカル保持で完了し、親 checkout の origin/main detached HEAD は変更しなかった。その後、追加指示により下記の公開を実施。

## 公開記録（2026-10-11）

- ユーザーの追加指示「PRしてくださ。」に基づき、既存ブランチを origin に push し、PR #88 を main 向けに作成した。実装・設計内容は変更せず、公開状態の記録のみ更新する。内容の承認・merge・Issue close の許可とは解釈しない。
- 公開前の再確認: `uv run --frozen pytest tests/scripts/test_meshy_conversion.py -q -rs` は83 passed / skip 0（143.48秒、exit 0）。ruff、diff-check、check-layout も exit 0。ログは worktree の `tmp/issue-85-publication/conversion.log`。
- PR 本文に既存の全体テスト失敗1件と LSP／実測版／offline 範囲の制約を明記した。private repository の CI は運用上停止中のため追加のCI待ちは行わない。
- 公開元は `origin/fix/issue-85-meshy-normal-map`。PR は OPEN、draft ではない。親 checkout・world・外部リポジトリを変更せず、worktree を保持する。

## PR #88 のレビュー選別（2026-10-11）

### 対象と実行許可

- 状態: completed（全指摘の現行検証・分類とマージ前の必要な検証を完了）。結論は **2: 修正不要としてマージする**。マージ・Issue 更新の実行結果は PR の状況コメントと作業報告で扱う。
- ユーザーの `review-fix-planning #88` 呼び出しは計画のみの指定を含まないため、同スキルの完遂経路を適用し、既存 PR への Spec の commit/push、最終コメント、検証した head のマージ、関連 Issue の更新を実行する。内容の個別承認とは別の実行許可として記録する。
- 同じ対象リポジトリ・Issue #85・PR #88・normal UV 正規化を扱う現行 Spec は本ファイルの1件、関連 Plan は冒頭の1件と確認し、本ファイルを更新する。設計・実装・Plan は変更しない。
- 入力は `reviews/#88-fix-issue-85-meshy-normal-map/` の全3ファイル。全ファイルの対象 HEAD は `42f1b997baa2` で、fetch した PR head `42f1b997baa2fdd4401afd94dd9ee031a73d6fb5` と一致する。
- clean かつ PR head と一致する既存の専用 worktree `/workspaces/reso-world/.worktrees/issue-85-meshy-normal-map` を再利用した。他セッション所有なので片付け対象にしない。親 checkout、world、ResoLoop のコードや導入版は変更しない。

### 全指摘の分類

件数は **解消済み0 / 対応する0 / 対応しない3**。同じ論点でも入力レビューの ID ごとに数える。

| 入力ファイル / ID | 指摘 | 分類 | 現行 HEAD の根拠と理由 |
| --- | --- | --- | --- |
| `deepseek-deepseek-v4.1-flash.md` / I-1 | E2E が元 GLB の normal UV の非空を明示的に断言していない | 対応しない | `tests/scripts/test_meshy_conversion.py:327-350` に original 側の UV 名の assertion はない。今回の E2E 保存物で original=`UVMap`、saved=`""` を実測し、現行は named UV 経路を通る。将来 importer が空を設定した場合のテスト耐久性の提案で、現行の変換の誤結果・停止ではない。 |
| `SWE-2-High.md` / L-1 | 上記と同じ E2E 前提の未固定 | 対応しない | 同じ実測と該当行を根拠とする。実 bpy の27ケースは名前を直接設定して named UV の許可・拒否を検査しており、現行のロジックの回帰ガードは存在する。 |
| `SWE-2-High.md` / I-1 | `safety()` の未知 case が既定構成を使う | 対応しない | `tests/fixtures/meshy/check_normal_uv.py:98-115,208` に未知 case の拒否はなく、隔離 worktree で `typo_not_defined` が単一 `PaintedUV` の構成として accepted になることを再現。現在使う `test_meshy_conversion.py:365-396` の27ケースはすべて正しい分岐に対応し成功する。テスト拡張時の typo 防止の提案で、実変換の入口には影響しない。 |

`claude-opus-5-5.md` は指摘0件。各レビューの Test suggestions は上の ID の提案の再掲であり、別指摘として重複計上しない。確認中に新たな PR 起因の致命的な欠陥は見つからなかった。

### 調査と判断

- PR の変更7ファイルを全文確認: `scripts/meshy_blender.py`、`tests/fixtures/meshy/create_fixture.py`、`tests/fixtures/meshy/check_normal_uv.py`、`tests/scripts/test_meshy_conversion.py`、`docs/meshy-resoloop.md`、本 Spec、関連 Plan。
- 関連処理は `scripts/meshy.py` の convert 呼び出し、`scripts/meshy_conversion.py` の全変換・拒否・保存経路、共通 `meshy-resoloop` スキルを確認。全メッシュ利用先の収集、共有ノード変更前の全 user / normal image 検査、既存空指定・3引数呼び出し・graph safety・culling 同意・拒否時の未公開を確認した。
- 独立した読み取り専用調査を `sp-recon` に同期委譲し、現行の3指摘と関連経路を照合した（exit 0、205.74秒）。子の実行未確認事項（worktree clean/head、一部ファイルの全文、実 bpy）は調整役が補完し、子の報告だけで判定していない。
- 推奨案は実装・テストを変更しないこと。対案の assertion 追加や未知 case の拒否は将来のテスト保険で、現行の致命的な欠陥の修正には当たらないため採用しない。PR の保証と食い違う実在の利用制約ではないため、PR 本文の保証は変更しない。
- 対応する項目がないため、新しい影響経路表・設計の見直し・ガードを外した対照は対象外。コードやスキルの変更もなく、追加テストは不要（文書記録のみを検査するテストは書かない）。
- 修正後の自己レビューは未実施。結論1の実装修正がないため同節の対象外であり、初期の独立調査と全変更確認を自己レビューと呼ばない。

### 実行検証

Blender `5.0.1`、導入済み ResoLoop `0.1.0-preview.17.fork.20261009.g84c7932`。API キーを使用せず、API・課金・live apply・Windows 操作は実行していない。

| 対象 | コマンド / 確認 | 結果 |
| --- | --- | --- |
| PR head の専用 worktree | `env -u MESHY_API_KEY uv run --frozen pytest tests/scripts/test_meshy_conversion.py -q -rs --basetemp <隔離root>/pytest -p no:cacheprovider` | 83 passed、skip 0、158.75秒、exit 0。normal GLB の convert/export/validate と saved blend/bundle の画像・UV・強度・階層・共有素材、および実 bpy の27 safety ケースを含む。 |
| PR head の専用 worktree | `bash .devcontainer/run-tests.bash` | 29本すべて PASS、exit 0。変換テストと並行した全体待機は208秒。 |
| PR head の専用 worktree | `bash scripts/check-layout.sh` / `git diff --check origin/main...HEAD` | 両方 exit 0。 |
| 変更 Python | `uvx ruff check scripts/meshy_blender.py tests/scripts/test_meshy_conversion.py tests/fixtures/meshy` | All checks passed、exit 0。 |
| 隔離した現行 HEAD | E2E の `normal-inspection.json` を読む | original normal UV=`UVMap`、saved normal UV=`""`。 |
| 隔離した現行 HEAD | `resoloop blender run tests/fixtures/meshy/check_normal_uv.py --arg=--case --arg=typo_not_defined --arg=--output --arg=<隔離root>/unknown-case.json --json` | exit 0、accepted=true、元の `PaintedUV` が空へ正規化。上表の非致命的な未知 case の挙動を再現。 |
| head と最新 base の組合せ | HEAD を照合した一時 worktree に `fe328c71db79f48f031c4da3323543af4593d322` を `merge --no-commit --no-ff`、同じ変換 suite / environment runner / layout を実行 | 競合なし。変換83 passed、skip 0、132.92秒、exit 0。environment 29本 PASS、layout PASS、各 exit 0。並行検証全体176秒。merge は push しない。 |

- 最新 base は PR の分岐点より進んでいたため、一時的なマージ組合せで同じ検証を通した。base の進行は #86 による legacy-reference guard の削除であり、上の過去記録の全体 pytest 失敗を今回再実測した失敗とは扱わない。今回は変換 suite と指定の環境検証を実行し、無関係な一括 pytest は再実行していない。
- `usaturn/create-reso-world` は private、PR は OPEN / draft=false。ルート `AGENTS.md` により CI 確認は不要。マージ可能範囲内である。
- scratch・ログ・pytest の保存物は一意の `/tmp/review-fix-planning.sU4MO8/` に閉じ込めた。検証完了後、登録した一時 worktree を `git worktree remove --force` で外してから親ディレクトリを削除し、消失を確認した。旧ディレクトリは再利用しない。
- 本文に残る未検証範囲（公開版/latest、標準 rebuild、Meshy 実 API、Windows/live、LSP 制約）は今回も未検証のままであり、指摘0件や offline 成功をそれらの成功の根拠にはしない。

### 所要時間

調整役の開始は 2026-10-11 15:53:14 UTC、マージ前の検証・分類記録まで約15分。主要内訳は準備・入力確認約2分、独立コード調査3分26秒、head 検証3分28秒、base 組合せ検証2分56秒、全文補完・再現・分類・記録約3分。commit/push・投稿・マージ・Issue 更新の最終所要は作業報告に記載する。
