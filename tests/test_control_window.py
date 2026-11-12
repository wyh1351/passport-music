"""Native Windows UI regression checks; other hosts skip the Tk window."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))


@unittest.skipUnless(sys.platform=='win32','Native Windows window check')
class ControlWindowTests(unittest.TestCase):
    def test_center_restore_and_reinstall_feedback(self):
        from control_center import Center
        from control_model import read_json,window_placement
        from control_service import monitor_work_areas,window_position,position_window
        with tempfile.TemporaryDirectory() as directory,patch.object(Center,'make_tray'),patch.object(Center,'refresh'),patch('control_center.registered',return_value=None):
            root=Path(directory)
            expected=window_placement({},monitor_work_areas())
            center=Center(root)
            try:
                center.app.update()
                actual=window_position(center.app)
                self.assertLessEqual(abs(actual['x']-expected['x']),2)
                self.assertLessEqual(abs(actual['y']-expected['y']),2)
                position_window(center.app,expected['x']+24,expected['y']+16)
                center.app.update();center.save_window()
                saved=read_json(center.window_file)
                self.assertEqual(saved['x'],expected['x']+24)
                center.installed=True
                with patch.object(center,'worker') as worker:
                    center.install()
                    self.assertTrue(center.install_button.disabled)
                    self.assertIn('正在',center.install_button.text)
                    args=worker.call_args.args
                    center.busy=True;center.install()
                    self.assertEqual(worker.call_count,1)
                    with patch('control_center.messagebox.showinfo') as info:
                        args[2](root)
                        info.assert_called_once()
                    self.assertIn('已安装并启动',center.install_status.cget('text'))
            finally:center.quit_ui()
            second=Center(root)
            try:
                second.app.update()
                self.assertEqual(window_position(second.app)['x'],saved['x'])
                self.assertEqual(window_position(second.app)['y'],saved['y'])
            finally:second.quit_ui()


if __name__=='__main__':unittest.main()
