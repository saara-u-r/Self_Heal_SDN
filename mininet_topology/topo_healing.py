from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

class SelfHealTopo(Topo):
    r"""
    Triangle Topology for Self-Healing:
    
       h1 --- s1 --------- s2 --- h2
               \         /
                \       /
                 \     /
                  -- s3 -- h3
    
    If link (s1-s2) fails, traffic should reroute via s3.
    """
    def build(self):
        # Add Switches
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')

        # Add Hosts
        h1 = self.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
        h3 = self.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')

        # Add Links (with bandwidth limits to test congestion features)
        # Main Path
        self.addLink(s1, s2, bw=10, delay='5ms', loss=0)
        
        # Redundant Paths (The "Healing" paths)
        self.addLink(s1, s3, bw=10, delay='10ms', loss=0)
        self.addLink(s3, s2, bw=10, delay='10ms', loss=0)

        # Host Links
        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(h3, s3)

def run_topology():
    topo = SelfHealTopo()
    # Connect to Remote Controller (Ryu)
    net = Mininet(topo=topo, 
                  controller=RemoteController('c0', ip='127.0.0.1', port=6633), 
                  switch=OVSKernelSwitch,
                  link=TCLink)
    
    net.start()
    
    # --- FIX: ENABLE STP TO PREVENT LOOPS ---
    print("[*] Enabling Spanning Tree Protocol (STP) on switches...")
    for sw in net.switches:
        sw.cmd('ovs-vsctl set Bridge', sw.name, 'stp_enable=true')
    
    print("[*] Waiting 45 seconds for STP to converge (Blocking loops)...")
    import time
    time.sleep(45) 
    # ----------------------------------------

    print("[+] Topology Started. Loop blocked. Ready for traffic.")
    print("[*] Use 'link s1 s2 down' in CLI to simulate failure.")
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_topology()
