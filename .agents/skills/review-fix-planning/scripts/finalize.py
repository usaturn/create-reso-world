"""追加修正が無いPRを、検証・状況投稿・マージ・関連Issue確認まで最終化する。

形式だけの検証記録を実検証の代わりにしない。司令塔が実際のコマンド、HEAD、検証したツリーが含むbaseを記録する。
状況を投稿する前とマージの直前に、PRのbaseブランチの今の先端がそのbaseと同じことを確かめ、違えばそこで止まる。
終了コード0だけがno_fix_needed。それ以外はstoppedと具体的な未完了箇所を返す。
結果のmergedは、最後に観測したPRのマージ状態（true・false）。確かめていなければnull（未マージとは言わない）。
マージしてよいPRはMERGEABLE_REPOSITORIESだけで、CIを確かめるかどうかはCI_REQUIREDで決める。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("planning_final_post", SCRIPT_DIR / "upsert_pr_comment.py")
assert SPEC is not None and SPEC.loader is not None
poster: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(poster)

# CIを確かめるか。GitHub Actionsを止めているリポジトリは確かめない。
# 表に無いリポジトリは確かめる（知らない対象を免除しない）。
CI_REQUIRED: Mapping[str, bool] = {
    "usaturn/create-reso-world": False,
    "usaturn/resoloop-meshy": False,
    "usaturn/resoloop": True,
}
# マージしてよい範囲（SKILL.mdの「マージしてよい範囲」）。マージは取り消せないので、このhelperでも守る。
# 範囲外は、GitHubに問い合わせる前にpermissionで止める。
MERGEABLE_REPOSITORIES = frozenset({"usaturn/create-reso-world", "usaturn/resoloop"})
# --spec-commit は、create-reso-worldのPRの結論2で、検証したHEADの上にSpecのcommitを載せたときに使う。
# 記録付きの投稿はPRのheadが検証したHEADのうちでないとできないので、記録を先に投稿してからSpecのcommitをpushする。
# このときは投稿せず、投稿済みの記録が渡した記録と同じことと、GitHubの比較でSpecのcommitが検証したHEADの上の
# Spec 1ファイル（SPEC_DIRECTORYの直下のMarkdownの追加か変更）だけの変更であることを確かめて、そのcommitをマージする。
SPEC_REPOSITORY = "usaturn/create-reso-world"
SPEC_DIRECTORY = "docs/superpowers/specs/"
SPEC_FILE_STATUSES = frozenset({"added", "modified"})
FULL_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")

FIELDS = (
    "url",
    "number",
    "headRefOid",
    "baseRefName",
    "state",
    "isDraft",
    "mergeable",
    "mergedAt",
    "statusCheckRollup",
    "closingIssuesReferences",
)
GREEN_CONCLUSIONS = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"})
PENDING_STATUSES = frozenset({"PENDING", "EXPECTED"})


class Stop(Exception):
    """秘密を含まない、具体的な障害。

    wait_for は、待てば解消する状態（ci: 公開CIの実行中・待機中、mergeable: GitHubがマージ可否を計算中、
    head: pushしたSpecのcommitがまだPRのheadに反映されていない）。司令塔が待ってから同じ記録で再実行する。
    base_moved は、検証した後にbaseが進んだ停止（ref: baseブランチの名前、verified: 検証の記録のbase、
    current: 今の先端）。待っても解消しないので、司令塔がcurrentで検証し直し、検証の記録を作り直してから再実行する。
    """

    def __init__(
        self, reason: str, *, wait_for: str | None = None, base_moved: dict[str, str] | None = None
    ) -> None:
        super().__init__(reason)
        self.wait_for = wait_for
        self.base_moved = base_moved


def check_evidence(checks: Mapping[str, Any], head: str) -> None:
    base = checks.get("base")
    if not isinstance(base, str) or FULL_SHA.fullmatch(base) is None:
        raise Stop("environment: 検証の記録に、検証したツリーが含む base の commit（完全な SHA）が無い")
    commands = checks.get("commands")
    if (
        set(checks) != {"head", "base", "commands"}
        or checks.get("head") != head
        or not isinstance(commands, list)
        or not commands
    ):
        raise Stop("environment: 同じHEADの正式検証の実行記録が無い")
    for command in cast(list[Any], commands):
        if not isinstance(command, dict):
            raise Stop("environment: 検証コマンドの実行記録が不正")
        command = cast(dict[str, Any], command)
        if set(command) != {"argv", "exit_code"}:
            raise Stop("environment: 検証コマンドの実行記録が不正")
        argv = command["argv"]
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(arg, str) or not arg.strip() or "\x00" in arg for arg in cast(list[Any], argv))
        ):
            raise Stop("environment: 検証コマンドの引数が不正")
        if type(command["exit_code"]) is not int or command["exit_code"] != 0:
            raise Stop("environment: 正式検証が成功していない")


def is_one_of(value: object, allowed: frozenset[str]) -> bool:
    """JSONの値が、許す文字列のどれかか。リストなど文字列でない値はハッシュできないので、先に除く。"""
    return isinstance(value, str) and value in allowed


def check_ci(view: Mapping[str, Any], repo: str) -> None:
    # CI免除は CI_REQUIRED で false の登録先だけ。表に無いリポジトリは CI を必須とする。
    if not CI_REQUIRED.get(repo, True):
        return
    checks = view.get("statusCheckRollup")
    if not isinstance(checks, list) or not checks:
        raise Stop("external: 公開PRのCI結果が無い")
    passed = pending = False
    for check in cast(list[Any], checks):
        if not isinstance(check, dict):
            raise Stop("external: CI結果の形式が不明")
        check = cast(dict[str, Any], check)
        kind = check.get("__typename")
        if kind == "CheckRun" and check.get("status") != "COMPLETED":
            pending = True
        elif kind == "CheckRun":
            if not is_one_of(check.get("conclusion"), GREEN_CONCLUSIONS):
                raise Stop("external: 公開PRのCIに失敗した検査がある")
            passed |= check.get("conclusion") == "SUCCESS"
        elif kind == "StatusContext" and is_one_of(check.get("state"), PENDING_STATUSES):
            pending = True
        elif kind == "StatusContext" and check.get("state") == "SUCCESS":
            passed = True
        else:
            raise Stop("external: 公開PRのCI状態が成功ではない")
    # 失敗はすぐ止める。未完了は、全件に失敗が無いときだけ待てば進む停止にする。
    if pending:
        raise Stop("external: 公開PRのCIが完了していない（実行中・待機中）", wait_for="ci")
    if not passed:
        raise Stop("external: 公開PRのCIに成功した検査が無い")


def check_merge_scope(repo: str) -> None:
    """マージしてよい範囲の外のPRは、GitHubに問い合わせる前に止める。"""
    if repo not in MERGEABLE_REPOSITORIES:
        raise Stop("permission: マージしてよい範囲（usaturn/create-reso-world・usaturn/resoloop）の外の PR")


def check_spec_commit(spec_commit: str, reviewed_head: str, repo: str) -> None:
    """--spec-commit を受け付ける条件。GitHubに問い合わせる前に確かめる。"""
    if not isinstance(spec_commit, str) or FULL_SHA.fullmatch(spec_commit) is None:
        raise Stop("environment: --spec-commit が完全なcommit SHA（小文字の16進数40桁か64桁）ではない")
    if spec_commit == reviewed_head:
        raise Stop("environment: --spec-commit が検証したHEADと同じで、Specのcommitではない")
    if repo != SPEC_REPOSITORY:
        raise Stop(f"permission: --spec-commit は {SPEC_REPOSITORY} のPRだけで使える")


def as_object(value: object) -> dict[str, Any] | None:
    return cast(dict[str, Any], value) if isinstance(value, dict) else None


def as_list(value: object) -> list[Any] | None:
    return cast(list[Any], value) if isinstance(value, list) else None


def is_count(value: object, expected: int) -> bool:
    """JSONの数。True == 1 のように、真偽値を数として通さない。"""
    return type(value) is int and value == expected


def is_spec_only_child(comparison: object, base: str, spec_commit: str) -> bool:
    """比較の応答が、baseの直接の子1 commitで、Spec 1ファイルだけの追加・変更かを返す。

    応答の形が想定と違うときも偽（成功と見なさない）。
    """
    body = as_object(comparison)
    if body is None:
        return False
    commits, files = as_list(body.get("commits")), as_list(body.get("files"))
    if (
        body.get("status") != "ahead"
        or not is_count(body.get("ahead_by"), 1)
        or not is_count(body.get("behind_by"), 0)
        or commits is None
        or len(commits) != 1
        or files is None
        or len(files) != 1
    ):
        return False
    commit, changed = as_object(commits[0]), as_object(files[0])
    if commit is None or changed is None or commit.get("sha") != spec_commit:
        return False
    parents = as_list(commit.get("parents"))
    if parents is None or [(as_object(parent) or {}).get("sha") for parent in parents] != [base]:
        return False
    name = changed.get("filename")
    if not isinstance(name, str) or not name.startswith(SPEC_DIRECTORY):
        return False
    leaf = name.removeprefix(SPEC_DIRECTORY)
    return is_one_of(changed.get("status"), SPEC_FILE_STATUSES) and "/" not in leaf and leaf.endswith(".md")


def check_spec_change(runner: Any, repo: str, reviewed_head: str, spec_commit: str) -> None:
    """GitHubの比較で、Specのcommitが検証したHEADの上のSpec 1ファイルだけの変更と確かめる。"""
    comparison = poster.load_json(
        poster.run_gh(["api", f"repos/{repo}/compare/{reviewed_head}...{spec_commit}"], runner=runner),
        "gh api compare",
    )
    if not is_spec_only_child(comparison, reviewed_head, spec_commit):
        raise Stop("environment: Spec の commit が検証した HEAD の上の Spec 1 ファイルだけの変更ではない")


def check_base(runner: Any, repo: str, view: Mapping[str, Any], verified: str) -> None:
    """PRのbaseブランチの今の先端が、検証の記録のbase（verified）と同じことを確かめる。

    先端はbaseブランチから読む。PRのbaseRefOidは、baseブランチの先端に追従しない。
    応答の名前も照合し、改名したブランチのリダイレクトや、URLの中で別の意味になる名前の応答を成功と見なさない。
    """
    ref = view.get("baseRefName")
    if not isinstance(ref, str) or not ref:
        raise Stop("external: PRのbaseブランチの先端を確認できない")
    branch = as_object(
        poster.load_json(poster.run_gh(["api", f"repos/{repo}/branches/{ref}"], runner=runner), "gh api branch")
    )
    commit = None if branch is None else as_object(branch.get("commit"))
    current = None if commit is None else commit.get("sha")
    if (
        branch is None
        or branch.get("name") != ref
        or not isinstance(current, str)
        or FULL_SHA.fullmatch(current) is None
    ):
        raise Stop("external: PRのbaseブランチの先端を確認できない")
    if current != verified:
        # ブランチの名前は停止理由に入れない（判断の記録に写されうる）。base_moved.ref で返す
        raise Stop(
            f"external: 検証した後にPRのbaseブランチが進んだ（検証したbase {verified[:12]}、今の先端 {current[:12]}）",
            base_moved={"ref": ref, "verified": verified, "current": current},
        )


def observe_merged(view: Mapping[str, Any], known: bool | None) -> bool | None:
    """PRの応答から、マージ済みかを返す。状態を読めない応答はNone（未確認）。

    マージは取り消せないので、一度観測したマージ済み（known）は後の応答で戻さない。
    """
    state = view.get("state")
    if known is True or state == "MERGED":
        return True
    if state in ("OPEN", "CLOSED"):
        return False
    return None


def check_view(
    view: Mapping[str, Any], head: str, *, allow_merged: bool = False, pushed_from: str | None = None
) -> None:
    """pushed_from は、headにpushしたcommitの親（--spec-commitの検証したHEAD）。

    pushの直後は、GitHubがまだpushの前のheadを返すことがある。openのままそのheadなら、待てば進む停止にする。
    """
    if view.get("headRefOid") != head:
        if pushed_from is not None and view.get("headRefOid") == pushed_from and view.get("state") == "OPEN":
            raise Stop("external: PRのheadがまだ検証したHEADのまま（Specのcommitのpushが反映される前）", wait_for="head")
        if view.get("state") == "MERGED":
            # 再実行しても完了しない。何がマージされたかを人が確かめる
            raise Stop("external: PRが検証済みHEADと別のHEADでマージされた")
        raise Stop("external: PRのHEADが検証済みHEADから変わった")
    if allow_merged and view.get("state") == "MERGED" and view.get("mergedAt"):
        return
    if view.get("state") != "OPEN":
        raise Stop("external: PRがOPENではない")
    if view.get("isDraft") is not False:
        raise Stop("external: PRがdraftになっている")
    if view.get("mergeable") == "UNKNOWN":
        # GitHubはbaseが動くとmergeableを非同期に計算し直し、計算前の問い合わせにはUNKNOWNを返す。
        raise Stop("external: GitHubがマージ可否を計算中（mergeable=UNKNOWN）", wait_for="mergeable")
    if view.get("mergeable") != "MERGEABLE":
        raise Stop("external: PRがマージ可能ではない")


def closing_issues(view: Mapping[str, Any], repo: str) -> list[int]:
    references = view.get("closingIssuesReferences")
    if not isinstance(references, list):
        raise Stop("external: 関連Issueの閉鎖指定を取得できない")
    numbers: list[int] = []
    for issue in cast(list[Any], references):
        if not isinstance(issue, dict):
            raise Stop("external: 関連Issueの番号を確認できない")
        issue = cast(dict[str, Any], issue)
        if type(number := issue.get("number")) is not int or number < 1:
            raise Stop("external: 関連Issueの番号を確認できない")
        if issue.get("url") != f"https://github.com/{repo}/issues/{number}":
            raise Stop("external: 関連Issueが別repositoryか、URLと番号が不一致")
        if number not in numbers:
            numbers.append(number)
    return numbers


def round_target(checked: Mapping[str, Any], comments: Sequence[Mapping[str, Any]], login: str) -> int | None:
    """このサイクルの自分のコメントIDを返す。過去の記録と照合できなければ記録の問題として止める。

    問題の文にはマーカーや '<!--' が入りうる。stopped の記録に写せるよう、判断IDだけを添える。
    """
    try:
        return cast(int | None, poster._round_target(checked, comments, login))
    except poster.CommentError as error:
        ids = sorted({match.group(0) for match in poster.records.DECISION_ID.finditer(str(error))})
        detail = f"（判断: {', '.join(ids)}）" if ids else ""
        raise Stop(f"environment: PR上の過去の記録と照合できない{detail}") from None


def posted_record(comments: Sequence[Mapping[str, Any]], comment_id: int | None) -> dict[str, Any] | None:
    """このサイクルの自分の状況コメントに載っている記録。無い・取り出せないならNone。"""
    for comment in comments:
        if comment["id"] == comment_id:
            try:
                return cast(dict[str, Any], poster.records.extract_record(comment["body"]))
            except poster.records.RecordError:
                return None
    return None


def view_issue(runner: Any, repo: str, number: int) -> dict[str, Any]:
    value = poster.load_json(
        poster.run_gh(["issue", "view", str(number), "--repo", repo, "--json", "url,number,state"], runner=runner),
        "issue view",
    )
    if not isinstance(value, dict):
        raise Stop("external: 関連Issueの取得形式が不正")
    issue = cast(dict[str, Any], value)
    if issue.get("url") != f"https://github.com/{repo}/issues/{number}" or issue.get("number") != number:
        raise Stop("external: 関連Issueの対象が一致しない")
    return issue


def finalize(
    record: Mapping[str, Any],
    markdown: str,
    checks: Mapping[str, Any],
    *,
    runner: Any = None,
    spec_commit: str | None = None,
) -> dict[str, Any]:
    active = poster.GhRunner() if runner is None else runner
    # GitHubに問い合わせる前は、PRの状態を見ていないのでNone
    merged: bool | None = None
    step = "input"
    result: dict[str, Any] = {"outcome": "stopped", "merged": None, "issues": []}
    try:
        checked = poster.records.validate_record(dict(record))
        try:
            checked, _ = poster._checked_record(checked, checked["planner"]["model"], markdown)
        except poster.CommentError:
            raise Stop("environment: 状況本文が投稿の条件を満たさない（空・マーカー・上限超過など）") from None
        if checked["outcome"] != "no_fix_needed":
            raise Stop("permission: Fix/Hold/Unverifiedの無いno_fix_needed記録だけを最終化できる")
        head = checked["reviewed_head"]
        repo, pr = checked["pr"]["repository"], checked["pr"]["number"]
        check_evidence(checks, head)
        check_merge_scope(repo)
        if spec_commit is not None:
            check_spec_commit(spec_commit, head, repo)
            result["spec_commit"] = spec_commit
        # マージするcommit。Specのcommitがあるときは、それがPRのheadになっている。
        merge_head = head if spec_commit is None else spec_commit
        step = "PR state/HEAD"
        view = poster.view_pr(pr, repo, active, FIELDS)
        # 合否の判定より先に、観測した状態を残す。headが違って止まっても、マージ済みの事実は失わない
        merged = observe_merged(view, merged)
        check_view(view, merge_head, allow_merged=True, pushed_from=None if spec_commit is None else head)
        closing_issues(view, repo)
        if spec_commit is not None:
            step = "Spec commit comparison"
            check_spec_change(active, repo, head, spec_commit)
        step = "authenticated login"
        login = poster.authenticated_login(active)
        step = "round history"
        comments = poster.list_comments(repo, pr, active)
        existing = round_target(checked, comments, login)
        if view["state"] == "MERGED":
            # マージ後は投稿helperが拒否し、記録を足せない。PR上の記録と食い違う結果を返さない。
            if posted_record(comments, existing) != checked:
                raise Stop("external: PR上の記録が渡したno_fix_needed記録と一致しない（無いを含む）ままマージされた")
        else:
            if spec_commit is not None and posted_record(comments, existing) != checked:
                # Specのcommitを載せたPRのheadは検証したHEADと違うので、ここでは記録を投稿できない。
                raise Stop(
                    "environment: PR上のこのサイクルの記録が渡したno_fix_needed記録と一致しない（無いを含む）。"
                    "Specのcommitをpushする前に、同じ記録を投稿する"
                )
            check_ci(view, repo)
            if spec_commit is None:
                # 古いbaseの検証の状況を投稿しない
                step = "base before posting"
                check_base(active, repo, view, checks["base"])
                step = "status posting"
                result["comment"] = poster.upsert(
                    pr, repo, checked["planner"]["model"], markdown, runner=active, record=checked
                )
            step = "pre-merge HEAD/CI"
            view = poster.view_pr(pr, repo, active, FIELDS)
            merged = observe_merged(view, merged)
            check_view(view, merge_head, allow_merged=True)
            if view["state"] != "MERGED":
                check_ci(view, repo)
                # 最後の確認。ここからGitHubがマージを処理するまでの間の前進は止められない
                # （GitHubのマージはbaseを固定できない。references/execution.md の 3.5 節）
                step = "pre-merge base"
                check_base(active, repo, view, checks["base"])
                step = "merge"
                # 依頼の後は、GitHubが処理したかを読み直して確かめるまで未確認（失敗の応答でも処理済みでありうる）
                merged = None
                # loopの最終化と同じmerge commit。squashは祖先関係によるマージ済みの判定で未取り込みに見える。
                poster.run_gh(
                    ["pr", "merge", str(pr), "--repo", repo, "--merge", "--match-head-commit", merge_head],
                    runner=active,
                )
        step = "post-merge confirmation"
        view = poster.view_pr(pr, repo, active, FIELDS)
        merged = observe_merged(view, merged)
        if view.get("state") != "MERGED" or not view.get("mergedAt") or view.get("headRefOid") != merge_head:
            raise Stop("external: マージ済み状態と検証済みHEADの一致を確認できない")
        for number in closing_issues(view, repo):
            step = f"Issue #{number} state"
            issue = view_issue(active, repo, number)
            if issue.get("state") == "OPEN":
                step = f"Issue #{number} close"
                poster.run_gh(["issue", "close", str(number), "--repo", repo], runner=active)
                issue = view_issue(active, repo, number)
            if issue.get("state") != "CLOSED":
                raise Stop("external: 関連IssueがCLOSEDになったことを確認できない")
            result["issues"].append(number)
        result["outcome"] = "no_fix_needed"
    except Stop as error:
        result["stop_reason"] = str(error)
        if error.wait_for is not None:
            result["wait_for"] = error.wait_for
        if error.base_moved is not None:
            result["base_moved"] = error.base_moved
    except poster.records.RecordError:
        result["stop_reason"] = "environment: 状況記録が不正で最終化を開始できない"
    except poster.CommentError:
        result["stop_reason"] = f"external: {step} の取得・検査・書込みに失敗した"
    except OSError, ValueError:
        result["stop_reason"] = f"environment: {step} の実行に必要な入力・コマンドを利用できない"
    result["merged"] = merged
    return result


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ValueError("invalid JSON") from None
    if not isinstance(value, dict):
        raise ValueError("JSON must be an object")
    return cast(dict[str, Any], value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-file", required=True, type=Path)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--checks-file", required=True, type=Path)
    parser.add_argument("--result-file", required=True, type=Path)
    parser.add_argument(
        "--spec-commit",
        default=None,
        help="create-reso-worldのPRで、検証したHEADの上に載せたSpecのcommit（完全なSHA）。記録は先に投稿しておく",
    )
    args = parser.parse_args(argv)
    result: dict[str, Any] = {"outcome": "stopped", "merged": None, "issues": []}
    temporary: Path | None = None
    stage = "入力読取り"
    try:
        record = read_object(args.record_file)
        markdown = args.body_file.read_text(encoding="utf-8")
        checks = read_object(args.checks_file)
        stage = "結果保存先の準備"
        destination = args.result_file
        if destination.is_symlink() or destination.exists() and not destination.is_file():
            raise ValueError("result must be a regular file, not a symlink")
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=".finalize-result-",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            result = finalize(record, markdown, checks, spec_commit=args.spec_commit)
            stage = "最終化結果の保存"
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        temporary = None
    except OSError, ValueError:
        result.update(outcome="stopped", stop_reason=f"environment: {stage}を完了できない")
        print(json.dumps(result, ensure_ascii=False))
        print("finalize: environment: input/result file unavailable or invalid", file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                print(f"finalize: temporary result remains at {temporary}", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["outcome"] == "no_fix_needed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
