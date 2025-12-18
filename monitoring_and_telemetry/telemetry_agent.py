import time
import psutil
import requests
import yaml
import numpy as np
import pandas as pd
from collections import deque
from prometheus_client import start_http_server, Gauge
import os

# --- CONFIG LOADER ---
with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

# --- PROMETHEUS METRICS ---
P_CPU = Gauge('sdn_controller_cpu', 'Controller CPU Usage')
P_MEM = Gauge('sdn_controller_mem', 'Controller Memory Usage')
P_PKT_IN = Gauge('sdn_packet_in_rate', 'Packet In Rate')
P_BW = Gauge('sdn_bandwidth', 'Bandwidth Usage')

class TelemetryAgent:
    def __init__(self):
        self.prev_stats = {}
        self.history = deque(maxlen=config['normalization']['window_size'])
        self.controller_url = f"http://{config['controller']['ip']}:{config['controller']['rest_port']}/stats/sh_features"
        
        # Initialize CSV logging
        if config['telemetry']['csv_enabled']:
            self.init_csv()

    def init_csv(self):
        columns = [
            'timestamp',
            # LSTM Features (8)
            'lstm_cpu', 'lstm_mem', 'lstm_rtt', 'lstm_pkt_in', 
            'lstm_pkt_out', 'lstm_flow_mod', 'lstm_flows_sec', 'lstm_bw',
            # Isolation Forest Features (12)
            'if_cpu', 'if_mem', 'if_rtt', 'if_pkt_in', 'if_pkt_out',
            'if_flow_mod', 'if_table_occ', 'if_link_loss', 'if_bw',
            'if_churn', 'if_zscore_avg', 'if_ratio_pkt_flow'
        ]
        
        # FIX: Check if file exists. If yes, skip creating headers (Append Mode).
        if not os.path.exists(config['telemetry']['csv_path']):
            df = pd.DataFrame(columns=columns)
            df.to_csv(config['telemetry']['csv_path'], index=False)
            print("[*] Created new CSV log file.")
        else:
            print("[*] Appending to existing CSV log file.")
    
    def get_system_metrics(self):
        return {
            'cpu': psutil.cpu_percent(interval=None),
            'mem': psutil.virtual_memory().percent
        }

    def get_real_rtt(self):
        """
        Measures RTT to the Controller (Localhost) or Gateway.
        Since Controller is local, we ping localhost or check processing time.
        For Mininet, we can ping the switches' management IP if available, 
        or estimating it via system load.
        Here we use a simple ping to 127.0.0.1 as a baseline for system load latency.
        """
        try:
            # Ping 1 packet, wait max 0.2s
            r = os.popen("ping -c 1 -W 0.2 127.0.0.1").read()
            # Extract time=0.043 ms
            if "time=" in r:
                return float(r.split("time=")[1].split(" ")[0])
        except:
            pass
        return 0.005

    def get_total_bandwidth(self):
        """
        Reads byte counts from all virtual interfaces (s1-ethX, s2-ethX, s3-ethX).
        """
        total_bytes = 0
        try:
            # List all interfaces starting with 's' (s1-eth1, etc in Mininet)
            interfaces = [i for i in os.listdir('/sys/class/net/') if i.startswith('s') and '-eth' in i]
            for iface in interfaces:
                try:
                    with open(f'/sys/class/net/{iface}/statistics/rx_bytes', 'r') as f:
                        total_bytes += int(f.read())
                    with open(f'/sys/class/net/{iface}/statistics/tx_bytes', 'r') as f:
                        total_bytes += int(f.read())
                except:
                    continue
        except:
            pass
        return total_bytes

    def get_network_metrics(self):
        """
        Fetches REAL data from the Ryu Controller API + System Interfaces.
        """
        try:
            response = requests.get(self.controller_url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                
                # Get Real Bandwidth (Bytes)
                current_bytes = self.get_total_bandwidth()
                
                # Get Real RTT
                current_rtt = self.get_real_rtt()
                
                return {
                    'packet_count': data.get('packet_in', 0),
                    'packet_out_count': data.get('packet_out', 0),
                    'flow_mod_count': data.get('flow_mod', 0),
                    'port_status_count': data.get('port_status', 0), # NEW
                    'byte_count': current_bytes, 
                    'flow_count': 0, 
                    'rtt': current_rtt 
                }
        except Exception as e:
            # print(f"[-] Controller Connection Failed: {e}")
            pass
        
        return None

    def calculate_rates(self, current, timestamp):
        if not self.prev_stats:
            self.prev_stats = {'data': current, 'time': timestamp}
            return None

        time_diff = timestamp - self.prev_stats['time']
        if time_diff == 0: return None

        prev = self.prev_stats['data']
        
        # --- CALCULATE RATES (The Core Logic) ---
        pkt_in_rate = (current['packet_count'] - prev.get('packet_count', 0)) / time_diff
        pkt_out_rate = (current['packet_out_count'] - prev.get('packet_out_count', 0)) / time_diff
        flow_mod_rate = (current['flow_mod_count'] - prev.get('flow_mod_count', 0)) / time_diff
        
        # Bandwidth Rate (Bytes per second)
        bw_rate = (current['byte_count'] - prev.get('byte_count', 0)) / time_diff
        
        # Port Status Rate
        port_status_rate = (current.get('port_status_count', 0) - prev.get('port_status_count', 0)) / time_diff
        
        # Link Loss Proxy (If bandwidth drops suddenly or RTT spikes, we infer loss)
        link_loss = 0
        # If port status changes (link down/up) OR RTT is huge
        if port_status_rate > 0 or current['rtt'] > 50: 
            link_loss = 1
        
        metrics = {
            'cpu': current['cpu'],
            'mem': current['mem'],
            'rtt': current['rtt'],
            'pkt_in_rate': max(0, pkt_in_rate),
            'pkt_out_rate': max(0, pkt_out_rate),
            'flow_mod_rate': max(0, flow_mod_rate),
            'flows_sec': 0, 
            'bandwidth': max(0, bw_rate),
            'table_occupancy': 0,
            'link_loss': link_loss,
            'churn_rate': 0
        }

        self.prev_stats = {'data': current, 'time': timestamp}
        self.history.append(metrics)
        return metrics

    def compute_z_score_avg(self, metrics):
        if len(self.history) < 5: return 0
        cpu_hist = [m['cpu'] for m in self.history]
        mean = np.mean(cpu_hist)
        std = np.std(cpu_hist)
        if std == 0: return 0
        return (metrics['cpu'] - mean) / std

    def run(self):
        print(f"[*] Telemetry Agent v1.0 - Listening on {config['telemetry']['prometheus_port']}")
        start_http_server(config['telemetry']['prometheus_port'])

        while True:
            try:
                ts = time.time()
                sys_data = self.get_system_metrics()
                net_data = self.get_network_metrics()
                
                if net_data:
                    raw_data = {**sys_data, **net_data}
                    processed = self.calculate_rates(raw_data, ts)
                    
                    if processed:
                        # Prepare Export Data
                        z_score = self.compute_z_score_avg(processed)
                        ratio_pkt_flow = processed['pkt_in_rate'] / (processed['flow_mod_rate'] + 1e-5)

                        # CSV Row Construction
                        row = {
                            'timestamp': ts,
                            'lstm_cpu': processed['cpu'], 'lstm_mem': processed['mem'],
                            'lstm_rtt': processed['rtt'], 'lstm_pkt_in': processed['pkt_in_rate'],
                            'lstm_pkt_out': processed['pkt_out_rate'], 'lstm_flow_mod': processed['flow_mod_rate'],
                            'lstm_flows_sec': processed['flows_sec'], 'lstm_bw': processed['bandwidth'],
                            'if_cpu': processed['cpu'], 'if_mem': processed['mem'],
                            'if_rtt': processed['rtt'], 'if_pkt_in': processed['pkt_in_rate'],
                            'if_pkt_out': processed['pkt_out_rate'], 'if_flow_mod': processed['flow_mod_rate'],
                            'if_table_occ': processed['table_occupancy'], 'if_link_loss': processed['link_loss'],
                            'if_bw': processed['bandwidth'], 'if_churn': processed['churn_rate'],
                            'if_zscore_avg': z_score, 'if_ratio_pkt_flow': ratio_pkt_flow
                        }

                        # Update Prometheus
                        P_CPU.set(processed['cpu'])
                        P_MEM.set(processed['mem'])
                        P_PKT_IN.set(processed['pkt_in_rate'])
                        
                        # Write CSV
                        if config['telemetry']['csv_enabled']:
                            pd.DataFrame([row]).to_csv(config['telemetry']['csv_path'], mode='a', header=False, index=False)

                        print(f"[Live] CPU: {processed['cpu']}% | Pkt-In Rate: {processed['pkt_in_rate']:.2f}/s | Flow-Mod: {processed['flow_mod_rate']:.2f}")

                time.sleep(config['controller']['poll_interval'])

            except KeyboardInterrupt:
                print("Stopping...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    agent = TelemetryAgent()
    agent.run()
