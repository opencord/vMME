
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


# models.py -  ExampleService Models

from core.models import Service, TenantWithContainer, Image
from django.db import models, transaction


MCORD_KIND = "EPC"   #added from vBBU

#these macros are currently not used, names hard-coded manually
SERVICE_NAME = 'vmme'
SERVICE_NAME_VERBOSE = 'VMME Service'
SERVICE_NAME_VERBOSE_PLURAL = 'VMME Services'
TENANT_NAME_VERBOSE = 'VMME Service Tenant'
TENANT_NAME_VERBOSE_PLURAL = 'VMME Service Tenants'

class VMMEService(Service):

    KIND = MCORD_KIND

    class Meta:
        proxy = True
        app_label = "vmme"
        verbose_name = "VMME Service"

class VMMETenant(TenantWithContainer):

    KIND = 'vmme'
    class Meta:
        verbose_name = "VMME Service Tenant"

    tenant_message = models.CharField(max_length=254, help_text="vMME message")
    image_name = models.CharField(max_length=254, help_text="Name of VM image")

    def __init__(self, *args, **kwargs):
        vmme_services = VMMEService.get_service_objects().all()
        if vmme_services:
            self._meta.get_field('provider_service').default = vmme_services[0].id
        super(VMMETenant, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(VMMETenant, self).save(*args, **kwargs)
        model_policy_vmmetenant(self.pk) #defined below

    def delete(self, *args, **kwargs):
        self.cleanup_container()
        super(VMMETenant, self).delete(*args, **kwargs)

    @property
    def image(self):
        img = self.image_name.strip()
        if img.lower() != "default":
            return Image.objects.get(name=img)
        else: 
            return super(VMMETenant, self).image

        

def model_policy_vmmetenant(pk):
    with transaction.atomic():
        tenant = VMMETenant.objects.select_for_update().filter(pk=pk)
        if not tenant:
            return
        tenant = tenant[0]
        tenant.manage_container()

