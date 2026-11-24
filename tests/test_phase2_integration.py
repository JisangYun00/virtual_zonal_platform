import asyncio
import json
import socket
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from core.management import MANAGEMENT_PORT, parse_state
from core.zones import Zone, Action, Signal
from zone_controller.controller import ZoneController
from zone_controller.management import StatePublisher
from zone_controller.camera import CameraService
from zone_controller.gpio import GPIOAdapter, load_wiring

class FakeCamera:
    def __init__(self): self.opens=0; self.closes=0
    def open(self):self.opens+=1
    def frame_jpeg(self):return b'JPEG-DATA'
    def close(self):self.closes+=1

class ManagementTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_and_changes_and_rejected_command(self):
        ctrl=ZoneController()
        pub=StatePublisher(ctrl,interval=60)
        await pub.start('127.0.0.10')
        ctrl.add_listener(pub.publish)
        try:
            r,w=await asyncio.open_connection('127.0.0.10', MANAGEMENT_PORT)
            seq,s=parse_state(await asyncio.wait_for(r.readline(), 1))
            self.assertEqual((seq,s.active_zone),(0,Zone.FRONT))
            ctrl.request(Zone.FRONT,Action.SET_SIGNAL,Signal.LEFT)
            seq,s=parse_state(await asyncio.wait_for(r.readline(),1))
            self.assertEqual((seq,s.signal),(1,Signal.LEFT))
            ctrl.request(Zone.REAR,Action.SET_SIGNAL,Signal.LEFT) # rejected no broadcast
            with self.assertRaises(asyncio.TimeoutError): await asyncio.wait_for(r.readline(),.05)
            ctrl.select_next()
            seq,s=parse_state(await asyncio.wait_for(r.readline(),1))
            self.assertEqual((seq,s.active_zone,s.signal),(2,Zone.REAR,Signal.OFF))
            w.close();await w.wait_closed()
        finally:
            await pub.close()

class CameraTests(unittest.TestCase):
    def test_rear_only_and_release(self):
        ctrl=ZoneController(); backend=FakeCamera()
        cam=CameraService(ctrl,backend)
        ctrl.add_listener(lambda:cam.on_state_change(ctrl.state))
        self.assertEqual(cam.snapshot()[0],403)
        ctrl.select_next()
        self.assertEqual(cam.snapshot(),(200,b'JPEG-DATA','image/jpeg'))
        self.assertEqual(backend.opens,1)
        ctrl.select_next()
        self.assertEqual(cam.snapshot()[0],403)
        self.assertEqual(backend.closes,1)
    def test_http_snapshot(self):
        ctrl=ZoneController(); cam=CameraService(ctrl, FakeCamera())
        cam.start('127.0.0.10', 0)
        url='http://127.0.0.10:%d/frame.jpg' % cam.httpd.server_port
        try:
            # urlopen honors external proxy environment; disable it for loopback
            from urllib.request import build_opener, ProxyHandler
            opener=build_opener(ProxyHandler({}))
            with self.assertRaises(HTTPError) as result:opener.open(url,timeout=2)
            self.assertEqual(result.exception.code,403)
            ctrl.select_next()
            with opener.open(url, timeout=2) as response:self.assertEqual(response.read(),b'JPEG-DATA')
        finally:cam.close()

class FakeGPIO:
    BOARD=1;IN=2;OUT=3;LOW=0;HIGH=1
    def __init__(self):self.values={};self.last={}
    def setmode(self,*a): pass
    def setup(self,pin,mode,initial=None):
        if mode==self.IN:self.values[pin]=1
        else:self.last[pin]=0
    def input(self,pin):return self.values[pin]
    def output(self,pin,value):self.last[pin]=value
    def cleanup(self):pass

class GpioTests(unittest.TestCase):
    def test_wiring_validation_and_outputs(self):
        import tempfile,os
        wiring={'inputs':dict(zip(('ZONE','LEFT','RIGHT'),(16,29,37))),
                'outputs':dict(zip(('ZONE_FRONT','ZONE_REAR','ZONE_LEFT','ZONE_RIGHT','SIGNAL_LEFT','SIGNAL_RIGHT','BRAKE'),(11,12,13,15,18,22,31)))}
        fd,path=tempfile.mkstemp()
        try:
            with os.fdopen(fd,'w') as f:json.dump(wiring,f)
            self.assertEqual(load_wiring(path),wiring)
            bad=json.loads(json.dumps(wiring));bad['inputs']['ZONE']=11
            with open(path,'w') as f:json.dump(bad,f)
            with self.assertRaises(ValueError):load_wiring(path)
        finally:os.unlink(path)
        ctrl=ZoneController();driver=FakeGPIO();adapter=GPIOAdapter(ctrl,wiring,driver)
        adapter.setup();adapter.sample(0)
        self.assertEqual(driver.last[11],1)
        driver.values[16]=0
        adapter.sample(.01);adapter.sample(.1)
        driver.values[16]=1
        adapter.sample(.2);adapter.sample(.3)
        self.assertEqual(ctrl.state.active_zone,Zone.REAR)
