# DSH Native Write Policy Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DSHのnative filesystem policyへcontrollerの限定的な追加書込先を接続し、PR固有領域で成果を作成できるようにするための後続作業を定義する。

**Architecture:** 公式の追加書込先APIを前提とし、既存`Dsh.prepare`とbubblewrapの境界へ接続する。導入済みDSHにはAPIがないため、この計画は**blocked/not ready**であり、Gate A/B/Cを満たすまで実装担当を起動しない。設定名や引数を推測した実装計画にしない。

**Tech Stack:** 既存Python >=3.14/uv/pytest、DSHの公式native policy、bubblewrap。新規依存・対応版は未採用。

**Spec:** `docs/superpowers/specs/2026-10-19-create-reso-world-issue116-dsh-native-write-policy-design.md`

## 状態・権限

- 文書状態: **draft**。計画の作成許可はあるが、内容承認・実装許可はない。
- 対象: usaturn/create-reso-world、親 #116。提案キー`dsh-native-write-policy`。新しい子Issueは未発行で番号はない。親の既存実行マップ/台帳/native依存は変更しない。
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-116-dsh-native-policy-plan`、文書branch `docs/issue-116-dsh-native-policy-plan`。PARENT_ROOT: `/workspaces/reso-world`。基準main `1335f410e624355cd558029bdcdad65eaa944ed8`。
- #153/PR #182の実装branchを変更しない。文書branchはローカルcommitだけで、push/新PRは公開未実施。4文書の内容は親Issueのコメントで公開・復元検査する。

## Global Constraints

- 公式に検証された追加書込先APIを条件にする。導入済み`0.2.0-rc.2`の追加roots未対応を解消済みとしない。
- `tools/workspace`・`projects.toml`は導入しない。#116冒頭の「致命的な指摘だけ修正・結論の三択・修正後自己レビュー最大1回」を維持する。
- 許可はcontrollerが起動前に確定したcanonicalな対象だけ。共有`.git`や親reviews全体へ広げず、symlinkの範囲外と隣接領域を拒否する。
- Request/Receipt/Resultと`Dsh.prepare(context: AdapterContext) -> LaunchSpec`、`AdapterContext.sandbox_write_paths`は変更しない。
- full-access、別cwd/HOME/cache、別ツールによる拒否回避、個人設定変更、子へのGitHub token、導入済みpackageの直接編集は行わない。
- #174/PR #180の診断/collect、#153のpr-review、他runtime・別の子を所有しない。外部repoのclone・実装・PR作成は未許可。
- Pythonはuvで実行。実装時のrootは正式な担当が作った孤立worktreeであり、本文のDOC_ROOTでコードを作り始めない。
- この計画作成中の実装テスト・DSH/Devin等の実機起動は0回。文書検証をコードの動作確認と報告しない。

## Review Focus

1. 正常な追加PR保存先がnative write/editとbashの両方で使え、追加bindだけの偽陽性になっていないか（Task 2）。
2. 許可したディレクトリの隣、別PR、symlink経由、read-onlyが拒否され、通常ファイルgrantのために親を許可していないか（Task 2）。
3. 版が新しいだけ/未知の設定キーが無視されるだけで対応済みと判定し、有料起動へ進まないか（Task 1/2）。
4. 起動後のcwd/Request/Identityの意味や秘密情報の掃除が変わらず、#174の診断修正と混ざらないか（Task 2/3）。
5. DSH単独の成功を、同一HEADの全員並行レビューや#153全体の完了へ読み替えないか（Task 3）。

## 実行予算

- 今回の計画は既存Issue全体の有効210分の残りを使い、**20分以内**を目安に停止・公開する。共通ledger: `/workspaces/reso-world/tmp/agents/issue-153.j8p_g6l_/budget.jsonl`。今回の資料: 同SESSIONの`planning-dsh/`。
- 段階目安: 既存ボード/所有確認4分、Spec/Planとbuilder check8分、構造・復元・公開8分。builder checkは読み取り専用1件・目安2分、実装や実機はしない。
- 将来の実装予算案: **90分**（未許可）。Gate A/B/C確認15分、Task 2のfake実装/回帰45分、Task 3の文書/統合確認15分、記録15分。予算と対応APIを具体化するまで着手しない。
- 将来のworkerは共有worktreeに書く実装子1件ずつ、検証は同期終了まで待つ。信頼性の同じ失敗は原因が変わる場合だけ1回まで。権限/安全の拒否は即停止し再試行しない。
- 実機予算は別許可が必要。候補はpending DSH1回、900秒・fallback無し。controllerは`task_watch.py`の1200秒/予約120秒/無進捗600秒/INT/grace30秒/escalate-kill無しを事前宣言し、停止確認まで待つ。既存の成功Devin/非runnerの再実行を含まない。
- checkpoint: 今回のSpec/Plan保存、復元完了、将来のGate Aと各Task終了、予算50%/100%。API失敗・予約競合・権限境界・予算上限で停止。情報不足は「公式API待ち」として保持し、別cwd設計や上流コード修正へ自動変更しない。

---

### Task 1: 公式対応の証拠と所有範囲を確定する（開始ゲート）

**Files:** このSpec/Planの既存ファイルのみ。新Issue・親実行マップ/公開台帳の更新は具体的に許可された場合だけ。

**Interfaces:**
- Consumes: DSH公式の追加書込先API資料、固定した公開版/package/ソース、現在の`Dsh.prepare`と`dsh_sandbox.py`、#174/PR #180の最新状態。
- Produces: 採用APIの正確な設定名・型・版/ハッシュ・native write/editとbashへの適用条件・read-only/ファイルgrantの意味を本Spec/Planへ記録したコミット。設定名は証拠から定める。

**テスト:** 今回は文書だけなので不要。代替は参照先・固定ソースの実在、APIの実現性、所有範囲、差分検査。将来は公式backendの副作用の無い隔離検証を使い、モデルを呼ばない。

- [ ] Step 1: 最新の公式資料と隔離した採用候補packageを照合し、additional rootsが実際にnative filesystemに適用されるAPIを特定する。版番号・helpに語があるだけでは成功としない。無ければここで停止しblockedを維持する。
- [ ] Step 2: controllerの許可集合、native policyの集合、bash/bwrapの集合を比較する検証を定義する。ディレクトリ・必要なfile grant・canonical化・read-only・未知API拒否の期待結果を固定する。
- [ ] Step 3: 親の調整役が新しい作業単位と所有を確定する。#153をnative接続の先行にして循環させず、#153側の消費テストと接続側の実装を分ける。#174が同じファイルを使う場合はprepareと診断/collectの非重複を確認する。
- [ ] Step 4: 正確な外部APIと失敗の表現をSpec/Planへ反映し、内容と実装/版変更の許可を得る。ここが未充足ならTask 2へ進まない。今回の計画作成指示を実装許可に流用しない。

### Task 2: DSHのnative許可とbashの許可を接続する（Task 1後のみ）

**Files:**
- Modify: `tools/agent_runner/adapters/dsh.py`の`Dsh.prepare`のみ。
- Modify as needed: `tools/agent_runner/dsh_sandbox.py`の既存grantの検査・適用部分のみ。
- Test: `tools/agent_runner/tests/adapters/dsh/test_adapter.py`、`test_sandbox.py`、必要なら`fake_cli.py`。
- Modify only DSH installation behavior: `.devcontainer/install_beforehand.bash`と`.devcontainer/test-install-beforehand.bash`（公式対応版への変更が必要で、具体的に許可されたときだけ）。

**Interfaces:**
- Consumes: Task 1で証拠とともに固定した公式API、既存`AdapterContext.sandbox_write_paths`、`Dsh.prepare(context) -> LaunchSpec`。
- Produces: 同じpublic interfaceのまま、必要なnative/bwrap双方の許可と未対応時の起動前拒否。外部APIが未確定なので、patchの具体的キーや新たなprivate関数は本版では定義せず、**Task 1で計画を更新するまで実装不能**とする。

**テスト:** 実際の許可・拒否・起動前の分岐を実行するため必要。固定文面・可変版やモデル一覧のコピーをテストにしない。

- [ ] Step 1: fake CLI/backendで、同一sessionから許可PR領域へのnative write/editとbashの書き込みが成功し、兄弟PR/隣接/symlink範囲外/read-onlyが拒否される失敗テストを書く。未対応・不明なAPIではLaunchSpecから有料プロセスを開始しないこと、file grantの親を許可しないことも固定する。
- [ ] Step 2: 実装worktreeをcwdに`uv run --locked pytest tools/agent_runner/tests/adapters/dsh -q`を同期実行し、意図した挙動の失敗を確認する。非対応APIを偽装してGREENにしない。
- [ ] Step 3: Task 1の公式APIへだけcontrollerの起動前許可を接続し、上記と同じコマンドでGREENを確認する。approval=never、workspace-write、Request/cwd、Identity、認証隔離を保つ。拒否後の再ルートは追加しない。
- [ ] Step 4: その変更を覆うrunnerのfake回帰を同期実行する。`uv run --locked pytest tools/agent_runner -q`。installerを変えた場合は`bash .devcontainer/test-install-beforehand.bash`も実行する。全exit0を確認し、許可されていないファイルをstageしない。実機はここでは起動しない。

### Task 3: 消費側への受け渡しと許可された実機だけを確認する

**Files:**
- Modify: `.devcontainer/README.md`のDSH制約の記述のみ。
- Create if needed: `tools/agent_runner/runtimes/dsh.rst`（現状は未存在）。RSTを作る場合はrst-writerを読む。
- Record: 本Spec/Plan、担当Issueコメント、#153への接続仕様の連絡。`.agents/skills/pr-review/`は#153担当が所有し、変更が必要なら調整役へ返す。

**Interfaces:**
- Consumes: Task 2の対応版・native許可・失敗条件と#153のprepare-parent/prepare/staged/finalize-parent/attach-runner。
- Produces: 採用版/APIと実行結果、適用範囲、未達の受け入れを明示した受け渡し。Resultを変更せず、停止・Identity/Request/digest/HEADを親が照合する。

**テスト:** 手順文面だけの新テストは不要。実装の回帰は必要。実機は追加の具体的な許可があるときだけ必要で、無ければ未実施と報告する。

- [ ] Step 1: 条件の説明を実装と照合し、既存の「追加bindだけでnativeも許可される」という誤解を残さない。DSHの制限と対応API、未対応時の停止を説明し、個人設定を変更しない。
- [ ] Step 2: 対応する実装commitで`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`を同期実行する。Task 2に対する独立レビューと必要な修正の確認は既存規則の上限内とする。
- [ ] Step 3: 実機が明示的に許可された場合だけ、現行PR HEADを再取得しfresh prepare-parentからpending DSH1回を監視付きで起動する。拒否で止め、権限や場所を変えてやり直さない。success時もpair/実行記録/cleanup/停止とnative writeの実証を照合し、結果を#153に返す。同一HEADの全員並行レビューが別途必要なら、追加構成/費用を許可された統合作業として分ける。
- [ ] Step 4: コードpush/実装PR作成が許可されている場合だけGitleaksで検査したSHAをそのまま送る。既存PRがあれば再利用し、#153/PR #182へ変更範囲外コードを混ぜない。マージ・新Issue・rebuildは行わない。失敗はblockedのまま記録し、所有claimを解放する。

## 自己点検・今回の到達点

Specのnative/bwrap整合・限定許可・未知API拒否はTask 1/2、認証/Request/停止と消費側の確認はTask 3に対応する。public signatureは変えない。公式APIが存在しない現時点では、Task 2のpatch形を確定できないため**実行準備未完了**と明示し、実装できる計画や対応済みのDSHを装わない。

今回完了するのは、推奨方針・代案・所有・依存・実行ゲート・検証を定義したdraft文書と復元可能なhandoffの公開のみ。builder checkは1回実施し、未存在だったruntime文書を「必要時の新設」へ修正した。コード・実装テスト・実機は一切実行していない。
