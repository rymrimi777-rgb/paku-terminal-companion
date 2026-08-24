"""
Unit tests for Paku Linux support across autoruns, scan, and debloat features.
"""

from __future__ import annotations

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from paku.ui.themes import get_theme
from paku.ui.mascot import MascotLoader
import paku.features.scan as scan_mod
import paku.features.autoruns as autoruns_mod
import paku.features.debloat as debloat_mod


class TestLinuxSupport(unittest.TestCase):

    def setUp(self):
        self.theme = get_theme("cherry")
        assets_dir = Path(__file__).parent.parent / "src" / "paku" / "assets"
        self.mascot_loader = MascotLoader(assets_dir)

    @patch("sys.platform", "linux")
    def test_get_desktop_autostart_entries(self):
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_dir", return_value=True), \
             patch.object(Path, "iterdir") as mock_iterdir:
            
            mock_file = MagicMock()
            mock_file.is_file.return_value = True
            mock_file.name = "testapp.desktop"
            mock_file.stem = "testapp"
            
            mock_iterdir.return_value = [mock_file]

            file_content = "[Desktop Entry]\nName=Test App\nExec=testapp --flag\n"
            with patch("builtins.open", unittest.mock.mock_open(read_data=file_content)):
                entries = scan_mod._get_desktop_autostart_entries()
                self.assertIsInstance(entries, list)
                if entries:
                    location, name, target = entries[0]
                    self.assertEqual(name, "Test App")
                    self.assertEqual(target, "testapp --flag")

    @patch("sys.platform", "linux")
    def test_get_startup_entries_linux(self):
        with patch("paku.features.scan._get_desktop_autostart_entries", return_value=[("~/.config/autostart", "App", "cmd")]):
            entries = scan_mod._get_startup_entries()
            self.assertEqual(entries, [("App", "cmd")])

    @patch("sys.platform", "linux")
    def test_cron_reboot_entries(self):
        fake_cron = "# Comment\n@reboot /usr/local/bin/my_job.sh\n* * * * * echo hi\n"
        with patch("subprocess.check_output", return_value=fake_cron):
            entries = autoruns_mod._get_cron_reboot_entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0][0], "@reboot Cron Job")
            self.assertEqual(entries[0][1], "/usr/local/bin/my_job.sh")

    @patch("sys.platform", "linux")
    def test_systemd_enabled_services(self):
        fake_output = "UNIT FILE STATE VENDOR PRESET\nbluetooth.service enabled enabled\ncups.service disabled enabled\n"
        with patch("subprocess.check_output", return_value=fake_output):
            services = autoruns_mod._get_systemd_enabled_services(user=False)
            self.assertEqual(len(services), 1)
            self.assertEqual(services[0][0], "bluetooth.service")
            self.assertEqual(services[0][1], "Systemd Service")

    @patch("sys.platform", "linux")
    def test_get_installed_linux_packages(self):
        with patch("paku.features.debloat._detect_package_manager", return_value="apt"), \
             patch("subprocess.check_output", side_effect=lambda cmd, **kwargs: "install ok installed" if "aisleriot" in cmd else ""):
            packages = debloat_mod._get_installed_linux_packages()
            self.assertTrue(any(pkg[0] == "aisleriot" for pkg in packages))

    @patch("sys.platform", "linux")
    def test_render_autoruns_linux_no_crash(self):
        with patch("paku.features.autoruns._get_desktop_autostart_entries", return_value=[("autostart", "App", "exec")]), \
             patch("paku.features.autoruns._get_cron_reboot_entries", return_value=[]), \
             patch("paku.features.autoruns._get_systemd_enabled_services", return_value=[]):
            try:
                autoruns_mod.render_autoruns(self.theme, self.mascot_loader, wait_for_enter=False, animations_enabled=False)
            except Exception as e:
                self.fail(f"render_autoruns on Linux raised an exception: {e}")

    @patch("sys.platform", "linux")
    def test_render_scan_linux_no_crash(self):
        with patch("paku.features.scan._get_desktop_autostart_entries", return_value=[]):
            try:
                scan_mod.render_scan(self.theme, self.mascot_loader, wait_for_enter=False, animations_enabled=False)
            except Exception as e:
                self.fail(f"render_scan on Linux raised an exception: {e}")

    @patch("sys.platform", "linux")
    def test_render_debloat_linux_no_crash(self):
        with patch("paku.features.debloat._get_installed_linux_packages", return_value=[("aisleriot", "Detected via apt (not removed)")]):
            try:
                debloat_mod.render_debloat(self.theme, self.mascot_loader, wait_for_enter=False, animations_enabled=False)
            except Exception as e:
                self.fail(f"render_debloat on Linux raised an exception: {e}")

    @patch("sys.platform", "win32")
    def test_win32_behavior_unmodified(self):
        # Confirm win32 guards work as before
        self.assertEqual(scan_mod._get_desktop_autostart_entries(), [])
        self.assertEqual(autoruns_mod._get_cron_reboot_entries(), [])
        self.assertEqual(autoruns_mod._get_systemd_enabled_services(), [])
        self.assertEqual(debloat_mod._get_installed_linux_packages(), [])


if __name__ == "__main__":
    unittest.main()
