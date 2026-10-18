# review-verify の評価記録

評価 controller 用。通常のレビュー確認では読まない。自然言語の期待を pytest の文字列照合にしない。

## 行動評価

同一 pressure scenario は `evals.json` の id=1。baseline はスキルを読まない新規 agent による判断シミュレーション（実測87秒）。採否・push判断を引き受け、専用 verdict と v2/要約の保存形式が抜けた。入力不足を補わないこと、依存不足を反証にしないこと、Markdown/JSON 不一致の照合はできていた。

| 確認項目 | スキル無しの観測 | スキルありの観測 |
| --- | --- | --- |
| 採否・push判断の境界 | 採否保留・push保留を判断した | 採否・重大度・push判断を呼び出し側に委ねた |
| 専用 verdict と成果物形式 | 専用 verdict/v2保存形式が無い | unverified/missing_checks、v2と要約の形式を示し、未生成を明示 |
| 不完全入力・依存不足・候補不一致 | 補完せず、未実行とし、不一致を照合する | fix_sections欠落で起動せず、依存不足をunverified、Markdown手動回収を示した |

スキルありは controller が新規 agent に同じ scenario を渡した判断シミュレーション。計測区間は2026-10-18T15:54:47Z〜15:55:52Zの65秒（参照・判断11秒、報告54秒、待機0秒）。初回読取の数秒は計測外で総時間不明。実環境での検証・Git操作・修正・外部起動は未実施。JSONや要約を実際に保存したとは主張せず、架空のSHA/位置/出典を補っていない。baseline87秒と区間の違う65秒を速度改善とは扱わない。

評価担当が実際に読んだ入口SHA256は `cd28e93b0b1b46c172e21e364cc7bd7c6752410e752ec28b9c2199fa42eeca62`。評価後の入口変更は評価資料リンクに「評価 controller 用（通常の確認では読まない）」を付けた説明だけで、確認手順は同じ。cycleの短縮HEAD比較と既存fetch手順への参照、fix_checkの成果物とエラー説明も自己レビューで明確化した。評価結果は単一scenarioの観測であり、実際のレビュー全工程・複数回の再現性を保証しない。fixtureの実行確認とは区別する。

## 実行 fixture

fake repository `example/review-demo`、fake PR #900。ネットワーク・資格情報・実モデルを使わない。コミットした base/head を作り、元 checkout に未コミット修正を置いたうえで、head の隔離 worktree だけを実行した。helper の from-markdown → validate → check-pair → v2 validate → stats を実行し、JSON と可読要約を保存した。

初回実測: head `ecc83e48199f4519fbf5efc3d3c2dfbde14c9fe5`。実行確認を含む生成時間0.492秒。confirmed 1、not_reproduced 1、unverified 1。reference link は1と誤算、inline link は0、uppercase Xは1。依存不足の実コマンドは非0。worktree は remove 成功。保存先は session の `cycle-fixture.hknipgvq/reviews/example/review-demo/#900-fixture/verified/`。全コマンド・終了値・stdout/stderr は同 fixture の `execution.json` に保存した。絶対 session パスは Task 1 の報告に記録する。

文書掲載の Python block を抽出して再実行した結果も exit 0。head `3ac428ab90b1042ec5a08b9f80c08135e8fa555c`、生成0.448秒、同じ verdict 件数。出力は session の `cycle-fixture.kmfkzk35/`。

この fixture は resolver の GitHub 照会や dispatcher を模倣しない。候補整合・コミット済挙動・v2成果物を検証する。dispatcher の動作検証は Task 2、skillあり行動評価は上表の別検証である。

## 再実行

`TOOL_ROOT` はスキルと既存 helper を持つ checkout、`PARENT_ROOT` は親 checkout、`SESSION_ROOT` は agent_tmp.py が作成した session の絶対パスにする。次の Python block を SESSION_ROOT 内の `cycle-fixture.py` に保存し、root の uv 環境で実行する。毎回一意の fixture 領域を作る。出力の JSON/要約と execution.json を読み、helper の終了コードを確認する。fixture を残す場合は完全パスを報告する。

```bash
uv run --project "$PARENT_ROOT" --locked python "$SESSION_ROOT/cycle-fixture.py" "$TOOL_ROOT" "$SESSION_ROOT"
```

