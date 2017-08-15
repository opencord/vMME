from core.models.plcorebase import *
from models_decl import VMMEService_decl
from models_decl import VMMETenant_decl

from django.db import models
from core.models import Service, PlCoreBase, Slice, Instance, Tenant, TenantWithContainer, Node, Image, User, Flavor, NetworkParameter, NetworkParameterType, Port, AddressPool
from core.models.plcorebase import StrippedCharField
import os
from django.db import models, transaction
from django.forms.models import model_to_dict
from django.db.models import *
from operator import itemgetter, attrgetter, methodcaller
from core.models import Tag
from core.models.service import LeastLoadedNodeScheduler
from services.vsgw.models import VSGWService, VSGWTenant
from services.vpgwc.models import VPGWCService, VPGWCTenant
from services.vhss.models import VHSSService, VHSSTenant
import traceback
from xos.exceptions import *
from xos.config import Config
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class VMMEService(VMMEService_decl):
   class Meta:
        proxy = True 

class VMMETenant(VMMETenant_decl):
   class Meta:
        proxy = True 

   def __init__(self, *args, **kwargs):
       vmmeservices = VMMEService.get_service_objects().all()
       if vmmeservices:
           self._meta.get_field("provider_service").default = vmmeservices[0].id
       super(VMMETenant, self).__init__(*args, **kwargs)
       self.cached_vsgw = None
       self.cached_vpgwc = None
       self.cached_vhss = None

   @property
   def vsgw(self):
       vsgw = self.get_newest_subscribed_tenant(VSGWTenant)
       if not vsgw:
           return None

       if (self.cached_vsgw) and (self.cached_vsgw.id == vsgw.id):
            return self.cached_vsgw

       vsgw.caller = self.creator
       self.cached_vsgw = vsgw
       return vsgw      

   @vsgw.setter
   def vsgw(self, value):
       raise XOSConfigurationError("VMMETenant.vsgw setter is not implemeneted")

   @property
   def vpgwc(self):
       vpgwc = self.get_newest_subscribed_tenant(VPGWCTenant)
       if not vpgwc:
           return None

       if (self.cached_vpgwc) and (self.cached_vpgwc.id == vpgwc.id):
            return self.cached_vpgwc

       vpgwc.caller = self.creator
       self.cached_vpgwc = vpgwc
       return vpgwc      

   @vpgwc.setter
   def vpgwc(self, value):
       raise XOSConfigurationError("VMMETenant.vpgwc setter is not implemeneted")

   @property
   def vhss(self):
       vhss = self.get_newest_subscribed_tenant(VHSSTenant)
       if not vhss:
           return None

       if (self.cached_vhss) and (self.cached_vhss.id == vhss.id):
            return self.cached_vhss

       vhss.caller = self.creator
       self.cached_vhss = vhss
       return vhss      

   @vhss.setter
   def vhss(self, value):
       raise XOSConfigurationError("VMMETenant.vhss setter is not implemeneted")

   # This model breaks down if there are multiple service objects
   def get_vsgw_service(self):
       vsgwservices = VSGWService.get_service_objects().all()
       if not vsgwservices:
           raise XOSConfigurationError("No VSGW Services available")
       return vsgwservices[0]

   def get_vpgwc_service(self):
       vpgwcservices = VPGWCService.get_service_objects().all()
       if not vpgwcservices:
           raise XOSConfigurationError("No VPGWC Services available")
       return vpgwcservices[0]

   def get_vhss_service(self):
       vhssservices = VHSSService.get_service_objects().all()
       if not vhssservices:
           raise XOSConfigurationError("No VHSS Services available")
       return vhssservices[0]

   def manage_vsgw(self):
       # Each vMME object owns exactly one VSGWTenant object
       if self.deleted:
           return

       if self.vsgw is None:
           vsgw = self.get_vsgw_service().create_tenant(subscriber_tenant=self, creator=self.creator)

   def manage_vpgwc(self):
       # Each vMME object owns exactly one VPGWCTenant object
       if self.deleted:
           return

       if self.vpgwc is None:
           vpgwc = self.get_vpgwc_service().create_tenant(subscriber_tenant=self, creator=self.creator)

   def manage_vhss(self):
       # Each vMME object owns exactly one VHSSTenant object
       if self.deleted:
           return

       if self.vhss is None:
           vhss = self.get_vhss_service().create_tenant(subscriber_tenant=self, creator=self.creator)

   def cleanup_vsgw(self):
       if self.vsgw:
           self.vsgw.delete()

   def cleanup_vpgwc(self):
       if self.vpgwc:
           self.vpgwc.delete()

   def cleanup_vhss(self):
       if self.vhss:
           self.vhss.delete()
  
   def cleanup_orphans(self):
       # ensure vMME only has one vSGW, vPGWC, and vHSS
       cur_vsgw = self.vsgw
       cur_vpgwc = self.vpgwc
       cur_vhss = self.vhss

       for vsgw in list(self.get_subscribed_tenants(VSGWTenant)):
           if (not cur_vsgw) or (vsgw.id != cur_vsgw.id):
              vsgw.delete()

       for vpgwc in list(self.get_subscribed_tenants(VPGWCTenant)):
           if (not cur_vpgwc) or (vpgwc.id != cur_vpgwc.id):
              vpgwc.delete()

       for vhss in list(self.get_subscribed_tenants(VHSSTenant)):
           if (not cur_vhss) or (vhss.id != cur_vhss.id):
              vhss.delete()

       if self.orig_instance_id and (self.orig_instance_id != self.get_attribute("instance_id")):
           instances = Instance.objects.filter(id=self.orig_instance.id)
           if instances:
               instances[0].delete()

   def save(self, *args, **kwargs):
       super(VMMETenant, self).save(*args, **kwargs)
       # This call needs to happen so that an instance is created for this
       # tenant is created in the slice. One instance is created per tenant.
       model_policy_vmmetenant(self.pk)

   def delete(self, *args, **kwargs):
       # Delete the instance that was created for this tenant
       self.cleanup_vsgw()
       self.cleanup_vpgwc()
       self.cleanup_vhss()
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
        tenant.manage_vsgw()
        tenant.manage_vpgwc()
        tenant.manage_vhss()
        tenant.cleanup_orphans()
