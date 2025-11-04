# SDN-based-QoS-Traffic-Classification-Load-Balancing-for-IoT-Gateway
This project implements a real-time, QoS-aware traffic classification and load balancing system for IoT gateways using SDN principles. It leverages Mininet for emulation, Ryu controllers for dynamic traffic management, and OpenFlow-enabled switches to prioritize critical IoT data, ensuring scalable and secure network operations.
SDN-based QoS Traffic Classification & Load Balancing for IoT Gateway

Project Overview:
This project implements a Software-Defined Networking (SDN) architecture to achieve real-time traffic classification and QoS-aware load balancing in IoT gateway environments. It uses Mininet for network emulation, Ryu as the SDN controller framework, and Open vSwitch (OVS) for programmable switches.

Features:
- Rule-based traffic classification based on protocol and port numbers.
- Dynamic load monitoring with adaptive threshold-based controller load balancing.
- Seamless switch migration between controllers to prevent overload.
- Streamlit dashboard for real-time visualization of controller loads and performance.

Technologies Used:
- Python 3.9+
- Ryu SDN Controller
- Mininet Network Simulator
- Open vSwitch
- Streamlit UI

Setup and Usage:

Installation:
1. Clone this repository
2. Install dependencies:
pip install -r requirements.txt

3. Configure queues using `setup_queues.sh`
4. Launch Ryu controllers:
ryu-manager decision_controller.py
ryu-manager enhanced_traffic_controller.py

5. Setup and run the network with:
sudo ./run_demo.sh

6. Start Streamlit dashboard:
streamlit run sdn_dashboard.py


Project Structure:
- `decision_controller.py`: Implements load balancing and migration logic.
- `enhanced_traffic_controller.py`: Traffic classifier and QoS enforcer.
- `multi_controller_topo.py`: Defines Mininet topology.
- `run_demo.sh`: Automates controller and network launching.
- `setup_queues.sh`: QoS queue configuration for OVS.
- `sdn_dashboard.py`: Streamlit dashboard UI.

License:
This project is licensed under the MIT License.

Acknowledgments:
Thanks to mentors and project collaborators for their guidance and support.
