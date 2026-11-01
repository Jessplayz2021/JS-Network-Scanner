import platform
import subprocess



def detect_os():
    return platform.system()

users_os = detect_os()



def get_wifi_info(users_os):
    ssid = None
    signal_strength = None
    if users_os == "Windows":

        result_windows = subprocess.run(
            ["netsh", "wlan", "show", "interface"],
            capture_output=True, 
            text=True
        )
        output = result_windows.stdout
        for line in output.splitlines():
            if line.strip().startswith("SSID "):
                ssid = line.split(":")[1].strip()
        
            elif line.strip().startswith("Signal"):
                signal_strength = line.split(":")[1].strip()
    elif users_os == "Darwin":
        return None, None

    
    elif users_os == "Linux":
        result_linux = subprocess.run(
            ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL", "device", "wifi", "list"],
            capture_output=True,
            text=True
        )
        output = result_linux.stdout




    return ssid, signal_strength

ssid, signal_strength = get_wifi_info(users_os)

if ssid is not None:
    print(f"Signal strength: {signal_strength}")
    print(f"Connected to Wi-Fi network: {ssid}")
else:
    print("No active Wi-Fi connection detected.")













