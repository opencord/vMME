

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

from synchronizers.new_base.modelaccessor import *
from synchronizers.new_base.model_policies.model_policy_tenantwithcontainer import TenantWithContainerPolicy, LeastLoadedNodeScheduler
from synchronizers.new_base.exceptions import *

class VMMETenantPolicy(TenantWithContainerPolicy):
    model_name = "VMMETenant"

    def handle_create(self, service_instance):
        return self.handle_update(service_instance)

    def handle_update(self, service_instance):
        if (service_instance.link_deleted_count>0) and (not service_instance.provided_links.exists()):
            self.logger.info("The last provided link has been deleted -- self-destructing.")
            self.handle_delete(service_instance)
            if VMMETenant.objects.filter(id=service_instance.id).exists():
                service_instance.delete()
            else:
                self.logger.info("Tenant %s is already deleted" % service_instance)
            return

        self.manage_container(service_instance)

    def handle_delete(self, service_instance):
        if service_instance.instance and (not service_instance.instance.deleted):
            all_service_instances_this_instance = VMMETenant.objects.filter(instance_id=service_instance.instance.id)
            other_service_instances_this_instance = [x for x in all_service_instances_this_instance if x.id != service_instance.id]
            if (not other_service_instances_this_instance):
                self.logger.info("VMMETenant Instance %s is now unused -- deleting" % service_instance.instance)
                self.delete_instance(service_instance, service_instance.instance)
            else:
                self.logger.info("VMMETenant Instance %s has %d other service instances attached" % (service_instance.instance, len(other_service_instances_this_instance)))

    def get_service(self, service_instance):
        service_name = service_instance.owner.leaf_model_name
        service_class = globals()[service_name]
        return service_class.objects.get(id=service_instance.owner.id)

    def find_instance_for_instance_tag(self, instance_tag):
        tags = Tag.objects.filter(name="instance_tag", value=instance_tag)
        if tags:
            return tags[0].content_object
        return None

    def find_or_make_instance_for_instance_tag(self, service_instance):
        instance_tag = self.get_instance_tag(service_instance)
        instance = self.find_instance_for_instance_tag(instance_tag)
        if instance:
            if instance.no_sync:
                # if no_sync is still set, then perhaps we failed while saving it and need to retry.
                self.save_instance(service_instance, instance)
            return instance

        desired_image = self.get_image(service_instance)
        desired_flavor = self.get_flavor(service_instance)

        slice = service_instance.owner.slices.first()

        (node, parent) = LeastLoadedNodeScheduler(slice, label=None).pick()

        assert (slice is not None)
        assert (node is not None)
        assert (desired_image is not None)
        assert (service_instance.creator is not None)
        assert (node.site_deployment.deployment is not None)
        assert (desired_image is not None)

        instance = Instance(slice=slice,
                            node=node,
                            image=desired_image,
                            creator=service_instance.creator,
                            deployment=node.site_deployment.deployment,
                            flavor=desired_flavor,
                            isolation=slice.default_isolation,
                            parent=parent)

        self.save_instance(service_instance, instance)

        return instance

    def manage_container(self, service_instance):
        if service_instance.deleted:
            return

        if service_instance.instance:
            # We're good.
            return

        instance = self.find_or_make_instance_for_instance_tag(service_instance)
        service_instance.instance = instance
        # TODO: possible for partial failure here?
        service_instance.save()

    def delete_instance(self, service_instance, instance):
        # delete the `instance_tag` tags
        tags = Tag.objects.filter(service_id=service_instance.owner.id, content_type=instance.self_content_type_id,
                                  object_id=instance.id, name="instance_tag")
        for tag in tags:
            tag.delete()

        tags = Tag.objects.filter(content_type=instance.self_content_type_id, object_id=instance.id,
                                  name="vm_vrouter_tenant")
        for tag in tags:
            address_manager_instances = list(ServiceInstance.objects.filter(id=tag.value))
            tag.delete()

            # TODO: Potential partial failure

            for address_manager_instance in address_manager_instances:
                self.logger.info("Deleting address_manager_instance %s" % address_manager_instance)
                address_manager_instance.delete()

        instance.delete()

    def save_instance(self, service_instance, instance):
        instance.no_sync = True   # prevent instance from being synced until we're done with it
        super(VMMETenantPolicy, self).save_instance(instance)

        try:
            if instance.isolation in ["container", "container_vm"]:
                raise Exception("Not supported")

            instance_tag = self.get_instance_tag(service_instance)
            if instance_tag:
                tags = Tag.objects.filter(name="instance_tag", value=instance_tag)
                if not tags:
                    tag = Tag(service=service_instance.owner, content_type=instance.self_content_type_id, object_id=instance.id, name="instance_tag", value=str(instance_tag))
                    tag.save()

            instance.no_sync = False   # allow the synchronizer to run now
            super(VMMETenantPolicy, self).save_instance(instance)
        except:
            # need to clean up any failures here
            raise
    
    def get_instance_tag(self, service_instance):
        return '%d'%service_instance.id
    
    def get_image(self, service_instance):
        return service_instance.vmme_vendor.image
    
    def get_flavor(self, service_vendor):
        return service_vendor.vmme_vendor.flavor
