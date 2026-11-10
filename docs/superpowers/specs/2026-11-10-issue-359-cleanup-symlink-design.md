# Issue #359: 定期掃除の導入先から helper を解決する

## 管理・実行許可

- 状態: `draft`。設計承認を得たという記録ではない。
- Issue: https://github.com/usaturn/create-reso-world/issues/359
- 利用者の明示入口: `issue-to-pr`、`#359 --implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max`。
- 通常の設計判断・検証・commit・push・PR・指定ループ内の finalize によるマージまで実行する指示。利用者は「途中で main が進んでいる場合は留意して止めずに進めてください」と指定したが、現行の適用規則は捕捉後の base 移動で停止を要求するため、その安全境界は維持する。
- 対象と文書: `usaturn/create-reso-world`、origin、`refs/heads/main`、捕捉 SHA `1b0df1212e47857e131d6936e0510520e4fb13ef`。親 checkout は編集せず、`fix/issue-359-cleanup-symlink` の worktree で作業する。

## 目的・現状

`install_beforehand.bash` は cleanup-workspace を ~/bin にコピーする。cleanup の helper 探索は `readlink -f` したスクリプト実体が `.devcontainer/` にある場合だけ repository 相対パスを使うため、コピーからの定期実行は全セッションを保持してしまう。

導入先をスクリプト実体への絶対 symlink に変更し、既存コピーも置換する。定期実行が、保存済みセッションだけを helper の `reap-check` → `cleanup --strict-reap` 経由で退役させられるようにする。cleanup 本体は git モード 100755 のため、リンク先の chmod は不要である。

## 確定した所有・除外

裁定: https://github.com/usaturn/create-reso-world/issues/359#issuecomment-6764063174 。#349 の「ボード外の follow-up と所有」にも同じ範囲がある。#359 に native parent はなく、blocked_by は空。#351 の PR #358 は main にマージ済み。

- コード変更は `.devcontainer/install_beforehand.bash` の cleanup 配置と `.devcontainer/test-install-beforehand.bash` だけ。
- 他の Herdr helper の配置は変更しない。
- `.devcontainer/zshrc.txt`、cleanup 本体の helper 探索規則、`.devcontainer/test-cleanup-workspace.bash` の既存ケースは変更しない。
- cwd・HOME・掃除対象データから helper を推測しない。実 PR、実セッション、実 HOME の掃除・再導入はしない。
- #347 と `run-tests.bash` を同時実行しない。実行直前に既知の実行を確認する。
- rebuild・実環境の定期起動は自動実行しない。マージ後の利用者確認として残し、PR は `Refs #359` にする。

## 設計と決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 / 委任・停止条件 |
| --- | --- | --- | --- |
| helper 解決の復旧 | cleanup だけを絶対 symlink にする | zshrc で helper env を設定 | Issue の明示裁定。#347 と所有が分離し、既存の実体解決を再利用できる |
| 既存コピー | symlink 作成時に置換する | コピーを残す / 再コピー | 現行の安全側コピーからも移行可能にする。ディレクトリにリンクを作る誤操作は避け、失敗を既存の return 1 で伝える |
| テスト | 配置関数を抽出し偽 HOME で実行、実 helper をローカル fixture に使う | 本番 postCreate / 実 PR / symlink 有無だけの照合 | 破壊操作を避け、実際の探索・退役と保持まで観測する。既知の気付きにくい不具合の再発防止は S |
| helper 不在 | 現行の保持動作を維持 | 探索先を増やす | 不明なコードの無人実行と未保存データの削除を避ける。不在の負例は既存 cleanup テストで代表させ重複させない |
| 実装方式 | runner 担当で 1 Task を順次実装、SDD の Task / 全体レビュー | self で実装 | `implement_task.py check` は self=false、一次担当は利用者指定の `pi_opencode-go_deepseek4-flash_max`、fallback は空。失敗時に self へ切り替えない |
| PR 修正ループ | 指定 implement と inspect 3 担当 | 既定レビュアー | 利用者指定。inspect は claude-code_opus_default / devin_swe2_max / pi_opencode-go_deepseek4-flash_max。max_cycles=3 は既定適用。fix の self-review / fix-check は既定の self、fallback は空 |

## 受け入れ基準

- **動作環境:** Ubuntu Dev Container、Bash・GNU coreutils・git・uv。リポジトリの絶対パスには空白を含めてもよい。検証は一意の一時 HOME / git repo / TMP_ROOT の中だけで行う。
- **実入力:** 偽 HOME の `bin/cleanup-workspace.bash` に旧コピーを置き、実際の配置関数で置換後、その導入先を直接実行する。実 helper が作成した保存済み review（複数行・日本語を含む本文）と未保存 draft を使い、helper env の明示なしで保存済みだけが退役し、未保存本文と保存先の review は残ること、git worktree 登録も退役分だけ外れることを観測する。再配置・再実行も成立する。
- **防御範囲:** helper が見つからない場合は削除せず理由を報告する（既存 cleanup テスト）。実 HOME・実 PR・既存の /tmp セッションには触れない。postCreate 全体の実行、他 helper の配置変更、壊れたスクリプト symlink 自体の実行成功は保証対象外である。

## 検証・公開

配置と cleanup の既存テストをまず実行し、変更前は 2 本とも成功（baseline.log）。新しい導入経路の動作検証を変更前に失敗させ、変更後に成功させる。静的確認は bash -n、差分・編集範囲・chmod の副作用の確認。README の入口で全 shell テスト、check-layout、スキル・tools の pytest を実行する。実環境の rebuild 後確認は別に残す。

Spec → Plan の Task 1 → 実行証拠を条件単位で対応させ、PR 前に統合担当が探索・保存・退役・保持の順序と証拠を照合する。PR 前に全体レビュー、Gitleaks、base / Issue / 競合を再確認する。base の SHA を無検証で差し替えない。
