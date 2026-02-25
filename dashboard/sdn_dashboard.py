import streamlit as st
import re
import pandas as pd

def read_file(filename):
    try:
        with open(filename) as f:
            return f.read()
    except FileNotFoundError:
        return None

def parse_flow_table(flow_table_str):
    entries = []
    for line in flow_table_str.strip().splitlines():
        queue_match = re.search(r"set_queue:(\d+)", line)
        priority_match = re.search(r"priority=(\d+)", line)
        src_match = re.search(r"dl_src=([\w:]+)", line)
        dst_match = re.search(r"dl_dst=([\w:]+)", line)
        in_port_match = re.search(r'in_port="?([\w-]+)"?', line)
        if queue_match and priority_match and src_match and dst_match and in_port_match:
            entries.append({
                "Priority": priority_match.group(1),
                "In Port": in_port_match.group(1),
                "Source": src_match.group(1),
                "Destination": dst_match.group(1),
                "QoS Queue": queue_match.group(1)
            })
    return entries

# Page title and layout
st.set_page_config(page_title="SDN IoT Gateway", layout="wide")
st.title("SDN IoT Gateway")

# Performance Metrics Section
st.header("Performance Metrics")

# Read iperf and ping output from files
iperf_text = read_file("iperf.txt")
ping_text = read_file("ping.txt")

# Parse throughput from iperf output
throughput_line = None
if iperf_text:
    for line in iperf_text.splitlines():
        if 'Mbits/sec' in line:
            throughput_line = line.strip()
            break

# Parse packet loss and latency via regex on ping line
packet_loss_val = None
latency_val = None
if ping_text:
    for line in ping_text.splitlines():
        if "Packet Loss =" in line:
            packet_loss_line = line.strip()
            loss_match = re.search(r"Packet Loss = ([\d\.]+)%", packet_loss_line)
            latency_match = re.search(r"Average Latency = ([\d\.]+) ms", packet_loss_line)
            if loss_match:
                packet_loss_val = loss_match.group(1)
            if latency_match:
                latency_val = latency_match.group(1)

# Display Throughput
if throughput_line:
    try:
        throughput_val = throughput_line.split()[-2]
        st.metric("Throughput (Mbits/sec)", throughput_val)
    except Exception:
        st.info("Throughput data format issue")
else:
    st.info("Throughput data not available yet.")

# Display Packet Loss
if packet_loss_val is not None:
    st.metric("Packet Loss (%)", packet_loss_val)
else:
    st.info("Packet loss data not available yet.")

# Display Average Latency
if latency_val is not None:
    st.metric("Average Latency (ms)", latency_val)
else:
    st.info("Latency data not available yet.")

# Flow Table summary section
st.header("Flow Table Summary")
for switch in ["s1", "s2", "s3"]:
    st.subheader(f"Switch {switch.upper()}")
    flow_text = read_file(f"flows_{switch}.txt")
    if flow_text:
        flow_entries = parse_flow_table(flow_text)
        if flow_entries:
            df = pd.DataFrame(flow_entries)
            st.table(df)
            st.caption(f"Total parsed flows: {len(flow_entries)}")
        else:
            if switch == "s2":
                st.info("Switch s2 currently operates mostly with default flow rules; no detailed flow entries detected.")
            else:
                st.info(f"No detailed flow entries found for switch {switch}.")
    else:
        st.info(f"Flow data for switch {switch} is not available yet.")

