import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kel import service
from kel.runner import run_broker
from kel.core import Store
import argparse
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--acp',action='store_true');p.add_argument('--run');p.add_argument('--rpc-run');p.add_argument('--migrate-idle',type=int);p.add_argument('--port',type=int,default=0)
a=p.parse_args()
if a.acp:
    from kel.acp_host import main
    sys.argv=[sys.argv[0],'--data',a.data]
    main()
elif a.migrate_idle:
    from kel.migration import migrate_idle
    import json
    print(json.dumps(migrate_idle(a.data,a.migrate_idle)))
elif a.rpc_run:
    from kel.coding_transport import serve
    serve(Store(a.data),a.rpc_run)
elif a.run:run_broker(Store(a.data),a.run)
else:service.serve(a.data,a.port)
