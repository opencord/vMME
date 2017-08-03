from core.models.plcorebase import *
from models_decl import VMMEService_decl
from models_decl import VMMETenant_decl

class VMMEService(VMMEService_decl):
   class Meta:
        proxy = True 

class VMMETenant(VMMETenant_decl):
   class Meta:
        proxy = True 

   def __init__(self, *args, **kwargs):
       vmmeservice = VMMEService.get_service_objects().all()
       if vmmeservice:
           self._meta.get_field(
                   "provider_service").default = vmmeservice[0].id
       super(VMMETenant, self).__init__(*args, **kwargs)

   def save(self, *args, **kwargs):
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