```python
"""Execute a committed fake cycle; all outputs stay in the supplied session root."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

tool, session = map(lambda p: Path(p).resolve(), sys.argv[1:3])
area = Path(tempfile.mkdtemp(prefix='cycle-fixture.', dir=session))
repo = area / 'repository'
repo.mkdir()
review = area / 'reviews/example/review-demo/#900-fixture'
(review / 'findings').mkdir(parents=True)
(review / 'verified').mkdir()
started = time.monotonic()
now = lambda: datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
started_at = now()
# Git's environment selectors override -C; never inherit host repositories/config.
env = {name: value for name, value in os.environ.items()
       if not name.startswith('GIT_') and name not in {'BASH_ENV', 'ENV'}}
home = area / 'home'
home.mkdir()
env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / 'config'),
           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
           GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
           GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
           PYTHONDONTWRITEBYTECODE='1')
transcript = []
def run(args, *, cwd=repo, ok=True):
    result = subprocess.run(list(map(str, args)), cwd=cwd, env=env, text=True, capture_output=True)
    transcript.append({'command': list(map(str, args)), 'exit_code': result.returncode,
                       'stdout': result.stdout, 'stderr': result.stderr})
    if ok and result.returncode:
        raise RuntimeError(transcript[-1])
    return result

git = lambda *args: run(['git', '-C', repo, *args]).stdout.strip()
git('init', '-q', '-b', 'fixture')
base_code = "import re\ndef count_done(text):\n    return len(re.findall(r'(?m)^- \\[([xX])\\]\\s+', text))\n"
head_code = base_code.replace(r'\]\s+', r'\](?!\()')
(repo / 'checkbox.py').write_text(base_code)
(repo / 'README.md').write_text('Only checkboxes followed by whitespace count; links do not count.\n')
git('add', 'checkbox.py', 'README.md')
git('commit', '-qm', 'fixture base')
base = git('rev-parse', 'HEAD')
(repo / 'checkbox.py').write_text(head_code)
git('add', 'checkbox.py')
git('commit', '-qm', 'fixture reference-link regression')
head = git('rev-parse', 'HEAD')
# Deliberately correct the source checkout without committing. It cannot prove HEAD correct.
(repo / 'checkbox.py').write_text(base_code)
wt = area / 'worktree'
git('worktree', 'add', '--detach', str(wt), head)
try:
    assert run(['git', '-C', wt, 'rev-parse', 'HEAD']).stdout.strip() == head
    probe = area / 'probe.py'
    probe.write_text("import json,sys\nsys.path.insert(0, sys.argv[1])\nfrom checkbox import count_done\nprint(json.dumps({s:count_done(s) for s in ['- [x](url)', '- [x][ref]', '- [x] item', '- [X] item']}))\n")
    command = [sys.executable, '-B', probe, wt]
    observed = json.loads(run(command).stdout)
    assert observed == {'- [x](url)': 0, '- [x][ref]': 1, '- [x] item': 1, '- [X] item': 1}
    failed = run([sys.executable, '-B', '-c', 'import fixture_missing_dependency_154'], cwd=wt, ok=False)
    assert failed.returncode != 0
    committed_doc = git('show', f'{head}:README.md')
finally:
    git('worktree', 'remove', '--force', str(wt))
review_md = f'''- 対象: fake PR #900 / head {head[:12]}
## Review history

| Reviewed at (UTC) | HEAD | Mode |
| --- | --- | --- |
| {started_at} | `{head[:12]}` | Initial |

## Summary

| Severity | 件数 |
| --- | --- |
| Medium | 2 |

## Medium

### M-1: reference links count as checkboxes
- 位置: `checkbox.py:3`
- 検出時 HEAD: `{head[:12]}`

### M-2: uppercase checkbox does not count
- 位置: `checkbox.py:3`
- 検出時 HEAD: `{head[:12]}`

## Unverified candidates

### U-1: optional dependency path may fail
- 位置: `checkbox.py:3`
'''
md = review / 'example-reviewer.md'
md.write_text(review_md)
helper = tool / '.agents/scripts/review_findings.py'
helper_cmd = [sys.executable, '-B', helper]
candidate = review / 'findings' / f'example-reviewer-{head[:12]}.json'
parsed = run([*helper_cmd, 'from-markdown', md, '--review-file', md.name, '--repo', 'example/review-demo',
              '--pr', '900', '--model', 'example-reviewer', '--runtime', 'fixture'], cwd=tool)
candidate.write_text(parsed.stdout)
run([*helper_cmd, 'validate', candidate], cwd=tool)
run([*helper_cmd, 'check-pair', md, candidate], cwd=tool)

def provenance(role, *, skills=None):
    return dict(agent_id='self' if role == 'verify' else 'unknown', role=role, provider='unknown',
                effort='unknown', session_id='unknown', cli_version='unknown', run_id='unknown',
                request_id='unknown', skills=skills or [])
skill = {'path': '.agents/skills/review-verify/SKILL.md',
         'sha256': hashlib.sha256((tool / '.agents/skills/review-verify/SKILL.md').read_bytes()).hexdigest()}
reviewer_prov = provenance('find')
def finding(number, source, prop, verdict, basis):
    return dict(id=f'V-{number}', sources=[f'example-reviewer#{source}@{head[:12]}'], property=prop,
                locations=['checkbox.py:3'], verdict=verdict, basis=basis, variants=[], statement_sites=[],
                pr_relation={'value': 'introduced' if number == 1 else 'unknown', 'basis':
                    f'{base} uses a whitespace boundary; {head} excludes only inline links' if number == 1 else 'No causal conclusion'},
                reported_severities=[] if source.startswith('U') else [
                    {'source': f'example-reviewer#{source}@{head[:12]}', 'severity': 'Medium'}])
f1 = finding(1, 'M-1', 'Links must not count as completed checkboxes', 'confirmed',
             'Committed HEAD execution returned 1 for reference link; inline link returned 0. Original checkout contains an uncommitted correction and was not executed.')
f1['reproduction'] = dict(commands=['uv run --project "$PARENT_ROOT" --locked python -B "$PROBE" "$WT"'],
                         place=f'{head} detached isolated worktree; probe outside worktree',
                         conditions='fake reference-link input - [x][ref]', result='exit 0; count_done returned 1')
f1['variants'] = [{'input': value, 'result': 'violates' if '[ref]' in value else 'holds',
                   'how': f'probe.py executed at {head}: observed {count}'} for value, count in observed.items()]
f1['statement_sites'] = [{'path': 'README.md:1', 'claim': committed_doc, 'result': 'inconsistent'}]
f2 = finding(2, 'M-2', 'Uppercase X checkboxes count', 'not_reproduced',
             f'probe.py executed at {head}: - [X] item returned 1')
f3 = finding(3, 'U-1', 'Optional dependency path works', 'unverified',
             f'Probe exited {failed.returncode}: dependency absent; this is not evidence against the candidate')
f3['missing_checks'] = 'Run the optional path with its dependency available'
seconds = time.monotonic() - started
verified = dict(schema='review-findings/v2', kind='verified', mode='cycle',
                pr={'repository': 'example/review-demo', 'number': 900}, reviewed_head=head, base=base,
                verifier={'model': 'unknown', 'runtime': 'fixture', 'provenance': provenance('verify', skills=[skill])},
                skill=skill, timing={'started_at': started_at, 'finished_at': now(), 'seconds': seconds, 'waiting_seconds': None},
                inputs=[dict(review_file=md.name, model='example-reviewer', runtime='fixture', provenance=reviewer_prov,
                             waiting_seconds=None, input_kind='markdown', findings_file=None, reviewed_head=head[:12], stale=False)],
                coverage={'closed': [{'target': 'README.md', 'how': f'git show {head}:README.md compared with probe'}],
                          'remaining': [{'target': 'optional dependency path', 'reason': 'dependency absent'}]},
                findings=[f1, f2, f3], accuracy={'reviewers': [dict(review_file=md.name, model='example-reviewer',
                    runtime='fixture', provenance=copy.deepcopy(reviewer_prov), skill_sha256=None, candidates=3,
                    confirmed=1, not_reproduced=1, unverified=1, missed=0, unique=['V-1'])],
                    'find_seconds': {md.name: None}, 'verify_seconds': seconds})
draft = review / 'verified' / '.cycle.json'
draft.write_text(json.dumps(verified, ensure_ascii=False, indent=2) + '\n')
run([*helper_cmd, 'validate', draft], cwd=tool)
output = draft.with_name(f'{head[:12]}.json')
draft.replace(output)
summary = output.with_suffix('.md')
summary.write_text(f'''# Fake cycle {head[:12]}

Input: example-reviewer.md, committed HEAD {head}; base {base}.

confirmed: 1; not_reproduced: 1; unverified: 1.

- V-1: reference links count as completed checkboxes at checkbox.py:3. Inline links hold; reference links violate. Committed README.md:1 disagrees.
- V-2: uppercase X was counted when executed; not_reproduced.
- V-3: dependency missing; unverified. Missing check: run optional dependency path.

Remaining: optional dependency path. Elapsed: {seconds:.3f}s; waiting unknown.
Cleanup: isolated worktree removed; scratch preserved with execution transcript.
''')
run([*helper_cmd, 'stats', review], cwd=tool)
(area / 'execution.json').write_text(json.dumps({'base':base, 'head':head, 'observed':observed,
                                               'commands':transcript}, ensure_ascii=False, indent=2))
print(json.dumps({'area':str(area), 'verified':str(output), 'summary':str(summary), 'head':head,
                  'counts':{'confirmed':1,'not_reproduced':1,'unverified':1}, 'seconds':seconds}))
```
