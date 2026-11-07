# Issue #331 Resonite managed data の latest リンクと環境変数 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 状態: draft
- Spec: `docs/superpowers/specs/2026-11-07-issue-331-resonite-managed-data-latest-design.md`
- 実行許可: `/issue-to-pr #331 --merge`（Spec の「管理」）。内容の承認ではない

**Goal:** コピーのスクリプトが照合に成功した最新の版へ `latest` を相対 symlink で付け替え、コンテナは `RESONITE_MANAGED_DATA_PATH=.../latest` で常にそれを指す。

**Architecture:** `copy-resonite-managed-data.bash` に、照合済みの版の一覧と `sort -V` による最新の判定、一時名の symlink と `mv -T` による付け替え、既存の版を照合し直して付け替える `--relink-latest` を足す。`devcontainer.json` の `containerEnv` に環境変数を足し、README を直す。

**Tech Stack:** bash、GNU coreutils（`sort -V`・`mv -T`・`sha256sum`・`readlink`）、devcontainer.json

## Global Constraints

- 共有フォルダ: `~/.local/share/create-reso-world/resonite-managed-data`。`latest` はその直下だけ
- 環境変数の値: `/home/vscode/.local/share/create-reso-world/resonite-managed-data/latest`
- 版の名前の規則: `^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$`、大文字・小文字によらず `latest` を除く
- 照合済みの版: 直下の symlink でない実ディレクトリで、symlink でない通常のファイルの `SHA256SUMS` を持つもの
- 終了コード: 0 成功（コピーは成功したが `latest` を変えなかった場合を含む）、1 失敗、2 引数の誤り

## 受け入れ基準

- 動作環境: スクリプトは WSL（コンテナの外）の bash・GNU coreutils。テストはこのコンテナで `bash .devcontainer/test-copy-resonite-managed-data.bash`（偽の DLL、`env HOME=<一時>`）。環境変数は rebuild 後のコンテナ
- 実入力: 版の名前は `2026.11.6.1136` の形。比較は `2025.9.9.9` < `2025.11.3.1234`（文字列順と逆）を含む。コピー元のパスは空白・括弧・日本語を含む
- 防御範囲: 対象は共有フォルダの直下の `latest` だけ。照合済みの版のうち最も新しい版のときだけ付け替える。対象外の反例: 照合に失敗した・中断した版（`SHA256SUMS` が無い）、既存より古い版、`latest` が symlink 以外、版の名前が `latest`（どれも `latest` を変えない）

## 実行方式

`superpowers:executing-plans`（inline）。理由: Task は 2 つで、Task 1 は 1 本のスクリプトとそのテストの逐次変更、Task 2 は Task 1 の動作に合わせた設定と文書。子に渡す利点が無い。

## 実行予算

- 全体の能動時間: 150 分（実装・検証 60 分、PR とループ 90 分。ループはサイクルの上限 3 × (レビュー 45 分の期限内) だが、1 サイクル目で終わる見込み）
- 再試行: 同じ失敗の再試行は 1 回まで
- checkpoint: Task の境界、PR の作成時
- 縮小の候補: `--relink-latest` を README の手順に替える（Spec D5 の別案）

## contingency

- `mv -T` が symlink を置き換えられない環境なら、Spec D3 の意味（途中の状態を残さない）を保つ `mv -Tf` に替え、ledger に記録する
- `sort -V` が版の比較を誤る形が見つかったら、利用者の裁定を待つ（意味が変わる）

---

### Task 1: `latest` の付け替えと `--relink-latest`（テストあり、S）

**Files:**
- Modify: `.devcontainer/copy-resonite-managed-data.bash`
- Test: `.devcontainer/test-copy-resonite-managed-data.bash`

**テストの要否:** 要る（S）。付け替えの条件・拒否が壊れても終了コード 0 のまま、古い版・照合していない版の DLL を使う、利用者が置いたものを上書きする損害が気付かれずに残る。拒否のテストには正常例を残す。

- [ ] **Step 1: 失敗するテストを足す**（既存の 6 の後、`PASS` の行の前）

