"""JS Spec Network Tool — a small, standard-library network diagnostic GUI.

Based on Jess's original cross-platform Wi-Fi information script.
Only test hosts and services you own or have permission to inspect.
"""

import platform
import queue
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk


# --- Original OS / Wi-Fi detection, retained and made GUI-friendly ---
def detect_os():
    return platform.system()


users_os = detect_os()


def get_wifi_info(users_os):
    """Return (SSID, signal) or (None, None) if unavailable."""
    ssid = None
    signal_strength = None

    if users_os == "Windows":
        try:
            result_windows = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
            if result_windows.returncode != 0:
                return None, None

            output = result_windows.stdout
            for line in output.splitlines():
                stripped = line.strip()
                if stripped.startswith("SSID ") and ":" in stripped:
                    ssid = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("Signal") and ":" in stripped:
                    signal_strength = stripped.split(":", 1)[1].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None, None

    elif users_os == "Darwin":
        try:
            result_Darwin = subprocess.run(
                ["networksetup", "-getairportnetwork", "en0"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
            if result_Darwin.returncode != 0:
                return None, None

            output = result_Darwin.stdout
            for line in output.splitlines():
                if line.strip().startswith("Current Wi-Fi Network:"):
                    ssid = line.split(":", 1)[1].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None, None

    elif users_os == "Linux":
        try:
            result_linux = subprocess.run(
                ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
            if result_linux.returncode != 0:
                return None, None

            output = result_linux.stdout
            for line in output.splitlines():
                fields = split_nmcli_fields(line)
                if len(fields) >= 3 and fields[0] == "*":
                    ssid = fields[1]
                    signal_strength = f"{fields[2]}%" if fields[2] else None
                    break
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None, None

    return ssid, signal_strength


def split_nmcli_fields(line):
    """Split nmcli terse fields, accounting for escaped colons and backslashes."""
    fields, current, escaped = [], [], False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


def get_local_info():
    hostname = socket.gethostname()
    try:
        addresses = sorted({result[4][0] for result in socket.getaddrinfo(
            hostname, None, family=socket.AF_INET
        )})
    except OSError:
        addresses = []
    return hostname, addresses


def parse_ports(text):
    """Accept comma-separated TCP port numbers, maximum 20 per check."""
    raw = [piece.strip() for piece in text.split(",")]
    if not raw or any(not piece.isdecimal() for piece in raw):
        raise ValueError("Enter port numbers separated by commas (for example: 22,80,443).")
    ports = list(dict.fromkeys(int(piece) for piece in raw))
    if len(ports) > 20 or any(not 1 <= port <= 65535 for port in ports):
        raise ValueError("Choose up to 20 distinct ports between 1 and 65535.")
    return ports


def check_tcp_ports(host, ports):
    """Attempt TCP connections; no packet crafting, network sweeping or exploits."""
    try:
        address = socket.gethostbyname(host)
    except socket.gaierror as exc:
        return [(None, f"Could not resolve {host}: {exc}")], None

    results = []
    for port in ports:
        try:
            with socket.create_connection((address, port), timeout=1.5):
                status = "OPEN (TCP connection succeeded)"
        except (socket.timeout, TimeoutError):
            status = "No response (filtered or timed out)"
        except ConnectionRefusedError:
            status = "CLOSED (connection refused)"
        except OSError as exc:
            status = f"Connection failed ({exc.strerror or str(exc)})"
        results.append((port, status))
    return results, address


class NetworkTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JS Spec | Network Tool")
        self.geometry("760x600")
        self.minsize(600, 490)
        self.configure(bg="#0c0e14")
        self.worker_results = queue.Queue()

        theme = ttk.Style(self)
        theme.theme_use("clam")
        theme.configure("TFrame", background="#151922")
        theme.configure("TLabel", background="#151922", foreground="#f7f9fc", font=("Segoe UI", 10))
        theme.configure("Heading.TLabel", background="#151922", foreground="#7bf3a2", font=("Segoe UI", 16, "bold"))
        theme.configure("TButton", padding=8, font=("Segoe UI", 10, "bold"))
        theme.configure("TNotebook", background="#0c0e14", borderwidth=0)
        theme.configure("TNotebook.Tab", padding=(18, 10))

        header = tk.Frame(self, bg="#0c0e14", padx=24, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="JS SPEC  /  NETWORK TOOL", bg="#0c0e14", fg="#7bf3a2",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(header, text="Wi-Fi details and targeted TCP connectivity checks",
                 bg="#0c0e14", fg="#aeb6c6", font=("Segoe UI", 10)).pack(anchor="w")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=22, pady=(0, 10))
        self.info_tab = ttk.Frame(self.notebook, padding=22)
        self.check_tab = ttk.Frame(self.notebook, padding=22)
        self.notebook.add(self.info_tab, text="My connection")
        self.notebook.add(self.check_tab, text="TCP checker")
        self.build_info_tab()
        self.build_check_tab()

        tk.Label(self, text="Use only on systems you own or are authorized to test  •  No data is uploaded",
                 bg="#0c0e14", fg="#aeb6c6", font=("Segoe UI", 9)).pack(pady=(0, 12))
        self.after(100, self.process_worker_results)
        self.refresh_info()

    def build_info_tab(self):
        ttk.Label(self.info_tab, text="Connection overview", style="Heading.TLabel").pack(anchor="w", pady=(0, 18))
        self.os_value = self.add_info_row("Operating system")
        self.host_value = self.add_info_row("Computer name")
        self.ip_value = self.add_info_row("Local IPv4 (hostname lookup)")
        self.ssid_value = self.add_info_row("Wi-Fi network (SSID)")
        self.signal_value = self.add_info_row("Signal strength")
        self.refresh_button = ttk.Button(self.info_tab, text="Refresh information", command=self.refresh_info)
        self.refresh_button.pack(anchor="w", pady=22)
        ttk.Label(self.info_tab, text="SSID detection depends on Wi-Fi hardware, system tools and OS language.",
                  wraplength=570).pack(anchor="w")

    def add_info_row(self, caption):
        frame = ttk.Frame(self.info_tab)
        frame.pack(fill="x", pady=6)
        ttk.Label(frame, text=f"{caption}:", width=29).pack(side="left")
        value = ttk.Label(frame, text="Loading...", wraplength=380)
        value.pack(side="left", fill="x", expand=True)
        return value

    def build_check_tab(self):
        ttk.Label(self.check_tab, text="Targeted TCP checker", style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(self.check_tab, text="Checks specific ports on one host you have permission to test.",
                  wraplength=600).pack(anchor="w", pady=(0, 16))
        ttk.Label(self.check_tab, text="Host or IPv4 address").pack(anchor="w")
        self.host_entry = ttk.Entry(self.check_tab, width=50)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(anchor="w", fill="x", pady=(4, 14))
        ttk.Label(self.check_tab, text="TCP ports (comma-separated, maximum 20)").pack(anchor="w")
        self.ports_entry = ttk.Entry(self.check_tab, width=50)
        self.ports_entry.insert(0, "22,80,443")
        self.ports_entry.pack(anchor="w", fill="x", pady=(4, 14))
        self.scan_button = ttk.Button(self.check_tab, text="Check TCP ports", command=self.start_check)
        self.scan_button.pack(anchor="w", pady=(0, 12))
        self.output = tk.Text(self.check_tab, height=12, bg="#0c0e14", fg="#f7f9fc",
                              insertbackground="#7bf3a2", relief="flat", padx=14, pady=12,
                              font=("Consolas", 10), wrap="word", state="disabled")
        self.output.pack(fill="both", expand=True)

    def refresh_info(self):
        self.refresh_button.configure(state="disabled")
        self.ssid_value.configure(text="Checking...")
        threading.Thread(target=self.info_worker, daemon=True).start()

    def info_worker(self):
        ssid, strength = get_wifi_info(users_os)
        hostname, addresses = get_local_info()
        self.worker_results.put(("info", users_os, hostname, addresses, ssid, strength))

    def start_check(self):
        host = self.host_entry.get().strip()
        if not host or len(host) > 253 or any(character.isspace() for character in host):
            messagebox.showerror("Invalid host", "Enter a valid hostname or IPv4 address.")
            return
        try:
            ports = parse_ports(self.ports_entry.get())
        except ValueError as exc:
            messagebox.showerror("Invalid ports", str(exc))
            return
        self.scan_button.configure(state="disabled")
        self.set_output(f"Checking {host} on {len(ports)} TCP port(s)...\n")
        threading.Thread(target=self.check_worker, args=(host, ports), daemon=True).start()

    def check_worker(self, host, ports):
        results, address = check_tcp_ports(host, ports)
        self.worker_results.put(("check", host, address, results))

    def set_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", text)
        self.output.configure(state="disabled")

    def process_worker_results(self):
        try:
            while True:
                result = self.worker_results.get_nowait()
                if result[0] == "info":
                    _, os_name, hostname, addresses, ssid, strength = result
                    self.os_value.configure(text=os_name)
                    self.host_value.configure(text=hostname)
                    self.ip_value.configure(text=", ".join(addresses) if addresses else "Unavailable")
                    self.ssid_value.configure(text=ssid or "Unavailable / not connected")
                    self.signal_value.configure(text=strength or "Unavailable")
                    self.refresh_button.configure(state="normal")
                elif result[0] == "check":
                    _, host, address, results = result
                    lines = [f"Host: {host}" + (f" ({address})" if address else ""), ""]
                    for port, status in results:
                        lines.append(f"{port}/tcp  {status}" if port is not None else status)
                    lines.append("\nNote: TCP connection results are not a security audit.")
                    self.set_output("\n".join(lines))
                    self.scan_button.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self.process_worker_results)


if __name__ == "__main__":
    NetworkTool().mainloop()
