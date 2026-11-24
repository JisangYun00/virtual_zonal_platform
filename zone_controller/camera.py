"""Optional REAR-only JPEG snapshot service; PySpin follows Lab 10 acquisition lifecycle.

This module must not be imported by core/. Hardware packages load only for FLIR.
"""
from __future__ import annotations
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from core.zones import Zone

CAMERA_PORT = 8080


class FlirBackend:
    def __init__(self):
        self.system = None
        self.cameras = None
        self.cam = None

    def open(self):
        import PySpin
        self.system = PySpin.System.GetInstance()
        self.cameras = self.system.GetCameras()
        if self.cameras.GetSize() == 0:
            raise RuntimeError("FLIR not found: check Lab 10 check_lab10.sh")
        self.cam = self.cameras.GetByIndex(0)
        self.cam.Init()
        self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
        self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        if PySpin.IsWritable(self.cam.PixelFormat):
            self.cam.PixelFormat.SetValue(PySpin.PixelFormat_BGR8)
        self.cam.BeginAcquisition()

    def frame_jpeg(self):
        import cv2
        image = self.cam.GetNextImage(1500)
        try:
            if image.IsIncomplete():
                raise RuntimeError("FLIR incomplete frame")
            frame = image.GetNDArray().copy()  # copy before releasing SDK memory
        finally:
            image.Release()
        ok, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ok:
            raise RuntimeError("JPEG encoding failed")
        return jpeg.tobytes()

    def close(self):
        try:
            if self.cam is not None:
                try:
                    if self.cam.IsStreaming():
                        self.cam.EndAcquisition()
                finally:
                    if self.cam.IsInitialized():
                        self.cam.DeInit()
        finally:
            self.cam = None
            if self.cameras is not None:
                self.cameras.Clear()
                self.cameras = None
            if self.system is not None:
                self.system.ReleaseInstance()
                self.system = None


class CameraService:
    def __init__(self, controller, backend=None):
        self.controller = controller
        self.backend = backend if backend is not None else FlirBackend()
        self.lock = threading.RLock()
        self.started = False
        self.epoch = 0
        self.httpd = None
        self.thread = None

    def on_state_change(self, state):
        with self.lock:
            self.epoch += 1
            if state.active_zone is not Zone.REAR:
                self._close()

    def _close(self):
        if self.started:
            try: self.backend.close()
            finally: self.started = False

    def snapshot(self):
        with self.lock:
            if self.controller.state.active_zone is not Zone.REAR:
                return 403, b'', 'text/plain'
            epoch = self.epoch
            try:
                if not self.started:
                    self.backend.open()
                    self.started = True
                frame = self.backend.frame_jpeg()
            except Exception:
                # Initialization might fail after acquiring SDK resources but
                # before self.started becomes True. Always release partial state.
                try:
                    self.backend.close()
                except Exception:
                    pass
                self.started = False
                return 503, b'camera unavailable', 'text/plain'
            if epoch != self.epoch or self.controller.state.active_zone is not Zone.REAR:
                return 403, b'', 'text/plain'
            return 200, frame, 'image/jpeg'

    def start(self, host: str, port: int = CAMERA_PORT):
        service = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/frame.jpg':
                    self.send_error(404)
                    return
                code, data, kind = service.snapshot()
                self.send_response(code)
                self.send_header('Content-Type', kind)
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                try: self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError): pass
            def log_message(self, format, *args):
                pass
        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        with self.lock:
            self._close()
