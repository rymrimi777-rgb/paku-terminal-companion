"""
Unit tests for Paku System Monitoring feature.
"""

from __future__ import annotations

import unittest
from paku.features.system import (
    get_memory_metrics,
    get_cpu_utilization,
    get_disk_partitions,
    get_top_processes,
    get_system_snapshot,
    _render_bar,
)


class TestSystemMonitoring(unittest.TestCase):

    def test_memory_metrics(self):
        mem = get_memory_metrics()
        self.assertGreater(mem.total_gb, 0.0)
        self.assertGreaterEqual(mem.used_gb, 0.0)
        self.assertGreaterEqual(mem.free_gb, 0.0)
        self.assertGreaterEqual(mem.percent, 0.0)
        self.assertLessEqual(mem.percent, 100.0)

    def test_cpu_utilization(self):
        cpu = get_cpu_utilization(sample_interval=0.05)
        self.assertIsInstance(cpu, float)
        self.assertGreaterEqual(cpu, 0.0)
        self.assertLessEqual(cpu, 100.0)

    def test_disk_partitions(self):
        disks = get_disk_partitions()
        self.assertIsInstance(disks, list)
        self.assertGreater(len(disks), 0)
        first = disks[0]
        self.assertTrue(len(first.mount) > 0)
        self.assertGreater(first.total_gb, 0.0)
        self.assertGreaterEqual(first.percent, 0.0)
        self.assertLessEqual(first.percent, 100.0)

    def test_top_processes(self):
        procs = get_top_processes(limit=5, sort_by="memory")
        self.assertIsInstance(procs, list)
        for p in procs:
            self.assertIsInstance(p.pid, int)
            self.assertIsInstance(p.name, str)
            self.assertGreaterEqual(p.mem_mb, 0.0)

    def test_system_snapshot_structure(self):
        snap = get_system_snapshot()
        self.assertIn("timestamp", snap)
        self.assertIn("cpu", snap)
        self.assertIn("memory", snap)
        self.assertIn("disks", snap)
        self.assertIn("top_processes", snap)
        self.assertIn("warnings", snap)
        self.assertIn("is_psutil_accelerated", snap)

    def test_render_bar(self):
        bar_empty = _render_bar(0.0, width=10)
        self.assertEqual(bar_empty, "░" * 10)
        bar_full = _render_bar(100.0, width=10)
        self.assertEqual(bar_full, "█" * 10)
        bar_half = _render_bar(50.0, width=10)
        self.assertEqual(bar_half, "█" * 5 + "░" * 5)


if __name__ == "__main__":
    unittest.main()
