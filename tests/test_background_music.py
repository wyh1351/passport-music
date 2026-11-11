import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'companion'))
from background_music import run_command,set_autostart,stop,decode_bridge_line,install_root,recovery_enabled,request_stop
from background_task import owns_task,task_definition

class BackgroundTests(unittest.TestCase):
    def test_management_uses_registered_custom_install_location(self):
        root=Path.cwd()/'custom install'
        with patch('background_music.persisted_root',return_value=None),patch('background_music.registered',return_value=run_command(root)):
            self.assertEqual(install_root(),root)

    def test_bridge_output_supports_utf8_and_windows_code_page(self):
        message='蓝牙已连接'
        self.assertEqual(decode_bridge_line(message.encode('utf-8'),'cp936'),message)
        self.assertEqual(decode_bridge_line(message.encode('cp936'),'cp936'),message)

    def test_logon_command_quotes_space_path_and_does_not_launch_player(self):
        command=run_command(Path('C:/Users/Example User/Passport Music'))
        self.assertTrue(command.startswith('"C:'))
        self.assertTrue(command.endswith('PassportMusicBackground.exe" --background'))
        self.assertNotIn('--launch-player',command)
        with self.assertRaises(ValueError): run_command(Path('C:/')/('a'*270))
        with self.assertRaises(ValueError): run_command(Path('C:/bad"path'))

    def test_different_registry_owner_cannot_be_replaced_or_disabled(self):
        fake=types.SimpleNamespace(CreateKey=MagicMock())
        with patch.dict(sys.modules,winreg=fake),patch('background_music.registered',return_value='other-owner'):
            for enabled in (True,False):
                with self.assertRaises(RuntimeError):set_autostart(Path('C:/Passport'),enabled)
        fake.CreateKey.assert_not_called()

    def test_stale_pid_for_other_executable_is_not_terminated(self):
        root=MagicMock()
        root.__truediv__.return_value.read_text.return_value='{"supervisor":123,"bridge":456}'
        with patch('background_music.owned_process',return_value=None) as own:
            stop(root)
        self.assertEqual(own.call_count,2)

    def test_manual_stop_and_disable_prevent_recovery(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            with patch('background_music.registered', return_value=None):
                self.assertFalse(recovery_enabled(root))
            with patch('background_music.registered', return_value=run_command(root)):
                self.assertTrue(recovery_enabled(root))
                with patch('background_music.setup_logger'), patch('background_music.stop') as stop_bridge:
                    request_stop(root)
                stop_bridge.assert_called_once_with(root)
                self.assertFalse(recovery_enabled(root))

    def test_task_export_checks_installation_even_with_console_encoded_xml(self):
        launcher = Path.cwd() / 'Music & Tools' / 'PassportMusicBackground.exe'
        sid = 'S-1-5-21-100-200-300-1001'
        task = task_definition(launcher, sid)
        self.assertTrue(owns_task(task.encode('utf-8'), launcher, sid))
        self.assertTrue(owns_task(task.encode('utf-16'), launcher, sid))
        self.assertFalse(owns_task(task.encode('utf-8'), launcher.with_name('other.exe'), sid))
        self.assertFalse(owns_task(task.encode('utf-8'), launcher, 'S-1-5-21-100-200-300-1002'))

if __name__=='__main__':unittest.main()
