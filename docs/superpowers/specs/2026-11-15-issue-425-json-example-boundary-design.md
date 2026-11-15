# Issue #425: JSONC/JSON5 の例と後続結果の境界

## 管理・実行許可

- 状態: `draft`
- 対象: https://github.com/usaturn/create-reso-world/issues/425
- 対象 repository: `usaturn/create-reso-world`
- 利用者の実行指示: `#425 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review pi_opencode-go_deepseek4-flash_max --implement pi_opencode-go_deepseek4-flash_max --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max`（元の改行は省略）。
- issue-to-pr の委任により通常の設計判断、検証、commit、push、PR 作成、指定ループの finalize によるマージまで実行する。内容の承認を得たという意味ではなく、文書は draft のままとする。
- コード・文書とも新しい linked worktree で編集し、base は `origin/refs/heads/main` の `eb9e378bd803a77c75fa01a30d92ccf0b3682f48`。捕捉状態と再照合は SESSION の helper で管理する。
- SESSION: `/workspaces/reso-world/tmp/agents/issue-425.55cedqeq/`

## 意図・現状

説明文中の閉じた JSONC/JSON5 設定例の後ろに正常な最終 JSON があるとき、pi・devin の collect が最終結果を失わないようにする。同時に、古い正常結果の後ろに壊れた最終回答が来たとき、その古い結果を成功として採用してはならない。

現在 `_example_fence` は言語名の `startswith("json")` 判定を使うため、コメントや末尾カンマを許す `jsonc`・`json5` も厳密な JSON の結果 fence と解釈する。そこにある object 候補の decode 失敗は即座に応答全体を拒否する。一方、既存の非 JSON fence・inline code の壊れた例は無条件に無視され、後続結果が無くても先行結果が残る。

Issue の決定済み事項は「結果 fence は json 完全一致」「壊れた例は例の後ろに有効な結果があるときだけ不問」「#416 より先に実装」。例の中の正常 object の扱いは委任されている。

## 目標・対象外

目標は共有 helper の例示境界、docstring、pi/devin runtime 文書を一致させること。変更ファイルは `tools/agent_runner/adapters/json_result.py`、`tools/agent_runner/tests/adapters/test_json_result.py`、`tools/agent_runner/runtimes/{pi,devin}.rst` に限る（本 Spec・Plan を除く）。

対象外: スキャナ全面書換え、他 adapter の接続・選択ポリシー変更、request_prompt 接続、上流へのコード変更・問い合わせ、実 CLI・有料モデル・実 API を使った不具合の再現。指定された設計・Spec・実装・PR レビューの外部担当起動は workflow の実行であり、この再現禁止と区別する。

既存の壊れた wrapper 内部の fragment 救済禁止、裸の壊れた候補、json/言語なし fence 内の壊れた候補の拒否を維持する。既知の不正配列・pseudo object の上流との差分は #436 の別作業であり、今回の保証へ追加しない。

## Approaches・決定記録

### D1: 言語判定と後続必須の確認を組み合わせる

- 選択した案: fence の info の最初の語を大文字小文字を無視して `json` と完全一致で比較する。閉じた fence に明示言語があり、それが `json` でなければ例とする（jsonc/json5 も含む）。言語なし・未閉鎖 fence の既存の扱いは変えない。既存の result fence の優先も維持し、その内側では inline code や非 JSON の入れ子 fence を例として認識しない。result fence 内の壊れた object 候補は、後続結果があっても拒否する。
- 別案: 言語判定だけ変更する。jsonc/json5 を JSON として別途 parse する。スキャナを上流の新実装へ置き換える。
- 理由: 判定だけでは OLD + 壊れた jsonc/json5 が OLD を成功にする。別 parser は不要で、上流全面移植は独立の #436 と競合する。
- 委任/停止条件: Issue の明示決定の実装。意図推測や壊れた結果の救済を要求する変更は採用しない。

### D2: 壊れた例の後ろの有効結果を必須にする

- 選択した案: 閉じた例（inline code と明示非 JSON fence）の中で object 候補の decode が失敗したら、例の終端を越えた位置に有効な結果候補が現れるまで応答を採用しない。例内の別の正常 object や nested fragment ではこの条件を満たさない。複数の壊れた例があれば、最後の壊れた例の終端より後ろの結果が必要。
- `json_object` では後続の正常 object（空 object を含む）が必要で、通常どおり最後の object を返す。正常 array は従来どおり丸ごと消費し、その内側では条件を満たさない。
- `first_json_object` の通常の先頭非空 object 選択は維持する。ただし壊れた例の例外許容には、選択した先頭結果自体が最後の壊れた例の終端より後ろにあることを必要とする（正常 array 内から従来どおり選ぶ場合は array の開始位置で判断する）。先頭候補が例より前なら、後ろに DONE があっても None とし、別の候補への差し替えはしない。OLD + 壊れた jsonc + DONE で OLD を新たに成功としない。adapter の first/last 選択ポリシーを決める #416 の作業は行わない。
- 別案: 壊れた例は位置を問わず無視する。jsonc/json5 だけ後続必須にし、他言語や inline code は無条件で許容する。
- 理由: 古い結果へのフォールバックを防ぎ、既存の例の共通処理で一貫した安全側の判定にする。対象と無関係な parser 書換えを避ける。
- 委任/停止条件: Issue の「例＋後続必須」を共有処理に反映する判断。後続の壊れた裸候補・結果 fence は例の有無にかかわらず拒否する。

