#!/usr/bin/env python3
"""Resumable local quality diagnostics. Standard library only; bwrap executes code.

Run: python3 run-quality.py --out results/<run-name>
Read: <out>/REPORT.md and progress.json. Reuse --out to resume the identical suite.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('quality_cases', ROOT / 'quality-cases.py')
cases_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases_module)
API = 'http://127.0.0.1:8731'

def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)

def request(body):
    req = urllib.request.Request(API + '/v1/chat/completions', json.dumps(body).encode(), {'Content-Type':'application/json'})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=1800) as response:
        data = json.load(response)
    return data, time.monotonic() - start

def body(prompt, max_tokens=512, effort='none', drafter='mtp'):
    value = {'messages':[{'role':'user','content':prompt}], 'max_tokens':max_tokens,
             'temperature':0, 'drafter':drafter, 'enable_thinking':effort != 'none', 'reasoning_effort':effort}
    if effort != 'none': value['max_thinking_tokens'] = 1536
    return value

def unfence(text):
    text = (text or '').strip()
    match = re.fullmatch(r'```(?:python|json)?\s*\n(.*?)\n```', text, re.S)
    return match.group(1) if match else text

WORKER = '''import importlib.util,json,sys
spec=importlib.util.spec_from_file_location("solution","/case/solution.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
inputs=json.load(sys.stdin)
results=[]
for args in inputs:
    try: results.append({"value":m.solve(*args)})
    except BaseException as e: results.append({"error":type(e).__name__+": "+str(e)[:200]})
print(json.dumps(results,ensure_ascii=False))
'''

def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (8,8))
    resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,512*1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024*1024,1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64,64))
    resource.setrlimit(resource.RLIMIT_CORE, (0,0))

def sandbox(code, inputs):
    with tempfile.TemporaryDirectory(prefix='qwen-quality-') as folder:
        directory = Path(folder)
        (directory/'solution.py').write_text(code)
        (directory/'worker.py').write_text(WORKER)
        command = ['bwrap','--unshare-all','--die-with-parent','--new-session',
                   '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64',
                   '--proc','/proc','--dev','/dev','--tmpfs','/tmp', '--clearenv',
                   '--setenv','PATH','/usr/bin','--setenv','PYTHONDONTWRITEBYTECODE','1',
                   '--ro-bind',folder,'/case','--chdir','/case','/usr/bin/python3','-I','/case/worker.py']
        with (directory/'stdout').open('w+') as stdout, (directory/'stderr').open('w+') as stderr:
            try:
                proc = subprocess.run(command, input=json.dumps(inputs), text=True, stdout=stdout, stderr=stderr,
                                      timeout=15, preexec_fn=limits)
            except subprocess.TimeoutExpired:
                return {'error':'execution timeout (15 seconds)'}
            stdout.seek(0); stderr.seek(0)
            output, errors = stdout.read(1024*1024), stderr.read(4096)
        if proc.returncode:
            return {'error':f'execution exit {proc.returncode}', 'stderr':errors}
        try:
            values = json.loads(output)
            if not isinstance(values,list) or len(values) != len(inputs): raise ValueError('wrong result count')
            return {'values':values}
        except (ValueError,TypeError) as e:
            return {'error':'invalid execution output: '+str(e), 'stdout':output[:1000], 'stderr':errors}

def evaluate_code(text, task):
    code = unfence(text)
    total = len(task['cases'])
    try:
        tree = ast.parse(code)
        if task['id'] == 'expression_parser':
            forbidden = {'eval','exec','compile','ast','subprocess','__import__'}
            for node in ast.walk(tree):
                names = []
                if isinstance(node,ast.Name): names = [node.id]
                if isinstance(node,ast.Attribute): names = [node.attr]
                if isinstance(node,(ast.Import,ast.ImportFrom)):
                    names = [a.name.split('.')[0] for a in node.names] + [getattr(node,'module','') or '']
                if forbidden.intersection(names):
                    return {'passed':False,'passed_cases':0,'total_cases':total,'error':'forbidden parser implementation'}
    except SyntaxError as e:
        return {'passed':False,'passed_cases':0,'total_cases':total,'error':str(e)}
    executed = sandbox(code,[c['args'] for c in task['cases']])
    if 'error' in executed:
        return {'passed':False,'passed_cases':0,'total_cases':total, **executed}
    failures = []
    for i,(actual,expected) in enumerate(zip(executed['values'],task['cases'])):
        if not isinstance(actual,dict) or 'error' in actual or actual.get('value') != expected['expected']:
            failures.append({'case':i,'args':expected['args'],'expected':expected['expected'],'actual':actual})
    return {'passed':not failures,'passed_cases':total-len(failures),'total_cases':total,'failures':failures}

def filler_rows(n, seed):
    rng = random.Random(seed)
    words = ['cedar','harbor','copper','orchard','violet','meadow','marble','silver']
    return [f'Archive record {i:06d}: site {rng.choice(words)}; batch {rng.randrange(100000,999999)}; status routine; note {rng.choice(words)} {rng.choice(words)}.\n' for i in range(n)]

def long_prompt(n, seed, mode):
    rows = filler_rows(n,seed)
    rng = random.Random(seed+999)
    names = ['KESTREL','OTTER','LYNX']
    expected = {}
    positions = {'early':[.05], 'middle':[.5], 'late':[.95], 'multi':[.05,.5,.95], 'absent':[], 'decode':[.5]}[mode]
    for j, position in enumerate(positions):
        value = ''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=16))
        expected[names[j]] = value
        rows[int(n*position)] = f'Authoritative registry entry: key {names[j]}; access_code {value}.\n'
    if mode == 'absent': expected = {'KESTREL':None}
    question = 'Return ONLY a JSON object mapping these registry keys to their exact access_code: '+', '.join(expected)+'. Use null if no authoritative registry entry exists. Do not guess.'
    if mode == 'decode':
        expected = {'access_code':expected['KESTREL'], 'sequence':list(range(1,129))}
        question = 'Return ONLY JSON with access_code equal to the authoritative KESTREL access_code from this archive, and sequence equal to the array of every integer from 1 through 128 inclusive, in order. No omissions or abbreviations.'
    return f'Document batch {seed}. Read the archive and answer the final question.\n<archive>\n'+''.join(rows)+'</archive>\n'+question, expected

def report(out, jobs):
    rows = []
    for job in jobs:
        path = out / (job['id']+'.json')
        if path.exists(): rows.append(json.loads(path.read_text()))
    completed = len(rows)
    state = {'completed':completed,'total':len(jobs),'finished':completed==len(jobs),
             'updated':time.strftime('%Y-%m-%d %H:%M:%S %z'),
             'passes':sum(r.get('evaluation',{}).get('passed',False) for r in rows),
             'errors':sum('error' in r for r in rows)}
    save(out/'progress.json',state)
    lines = ['# Qwen3.8 Flash Next: local quality diagnostics','',
             f'Completed {completed}/{len(jobs)} requests. Updated {state["updated"]}.','',
             'Configuration: Halogen 0.14.0, quality overlay, 65,536-token context, desktop active. Temperature 0. Retrieval uses MTP with thinking off. Coding compares thinking off and low effort with a 1,536-token thinking budget and 4,096 total output tokens. No repair attempts.','',
             'This is a small custom diagnostic suite, not HumanEval, SWE-bench or a general coding-quality score. Synthetic archive retrieval does not establish comprehension of real books or repositories. Ten unique Python tasks use deterministic hidden cases. Two tasks repeat with about 32K tokens of distractors. Complexity targets are not formally verified.','',
             'Requests are sequential; drafter order is alternated for long-context speed pairs. Cache counters are retained; wall time includes prompt processing and cannot be treated as cold-prefill speed. Context lengths below are actual API prompt-token counts, not requested targets. Generation speed is the engine decode metric, not full-request throughput.','',
             '| Test | Mode | Input tokens | Output tokens | Correct | Cases | Decode tok/s | Wall s | Cached / restored |',
             '|---|---|---:|---:|---|---:|---:|---:|---:|']
    for r in rows:
        resp = r.get('response',{})
        usage,timing = resp.get('usage',{}),resp.get('timings',{})
        evaluation = r.get('evaluation',{})
        mode = r['job'].get('effort','none')+'/'+r['job'].get('drafter','mtp')
        count = f'{evaluation["passed_cases"]}/{evaluation["total_cases"]}' if 'total_cases' in evaluation else '—'
        correct = 'ERROR' if 'error' in r else ('PASS' if evaluation.get('passed') else 'FAIL')
        lines.append(f'| {r["job"]["id"]} | {mode} | {usage.get("prompt_tokens",0)} | {usage.get("completion_tokens",0)} | {correct} | {count} | {timing.get("predicted_per_second",0):.1f} | {r.get("wall_seconds",0):.1f} | {timing.get("cache_n",0)} / {timing.get("disk_restore_n",0)} |')
    lines += ['', '## Aggregate results','']
    for group in ('retrieval','decode','coding','coding_long'):
        for effort in (('none','low') if group.startswith('coding') else ('none',)):
            selected = [r for r in rows if r['job']['group']==group and r['job'].get('effort','none')==effort]
            if selected:
                passed = sum(r.get('evaluation',{}).get('passed',False) for r in selected)
                lines.append(f'- {group}, thinking {effort}: {passed}/{len(selected)} complete-task passes.')
    lines += ['', '## Long-context generation comparison','']
    for target in (8192,32768,60000):
        pair = [r for r in rows if r['job']['group']=='decode' and r['job']['target']==target and 'response' in r]
        if len(pair)==2:
            by_mode = {r['job']['drafter']:r for r in pair}
            serial = by_mode['serial']['response']['timings']['predicted_per_second']
            mtp = by_mode['mtp']['response']['timings']['predicted_per_second']
            same = by_mode['serial']['response']['choices'][0]['message'] == by_mode['mtp']['response']['choices'][0]['message']
            lines.append(f'- Target {target:,}: serial {serial:.1f} tok/s; MTP {mtp:.1f} tok/s; ratio {mtp/serial:.2f}x; identical messages: {same}. One pair only; structured counting output is not representative of all generation.')
    failures = [r for r in rows if not r.get('evaluation',{}).get('passed')]
    if failures:
        lines += ['', '## Failures to inspect','']
        for r in failures:
            reason = r.get('error') or r.get('evaluation',{}).get('error') or json.dumps(r.get('evaluation',{}).get('failures',r.get('evaluation',{})),ensure_ascii=False)[:600]
            lines.append(f'- {r["job"]["id"]}: {reason}. Full request, answer and checks: `{r["job"]["id"]}.json`.')
    lines += ['', 'Artifacts: manifest.json records the planned tests and script hashes; each per-test JSON retains the exact request, full answer, timings and evaluation; suite-cases.json contains hidden checks; progress.json is machine-readable. API errors count as errors rather than model-quality failures. Code runs with no network or home mount, read-only runtime and time/memory limits.','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    return state

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path, required=True)
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--report-only',action='store_true')
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    if args.self_test:
        assert sandbox('def solve(x): return x+1',[[2]]) == {'values':[{'value':3}]}
        check = sandbox('import os, socket\ndef solve():\n return [os.path.exists("/home/wowzontle"),len(socket.if_nameindex())]',[[]])
        assert check['values'][0]['value'] == [False,1],check
        assert 'error' in sandbox('def solve():\n while True: pass',[[]])
        task = cases_module.tasks()[0]
        assert evaluate_code('def solve(x): return []',task)['passed'] is False
        print('PASS: isolated execution, home hidden, only loopback, CPU limit, wrong answer rejection',flush=True)
        return
    tasks = cases_module.tasks()
    jobs=[]
    for target in (8192,32768,60000):
        for mode in ('early','middle','late','multi','absent'):
            jobs.append({'id':f'retrieval-{target}-{mode}','group':'retrieval','target':target,'mode':mode})
        for drafter in (('mtp','serial') if target==32768 else ('serial','mtp')):
            jobs.append({'id':f'decode-{target}-{drafter}','group':'decode','target':target,'mode':'decode','drafter':drafter})
    for i, task in enumerate(tasks):
        for effort in (('low','none') if i%2 else ('none','low')):
            jobs.append({'id':f'coding-{task["id"]}-{effort}','group':'coding','task':task['id'],'effort':effort})
    for task_id in ('toposort','expression_parser'):
        for effort in ('none','low'):
            jobs.append({'id':f'coding-long-{task_id}-{effort}','group':'coding_long','task':task_id,'effort':effort,'target':32768})
    manifest = {'suite_version':1,'seed':cases_module.SEED,'jobs':jobs,
                'script_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'quality-cases.py')}}
    if args.report_only:
        print(json.dumps(report(out,jobs))); return
    # Prevent two runners from sharing this output directory.
    import fcntl
    lock = (out/'runner.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (out/'manifest.json').exists():
        if json.loads((out/'manifest.json').read_text()) != manifest:
            raise RuntimeError('Suite changed; use a new output directory rather than mixing results')
    else: save(out/'manifest.json',manifest)
    save(out/'suite-cases.json',tasks)
    with urllib.request.urlopen(API+'/health',timeout=15) as response:
        health=json.load(response)
    save(out/'health.json',health)
    if health.get('context',0)<65536: raise RuntimeError('Expected 65,536 context')
    if health.get('busy'): raise RuntimeError('Model is busy; avoid mixing benchmark traffic')
    assert sandbox('def solve(x): return x',[[42]]) == {'values':[{'value':42}]}, 'Sandbox unavailable'
    # Calibrate archive length with actual server tokenizer, keeping complete responses.
    calibration=[]
    for n in (100,300):
        path=out/f'calibration-{n}.json'
        if path.exists(): row=json.loads(path.read_text())
        else:
            prompt,_=long_prompt(n, cases_module.SEED,'middle')
            req=body(prompt,1)
            response,wall=request(req)
            row={'request':req,'response':response,'wall_seconds':wall}
            save(path,row)
        calibration.append(row['response']['usage']['prompt_tokens'])
    slope=(calibration[1]-calibration[0])/200
    intercept=calibration[0]-100*slope
    if slope<=0: raise RuntimeError('Invalid token calibration')
    save(out/'calibration.json',{'tokens_per_row':slope,'overhead':intercept})
    state=report(out,jobs)
    for index,job in enumerate(jobs):
        path=out/(job['id']+'.json')
        if path.exists(): continue
        print(json.dumps({'starting':job['id'],'number':index+1,'total':len(jobs)}),flush=True)
        save(out/'current.json',{'job':job,'started':time.strftime('%Y-%m-%d %H:%M:%S %z')})
        if job['group'] in ('retrieval','decode'):
            n=max(10,round((job['target']-intercept)/slope))
            # Shared prompt for the paired drafters; unique documents elsewhere.
            seed=cases_module.SEED+job['target']+(['early','middle','late','multi','absent','decode'].index(job['mode'])*100)
            prompt,expected=long_prompt(n,seed,job['mode'])
            req=body(prompt,1024 if job['group']=='decode' else 256,drafter=job.get('drafter','mtp'))
        else:
            task=next(t for t in tasks if t['id']==job['task'])
            instructions='Write Python 3 code implementing the following function. Return ONLY source code, no explanation or Markdown. Standard library only, no input/output or top-level execution.\n'+task['spec']
            if job['group']=='coding_long':
                n=max(10,round((job['target']-intercept-200)/slope))
                rows=filler_rows(n,cases_module.SEED+55)
                rows[n//2]='\n<required_task>\n'+instructions+'\n</required_task>\n'
                prompt='Find the required_task section in the archive below and implement it. Other archive records are irrelevant.\n'+''.join(rows)+'\nReturn only Python code for the required_task section above.'
            else: prompt=instructions
            req=body(prompt,4096,effort=job['effort'])
        row={'job':job,'request':req}
        try:
            # If evaluation was interrupted, reuse the persisted API result.
            raw_path=out/(job['id']+'.response.json')
            if raw_path.exists():
                raw=json.loads(raw_path.read_text()); response,wall=raw['response'],raw['wall_seconds']
            else:
                response,wall=request(req)
                save(raw_path,{'request':req,'response':response,'wall_seconds':wall})
            row.update(response=response,wall_seconds=wall)
            choice=response['choices'][0]
            text=choice['message'].get('content','')
            if job['group'].startswith('coding'):
                evaluation=evaluate_code(text,task)
                (out/(job['id']+'.py')).write_text(unfence(text))
            else:
                try:
                    actual=json.loads(unfence(text))
                    evaluation={'passed':actual==expected,'actual':actual,'expected':expected}
                except ValueError:
                    evaluation={'passed':False,'error':'answer was not valid JSON','expected':expected}
            if choice['finish_reason']=='length':
                evaluation['truncated']=True
                evaluation['passed']=False
            row['evaluation']=evaluation
        except Exception as e:
            row['error']=f'{type(e).__name__}: {e}'
            row['traceback']=traceback.format_exc()
        save(path,row)
        state=report(out,jobs)
        print(json.dumps({'finished':job['id'],'passed':row.get('evaluation',{}).get('passed'),
                          'error':row.get('error'),'wall_seconds':round(row.get('wall_seconds',0),2),
                          'completed':state['completed'],'total':state['total']}),flush=True)
        # Stop on transport/harness errors; remove that error JSON explicitly to retry.
        if 'error' in row: raise RuntimeError(row['error'])
    save(out/'complete.json',state)
    subprocess.run(['notify-send','Qwen quality tests finished',f'{state["passes"]}/{state["total"]} checks passed. Report: {out}/REPORT.md'],check=False)
    print('COMPLETE: '+str(out/'REPORT.md'),flush=True)

if __name__=='__main__':
    main()
