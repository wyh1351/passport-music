import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from control_model import BridgeStatus, read_json, status_view, save_port, port_available, installation_present


class ControlModelTests(unittest.TestCase):
    def test_installed_state_does_not_depend_on_login_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertFalse(installation_present(root,None,'expected'))
            self.assertTrue(installation_present(root,'expected','expected'))
            (root/'installation.json').write_text('{"schema":1,"installed":true}')
            for name in ('PassportMusicBackground.exe','PassportMusic.exe'):(root/name).touch()
            self.assertTrue(installation_present(root,None,'expected'))
    def test_stale_or_wrong_process_never_shows_connected(self):
        player={'internal_player':True,'available':True}
        for health in ({'phase':'connected','updated':1,'pid':10},
                       {'phase':'connected','updated':100,'pid':20},
                       {'phase':'connected','updated':101,'pid':10}):
            state=status_view(health,player,True,now=100,pid=10)
            self.assertFalse(state['connected'])
        self.assertTrue(status_view({'phase':'connected','updated':100,'pid':10},player,True,now=100,pid=10)['ready'])

    def test_stop_overrides_recent_telemetry(self):
        health={'phase':'connected','updated':100}
        for running,paused in ((False,False),(True,True)):
            self.assertFalse(status_view(health,{'internal_player':True},running,paused,now=100)['connected'])

    def test_faults_have_distinct_recovery_actions(self):
        cases=[(False,False,{},'start'),(True,False,{'port_blocked':True,'process_running':True},'settings'),
               (True,False,{'process_running':True},'player'),(True,False,{'internal_player':True},'bluetooth')]
        for running,paused,player,action in cases:
            with self.subTest(action=action):self.assertEqual(status_view({},player,running,paused)['action'],action)
        health={'phase':'connected','updated':100,'lyrics':'error'}
        self.assertEqual(status_view(health,{'internal_player':True},True,now=100)['action'],'help')

    def test_invalid_port_never_overwrites_saved_value(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);save_port(root,19223)
            for value in ('80','65536','localhost:9223','bad','９２２３'):
                with self.assertRaises(ValueError):save_port(root,value)
                self.assertEqual((root/'desktop-port.txt').read_text().strip(),'19223')

    def test_status_is_bounded_and_does_not_store_song_data(self):
        with tempfile.TemporaryDirectory() as folder,patch('control_model.time.time',return_value=100):
            status=BridgeStatus(folder);status.update('connected',lyrics='ready')
            data=read_json(Path(folder)/'bridge-status.json')
            self.assertEqual(set(data),{'phase','lyrics','pid','updated'})
            self.assertEqual(data['phase'],'connected')
            status.update('retrying',lyrics='waiting')
            self.assertEqual(read_json(status.path)['phase'],'retrying')

    def test_read_only_status_does_not_break_bridge(self):
        with tempfile.TemporaryDirectory() as folder,patch('control_model.atomic_json',side_effect=PermissionError):
            BridgeStatus(folder).update('connected')

    def test_port_check_releases_its_socket(self):
        import socket
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        self.assertTrue(port_available(port));self.assertTrue(port_available(port))


if __name__=='__main__':unittest.main()
