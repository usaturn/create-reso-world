# Issue #105 上流PR提出 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to follow this plan task by task. This task publishes an already implemented and validated candidate; no new application code is planned.

**Goal:** 検証済み feat/plugin-system を orange3134/resoloop:main へ直接PRし、作成結果をIssue #105へ記録する。

**Architecture:** 4機能を共有基盤・CLI・文書・最小例とまとめて1本のPRで提出する。候補treeは変えず、Spec・Planはcreate-reso-worldの文書専用ブランチへ置く。

**Tech Stack:** GitHub repository/PR APIs、Markdown、既存の.NET 10.0.201検証記録。

**Spec:** docs/superpowers/specs/2026-11-19-create-reso-world-issue105-upstream-pr-design.md

- 文書の状態: draft（内容承認の記録は作らない）
- 実行許可: 2026-11-19の利用者の明示指示により、準備完了後は追加確認なく上流PRを作成する。

## Global Constraints

- 提出head c72deaf0e13f9a423d3bd4ef0afef79ee4a6cb9b、tree 9d1fa089f93de4e0c74afb63da64a83ca439b6a6。
- 上流base main 32309ca3deb4560e6a31a8985dba87ba5485c946。投稿前に現在のrefを再取得する。
- 4機能・plugin install/list/remove・文書・例とD-1〜D-6を維持し、本体コードを変更しない。
- 旧feat/plugin-v2、fork main、公開済み候補の履歴を書き換えない。
- 上流のマージは作者に委ねる。PR作成だけで#105を閉じない。
- 本体検証の既存結果と、今回実行したAPI/静的確認を区別する。
- Spec・Planはcreate-reso-worldのdocs/superpowersへ保存し、resoloopの差分に入れない。

## Review Focus

- 間違ったrepo/base/head: 作成前と作成後のAPI応答を固定の提出先・headと照合する。
- 重複投稿: 投稿前に同じheadまたは同目的のPRを検索し、結果不明時は作成を再送する前に読み戻す。
- 古い検証: candidateとCI merge commitのtreeを照合し、head/treeが変化したら影響する検証を見直す。
- 誤った完了報告: mergedが確認できるまで#105をopenに保ち、投稿済みとマージ済みを別々に記録する。
- 実機検証や安全性の過大な主張: 実機未実施、利用者権限での実行、署名・sandboxではないことを英日両本文で照合する。

上記は実際の投稿対象・状態を読む確認で行う。コードを変更しないため、固定値や文書文言を複製する新規テストは作らない。

## Task 1: 候補と投稿内容を確定する

**Files:** Specと本Plan。ResoLoopのコード変更なし。  
**Consumes:** #101/#33、公開済み提出候補、上流ref、CI記録。  
**Produces:** 正確なbase/head/treeと英日PR本文。  
**テスト:** 新規テスト不要。既存の検証証拠とGitHub APIで確認する。

- [x] #101/#33のcompletedと公開済み成果を確認する。
- [x] head/base・compare（38先行0遅れ、53ファイル）を確認する。
- [x] Windows job成功とCI merge commit/候補のtree一致、Linuxの記録を確認する。
- [x] install→verify→command/doctorと、skills/recipes/docsを読取レビューする。
- [x] 1本のPRを選び、Specに代案と理由、英日本文、既知の制限を記録する。
- [x] 利用者の追加確認不要の指示をIssue #105に記録する。

## Task 2: 提出文書を公開する

**Files:** Create docs/superpowers/specs/2026-11-19-create-reso-world-issue105-upstream-pr-design.md、Create docs/superpowers/plans/2026-11-19-create-reso-world-issue105-upstream-pr.md。  
**Consumes:** Task 1のSpec/Plan。  
**Produces:** create-reso-worldの文書commitと文書専用PR。  
**テスト:** 新規テスト不要。commit tree内のパス・本文の読戻しと差分確認で代える。

- [x] create-reso-worldのmainから文書専用ブランチを作り、2文書をコミットする。
- [x] 文書専用PRをmain宛てに作成する。Refs #105とし、自動closeを指定しない。
- [x] リモートの2文書を読み戻し、保存した内容と一致することを確認する。

