# Superpowers の Spec・Plan

この下には、Superpowers のスキル（brainstorming、writing-plans など）で作った設計（`specs/`）と実装計画（`plans/`）を置く。運用の現行設計は `specs/2026-10-04-create-reso-world-pr16-document-lifecycle-root-cause-review-fixes-design.md` にある。

## 保存先

- 対象のリポジトリにかかわらず、Spec・Plan はこのリポジトリ（`usaturn/create-reso-world`）の `docs/superpowers/` にコミットする。ResoLoop や無関係なリポジトリの作業でも、そちらには置かない
- Spec は `specs/YYYY-MM-DD-<topic>-design.md`、Plan は `plans/YYYY-MM-DD-<topic>.md` とする。Issue・PR に関する文書の `<topic>` には、リポジトリを表す語と番号を含める（例: `usaturn-resoloop-pr9-list-shrink-review-fixes`）
- 同じテーマのレビュー修正は、新しいファイルを作らずに既存の文書を更新する。過去の版は Git の履歴で追う
- 更新する前に、対象リポジトリ・Issue/PR・テーマ・正本のパスで現行の Spec/Plan を探す。ファイル名の basename や日付だけでは照合しない。複数の候補があって後継の指定や明示パスで確定できないときは、進めずに確認する。回ごとの新規文書（roundN）は既定で作らない。本当に新しい文書は、独立承認されたアーキテクチャ再設計など明示的な理由があるときだけで、その理由を文書の冒頭に記録する

## 状態

文書の冒頭に、文書管理リポジトリ、対象リポジトリと Issue・PR、検証したコードの HEAD、状態、関連する文書を書く。

| 状態 | 意味 |
| --- | --- |
| draft | 明示承認をまだ得ていない |
| approved | 指定された版の内容について明示承認を得た |
| completed | 作業が完了した。結果と検証の根拠を併記する |
| superseded | 後継の文書に置き換えた |
| cancelled | 取りやめた。理由を残す |

コミットしただけでは `approved` にしない。承認は、確認したコミットの SHA に結び付けて記録する。完了・置換・取りやめの後も、文書は削除しない。

承認後の状態変更・記録追記だけの変更（metadata-only）は再承認を求めず、承認済みの版をそのまま残す。現行・復元版の SHA は記録追記後の版に更新できる。実質的な設計・計画の変更は再承認を必要とする（記録した実行許可がその変更を明示的に含む場合を除く）。例外で進める場合は許可された変更内容を記録し、一般的な継続指示だけで変更の承認を推測しない。実行の許可、完了の証拠、公開の状態は、内容の承認と別の事実として記録する。

明示・検証済み `CODE_ROOT` を使う任意リポジトリの PR レビューと、その PR の承認済み実装修正（approved PR review-fix implementation）の既存経路は維持する。一般的な外部実装・Issue 実装と remote なしの PR 連携は非対応であり、文書保存や計画の完了だけでは実行可能にならない。実行許可が欠ける場合も handoff は blocked / not ready とし、欠けている指示・規則を記録する。

## 確認用コピー

ユーザに確認を依頼する前に、コミット済みの版を親 checkout の `tmp/superpowers-review/` にコピーする。

```bash
bash scripts/superpowers-review-copy.sh --doc-root "$DOC_ROOT" --parent-root "$PARENT_ROOT" \
  --path docs/superpowers/specs/2026-10-03-example-design.md --name resoloop-pr9-list-shrink-spec.md
```

- コピーは閲覧のためのもので、正本ではない。引き継ぎや復元には、コミット済みの正本を使う
- コピーは既存の entry を決して差し替えない。同じ名前で再コピーすると、内容が同一なら `unchanged` と表示して書き換えず、異なれば別名を案内して拒否する
- 正本が変わったら `...-r2-spec.md`・`...-r2-plan.md` のような別名で新しいコピーを公開する。旧コピーとユーザの注記は残る。ユーザが編集したコピーは差し替えず、差分を正本へ反映してからコピーし直す
- コピーの作成は共通 context 検証（operation `review-copy`）を通る。親 checkout（`PARENT_ROOT`）と文書 checkout（`DOC_ROOT`）だけを照合し、コード側の cwd（`CODE_ROOT`）は親やコピー元に使わない

## 公開

- このリポジトリ自身の変更に伴う文書は、その作業の PR に含める
- 他のリポジトリの変更に伴う文書は、このリポジトリの文書用ブランチから、テーマごとに 1 つの文書専用 PR で公開する。コード側の PR とは相互に参照する
- push・PR 作成・マージは、ユーザまたは使っているワークフローの明示指示があるときだけ行う。ローカルのコミットだけのときは「公開未実施」と報告する

## 履歴と現行仕様

Spec・Plan は判断と実装の経緯の記録である。完了した Plan の手順を、今の環境でそのまま再実行してよいという意味ではない。利用者が参照する現在の手順は、各リポジトリの README などの通常のドキュメントに書く。
