"""Run pinned upstream benchmark, retaining every response and request timing."""
import importlib.util,json,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'results'/time.strftime('%Y%m%d-%H%M%S-benchmark')
out.mkdir(parents=True)
source=Path('/home/wowzontle/Work/Projects/halogen-flash-server/tools/halogen-bench.py')
spec=importlib.util.spec_from_file_location('bench',source)
bench=importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
original=bench.post
count=0
def record(api,body,timeout=1800):
 global count
 response,wall=original(api,body,timeout)
 count+=1
 row={'request':body,'response':response,'wall_seconds':wall}
 (out/f'{count:03d}.json').write_text(json.dumps(row,indent=2)+'\n')
 print(json.dumps({'request':count,'drafter':body.get('drafter','default'),'usage':response.get('usage'),'timings':response.get('timings'),'wall_seconds':round(wall,3)}),file=sys.stderr,flush=True)
 return response,wall
bench.post=record
sys.argv=[str(source),'--api','http://127.0.0.1:8731','-p','1024,8192,32768','-n','300','-d','serial,mtp','-r','3','--effort','none','--json']
(out/'command.json').write_text(json.dumps(sys.argv,indent=2))
print('Results: '+str(out),file=sys.stderr,flush=True)
with (out/'summary.txt').open('w') as f:
 sys.stdout=f
 code=bench.main()
raise SystemExit(code)