### D3: 例内の正常 object は従来どおり候補にする

- 選択した案: 厳密な JSON として読める object は jsonc/json5 の例内でも通常候補として残す。壊れた例の後続必須条件を例内で満たすことはできない。
- 別案: jsonc/json5 または全言語の例を不透明にして、その中の正常 object も一切候補にしない。
- 理由: 既存 helper の「正常な例は候補」という挙動を維持する。不透明化は従来の非 JSON 例にも変更を広げ、今回の不具合を直すのに不要。後続最終 object があれば json_object はそれを選ぶ。
- 明示する限界: 壊れた候補を一つも含まない正常 object のみの例は、後続結果が無くても正常候補になる。本 Issue が委任した選択であり、任意の設定例を意味で判別する機能は作らない。first_json_object は先頭選択を維持するため、例内の正常 object を選び得る（現行 adapter からの呼出なし。#416 は json_object 接続を予定）。
- 委任/停止条件: Issue の「エージェントに任せる事項」。この限界を隠したり、すべての JSONC/JSON5 設定を完全に解釈できると説明しない。

### D4: 上流・所有・実行方式

- 選択した案: 2026-11-15 に上流 `usaturn/agent-workspace` main `13d403e54b296ccafbe23b15575c1d9145958a6e` の json_result.py を read-only で取得。上流も `startswith("json")` と正常例の候補化を維持していた。今回の後続必須条件は下流の利用者決定を優先し、#436 の取込時に再照合する。
- #416 のコメント https://github.com/usaturn/create-reso-world/issues/416#issuecomment-6857439042 は json_result.py と test_json_result.py を #425 の所有とする。最新本文は実装順を #425 → #416 とし、これに従う。#436 は未分割の差分追跡で同ファイルを含むが、該当する open PR・branch・worktree・予約は見つからなかった。#457 の上流確認は #425 の阻害依存ではない。base の非既定要求、明示承認待ち、ボードキーは無い。
- 別案: #416 を先に実装する。上流との差分をすべて先に取り込む。
- 理由: Issue が決めた順序と所有を守り、scanner 全面変更や別 Issue の作業を混ぜない。
- 実装担当: 利用者指定の `pi_opencode-go_deepseek4-flash_max`、fallback 空、self=false。implement_task.py に Task 単位で依頼する SDD 方式。controller は統合判断・レビュー・GitHub 操作を担当する。失敗時に self へ切り替えない。
- 設計レビュー: 利用者指定の `pi_openai-codex_gpt6-sol_xhigh`、fallback 空。Spec レビュー: 利用者指定の `pi_opencode-go_deepseek4-flash_max`、fallback 空。helper の check はすべて成功。明示 Spec レビューが builder check を代替する。
- PR 修正ループ: max_cycles=3 は既定。inspect は利用者指定 `devin_swe2_max,pi_opencode-go_deepseek4-flash_max`、fix implement は利用者指定 `pi_opencode-go_deepseek4-flash_max`。self-review/fix-check は既定 self、全 fallback 空。最後のブランチ全体レビューはループの最初のサイクルで行い、Task レビューは省かない。
- 旧 Spec `docs/superpowers/specs/2026-11-13-issue-418-pi-json-result-design.md` で対象外だった jsonc/json5 の境界を、本 Issue の決定により今回扱う。

## 受け入れ基準

- 動作環境: Dev Container、捕捉した main 以降のローカル parser と pi/devin collect。保存した偽イベントのみで検証し、実 CLI・有料モデル・実 API による再現は行わない。
- 実入力: 非 ASCII の説明と複数行 jsonc コメント付き / json5 末尾カンマ付き設定例、続く厳密な `{"status":"DONE"}`（json fence または裸）。両経路で success と payload 一致を観測する。
- 防御範囲: OLD + 壊れた jsonc/json5 で後続結果が無い場合は response_failed/payload None。例内の後続 object も例終端より前なら救済しない。壊れた json/JSON fence、言語なし fence、裸の壊れた後続候補、wrapper 内の正常 fragment の救済は禁止。未閉鎖 fence・正常例の候補・array/first の既存選択を今回の文書で保証する範囲以上に変更しない。
- テスト: S のガードを共有 helper 側に代表だけ追加し、正常な例＋後続結果を陽性対照に残す。後続無しの拒否は壊れた object 候補を含む例が対象であり、壊れた候補が無い正常 object だけの jsonc/json5 例（OLD が先行する場合を含む）は D3 に従って候補になる。この委任された限界は Plan の一時 probe でも確認する。result fence 内の入れ子例は D1 の優先に従う。adapter ごとの同じ規則の全組合せや文書固定値テストをコミットしない。pi/devin の実経路は SESSION の一時 probe で両方実行する。
- 一致条件: 実装・docstring・pi/devin runtime 文書に、厳密な json 言語判定、壊れた例の後続必須、正常例の候補化と上記限界を反映する。

