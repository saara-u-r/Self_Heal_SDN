from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import json
import time

# API Configuration
SH_CONTROLLER_INSTANCE_NAME = 'sh_controller_api'
URL = '/stats/sh_features'

class SelfHealingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SelfHealingController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(SelfHealingControllerController, 
                      {SH_CONTROLLER_INSTANCE_NAME: self})
        
        # Internal Counters for ML Features
        self.packet_in_count = 0
        self.packet_out_count = 0
        self.flow_mod_count = 0
        self.port_status_count = 0  # FEATURE: Link Flaps / Status Changes
        self.start_time = time.time()
        
        # Link map for topology discovery
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install Table-Miss Flow Entry (Default: Send to Controller)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        # Triggered when a link goes DOWN or UP
        self.port_status_count += 1
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        
        ofproto = msg.datapath.ofproto
        if reason == ofproto.OFPPR_ADD:
            self.logger.info("Port added %s", port_no)
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info("Port deleted %s", port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info("Port modified %s", port_no)
        
        # CRITICAL FIX: Invalidate MAC table for this switch so we re-learn paths
        # This handles the "No route" / broken connectivity after Link Flap
        if msg.datapath.id in self.mac_to_port:
            self.logger.info("Clearing MAC table for dpid %s due to port status change", msg.datapath.id)
            del self.mac_to_port[msg.datapath.id]
            
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)
        self.flow_mod_count += 1  # FEATURE: Increment Flow Mod Count

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        self.packet_in_count += 1  # FEATURE: Increment Packet In Count
        
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        # Simple Learning Switch Logic
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install a flow to avoid packet-in next time
        #if out_port != ofproto.OFPP_FLOOD:
        #   match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
        #    self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        self.packet_out_count += 1 # FEATURE: Increment Packet Out Count

class SelfHealingControllerController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SelfHealingControllerController, self).__init__(req, link, data, **config)
        self.sh_app = data[SH_CONTROLLER_INSTANCE_NAME]

    @route('sh_features', URL, methods=['GET'])
    def get_features(self, req, **kwargs):
        # EXPOSE METRICS TO TELEMETRY AGENT
        body = json.dumps({
            "packet_in": self.sh_app.packet_in_count,
            "packet_out": self.sh_app.packet_out_count,
            "flow_mod": self.sh_app.flow_mod_count,
            "port_status": self.sh_app.port_status_count, # NEW FEATURE
            "uptime": time.time() - self.sh_app.start_time
        })
        # FIX IS HERE: Added charset='utf-8'
        return Response(content_type='application/json', body=body, charset='utf-8')

