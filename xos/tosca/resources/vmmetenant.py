from services.vmme.models import VMMETenant, VMMEService
from xosresource import XOSResource

class XOSVMMETenant(XOSResource):
    provides = "tosca.nodes.VMMETenant"
    xos_model = VMMETenant
    copyin_props = ["tenant_message"]  #should this be a list or a tuple (as in exampleservice) ? 
    name_field = None  #should this be "service_specific id" (as in exampleservice) ? 

    def get_xos_args(self, throw_exception=True):
        args = super(XOSVMMETenant, self).get_xos_args()

        provider_name = self.get_requirement("tosca.relationships.MemberOfService", throw_exception=throw_exception)
        if provider_name:
            args["provider_service"] = self.get_xos_object(VMMEService, throw_exception=throw_exception, name=provider_name)

        return args

    def get_existing_objs(self):
        args = self.get_xos_args(throw_exception=False)
        provider_service = args.get("provider", None)
        if provider_service:
            return [ self.get_xos_object(provider_service=provider_service) ]
        return []

    def postprocess(self, obj):
        pass

    def can_delete(self, obj):
        return super(XOSVMMETenant, self).can_delete(obj)