## レビュー記録

- 設計レビュー（外部 helper、1 回）: `review_dir=/workspaces/reso-world/tmp/agents/issue-425.55cedqeq/2026-11-15-issue-425-json-example-boundary-design.design-review/review-1`、review_id `fad23de98ce04c1ea9ab86b6083310e9`、reviewed spec SHA-256 `ea0bf7d3eecb14f943018b84a2f1deac01e0c017b5b08094a70e59e29f973091`。requested/actual はともに `pi_openai-codex_gpt6-sol_xhigh`、identity は model `gpt-6.1-sol` / provider `openai-codex` / effort `xhigh`。fallback 使用なし、elapsed_seconds=113.28434491099324、exit_code=0、stop_confirmed=true。sound、concerns/questions/incomplete は空のため採否対象なし。
- outside_changes は空。unprotected_changes は既存の消失した `/tmp/pr-review-376-*` 4 件、`/tmp/review-fix-planning.*` 2 件と、並行する #434 の feature/attempt worktree の変化（詳細は review.json）。いずれも本 Issue の対象外で、回収・変更はしない。本 Issue の HEAD・index・tracked/untracked は監査で維持された。

- Spec レビュー初回（外部 helper）: `review_dir=/workspaces/reso-world/tmp/agents/issue-425.55cedqeq/2026-11-15-issue-425-json-example-boundary-design.spec-review/review-1`、review_id `562a6b6cfec84b9f9633db6936f7a44b`、reviewed spec SHA-256 `cfc7e45dbad32596a2a3e4515583e64897591770c8d766efaf5132187ccf0202`。requested/actual はともに `pi_opencode-go_deepseek4-flash_max`、identity は `deepseek-v4.1-flash` / `opencode-go` / `max`。fallback 使用なし、elapsed_seconds=1252.5900289419951、exit_code=0、stop_confirmed=true。outside_changes 空、unprotected_changes は既存消失登録と #434 の feature/attempt worktree（詳細は review.json）。本 Issue の checkout の保護は維持された。
- S1 minor 採用: D3 の委任判断と、壊れた候補がある場合に限る後続必須の関係を受け入れ基準・Plan に明記する。D3 の意味は変更しない。
- S2 important 採用: result fence の優先と、その内側で inline/入れ子 fence を例としない既存の境界を D1 と文書・Plan へ明記する。拒否の保証を維持する明確化であり、対象機能は変えない。反映後に同じ担当で Spec 再レビューを 1 回行う。
- S3 minor 採用: first_json_object は選択した候補自体が最後の壊れた例より後ろにある場合だけ許容する。先頭選択の意味を変えず、OLD + 壊れた jsonc + DONE の新たな誤採用を防ぐ安全側の限定を D2 に反映する。

- Spec 再レビュー（外部 helper、2 回目・上限）: `review_dir=/workspaces/reso-world/tmp/agents/issue-425.55cedqeq/2026-11-15-issue-425-json-example-boundary-design.spec-review/review-2`、review_id `df05d81f931d42d78c6ed3fa10db4e2f`、reviewed spec SHA-256 `8e452765e7e9e8fb68aec504d657e9f6cb462be82993496426d3040624282603`。requested/actual はともに `pi_opencode-go_deepseek4-flash_max`、identity は `deepseek-v4.1-flash` / `opencode-go` / `max`。fallback 使用なし、elapsed_seconds=1133.3505372719956、exit_code=0、stop_confirmed=true。findings/incomplete は空、採否対象なし。outside_changes 空。unprotected_changes は既存消失登録、別の PR #458 の review/loop 領域および #434 feature worktree の変化（review.json に完全パス記録）。本 Issue の checkout は不変。

## 検証・終了

baseline: `uv run --locked pytest tools/agent_runner/tests/adapters/test_json_result.py -q` は終了コード 0（4 passed）。ログは SESSION/baseline.log。

Plan で必須コマンドと S テストを固定し、Red→Green、fake collect、全体 pytest、`.devcontainer/run-tests.bash`、`scripts/check-layout.sh`、diff、Gitleaks を確認する。GitHub Actions は無効のままで CI を追加しない。

マージ後に同じ fake collect 入力をマージ済みツリーでも再確認する項目が Issue に残るため、PR は `Refs #425` とし、マージだけで Issue を close しない。後続の確認・Issue 更新は loop/finalize の権限と観測結果に従い、未実施を成功にしない。
