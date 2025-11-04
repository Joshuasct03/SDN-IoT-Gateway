from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet


class DecisionController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # Use OpenFlow 1.3

    def __init__(self, *args, **kwargs):
        super(DecisionController, self).__init__(*args, **kwargs)
        self.controller_loads = {}  # dpid -> load
        self.threshold = 1000000  # initial migration threshold
        self.datapaths = {}
        self.switch_to_controller = {}  # switch dpid to controller dpid
        self.switch_priority = {}  # switch dpid to priority: HIGH/MEDIUM/LOW
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        dpid = datapath.id
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dpid] = datapath
            self.logger.info("Registered datapath %s", dpid)
            self.switch_to_controller[dpid] = dpid  # Initially own controller
            self.switch_priority[dpid] = 'LOW'  # Default priority
        elif ev.state == DEAD_DISPATCHER:
            if dpid in self.datapaths:
                self.logger.info("Unregistered datapath %s", dpid)
                self.datapaths.pop(dpid)
            if dpid in self.switch_to_controller:
                self.switch_to_controller.pop(dpid)
            if dpid in self.switch_priority:
                self.switch_priority.pop(dpid)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, MAIN_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # install table-miss flow entry to send unmatched packets to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.logger.info(f"Switch {datapath.id}: Installed table-miss flow")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == 0x88cc:  # Ignore LLDP packets
            return

        in_port = msg.match['in_port']

        # Example: Flood all packets (replace with real logic)
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        self.logger.debug(f"Flooded packet on switch {datapath.id}")

    def _monitor(self):
        while True:
            self.collect_loads()
            self.adjust_threshold()
            self.check_migration()
            hub.sleep(10)

    def collect_loads(self):
        for dp in self.datapaths.values():
            self.request_stats(dp)

    def request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply)
    def flow_stats_reply_handler(self, ev):
        dpid = ev.msg.datapath.id
        total_load = 0
        for stat in ev.msg.body:
            weight = 1
            total_load += stat.packet_count * weight
        self.controller_loads[dpid] = total_load
        self.logger.info("Controller load - DPID %s: %d", dpid, total_load)

    def adjust_threshold(self):
        if len(self.controller_loads) == 0:
            return
        avg_load = sum(self.controller_loads.values()) / len(self.controller_loads)
        new_threshold = int(avg_load * 1.5)
        if new_threshold != self.threshold:
            self.logger.info("Adjusting threshold from %d to %d",
                             self.threshold, new_threshold)
            self.threshold = new_threshold

    def check_migration(self):
        for dpid, load in self.controller_loads.items():
            if load > self.threshold:
                self.logger.info(f"Overload detected on controller {dpid}, migrating switches...")
                self.migrate_switches(dpid)

    def migrate_switches(self, overloaded_dpid):
        self.logger.info(f"Performing migration from overloaded controller {overloaded_dpid}")

        switches = [sw for sw, ctrl in self.switch_to_controller.items() if ctrl == overloaded_dpid]
        sorted_controllers = sorted(((d, l) for d, l in self.controller_loads.items() if d != overloaded_dpid),
                                    key=lambda x: x[1])
        if not sorted_controllers:
            self.logger.info("No other controllers to migrate to")
            return
        target_dpid = sorted_controllers[0][0]

        low_priority_switches = [sw for sw in switches if self.switch_priority.get(sw, 'LOW') == 'LOW']
        if not low_priority_switches:
            self.logger.info("No low priority switches available for migration")
            return

        for sw in low_priority_switches:
            self.logger.info(f"Migrating switch {sw} from controller {overloaded_dpid} to {target_dpid}")
            self.switch_to_controller[sw] = target_dpid
            # Notify external script or orchestration system to perform actual migration
            break  # migrate one at a time


if __name__ == "__main__":
    from ryu.cmd import manager

    manager.main()