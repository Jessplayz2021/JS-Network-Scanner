import platform
import subprocess


def detect_os():
    return platform.system()





def get_wifi_info():
    ssid = None
    signal_strength = None
    result = subprocess.run(
        ["netsh", "wlan", "show", "interface"],
         capture_output=True, 
         text=True
    )
    output = result.stdout
    for line in output.splitlines():
        if line.strip().startswith("SSID "):
            ssid = line.split(":")[1].strip()
        
        elif line.strip().startswith("Signal"):
            signal_strength = line.split(":")[1].strip()
    return ssid, signal_strength

ssid, signal_strength = get_wifi_info()

if ssid is not None:
    print(f"Signal strength: {signal_strength}")
    print(f"Connected to Wi-Fi network: {ssid}")
else:
    print("No active Wi-Fi connection detected.")


os = detect_os()








