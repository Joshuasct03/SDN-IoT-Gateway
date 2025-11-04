#!/bin/bash

# Clean stale Mininet states (runs as sudo)
sudo mn -c

# Set bridges to OpenFlow13 and restart OVS service
sudo ovs-vsctl set bridge s1 protocols=OpenFlow13
sudo ovs-vsctl set bridge s2 protocols=OpenFlow13
sudo ovs-vsctl set bridge s3 protocols=OpenFlow13
sudo systemctl restart openvswitch-switch
sleep 3

# Activate Python virtual environment for Ryu
source /home/miniproject/minor_project_main/ryu-py39-venv/bin/activate

# Start controllers (run detached, do NOT kill from here)
ryu-manager --verbose --ofp-tcp-listen-port 6633 enhanced_traffic_controller.py > enhanced_traffic_controller.log 2>&1 &
pid1=$!
ryu-manager --verbose --ofp-tcp-listen-port 6634 decision_controller.py > decision_controller.log 2>&1 &
pid2=$!

# Wait for controllers to start
sleep 10

# Run Mininet topology and tests (do NOT sudo python3 here as entire script runs with sudo)
python3 multi_controller_topo.py -c "pingall; exit" | tee demo_output.log

# Parse iperf and ping sections from demo_output.log
grep -A 10 "Raw iperf output:" demo_output.log > iperf.txt
grep -A 5 "Ping Test Results" demo_output.log > ping.txt

# Flow dumps now handled inside python script to avoid ovs-ofctl errors
# So remove external ovs-ofctl flow dumps from this script

# Optional: kill controller processes outside this script manually, or leave running
# kill $pid1
# kill $pid2

# Deactivate virtual environment
deactivate

# Run Streamlit dashboard via full path inside virtualenv
/home/miniproject/minor_project_main/ryu-py39-venv/bin/streamlit run sdn_dashboard.py

echo "Demo complete. Check enhanced_traffic_controller.log, decision_controller.log, demo_output.log, and streamlit dashboard for details."
