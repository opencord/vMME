
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
from services.vmme.models import VMMEService, VMMETenant
from synchronizers.base.SyncInstanceUsingAnsible import SyncInstanceUsingAnsible

parentdir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, parentdir)

class SyncVMMETenant(SyncInstanceUsingAnsible):

    provides = [VMMETenant]

    observes = VMMETenant

    requested_interval = 0

    template_name = "vmmetenant_playbook.yaml"

    service_key_name = "/opt/xos/synchronizers/vmme/vmme_private_key"

    def __init__(self, *args, **kwargs):
        super(SyncVMMETenant, self).__init__(*args, **kwargs)

    def fetch_pending(self, deleted):

        if (not deleted):
            objs = VMMETenant.get_tenant_objects().filter(
                Q(enacted__lt=F('updated')) | Q(enacted=None), Q(lazy_blocked=False))
        else:
            # If this is a deletion we get all of the deleted tenants..
            objs = VMMETenant.get_deleted_tenant_objects()

        return objs

    def get_vmmeservice(self, o):
        if not o.provider_service:
            return None

        vmmeservice = VMMEService.get_service_objects().filter(id=o.provider_service.id)

        if not vmmeservice:
            return None

        return vmmeservice[0]

    # Gets the attributes that are used by the Ansible template but are not
    # part of the set of default attributes.
    def get_extra_attributes(self, o):
        fields = {}
        fields['tenant_message'] = o.tenant_message
        fields['image_name'] = o.image_name
        return fields

