#!/usr/bin/env python3
"""Two paired near-full native-context requests; retain exact inputs and answers."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('quality', ROOT/'run-quality.py')
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)

def save(path, obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2)+'\n'); tmp.replace(path)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(quality.API+'/health',timeout=15) as r: health=json.load(r)
    save(out/'health.json',health)
    assert health['context']==262144 and health['kv_pool_positions']==262144, 'Wrong context or reduced pool'
    assert health['slots']==1 and not health['busy'], 'Expected one idle slot'
    if (out/'serial.json').exists() or (out/'mtp.json').exists():
        raise RuntimeError('Use a new output directory for a fresh paired test')
    calibration=[]
    for count in (100,300):
        prompt,_=quality.long_prompt(count,20260927,'middle')
        req=quality.body(prompt,1)
        response,wall=quality.request(req)
        save(out/f'calibration-{count}.json',{'request':req,'response':response,'wall_seconds':wall})
        calibration.append(response['usage']['prompt_tokens'])
    slope=(calibration[1]-calibration[0])/200
    overhead=calibration[0]-100*slope
    target=260000
    count=round((target-overhead-60)/slope)
    rows=quality.filler_rows(count,20260927+262144)
    rng=random.Random(262144)
    expected={}
    placements=[]
    for key,fraction in [('KESTREL',.05),('OTTER',.5),('LYNX',.95)]:
        code=''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=16))
        index=int(count*fraction)
        rows[index]=f'Authoritative registry entry: key {key}; access_code {code}.\n'
        expected[key]=code
        placements.append({'key':key,'row':index,'fraction_of_rows':fraction})
    expected['MISSING']=None
    expected['sequence']=list(range(1,129))
    prompt=('Native-context test document 262144. Read the archive and answer the final question.\n<archive>\n'
            +''.join(rows)+'</archive>\n'
            'Return ONLY a JSON object with keys KESTREL, OTTER, LYNX, MISSING, and sequence. '
            'For the four registry keys, return the exact access_code from its authoritative registry entry, '
            'or null if that key has no authoritative entry. Do not guess. '
            'For sequence return an array of every integer from 1 through 128 inclusive in order, '
            'without omissions or abbreviations.')
    save(out/'plan.json',{'window':262144,'target_input_tokens':target,'max_output_tokens':1024,
                         'tokens_per_row':slope,'calibration_overhead':overhead,'rows':count,
                         'placements':placements,'expected':expected,'order':['serial','mtp'],
                         'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                         'note':'Positions are fractions of archive rows, not exact tokenizer offsets. Prompt cache stays in mode 1.'})
    (out/'prompt.txt').write_text(prompt)
    results=[]
    for drafter in ('serial','mtp'):
        req=quality.body(prompt,max_tokens=1024,drafter=drafter)
        save(out/f'{drafter}-request.json',req)
        save(out/'progress.json',{'phase':'request','drafter':drafter,'completed':len(results),'total':2})
        print(f'START {drafter}: target approximately {target:,} input tokens, 1,024 output-token budget',flush=True)
        response,wall=quality.request(req)
        save(out/f'{drafter}-response.json',{'response':response,'wall_seconds':wall})
        choice=response['choices'][0]
        try: actual=json.loads(quality.unfence(choice['message'].get('content','')))
        except ValueError: actual=None
        checks={key:isinstance(actual,dict) and key in actual and actual[key]==value for key,value in expected.items()}
        count_actual=response['usage']['prompt_tokens']
        row={'drafter':drafter,'response':response,'wall_seconds':wall,'expected':expected,'actual':actual,
             'checks':checks,'passed':actual==expected and choice['finish_reason']=='stop',
             'context_fraction':count_actual/262144,
             'near_full_context':256000<=count_actual and count_actual+1024<=262144}
        save(out/f'{drafter}.json',row);results.append(row)
        print(json.dumps({'finished':drafter,'passed':row['passed'],'input_tokens':count_actual,
                          'wall_seconds':round(wall,2),'timings':response['timings']}),flush=True)
        if not row['near_full_context']:
            raise RuntimeError('Actual token count outside intended near-full-context range')
    a,b=results
    identical=a['response']['choices'][0]['message']==b['response']['choices'][0]['message']
    summary={'completed':2,'passed':sum(r['passed'] for r in results),'identical_messages':identical,
             'context':262144,'actual_input_tokens':a['response']['usage']['prompt_tokens'],
             'finished':time.strftime('%Y-%m-%d %H:%M:%S %z')}
    save(out/'summary.json',summary); save(out/'progress.json',{'phase':'complete',**summary})
    lines=['# 256K native-context attempt','',
           'Configured context and KV pool: 262,144 tokens, one slot, 16,384-token prefill arena. Desktop active. Same pinned Halogen 0.14.0 image, native W4B weights and quality overlay as the earlier tests. Thinking off, temperature zero. MTP includes default prompt-lookup assistance.','',
           f'Actual input: **{summary["actual_input_tokens"]:,} tokens**, {summary["actual_input_tokens"]/262144:.2%} of the configured window. Output allowance: 1,024 tokens. This is near-full occupancy, not 262,144 input tokens plus output.','',
           'One synthetic archive holds independent random codes at approximately 5%, 50% and 95% of its rows. The answer must return all three, null for an absent key, and the complete sequence 1–128. This is one task in two decoding modes, not five independent retrieval tasks.','',
           '| Mode | Correct | Code checks | Absent key | Sequence | Output tokens | Decode tok/s | Request s | Cached / restored |',
           '|---|---|---|---|---|---:|---:|---:|---:|']
    for r in results:
        t=r['response']['timings'];u=r['response']['usage'];c=r['checks']
        codes=sum(c[k] for k in ('KESTREL','OTTER','LYNX'))
        lines.append(f'| {r["drafter"]} | {r["passed"]} | {codes}/3 | {c["MISSING"]} | {c["sequence"]} | {u["completion_tokens"]} | {t["predicted_per_second"]:.2f} | {r["wall_seconds"]:.2f} | {t.get("cache_n",0)} / {t.get("disk_restore_n",0)} |')
    speed=a['response']['timings']['predicted_per_second']
    lines+=['',f'Identical full messages: **{identical}**. MTP/serial engine decode ratio: **{b["response"]["timings"]["predicted_per_second"]/speed:.2f}x**.','',
            'Serial ran first, MTP second; there is only one pair and no counterbalanced thermal control. Prompt caching remained enabled, so compare engine decode rates separately from request wall time. Cache counters above identify reused input. This result does not establish general long-document comprehension, coding quality, or performance on unrelated prompts.','',
            'Full requests/responses and prompt text are saved here. `memory.jsonl` samples host memory, swap and PSI; `startup.log` records the engine memory accounting. `session.json` records the temporary configuration and `cleanup.json` records restoration after the model unloads.','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    print('RESULTS '+str(out/'REPORT.md'),flush=True)

if __name__=='__main__': main()
