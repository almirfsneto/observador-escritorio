"""Synthetic owner killed by the Windows test to verify job/watchdog teardown."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from observador.owned_channel import OwnedSyntheticChannel

channel=OwnedSyntheticChannel(ttl_ms=30000)
try:
    channel.start()
    peer=channel._binding['child']
    print(json.dumps(dict(pid=peer['pid'],start_ticks=peer['start_ticks'])),flush=True)
    time.sleep(30)
finally:channel.close()
