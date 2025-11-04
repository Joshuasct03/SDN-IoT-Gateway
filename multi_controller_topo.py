import re
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel

class MultiControllerTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')

        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(h3, s3)
        self.addLink(s1, s2)
        self.addLink(s2, s3)

def parse_iperf_output(output):
    bandwidth_match = re.search(r'(\d+\.?\d*)\sMbits/sec', output)
    return float(bandwidth_match.group(1)) if bandwidth_match else None

def run_ping(net, src, dst, count=5):
    print(f"Running ping test from {src} to {dst}...")
    ping_result = net.get(src).cmd(f'ping -c {count} {net.get(dst).IP()}')
    loss_match = re.search(r'(\d+)% packet loss', ping_result)
    latency_match = re.search(r'rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms', ping_result)
    loss = int(loss_match.group(1)) if loss_match else None
    latency_avg = float(latency_match.group(2)) if latency_match else None
    return loss, latency_avg

def print_traffic_classification(flow_table_str):
    print("\n=== Traffic Classification and QoS Queue Assignments ===")
    for line in flow_table_str.splitlines():
        if "actions=" in line:
            queue_match = re.search(r"set_queue:(\d+)", line)
            priority_match = re.search(r"priority=(\d+)", line)
            src_match = re.search(r"dl_src=([\w:]+)", line)
            dst_match = re.search(r"dl_dst=([\w:]+)", line)
            in_port_match = re.search(r"in_port=\"?([\w-]+)\"?", line)
            if queue_match and priority_match and src_match and dst_match and in_port_match:
                print(f"Flow with priority {priority_match.group(1)} on port {in_port_match.group(1)}")
                print(f"  Source MAC: {src_match.group(1)}, Destination MAC: {dst_match.group(1)}")
                print(f"  Assigned to QoS Queue: {queue_match.group(1)}\n")

if __name__ == '__main__':
    setLogLevel('info')

    net = Mininet(topo=MultiControllerTopo(), controller=None, switch=OVSSwitch)
    c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, ip='127.0.0.1', port=6634)

    c1.start()
    c2.start()
    net.start()

    net.get('s1').start([c1])
    net.get('s2').start([c2])
    net.get('s3').start([c1])

    print("Starting iperf server on h2...")
    net.get('h2').cmd('iperf -s &')

    print("Starting iperf client on h1...")
    iperf_output = net.get('h1').cmd('iperf -c %s -t 10' % net.get('h2').IP())
    print("Raw iperf output:\n", iperf_output)

    bandwidth = parse_iperf_output(iperf_output)
    if bandwidth:
        print(f"Measured Throughput: {bandwidth:.2f} Mbits/sec")
        if bandwidth > 30:
            print("Throughput is strong and meets design expectations for efficient data transfer.")
        else:
            print("Throughput is lower than expected; this might indicate network congestion or inefficiencies.")

    net.get('h2').cmd('pkill iperf')

    # Start iperf server on h1 to generate flows on s2
    print("Starting iperf server on h1...")
    net.get('h1').cmd('iperf -s &')

    print("Starting iperf client on h2...")
    iperf_output_h2_to_h1 = net.get('h2').cmd('iperf -c %s -t 10' % net.get('h1').IP())
    print("Raw iperf output from h2 to h1:\n", iperf_output_h2_to_h1)

    net.get('h1').cmd('pkill iperf')

    loss, latency = run_ping(net, 'h1', 'h3')
    if loss is not None and latency is not None:
        print(f"Ping Test Results from h1 to h3: Packet Loss = {loss}%, Average Latency = {latency} ms")
        if loss == 0:
            print("Zero packet loss indicates very reliable network connectivity.")
        else:
            print("Packet loss detected; reliability can be improved.")

    # Dump and parse flow tables for s1, s2, s3
    for sw in ['s1', 's2', 's3']:
        flows = net.get(sw).dpctl('dump-flows -O OpenFlow13')
        with open(f'flows_{sw}.txt', 'w') as f:
            f.write(flows)
        print(f"Flow table on {sw}:")
        print(flows)
        print_traffic_classification(flows)
        print(f"Dumped flows for {sw} to flows_{sw}.txt\n")

    CLI(net)
    net.stop()
