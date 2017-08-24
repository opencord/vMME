tosca_definitions_version: tosca_simple_yaml_1_0

# compile this with "m4 vmme.m4 > vmme.yaml"

# include macros
include(macros.m4)

node_types:
    tosca.nodes.VMMEService:
        derived_from: tosca.nodes.Root
        description: >
            VMME Service
        capabilities:
            xos_base_service_caps
        properties:
            xos_base_props
            xos_base_service_props
                
    tosca.nodes.VMMETenant:
        derived_from: tosca.nodes.Root
        description: >
            VMME Tenant
        properties:
            xos_base_tenant_props
