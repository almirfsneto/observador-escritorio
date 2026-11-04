"""Synthetic owner killed by the Windows test. Only fixed diagnostics on failure."""
import json
from pathlib import Path
import sys
import time

channel=None
try:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
    from observador.owned_channel import OwnedSyntheticChannel
    channel=OwnedSyntheticChannel(ttl_ms=30000)
    channel.start()
    peer=channel._binding['child']
    print(json.dumps(dict(pid=peer['pid'],start_ticks=peer['start_ticks'])),flush=True)
    time.sleep(30)
except BaseException:
    if channel:
        channel.close();snapshot=channel.snapshot()
        print(json.dumps(dict(phase=snapshot['phase'],fixture_exit_code=snapshot['fixture_exit_code'])),flush=True)
    else:print(json.dumps(dict(phase='import',fixture_exit_code=None)),flush=True)
    raise SystemExit(82) from None
finally:
    if channel:channel.close()
