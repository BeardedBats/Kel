"""Linux entry point: put one native worker and descendants in its own cgroup."""
import os
from pathlib import Path
import re
import sys

group=sys.argv[1]
if not re.fullmatch('[a-f0-9]{32}',group):raise SystemExit('Invalid worker group')
directory=Path('/sys/fs/cgroup/kel-v1')/group
directory.mkdir(parents=True,exist_ok=True)
(directory/'cgroup.procs').write_text(str(os.getpid()))
for name,value in [('memory.max','2147483648'),('pids.max','256')]:
    if (directory/name).exists():(directory/name).write_text(value)
os.execvp(sys.argv[2],sys.argv[2:])
