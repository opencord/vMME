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

from models_decl import VMMEService_decl
from models_decl import VMMEVendor_decl
from models_decl import VMMETenant_decl

from django.db import models
from core.models import Service, XOSBase, Slice, Instance, ServiceInstance, TenantWithContainer, Node, Image, User, Flavor, NetworkParameter, NetworkParameterType, Port, AddressPool
import os
from django.db import models, transaction
from django.forms.models import model_to_dict
from django.db.models import *
from operator import itemgetter, attrgetter, methodcaller
from core.models import Tag
from core.models.service import LeastLoadedNodeScheduler
import traceback
from xos.exceptions import *

class VMMEService(VMMEService_decl):
   class Meta:
        proxy = True

   def create_tenant(self, **kwargs):
       t = VMMETenant(kind="vEPC", owner=self, connect_method="na", **kwargs)
       t.save()
       return t

class VMMEVendor(VMMEVendor_decl):
   class Meta:
        proxy = True

class VMMETenant(VMMETenant_decl):
   class Meta:
        proxy = True

   def __init__(self, *args, **kwargs):
       vmmeservices = VMMEService.get_service_objects().all()
       if vmmeservices:
           self._meta.get_field("owner").default = vmmeservices[0].id
       super(VMMETenant, self).__init__(*args, **kwargs)

   @property
   def image(self):
       if not self.vmme_vendor:
           return super(VMMETenant, self).image
       return self.vmme_vendor.image

   def save_instance(self, instance):
       if self.vmme_vendor:
           instance.flavor = self.vmme_vendor.flavor
       super(VMMETenant, self).save_instance(instance)

   def save(self, *args, **kwargs):
       if not self.creator:
           if not getattr(self, "caller", None):
               raise XOSProgrammingError("VMMETenant's self.caller was not set")
           self.creator = self.caller
           if not self.creator:
               raise XOSProgrammingError("VMMETenant's self.creator was not set")

       super(VMMETenant, self).save(*args, **kwargs)
       # This call needs to happen so that an instance is created for this
       # tenant is created in the slice. One instance is created per tenant.
       model_policy_vmmetenant(self.pk)

   def delete(self, *args, **kwargs):
       # Delete the instance that was created for this tenant
       self.cleanup_container()
       super(VMMETenant, self).delete(*args, **kwargs)

def model_policy_vmmetenant(pk):
    # This section of code is atomic to prevent race conditions
    with transaction.atomic():
        # We find all of the tenants that are waiting to update
        tenant = VMMETenant.objects.select_for_update().filter(pk=pk)
        if not tenant:
            return
        # Since this code is atomic it is safe to always use the first tenant
        tenant = tenant[0]
        tenant.manage_container()