## Task 3: 上流PRを作成する

**Files:** 上流PRのタイトル・本文のみ。本体変更なし。  
**Consumes:** Spec内のタイトル/本文、検証済みhead/base。  
**Produces:** orange3134/resoloopのopen PR URL。  
**テスト:** GitHub応答と再取得による照合。新規テスト不要。

- [x] 投稿直前のfork head、上流main、同head/同目的の既存PRを再確認する。
- [x] repository=orange3134/resoloop、base=main、head=usaturn:feat/plugin-system、draft=falseで作成する。利用者への追加の文面確認・実行許可要求は行わない。
- [x] PRを再取得し、URL・repo/base/head・draft・state・本文・差分を照合する。
- [x] PRのCI状態を取得し、進行中と成功を区別して記録する。

## Task 4: 作成結果を記録する

**Files:** Spec・Planの実行記録、Issue #105本文。  
**Consumes:** 上流PR URL、文書PR URL、作成後のAPI照合結果。  
**Produces:** 投稿済みの状態と残作業が再開可能な記録。  
**テスト:** GitHubの本文を読み戻す。新規テスト不要。

- [x] 上流PR URL・head/base・検証根拠・文書PRをSpecと#105に記録する。
- [x] 本Planの投稿完了までの実行結果を更新する。
- [x] #105はopenのまま、上流レビューとマージ確認が残ることを明記する。
- [x] 利用者へ作成したPRのURLと現状を報告する。

## 実行予算

本体の再実装はしない。通常は準備・レビュー・文書公開・PR投稿・読戻しを1回ずつ行う。作業目安は30分以内、外部サービスの待ち時間を除く。レビューは独立した2担当、投稿前照合は対象を絞って行う。結果不明時に作成操作を繰り返さない。

## Contingency

- head/baseが変化: 新しい差分と影響する検証を調べる。既存の公開履歴をforce pushで戻さない。
- 同目的のPRが既に存在: 重複作成せず既存の状況・headを確認する。
- 投稿権限やサービスで作成失敗: 実際のエラーを記録し、作成済みかを検索・読戻しで確認する。既存の許可やアクセス制御を変更して回避しない。
- レビューで具体的な重大不具合: 投稿前に原因と修正範囲を確かめる。既知の軽微な制限を無制限な再設計へ広げない。
- 上流PR作成後の待ち: 投稿は完了として報告し、作者によるレビュー・取り込み待ちを#105に記録する。未マージをcompletedとしない。

## 実行記録（2026-11-19 JST）

- Task 1・2完了。文書専用PR: https://github.com/usaturn/create-reso-world/pull/472 。初回公開commit 7105f701e60438183558a4b7be71424f1d816438 の2文書を読み戻し、内容一致を確認した。
- 初回の上流PR作成はGitHub連携の 403: Resource not accessible by integration で失敗し、その後の再検索で同headのPRが無いことを確認した。利用者が仮想マシンのブラウザーでログイン後、usaturnとして認証済みであることを確認し、作業を再開した。
- Task 3完了。投稿直前にhead/baseの一致と重複PRなしを再確認し、05:00 JSTに https://github.com/orange3134/resoloop/pull/20 を作成した。open、draft=false、merged=false。GitHub APIでURL・repo/base/head・英日本文の一致と差分（38コミット・53ファイル、+7,949/-33）を確認した。maintainer_can_modify=false。
- 上流CI https://github.com/orange3134/resoloop/actions/runs/44386456609 を確認した。05:02 JSTではin_progress。Windows jobのRestore・Buildはsuccess、Testはin_progress、Pack・installed-tool smoke test等はpending。実行中を成功扱いにしていない。
- Task 4は提出結果・文書PR・検証根拠・CI観測時の状態をSpecとIssue #105に記録する範囲で完了。利用者へ上流PRのURLを報告した。
- このPlanの提出作業は完了。Issue #105全体はopenで、上流CIの完了・作者のレビュー対応と実際のマージ確認が残る。#102は開始しない。上流PRを重複作成しない。
