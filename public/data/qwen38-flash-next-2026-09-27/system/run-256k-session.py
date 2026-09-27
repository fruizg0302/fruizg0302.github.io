#!/usr/bin/env python3
"""Temporary root-owned model-service override; run tests as the desktop user.

Launch in a transient systemd unit with this script's cleanup as ExecStopPost.
"""
import json
import os
from pathlib import Path
import pwd
import re
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path('/home/wowzontle/Work/Experiments/qwen38-flash-next')
OUT=ROOT/'results/20260927-256k'
DROP=Path('/run/systemd/system/qwen38-halogen.service.d/256k-experiment.conf')
STATE=Path('/run/qwen38-256k-session.json')
UNIT='qwen38-halogen.service'
USER=pwd.getpwnam('wowzontle')

def command(*args,check=True):
    return subprocess.run(args,text=True,capture_output=True,check=check)

def write(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n')
    os.chown(path,USER.pw_uid,USER.pw_gid)

def cleanup():
    if not STATE.exists(): return
    state=json.loads(STATE.read_text())
    if state['owner']!=os.environ.get('INVOCATION_ID'):
        raise RuntimeError('Temporary configuration belongs to another invocation')
    if DROP.exists() and DROP.read_text()!=state['override']:
        raise RuntimeError('Override changed externally; refusing to replace it')
    stopped=command('systemctl','stop',UNIT,check=False)
    status=command('systemctl','show',UNIT,'-p','ActiveState','--value').stdout.strip()
    if stopped.returncode or status not in ('inactive','failed'):
        raise RuntimeError('Model failed to stop; retaining override/state for inspection')
    if DROP.exists(): DROP.unlink()
    command('systemctl','daemon-reload')
    command('systemctl','reset-failed',UNIT,check=False)
    tuned=command('systemctl','is-active','tuned.service',check=False).stdout.strip()
    ppd=command('systemctl','is-active','power-profiles-daemon.service',check=False).stdout.strip()
    profile=command('powerprofilesctl','get',check=False).stdout.strip()
    write(OUT/'cleanup.json',{'model':command('systemctl','is-active',UNIT,check=False).stdout.strip(),
                            'tuned':tuned,'power_profiles_daemon':ppd,'profile':profile,
                            'runtime_override_removed':not DROP.exists(),
                            'power_state_removed':not Path('/run/qwen38-power-state.json').exists()})
    if tuned=='active' or ppd!=state['ppd'] or profile!=state['profile'] or Path('/run/qwen38-power-state.json').exists():
        raise RuntimeError('Power restoration did not match prior state')
    STATE.unlink()
    print('CLEANUP: model unloaded; 64K configuration and desktop power settings restored.',flush=True)

def memory():
    values={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
    pressure=Path('/proc/pressure/memory').read_text()
    full=float(re.search(r'full avg10=([\d.]+)',pressure)[1])
    return {'time':time.time(),'free_kib':values['MemFree'],'available_kib':values['MemAvailable'],
            'swap_used_kib':values['SwapTotal']-values['SwapFree'],'psi_full_avg10':full}

def run():
    if STATE.exists() or DROP.exists(): raise RuntimeError('Another 256K session or override exists')
    if command('systemctl','is-active','--quiet',UNIT,check=False).returncode==0:
        raise RuntimeError('Model already active; refusing to interrupt another session')
    loaded=command('runuser','-u',USER.pw_name,'--','/usr/bin/ollama','ps').stdout
    if len(loaded.strip().splitlines())>1: raise RuntimeError('Ollama has a loaded model')
    if any(OUT.glob('*-response.json')): raise RuntimeError('Output directory already contains test results')
    text=Path('/etc/systemd/system/qwen38-halogen.service').read_text()
    assert 'HALOGEN_CTX=65536 -e HALOGEN_KV_POOL_POSITIONS=65536' in text
    start=text[text.index('ExecStart='):text.index('\nExecStop=')]
    start=start.replace('HALOGEN_CTX=65536 -e HALOGEN_KV_POOL_POSITIONS=65536','HALOGEN_CTX=262144 -e HALOGEN_KV_POOL_POSITIONS=262144')
    override='[Service]\nExecStart=\n'+start+'\n'
    state={'owner':os.environ['INVOCATION_ID'],'override':override,
           'profile':command('powerprofilesctl','get').stdout.strip(),
           'ppd':command('systemctl','is-active','power-profiles-daemon.service').stdout.strip()}
    STATE.write_text(json.dumps(state)); STATE.chmod(0o600)
    OUT.mkdir(parents=True,exist_ok=True)
    write(OUT/'session.json',state)
    DROP.parent.mkdir(parents=True,exist_ok=True); DROP.write_text(override)
    command('systemctl','daemon-reload')
    baseline=memory();bad=0;process=None;start_time=time.time()
    def sample():
        nonlocal bad
        row=memory()
        with (OUT/'memory.jsonl').open('a') as f: f.write(json.dumps(row)+'\n')
        os.chown(OUT/'memory.jsonl',USER.pw_uid,USER.pw_gid)
        bad=bad+1 if row['psi_full_avg10']>=20 else 0
        if row['swap_used_kib']-baseline['swap_used_kib']>512*1024 or bad>=6:
            raise RuntimeError('Memory-pressure guard: >512 MiB new swap or sustained full memory PSI >=20%')
        return row
    try:
        command('systemctl','start',UNIT)
        print('STARTUP: temporary 262,144-token context and pool, one slot.',flush=True)
        for attempt in range(120):
            sample()
            if command('systemctl','is-active','--quiet',UNIT,check=False).returncode:
                raise RuntimeError('Model service stopped during initialization')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8731/health',timeout=3) as r: health=json.load(r)
                if health.get('status')=='ok' and health.get('engine',{}).get('responds'): break
            except (OSError,ValueError): pass
            time.sleep(5)
        else: raise RuntimeError('Model did not become ready within startup deadline')
        log=command('journalctl','-u',UNIT,'--since','@'+str(int(start_time)),'--no-pager').stdout
        (OUT/'startup.log').write_text(log);os.chown(OUT/'startup.log',USER.pw_uid,USER.pw_gid)
        matches=re.findall(r'host memory left for everything else:.*?\(([\d.]+) GiB total',log)
        if not matches or float(matches[-1])<16:
            raise RuntimeError('Startup memory report missing or below 16 GiB headroom')
        write(OUT/'startup-health.json',health)
        print('READY: engine reports '+matches[-1]+' GiB host headroom.',flush=True)
        process=subprocess.Popen(['runuser','-u',USER.pw_name,'--','/usr/bin/python3','-u',str(ROOT/'run-256k.py'),'--out',str(OUT)])
        while process.poll() is None:
            sample();time.sleep(5)
        if process.returncode: raise RuntimeError(f'Test runner exited {process.returncode}')
        write(OUT/'session-result.json',{'success':True,'elapsed_seconds':time.time()-start_time})
    except BaseException as e:
        write(OUT/'session-result.json',{'success':False,'error':str(e),'elapsed_seconds':time.time()-start_time})
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
        log=command('journalctl','-u',UNIT,'--since','@'+str(int(start_time)),'--no-pager',check=False).stdout
        (OUT/'service.log').write_text(log);os.chown(OUT/'service.log',USER.pw_uid,USER.pw_gid)
        cleanup()

if __name__=='__main__':
    if os.geteuid()!=0: raise SystemExit('Run through the authorized transient system service')
    if sys.argv[1:]==['cleanup']: cleanup()
    elif sys.argv[1:]==['run']: run()
    else: raise SystemExit('Usage: run-256k-session.py run|cleanup')
