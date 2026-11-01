import platform
import subprocess


def detect_os():
    return platform.system()

result = subprocess.run(
    ["netsh", "wlan", "show", "interface"],
     capture_output=True, 
     text=True
)

os = detect_os()

output = result.stdout

for line in output.splitlines():
    if line.strip().startswith("SSID "):
        ssid = line.split(":")[1].strip()
        print(f"Connected to Wi-Fi network: {ssid}")
    elif line.strip().startswith("Signal"):
        signal_strength = line.split(":")[1].strip()
        print(f"Signal strength: {signal_strength}")
        