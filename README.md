# SDN-Based QoS Traffic Classification & Load Balancing for IoT Gateway

## Overview

This project implements a **Software-Defined Networking (SDN) based IoT gateway** that performs real-time traffic classification and adaptive controller load balancing to maintain Quality of Service (QoS) in dynamic network environments.

The system separates the control plane using multiple SDN controllers and dynamically redistributes network load to prevent controller overload while prioritizing critical IoT traffic.

The implementation is developed and evaluated using **Mininet**, **Ryu SDN Controller**, and **Open vSwitch (OVS)** with a monitoring dashboard for real-time performance visualization.

---

## Problem Statement

IoT gateways handle heterogeneous traffic with different latency and reliability requirements.
Traditional networks use static configurations, which can lead to:

* Controller overload
* Increased flow setup delay
* QoS degradation for critical traffic

This project addresses these challenges using SDN programmability and adaptive decision logic.

---

## Key Features

* Rule-based traffic classification using protocol and port information
* QoS-aware queue assignment (High / Medium / Low priority)
* Dual-controller SDN architecture
* Adaptive threshold-based controller load balancing
* Automatic switch migration between controllers
* Real-time monitoring dashboard using Streamlit
* Automated experiment setup using scripts

---

## System Architecture

![Architecture](images/architecture.png)

---

## Technologies Used

* Python 3.9+
* Ryu SDN Controller
* Mininet Network Emulator
* Open vSwitch (OVS)
* OpenFlow 1.3
* Streamlit Dashboard

---

## Project Structure

```
SDN-IoT-Gateway/
│
├── controllers/        # SDN controller applications
├── topology/           # Mininet topology definition
├── dashboard/          # Streamlit monitoring UI
├── scripts/            # Automation scripts
├── images/             # Architecture & result screenshots
├── docs/               # Project documentation
├── requirements.txt
└── README.md
```

---

## How It Works

1. Traffic arrives at OpenFlow switches in the Mininet topology.
2. The **Work Controller** classifies packets based on protocol and assigns QoS queues.
3. Controller load is continuously monitored using telemetry.
4. The **Decision Controller** detects overload conditions.
5. Switches are migrated dynamically to balance controller load.
6. Performance metrics are visualized through the dashboard.

---

## Quick Demo (Recommended)

### 1️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Configure QoS queues

```bash
bash scripts/setup_queues.sh
```

### 3️⃣ Start controllers

```bash
ryu-manager controllers/decision_controller.py
ryu-manager controllers/enhanced_traffic_controller.py
```

### 4️⃣ Run Mininet topology

```bash
sudo bash scripts/run_demo.sh
```

### 5️⃣ Launch dashboard

```bash
streamlit run dashboard/sdn_dashboard.py
```

---

## Results

Experimental evaluation in Mininet showed:

* Improved throughput under controller load conditions
* Reduced network latency through adaptive migration
* Stable QoS prioritization for critical flows

Example dashboard output:

![Results](images/results.png)

---

## My Contributions

* Implemented SDN traffic classification and QoS queue assignment
* Developed adaptive controller load monitoring and migration logic
* Integrated Streamlit dashboard for performance visualization
* Performed Mininet experimentation and testing

---

## Academic Context

This project was developed as a **B.Tech Minor Project** in Electronics and Communication Engineering (Networking Minor).

The implementation focuses on demonstrating SDN-based adaptive traffic management concepts in an emulated IoT gateway environment.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgment

Developed as a team academic project under faculty guidance at
Sree Chitra Thirunal College of Engineering, Thiruvananthapuram.
