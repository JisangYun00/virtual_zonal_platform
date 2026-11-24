"""Minimal standard-library desktop dashboard for the existing team protocol."""
from __future__ import annotations
import argparse
import asyncio
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from core.protocol import command
from core.zones import Action, Signal, Zone, DEFAULT_SUBNET, zone_address
from central.__main__ import send
from central.status import follow


class Dashboard(tk.Tk):
    def __init__(self, subnet: str, timeout: float = 1.0):
        super().__init__()
        self.title("Virtual Zonal Platform - Central Controller")
        self.geometry("920x680")
        self.subnet, self.timeout = subnet, timeout
        self.events = queue.Queue()
        self.seq = 0
        self.active = None
        self.zone_labels = {}
        self.status = tk.StringVar(value="Connecting to management...")
        self.lamps = tk.StringVar(value="Signal: ?    Brake: ?")
        self._build()
        threading.Thread(target=self._follow, daemon=True).start()
        self.after(80, self._drain)

    def _build(self):
        ttk.Label(self, text="SDV Virtual Zonal Architecture", font=("Arial", 20, "bold")).pack(pady=10)
        ttk.Label(self, textvariable=self.status, font=("Arial", 12)).pack()
        diagram = ttk.Frame(self)
        diagram.pack(pady=16)
        for name, row, col in [("FRONT", 0, 1), ("LEFT", 1, 0),
                               ("RIGHT", 1, 2), ("REAR", 2, 1)]:
            item = tk.Label(diagram, text=name, width=22, height=4, bg="#d9e5f5",
                            fg="#17324f", font=("Arial", 12, "bold"), relief="solid")
            item.grid(row=row, column=col, padx=8, pady=8)
            self.zone_labels[name] = item
        tk.Label(diagram, text="Central\nLaptop", width=22, height=4,
                 bg="#ffe0ab", relief="solid", font=("Arial", 11, "bold")).grid(row=1, column=1)
        ttk.Label(self, textvariable=self.lamps, font=("Arial", 12)).pack(pady=5)
        controls = ttk.Frame(self)
        controls.pack(pady=12)
        for label, action, value in [("LEFT", Action.SET_SIGNAL, Signal.LEFT),
                                     ("RIGHT", Action.SET_SIGNAL, Signal.RIGHT),
                                     ("HAZARD", Action.SET_SIGNAL, Signal.HAZARD),
                                     ("SIGNAL OFF", Action.SET_SIGNAL, Signal.OFF),
                                     ("BRAKE ON", Action.SET_BRAKE, True),
                                     ("BRAKE OFF", Action.SET_BRAKE, False)]:
            ttk.Button(controls, text=label, command=lambda a=action, v=value: self._command(a, v)).pack(side="left", padx=3)
        ttk.Button(self, text="Open REAR camera window", command=self._video).pack(pady=6)
        self.log = tk.Text(self, height=8, state="disabled")
        self.log.pack(fill="both", expand=True, padx=16, pady=6)
        ttk.Label(self, text="Zone transitions originate on Jetson (ZONE SELECT). Camera viewer opens in a separate window.").pack(pady=6)

    def _video(self):
        subprocess.Popen([sys.executable, '-m', 'central.video', '--subnet', self.subnet])

    def _follow(self):
        async def worker():
            await follow(self.subnet + ".10", lambda seq, s: self.events.put(("state", seq, s)))
        asyncio.run(worker())

    def _command(self, action, value):
        if self.active is None:
            self._write("Not connected to management channel yet")
            return
        self.seq += 1
        rid, zone = self.seq, self.active
        host = zone_address(self.subnet, zone)
        def work():
            try:
                response, ms = send(host, command(rid, action, value), self.timeout)
                self.events.put(("log", "%s %s -> %s (%.2fms)" % (
                    zone.value, action.value, response.status.value, ms)))
                self.events.put(("state", None, response.state))
            except Exception as exc:
                self.events.put(("log", "Command failed: " + str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def _drain(self):
        try:
            while True:
                item = self.events.get_nowait()
                if item[0] == "log": self._write(item[1])
                else:
                    _, seq, state = item
                    self.active = state.active_zone
                    self.status.set("ACTIVE: %s  |  Management: %s" % (state.active_zone.value, self.subnet + ".10"))
                    self.lamps.set("Signal: %s    Brake: %s" % (state.signal.value, "ON" if state.brake else "OFF"))
                    for z, label in self.zone_labels.items():
                        label.configure(bg="#59c4a1" if z == self.active.value else "#d9e5f5")
                    if seq is not None: self._write("STATE #%s: %s" % (seq, state.active_zone.value))
        except queue.Empty:
            pass
        self.after(80, self._drain)

    def _write(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--subnet", default=DEFAULT_SUBNET)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args(argv)
    Dashboard(args.subnet, args.timeout).mainloop()

if __name__ == "__main__":
    main()
