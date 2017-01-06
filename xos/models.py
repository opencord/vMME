# models.py -  ExampleService Models

from core.models import Service, TenantWithContainer
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

    #default_attributes = {"tenant_message": "New vMME Component"}  will this work? 
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


def model_policy_vmmetenant(pk):
    with transaction.atomic():
        tenant = VMMETenant.objects.select_for_update().filter(pk=pk)
        if not tenant:
            return
        tenant = tenant[0]
        tenant.manage_container()

