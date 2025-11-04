from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp, icmp
from ryu.lib import hub
import time

class EnhancedTrafficController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    STATS_PERIOD = 10  # seconds

    def __init__(self, *args, **kwargs):
        super(EnhancedTrafficController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.load_stats = {}  # holds weighted load per switch
        self.flow_priorities = {}  # key: (dpid, src, dst, in_port), value: priority
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.logger.info(f"Switch {datapath.id}: Installed table-miss flow")

    def priority_value(self, priority_str):
        priorities = {'HIGH': 30, 'MEDIUM': 20, 'LOW': 10}
        return priorities.get(priority_str, 10)

    def add_flow(self, datapath, priority, match, actions,
                 buffer_id=None, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        if isinstance(priority, str):
            priority_val = self.priority_value(priority)
        else:
            priority_val = priority

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        try:
            if buffer_id:
                mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                        priority=priority_val, match=match,
                                        instructions=inst, idle_timeout=idle_timeout,
                                        hard_timeout=hard_timeout)
            else:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority_val,
                                        match=match, instructions=inst,
                                        idle_timeout=idle_timeout, hard_timeout=hard_timeout)
            datapath.send_msg(mod)
            dpid = datapath.id
            src = match.get('eth_src')
            dst = match.get('eth_dst')
            in_port = match.get('in_port')
            flow_key = (dpid, src, dst, in_port)
            self.flow_priorities[flow_key] = priority_val
            self.logger.info(f"Flow added on DPID {dpid} with priority {priority_val}")
        except Exception as e:
            self.logger.error(f"Failed to add flow: {e}")

    def classify_priority(self, pkt):
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return 'LOW'
        proto = ip_pkt.proto
        if proto == 6:  # TCP
            tcp_pkt = pkt.get_protocol(tcp.tcp)
            if tcp_pkt and tcp_pkt.dst_port in [80, 443]:
                return 'HIGH'
            else:
                return 'MEDIUM'
        elif proto == 17:  # UDP
            udp_pkt = pkt.get_protocol(udp.udp)
            if udp_pkt and udp_pkt.dst_port == 53:
                return 'HIGH'
            else:
                return 'LOW'
        elif proto == 1:  # ICMP
            return 'MEDIUM'
        else:
            return 'LOW'

    def priority_to_queue(self, priority):
        if priority == 'HIGH':
            return 1
        elif priority == 'MEDIUM':
            return 2
        else:
            return 3

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        # Log datapath ID to confirm packet_in from all switches including s2
        self.logger.info(f"Packet_in received from DPID {dpid}")

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == 0x88cc:
            return
        dst = eth.dst
        src = eth.src

        # Learn MAC address per datapath
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)

        priority = self.classify_priority(pkt)
        queue_id = self.priority_to_queue(priority)

        self.logger.info(f"DPID {dpid} Packet from {src} to {dst} Priority={priority} Queue={queue_id}")

        actions = [parser.OFPActionSetQueue(queue_id),
                   parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, priority, match, actions,
                          buffer_id=msg.buffer_id, idle_timeout=30)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info("Register datapath: %s", datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == CONFIG_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self.request_stats(dp)
            hub.sleep(self.STATS_PERIOD)

    def request_stats(self, datapath):
        self.logger.debug("Requesting stats from datapath %s", datapath.id)
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id
        total_load = 0
        for stat in ev.msg.body:
            src = stat.match.get('eth_src')
            dst = stat.match.get('eth_dst')
            in_port = stat.match.get('in_port')
            flow_key = (dpid, src, dst, in_port)
            priority = self.flow_priorities.get(flow_key, 10)
            weight = 3 if priority >= 30 else 2 if priority >= 20 else 1
            load = stat.packet_count * weight
            total_load += load
        self.load_stats[dpid] = total_load
        self.logger.info(f"DPID {dpid} Load: {total_load}")


if __name__ == "__main__":
    from ryu.cmd import manager
    manager.main()
