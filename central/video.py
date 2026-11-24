"""Optional Laptop JPEG viewer. Pillow is needed only for the video window."""
import argparse
import io
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request

from PIL import Image, ImageTk
from core.zones import DEFAULT_SUBNET


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--subnet', default=DEFAULT_SUBNET)
    args=parser.parse_args(argv)
    root=tk.Tk()
    root.title('REAR camera - Virtual Zonal')
    root.geometry('800x580')
    label=tk.Label(root, text='REAR image will appear here; FRONT/LEFT/RIGHT -> unavailable')
    label.pack(fill='both', expand=True)
    status=tk.StringVar(value='Connecting...')
    tk.Label(root, textvariable=status).pack()
    closing=threading.Event()
    latest={'image':None, 'state':'Connecting...'}
    lock=threading.Lock()
    url='http://%s.10:8080/frame.jpg' % args.subnet
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def fetch():
        while not closing.is_set():
            try:
                with opener.open(url, timeout=2) as response:
                    data=response.read(4*1024*1024)
                image=Image.open(io.BytesIO(data))
                image.thumbnail((780,520))
                with lock:
                    latest['image']=image.copy()
                    latest['state']='REAR camera receiving'
            except urllib.error.HTTPError as exc:
                with lock:
                    latest['image']=None
                    latest['state']='Camera disabled outside REAR' if exc.code==403 else 'Camera unavailable (HTTP %s)'%exc.code
            except Exception as exc:
                with lock:
                    latest['image']=None
                    latest['state']='Waiting for Jetson video: %s'%exc
            closing.wait(.12)
    threading.Thread(target=fetch, daemon=True).start()

    def refresh():
        with lock:
            pic=latest['image']
            text=latest['state']
        status.set(text)
        if pic is not None:
            photo=ImageTk.PhotoImage(pic)
            label.configure(image=photo, text='')
            label.image=photo
        else:
            label.configure(image='', text=text)
            label.image=None
        if not closing.is_set(): root.after(160, refresh)
    def on_close():
        closing.set()
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', on_close)
    refresh()
    root.mainloop()

if __name__=='__main__':main()
