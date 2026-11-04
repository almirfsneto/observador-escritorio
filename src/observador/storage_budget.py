"""Conservative budget for an exclusively owned DELETE-journal SQLite directory.

This is a writer admission check with journal reserve, not an OS filesystem quota.
It cannot constrain an administrator or other programs writing into the directory.
"""
from pathlib import Path
import shutil

from .private_directory import reject_links


class StorageBudget:
    def __init__(self, path, max_db_bytes, max_total_bytes=None, min_free_bytes=1024*1024):
        self.path = Path(path).absolute()
        # cache_spill=OFF ensures one journal segment; allow a 64 KiB sector/header
        # plus page-number/checksum overhead and an additional 64 KiB safety margin.
        self.reserve = max_db_bytes + (max_db_bytes // 512 + 1) * 8 + 131072
        self.limit = max_total_bytes if max_total_bytes is not None else 3*max_db_bytes + 1024*1024
        if self.limit < max_db_bytes + self.reserve or min_free_bytes < 0:
            raise ValueError('invalid_storage_budget')
        self.min_free = min_free_bytes
        self.peak_observed = 0
        self.last_observed = None
        self.observations = 0

    def usage(self):
        size = 0
        for index, entry in enumerate(self.path.parent.iterdir()):
            if index >= 64:
                raise OSError('storage_directory_unexpected')
            reject_links(entry)
            if not entry.is_file():
                raise OSError('storage_directory_unexpected')
            size += entry.stat().st_size
        self.peak_observed = max(size, self.peak_observed)
        self.last_observed = size
        self.observations += 1
        return size

    def snapshot(self):
        # Cached gauges only: safe to copy from the writer, never scan from UI.
        return dict(limit_bytes=self.limit,reserve_bytes=self.reserve,
                    observed_bytes=self.last_observed,peak_observed_bytes=self.peak_observed if self.observations else None,
                    observations=self.observations,physical_quota=False)

    def check(self, reserve=True):
        size = self.usage()
        needed = self.reserve if reserve else 0
        if size + needed > self.limit:
            raise OSError('storage_budget_exceeded')
        if shutil.disk_usage(self.path.parent).free < needed + self.min_free:
            raise OSError('storage_space_unavailable')
        return size
