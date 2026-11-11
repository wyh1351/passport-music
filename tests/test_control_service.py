import asyncio
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch,MagicMock,AsyncMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from control_service import change_port, open_player, select_player_window, show_player


class ControlServiceTests(unittest.TestCase):
    def test_hidden_tray_main_window_is_a_valid_restore_target(self):
        main=dict(handle=10,visible=False,owned=False,titled=True,width=1100,height=760)
        helpers=[dict(main,handle=11,visible=True,width=32,height=32),dict(main,handle=12,visible=True,owned=True)]
        self.assertEqual(select_player_window([*helpers,main]),main)

    def test_hidden_window_is_restored_without_relaunch_or_restart(self):
        window=dict(handle=10,visible=False,owned=False,titled=True,width=1100,height=760)
        api=MagicMock();api.IsWindowVisible.return_value=True
        with patch('control_service.player_window_candidates',return_value=(api,[window])),patch('control_service.subprocess.Popen') as launch:
            self.assertTrue(show_player(Path('D:/CloudMusic/cloudmusic.exe')))
        api.ShowWindow.assert_called_once_with(10,9)
        api.SetForegroundWindow.assert_called_once_with(10)
        launch.assert_not_called()

    def test_small_or_untitled_helpers_are_not_shown(self):
        window=dict(handle=10,visible=False,owned=False,titled=True,width=1100,height=760)
        self.assertIsNone(select_player_window([dict(window,titled=False),dict(window,width=1),dict(window,owned=True)]))

    def test_occupied_new_port_does_not_save_or_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'desktop-port.txt').write_text('19223')
            with patch('control_service.port_available',return_value=False),patch('control_service.restart_bridge') as restart:
                with self.assertRaises(ValueError):change_port(root,20480)
                self.assertEqual((root/'desktop-port.txt').read_text(),'19223')
                restart.assert_not_called()

    def test_saved_port_is_used_to_open_and_show_player(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'desktop-port.txt').write_text('19223')
            with patch('ncm_desktop.locate_player',return_value=Path('D:/CloudMusic/cloudmusic.exe')),patch('ncm_desktop.launch_player',new_callable=AsyncMock) as launch,patch('control_service.show_player',return_value=True) as show:
                open_player(root)
            launch.assert_awaited_once_with(str(Path('D:/CloudMusic/cloudmusic.exe')),19223)
            show.assert_called_once()


if __name__=='__main__':unittest.main()
