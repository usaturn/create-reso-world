# Issue #248: flux-sdk の扱いを改める Implementation Plan

**Goal:** flux-sdk を「既定では入れない。必要なときに入れる」と読める記述にし、導入・前提・確認方法を `.devcontainer/README.md` に書く。

**Spec:** `docs/superpowers/specs/2026-10-24-create-reso-world-issue248-flux-sdk-docs-design.md`

## 管理

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/248
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-248-flux-sdk-readme`
- 実行許可: Spec の「管理」と同じ（`--merge`）
- 実行方式: inline（`superpowers:executing-plans`）。`implement_task.py check` の `self` が true で、変更は文書 3 か所の短い編集であり、委譲する文脈の手間が上回る
- 基準: `origin/main` の `7cf6071`

## 実行予算

- Issue 全体の能動時間の予算: 120 分（実装・検証 30 分、PR 修正ループ最大 3 サイクルのうち収まる範囲）
- 再試行の上限: 同じ signature の信頼性の失敗（`run-tests.bash` の時間切れ・負荷）は 1 回まで。安全の失敗は再試行せず止まる
- checkpoint: 編集の後、検証の後、PR の作成の後、ループの各サイクルの後
- 縮小の候補: `run-tests.bash` が負荷で落ちたら、落ちたテストだけを単独で再実行し、基準の同じテストと比べる

## Task 1: 文書の編集

- 担当ファイル: `.devcontainer/README.md`、`README.md`、`docs/resoloop-fork-workflow.md`
- テストの要否: 不要（採用基準の F。確かめは検証のコマンドと `git diff`）
- [ ] `.devcontainer/README.md` の「ProtoFlux 用の flux-sdk は…導入しない。」を、既定では導入しないことと、節への参照に置き換える
- [ ] 同 README の「Resonite の写真フォルダ（任意）」の前に、「ProtoFlux 用の flux-sdk（必要なときだけ）」の節を足す（Spec の「書く内容」の 1〜5）
- [ ] `README.md` の「対象外」から「flux-sdk の導入」を外す
- [ ] `docs/resoloop-fork-workflow.md` の「対象外」の 1 文を、`.devcontainer/README.md` の節への参照に置き換える

## Task 2: 検証

- [ ] `rg -n "flux-sdk" .devcontainer/README.md README.md docs/resoloop-fork-workflow.md` で古い断定が無いこと
- [ ] `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash` の終了コードが 0
- [ ] `git diff --stat origin/main` が、3 つの文書と Spec・Plan だけ
- [ ] `resoloop flux status` の案内（版・導入コマンド）と、書いた内容が一致する

## 要件と Task・検証の対応

| 受け入れ基準 | Task | 検証 |
| --- | --- | --- |
| 既定では導入しないことが分かる | 1 | `rg` で該当の文を確認 |
| 何を・どの版で・どう入れるか分かる | 1 | `resoloop flux status` の案内と照合 |
| 導入の確認方法が分かる | 1 | 同上 |
| 古い断定が範囲に残らない | 1 | `rg` の出力 |
