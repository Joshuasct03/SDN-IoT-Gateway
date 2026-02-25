#!/bin/bash

# Run all QoS and queue configuration commands as a single sudo session for efficiency
sudo bash -c '
for sw in s1 s2 s3; do
  for port in $(ovs-vsctl list-ports $sw); do
    ovs-vsctl -- set port $port qos=@newqos -- \
    --id=@newqos create qos type=linux-htb other-config:max-rate=100000000 queues:1=@q1 queues:2=@q2 queues:3=@q3 -- \
    --id=@q1 create queue other-config:min-rate=50000000 other-config:max-rate=100000000 -- \
    --id=@q2 create queue other-config:min-rate=20000000 other-config:max-rate=50000000 -- \
    --id=@q3 create queue other-config:min-rate=10000000 other-config:max-rate=20000000
  done
done
'
