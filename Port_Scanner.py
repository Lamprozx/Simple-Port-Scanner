import socket
import threading
import time
import sys
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

# ============================================
# Config
# ============================================
TARGET = "target.com" 
TIMEOUT = 2
MAX_THREADS = 100
COMMON_PORTS = [
    # Web Ports
    80, 443, 8080, 8443, 8000, 8008, 3000, 5000,
    
    # Security/Admin
    22, 21, 23, 25, 53, 110, 143, 445, 3389,
    
    # Database
    3306, 5432, 27017, 6379, 1521,
    
    # Special Services
    8888, 9000, 9001, 9200, 5601, 11211,
    
    # Development
    3001, 4200, 5001, 6000, 7000, 8001,
    
    # Cloud/Container
    2375, 2376, 2377, 7946, 4789, 10250,
]


ALL_PORTS = range(1, 65536)

# ============================================
# PORT SCANNER CLASS
# ============================================
class PortScanner:
    def __init__(self, target, timeout=2):
        self.target = target
        self.timeout = timeout
        self.open_ports = []
        self.banner_results = {}
        
        # Resolve IP
        try:
            self.ip = socket.gethostbyname(target)
            print(f"[+] Target: {target} -> {self.ip}")
        except socket.gaierror:
            print(f"[-] Could not resolve {target}")
            sys.exit(1)
    
    def scan_port(self, port):
        """Scan single port"""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            # Try to connect
            result = sock.connect_ex((self.ip, port))
            
            if result == 0:
                print(f"[🔥] PORT {port} OPEN")
                self.open_ports.append(port)
                
                # Try to get banner
                try:
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                    banner = sock.recv(1024).decode('utf-8', errors='ignore')
                    if banner:
                        self.banner_results[port] = banner[:200]
                        print(f"[📝] Banner: {banner[:100]}...")
                except:
                    pass
                
                sock.close()
                return True
            else:
                sock.close()
                return False
                
        except Exception as e:
            return False
    
    def stealth_scan(self, port):
        """Stealth SYN scan simulation"""
        try:
            # Raw socket for SYN scan (root needed)
            import struct
            
            # Create raw socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            
            # Build TCP SYN packet
            source_port = 12345
            seq = 0
            ack_seq = 0
            doff = 5
            
            # TCP flags
            tcp_flags = 0b00000010  # SYN
            
            tcp_header = struct.pack('!HHLLBBHHH',
                source_port, port,    # Source, Dest port
                seq,                  # Sequence number
                ack_seq,              # Acknowledgement number
                (doff << 4),          # Data offset
                tcp_flags,            # Flags
                8192,                 # Window
                0,                    # Checksum (0 for now)
                0                     # Urgent pointer
            )
            
            # Send packet
            sock.sendto(tcp_header, (self.ip, 0))
            
            # Listen for response
            sock.settimeout(1)
            try:
                response = sock.recv(1024)
                # Check if SYN-ACK received
                if response and len(response) > 0:
                    print(f"[⚡] PORT {port} OPEN (Stealth SYN)")
                    return True
            except socket.timeout:
                pass
                
            sock.close()
            
        except PermissionError:
            print("[!] Need root for SYN scan, falling back to connect scan")
            return self.scan_port(port)
        except:
            return False
    
    def service_detection(self, port):
        """Detect service running on port"""
        services = {
            80: "HTTP",
            443: "HTTPS",
            22: "SSH",
            21: "FTP",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            3306: "MySQL",
            5432: "PostgreSQL",
            27017: "MongoDB",
            6379: "Redis",
            9200: "Elasticsearch",
            5601: "Kibana",
            11211: "Memcached",
            3389: "RDP",
            5900: "VNC",
            8080: "HTTP-Proxy",
            8443: "HTTPS-Alt",
            8888: "Sun/JDBC",
            9000: "PHP-FPM",
        }
        
        return services.get(port, "Unknown")
    
    def scan_range(self, ports, use_stealth=False, max_threads=100):
        """Scan range of ports with threading"""
        print(f"[*] Scanning {len(ports)} ports on {self.target}")
        print(f"[*] Threads: {max_threads}, Timeout: {self.timeout}s")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            if use_stealth:
                results = list(executor.map(self.stealth_scan, ports))
            else:
                results = list(executor.map(self.scan_port, ports))
        
        elapsed = time.time() - start_time
        print(f"\n[+] Scan completed in {elapsed:.2f} seconds")
        print(f"[+] Found {len(self.open_ports)} open ports")
        
        return self.open_ports
    
    def full_scan(self):
        """Full 1-65535 port scan"""
        print("[⚡] INITIATING FULL PORT BRUTEFORCE ⚡")
        print("[!] This will take a while (1-65535)")
        
        # Scan in batches
        batch_size = 1000
        all_ports = list(ALL_PORTS)
        
        for i in range(0, len(all_ports), batch_size):
            batch = all_ports[i:i + batch_size]
            print(f"[*] Scanning batch {i//batch_size + 1}/66: ports {batch[0]}-{batch[-1]}")
            
            self.scan_range(batch, max_threads=50)
            time.sleep(1)  # Avoid detection
        
        return self.open_ports
    
    def generate_report(self):
        """Generate scan report"""
        print("\n" + "="*60)
        print("📊 PORT SCAN REPORT")
        print("="*60)
        
        print(f"Target: {self.target} ({self.ip})")
        print(f"Open Ports: {len(self.open_ports)}")
        print(f"Scan Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "-"*60)
        
        if self.open_ports:
            print("PORT\tSTATE\tSERVICE\t\tBANNER")
            print("-"*60)
            
            for port in sorted(self.open_ports):
                service = self.service_detection(port)
                banner = self.banner_results.get(port, "N/A")
                print(f"{port}\tOPEN\t{service}\t\t{banner[:30]}...")
        
        # Save to file
        filename = f"port_scan_{self.target}_{int(time.time())}.txt"
        with open(filename, 'w') as f:
            f.write(f"Port Scan Report - {self.target}\n")
            f.write(f"IP: {self.ip}\n")
            f.write(f"Scan Time: {time.ctime()}\n")
            f.write(f"Open Ports: {len(self.open_ports)}\n\n")
            
            for port in sorted(self.open_ports):
                service = self.service_detection(port)
                banner = self.banner_results.get(port, "")
                f.write(f"Port {port} ({service}):\n")
                f.write(f"  Banner: {banner[:500]}\n")
                f.write("-"*40 + "\n")
        
        print(f"\n[💾] Report saved to: {filename}")

# ============================================
# WEB-SPECIFIC PORT SCANNING
# ============================================
def web_port_bruteforce(target):
    print("\n" + "="*60)
    print("🌐 WEB PORT BRUTEFORCE")
    print("="*60)
    
    web_ports = [
        # HTTP/HTTPS
        80, 443, 8080, 8443, 8000, 8008, 8081, 8888,
        8088, 8880, 8082, 8083, 8084, 8085, 8086,
        
        # Development
        3000, 3001, 4200, 5000, 5001, 6000, 7000, 9000,
        
        # Admin Panels
        2082, 2083, 2086, 2087, 2095, 2096,
        8089, 8447, 8889, 9001, 9002,
        
        # Special
        10000, 1080, 3128, 8001, 8010, 8080,
        8181, 8282, 8383, 8484, 8585,
        
        # Cloud/New Tech
        1024, 1025, 1026, 1027, 1028, 1029,
        30000, 30001, 30002, 30003,
    ]
    
    print(f"[*] Bruteforcing {len(web_ports)} web ports on {target}")
    
    scanner = PortScanner(target)
    open_ports = scanner.scan_range(web_ports)
    
    print("\n[+] WEB PORT ANALYSIS:")
    for port in sorted(open_ports):
        if port in [80, 443, 8080, 8443, 8000, 3000]:
            print(f"[🌐] Critical Web Port: {port}")
            
            # Try to access with curl
            import subprocess
            try:
                if port == 443:
                    url = f"https://{target}:{port}"
                else:
                    url = f"http://{target}:{port}"
                
                result = subprocess.run(
                    ['curl', '-s', '-I', '--max-time', '5', url],
                    capture_output=True, text=True
                )
                
                if 'HTTP' in result.stdout:
                    print(f"   Response: {result.stdout.split('\\n')[0]}")
            except:
                pass
    
    return open_ports

# ============================================
# MAIN EXECUTION
# ============================================
def main():
    print("🔥 PORT SCANNER 🔥")
    print("[!] For authorized testing only!\n")
    
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <target> [scan_type]")
        print("\nScan Types:")
        print("  quick    - Scan common ports (default)")
        print("  web      - Bruteforce web ports")
        print("  full     - Full 1-65535 scan")
        print("  stealth  - Stealth SYN scan")
        print("\nExample: python3 port_scanner.py example.com web")
        sys.exit(1)
    
    target = sys.argv[1]
    scan_type = sys.argv[2] if len(sys.argv) > 2 else "quick"
    
    scanner = PortScanner(target)
    
    if scan_type == "quick":
        print("[*] Quick scan (common ports)")
        scanner.scan_range(COMMON_PORTS)
        
    elif scan_type == "web":
        web_port_bruteforce(target)
        
    elif scan_type == "full":
        confirm = input("[!] Full scan takes time and is noisy. Continue? (y/n): ")
        if confirm.lower() == 'y':
            scanner.full_scan()
            
    elif scan_type == "stealth":
        print("[*] Stealth SYN scan (requires root)")
        scanner.scan_range(COMMON_PORTS[:50], use_stealth=True)
        
    else:
        print(f"[-] Unknown scan type: {scan_type}")
        sys.exit(1)
    
    # Generate report
    if scanner.open_ports:
        scanner.generate_report()
        
       
        print("[-] No open ports found")

if __name__ == "__main__":
    main()