```bash
lnk() { readlink -- "$1/$share/latest" 2>/dev/null || printf '<none>'; }

# 7. 照合に成功した最新の版だけを latest が指す。sort -V で古い版（文字列では新しい）と、SHA256SUMS の無い（中断した）新しい版のフォルダでは変わらない
h="$tmp/h7"; mkdir "$h"
run "$h" '' --source "$src" --version 2025.9.1.1
[ "$rc" -eq 0 ] && [ "$(lnk "$h")" = 2025.9.1.1 ] || fail "first copy did not create latest -> 2025.9.1.1 ($rc, $(lnk "$h")):
$out"
mkdir "$h/$share/2026.1.1.1"
run "$h" '' --source "$src" --version 2025.11.3.1234
[ "$rc" -eq 0 ] && [ "$(lnk "$h")" = 2025.11.3.1234 ] || fail "newer verified copy did not move latest ($rc, $(lnk "$h")):
$out"
run "$h" '' --source "$src" --version 2025.9.9.9
[ "$rc" -eq 0 ] && [ -f "$h/$share/2025.9.9.9/SHA256SUMS" ] || fail "older copy failed ($rc):
$out"
[ "$(lnk "$h")" = 2025.11.3.1234 ] || fail "older copy moved latest to $(lnk "$h")"

# 8. 照合に失敗したコピーでは latest が変わらない
run "$h" "$tmp/bin-corrupt" --source "$src" --version 2027.1.1.1
expect_refused "corrupt copy with latest"
[ "$(lnk "$h")" = 2025.11.3.1234 ] || fail "failed copy moved latest to $(lnk "$h")"

# 9. latest が symlink でなければ、版のフォルダを作らずに止まり、何も変えない
h="$tmp/h9"; mkdir -p "$h/$share/latest"
printf 'user data\n' > "$h/$share/latest/keep"
before="$(snapshot "$h")"
run "$h" '' --source "$src" --version "$version"
expect_refused "latest is a directory"
[ "$(snapshot "$h")" = "$before" ] || fail "latest directory case changed files"

# 10. 版の名前に latest を使えない。何も作らない
h="$tmp/h10"; mkdir "$h"
for v in latest LATEST; do
  run "$h" '' --source "$src" --version "$v"
  expect_refused "version '$v'"
done
[ -z "$(find "$h" -mindepth 1 -print -quit)" ] || fail "version latest created files: $(find "$h" -mindepth 1)"

# 11. --relink-latest は既存の版を照合し直し、通ったときだけ latest を付け替える
h="$tmp/h11"; mkdir "$h"
run "$h" '' --source "$src" --version 2025.11.3.1234
[ "$rc" -eq 0 ] || fail "relink setup copy failed:
$out"
rm -- "$h/$share/latest"
run "$h" '' --relink-latest --version 2025.11.3.1234
[ "$rc" -eq 0 ] && [ "$(lnk "$h")" = 2025.11.3.1234 ] || fail "relink of a verified version failed ($rc, $(lnk "$h")):
$out"
cp -a -- "$h/$share/2025.11.3.1234" "$h/$share/2026.2.1.1"
printf x >> "$h/$share/2026.2.1.1/FrooxEngine.dll"
run "$h" '' --relink-latest --version 2026.2.1.1
[ "$rc" -ne 0 ] || fail "relink of a modified version exited 0:
$out"
[ "$(lnk "$h")" = 2025.11.3.1234 ] || fail "relink of a modified version moved latest to $(lnk "$h")"
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `bash .devcontainer/test-copy-resonite-managed-data.bash`
Expected: `FAIL: first copy did not create latest -> 2025.9.1.1`

- [ ] **Step 3: スクリプトを実装する**

引数: `--relink-latest`（`--version` が要り、`--source` は取らない）を足す。版の規則の検査の後に `[ "${version,,}" != latest ] || die ... 2`。関数を足す:

```bash
latest="$root/latest"
latest_replaceable() { [ -L "$latest" ] || [ ! -e "$latest" ]; }
is_verified() {  # 直下の照合済みの版か
  [[ "$1" =~ ^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$ ]] && [ "${1,,}" != latest ] &&
    [ -d "$root/$1" ] && [ ! -L "$root/$1" ] && [ -f "$root/$1/SHA256SUMS" ] && [ ! -L "$root/$1/SHA256SUMS" ]
}
newest_verified() {
  local p
  { printf '%s\n' "$version"; for p in "$root"/*; do is_verified "${p##*/}" && printf '%s\n' "${p##*/}"; done; } |
    LC_ALL=C sort -V | tail -n 1
}
update_latest() {
  local newest tmp_link
  newest="$(newest_verified)"
  if [ "$newest" != "$version" ]; then
    printf 'latest was not changed: %s is newer than %s (latest -> %s)\n' "$newest" "$version" "$(readlink -- "$latest" || printf '<none>')"
    return 0
  fi
  latest_replaceable || die "$latest is not a symlink, so it was not replaced. ..."
  tmp_link="$root/.latest.$$.$RANDOM"
  ln -s -- "$version" "$tmp_link" || die "cannot create $tmp_link"
  if ! mv -T -- "$tmp_link" "$latest"; then rm -f -- "${tmp_link:?}"; die "cannot replace $latest"; fi
  printf 'latest -> %s\n' "$version"
}
```

コピーでは、版のフォルダを作る前に `latest_replaceable || die`、`SHA256SUMS` を置いて `succeeded=true` にした後に `update_latest`、その後に成功の文。`--relink-latest` では、版のフォルダと `SHA256SUMS` を確かめ、`latest_replaceable` を確かめ、`sha256sum --quiet --strict -c SHA256SUMS` と一覧以外のファイル・通常のファイル以外が無いことを確かめてから `update_latest`。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `bash .devcontainer/test-copy-resonite-managed-data.bash`
Expected: `PASS: ...`、終了コード 0。`uv tool run --from shellcheck-py shellcheck .devcontainer/copy-resonite-managed-data.bash .devcontainer/test-copy-resonite-managed-data.bash` が終了コード 0

- [ ] **Step 5: Commit**

### Task 2: 環境変数と README（テストなし）

**Files:**
- Modify: `.devcontainer/devcontainer.json`（`containerEnv`）
- Modify: `.devcontainer/README.md`（ProtoFlux の節の概要、「Resonite の managed data（ProtoFlux、任意）」の節）

**テストの要否:** 要らない。設定の値と文書は F。代わりに `bash scripts/check-layout.sh`（devcontainer.json の解析と mount の照合）、`bash .devcontainer/run-tests.bash`、`git diff` で確かめる。

- [ ] **Step 1:** `containerEnv` に `"RESONITE_MANAGED_DATA_PATH": "/home/vscode/.local/share/create-reso-world/resonite-managed-data/latest"` とコメントを足す
- [ ] **Step 2:** README の節を Spec D8 のとおり直す（`initialize.bash` の説明、状態の表、手順 2 の `latest`、既にコピーした版の `--relink-latest`、手順 4 の `lib` を `latest` に、手順 5 を環境変数と版の固定（`--library-path`）に、手順 6 の `latest` が指す版を消さないこと）
- [ ] **Step 3:** 検証を実行し、Commit

## 完了

（実行の結果を書く）
