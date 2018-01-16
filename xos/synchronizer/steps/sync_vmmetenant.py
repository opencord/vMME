# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from django.db.models import Q, F
#from services.vmme.models import VMMEService, VMMETenant
from synchronizers.new_base.modelaccessor import *
from synchronizers.new_base.SyncInstanceUsingAnsible import SyncInstanceUsingAnsible

parentdir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, parentdir)

class SyncVMMETenant(SyncInstanceUsingAnsible):

    provides = [VMMETenant]

    observes = VMMETenant

    requested_interval = 0

    template_name = "vmmetenant_playbook.yaml"

    service_key_name = "/opt/xos/configurations/mcord/mcord_private_key"

    def __init__(self, *args, **kwargs):
        super(SyncVMMETenant, self).__init__(*args, **kwargs)

    def get_extra_attributes(self, o):
        fields = {}

        fields['s6a_hss_ip']   = self.get_ip_address_from_peer_service_instance('s6a_network', 'VHSSTenant', o, 's6a_hss_ip')
        fields['s1mme_enb_ip'] = o.enodeb_ip_addr
        fields['s1mme_mme_ip'] = self.get_my_ip_address(o, 'flat_network_s1mme', 's1mme_mme_ip')
        fields['s11_mme_ip']   = self.get_my_ip_address(o, 's11_network', 's11_mme_ip')
        fields['s11_sgw_ip']   = self.get_ip_address_from_peer_service_instance('s11_network', 'VSPGWCTenant', o, 's11_sgw_ip')

        return fields

    def get_my_ip_address(self, o, network_name, parameter=None):
        return self.get_ip_address_from_peer_service_instance_instance(network_name, o, o, parameter)

    def get_ip_address_from_peer_service_instance(self, network_name, sitype, o, parameter=None):
        peer_si = self.get_peer_serviceinstance_of_type(sitype, o)
        return self.get_ip_address_from_peer_service_instance_instance(network_name, peer_si, o, parameter)

    def get_ip_address_from_peer_service_instance_instance(self, network_name, peer_si, o, parameter=None):
        try:
            net_id = self.get_network_id(network_name)
            ins_id = peer_si.leaf_model.instance_id
            ip_address = Port.objects.get(
                network_id=net_id, instance_id=ins_id).ip
        except Exception:
            self.log.error("Failed to fetch parameter",
                           parameter=parameter,
                           network_name=network_name)
            self.defer_sync(o, "Waiting for parameters to become available")

        return ip_address

    def get_peer_serviceinstance_of_type(self, sitype, o):
        prov_link_set = ServiceInstanceLink.objects.filter(
            subscriber_service_instance_id=o.id)

        try:
            peer_service = next(
                p.provider_service_instance for p in prov_link_set if p.provider_service_instance.leaf_model_name == sitype)
        except StopIteration:
            sub_link_set = ServiceInstanceLink.objects.filter(
                provider_service_instance_id=o.id)
            try:
                peer_service = next(
                    s.subscriber_service_instance for s in sub_link_set if s.subscriber_service_instance.leaf_model_name == sitype)
            except StopIteration:
                self.log.error(
                    'Could not find service type in service graph', service_type=sitype, object=o)
                raise ServiceGraphException(
                    "Synchronization failed due to incomplete service graph")

        return peer_service

    # To get each network id
    def get_network_id(self, network_name):
        return Network.objects.get(name=network_name).id