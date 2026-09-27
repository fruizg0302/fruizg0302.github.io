import json,statistics
from pathlib import Path
root=Path(__file__).resolve().parent/'results'
p=sorted(root.glob('*-benchmark'))[-1]
rows=[json.loads(x.read_text()) for x in sorted(p.glob('[0-9][0-9][0-9].json'))]
summary={'directory':str(p),'requests':len(rows),'generation':{},'cold_prefill':{},'cached_prefill_requests':0}
for mode in ('serial','mtp'):
 gen=[r for r in rows if r['request'].get('drafter')==mode and r['request']['max_tokens']==300]
 if gen:
  e2e=[r['response']['usage']['completion_tokens']/r['wall_seconds'] for r in gen]
  decode=[r['response']['timings']['predicted_per_second'] for r in gen]
  summary['generation'][mode]={'samples':len(gen),'e2e_mean':statistics.mean(e2e),'decode_mean':statistics.mean(decode),'decode_min':min(decode),'decode_max':max(decode)}
 for r in rows:
  if r['request'].get('drafter')!=mode or r['request']['max_tokens']!=1:continue
  t=r['response']['timings']; n=r['response']['usage']['prompt_tokens']
  if t.get('cache_n',0) or t.get('disk_restore_n',0):
   summary['cached_prefill_requests']+=1;continue
  summary['cold_prefill'].setdefault(str(n),[]).append(n/r['wall_seconds'])
summary['cold_prefill']={k:{'samples':len(v),'e2e_mean':statistics.mean(v)} for k,v in summary['cold_prefill'].items()}
# Same prompt and repetition, greedy serial vs MTP, compare complete messages.
by={}
for r in rows:
 if r['request']['max_tokens']!=300:continue
 key=r['request']['messages'][0]['content']
 by.setdefault(key,{}).setdefault(r['request']['drafter'],[]).append(r['response']['choices'][0]['message'])
pairs=[(a,b) for modes in by.values() for a,b in zip(modes.get('serial',[]),modes.get('mtp',[]))]
summary['greedy_output_pairs']={'compared':len(pairs),'identical':sum(a==b for a,b in pairs)}
(p/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
