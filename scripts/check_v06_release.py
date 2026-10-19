from hardening_v06 import validate_source
"""Execute final application checks and bind their logs to frozen source."""
import copy
import os
import subprocess
import sys
from evaluate_v06 import BASE, ROOT, CONFIG, hashes, write

before=hashes();configuration=copy.deepcopy(CONFIG)
assert before==validate_source()
commands={
 'pytest':([sys.executable,'-m','pytest','-q'],ROOT,'pytest-final.log'),
 'frontend_build':(['npm','run','build'],ROOT/'frontend','frontend-build-final.log'),
 'browser':(['npm','run','test:e2e'],ROOT/'frontend','playwright-final.log'),
}
exits={}
for name,(command,cwd,log) in commands.items():
    with (BASE/log).open('x') as output:
        result=subprocess.run(command,cwd=cwd,stdout=output,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
    exits[name]=result.returncode;print(name,result.returncode,flush=True)
write(BASE/'release-checks.json',{'source_before':before,'source_after':hashes(),'config_unchanged':CONFIG==configuration,'exit_codes':exits,'commands':{name:command for name,(command,_,_) in commands.items()}})
if any(exits.values()) or hashes()!=before:raise SystemExit(1)
