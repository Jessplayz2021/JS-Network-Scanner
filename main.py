import platform
import subprocess



def detect_os():
    return platform.system()

users_os = detect_os()



def get_wifi_info(users_os):
    ssid = None
    signal_strength = None
    if users_os == "Windows":
        try:
            result_windows = subprocess.run(
                ["netsh", "wlan", "show", "interface"],
                capture_output=True, 
                text=True
            )
            
            if result_windows.returncode != 0:
                print("Sorry this wasn't possible at this time!")
                print(result_windows.stdout.strip())
                return None, None
            
            output = result_windows.stdout
            for line in output.splitlines():
                if line.strip().startswith("SSID "):
                    ssid = line.split(":")[1].strip()
        
                elif line.strip().startswith("Signal"):
                    signal_strength = line.split(":")[1].strip()
                    
        except FileNotFoundError:
            print("Sorry, Command not found!")
            return None, None
        
        
    elif users_os == "Darwin":
        try:
            result_Darwin = subprocess.run(
                ["networksetup", "-getairportnetwork", "en0"],
                capture_output=True,
                text=True
            )
            
            if result_Darwin.returncode != 0:
                print("Sorry this wasn't possible at this time!")
                print(result_Darwin.stdout.strip())
                return None, None
        
            output = result_Darwin.stdout
            for line in output.splitlines():
                if line.strip().startswith("Current Wi-Fi Network:"):
                    ssid = line.split(":",1)[1].strip()
                    
        except FileNotFoundError:
            print("Sorry, Command not found!")
            return None, None

            

    
    elif users_os == "Linux":
        try:
            result_linux = subprocess.run(
                ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL", "device", "wifi", "list"],
                capture_output=True,
                text=True
            )
            
            if result_linux.returncode != 0:
                print("Sorry but this wasn't possible")
                print(result_linux.stderr.strip())
                return None, None
            
            output = result_linux.stdout
            for line in output.splitlines():
                if line.startswith("*:"):
                    ssid = line.split(":")[1].strip()
                    signal_strength = f"{line.split(':')[2].strip()}%"
                    
        except FileNotFoundError:
            print("We dont accept none nmcli people round here, please leave me alone :(")
            return None, None





    return ssid, signal_strength

ssid, signal_strength = get_wifi_info(users_os)

if ssid is not None:
    print(f"Signal strength: {signal_strength}")
    print(f"Connected to Wi-Fi network: {ssid}")
else:
    print("No active Wi-Fi connection detected.")













