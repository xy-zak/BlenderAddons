import bpy
from bpy.types import Panel
from ..core import osc_server

# Mappings UI Panel
class OSC_PT_MappingsPanel(Panel):
    bl_label = "OSC Mappings"
    bl_idname = "OSC_PT_MappingsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Add mapping button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("osc.add_mapping", icon='ADD')
        
        # List mappings
        if len(context.scene.osc_mappings) == 0:
            box = layout.box()
            box.label(text="No mappings defined", icon='INFO')
        else:
            for idx, mapping in enumerate(context.scene.osc_mappings):
                box = layout.box()
                row = box.row()
                row.prop(mapping, "is_active", text="")
                
                if mapping.is_active:
                    row.label(text=f"Mapping {idx+1}")
                else:
                    row.label(text=f"Mapping {idx+1} (Disabled)")
                
                row.operator("osc.remove_mapping", text="", icon='X').index = idx
                
                box.prop(mapping, "target_object")
                box.prop(mapping, "property_type")
                
                if mapping.property_type == 'custom_property':
                    box.prop(mapping, "custom_property_name")
                
                box.prop(mapping, "osc_address")
                
                # Raw input range
                row = box.row()
                row.label(text="Input Range:")
                
                row = box.row(align=True)
                row.prop(mapping, "raw_min_value", text="Min")
                row.prop(mapping, "raw_max_value", text="Max")
                
                # Remapped output range
                row = box.row()
                row.label(text="Output Range:")
                
                row = box.row(align=True)
                row.prop(mapping, "remap_min_value", text="Min")
                row.prop(mapping, "remap_max_value", text="Max")
                
                # Driver info toggle
                row = box.row()
                row.prop(mapping, "show_driver_info", icon='DRIVER')
                
                # Show driver info if toggled
                if mapping.show_driver_info and osc_server.is_server_running:
                    driver_box = box.box()
                    driver_box.label(text="Driver Expressions:")
                    
                    # Raw OSC value
                    row = driver_box.row()
                    row.label(text="Raw Value:")
                    raw_op = row.operator("osc.copy_driver_expression", text="Copy", icon='COPYDOWN')
                    raw_op.driver_type = "raw"
                    raw_op.address = mapping.osc_address
                    
                    # Mapped OSC value
                    row = driver_box.row()
                    row.label(text="Mapped Value:")
                    mapped_op = row.operator("osc.copy_driver_expression", text="Copy", icon='COPYDOWN')
                    mapped_op.driver_type = "mapped"
                    mapped_op.address = mapping.osc_address
                    
                    # Custom remap function
                    row = driver_box.row()
                    row.label(text="Custom Remap Function:")
                    custom_op = row.operator("osc.copy_driver_expression", text="Copy", icon='COPYDOWN')
                    custom_op.driver_type = "custom"
                    custom_op.address = mapping.osc_address
                    custom_op.raw_min = mapping.raw_min_value
                    custom_op.raw_max = mapping.raw_max_value
                    custom_op.remap_min = mapping.remap_min_value
                    custom_op.remap_max = mapping.remap_max_value
                    
                    # Current values display
                    driver_box.label(text="Current values:")
                    
                    # Raw value
                    raw_value = osc_server.osc_values_dict.get(mapping.osc_address, 0.0)
                    driver_box.label(text=f"Raw: {round(raw_value, 4)}")
                    
                    # Mapped value
                    mapped_key = f"{mapping.osc_address}_mapped"
                    mapped_value = osc_server.mapped_values_dict.get(mapped_key, 0.0)
                    driver_box.label(text=f"Mapped: {round(mapped_value, 4)}")
                    
                    # Example usage
                    driver_box.label(text="Usage: Add a driver, set to Scripted Expression")
                    driver_box.label(text="Paste the copied expression")
                elif mapping.show_driver_info and not osc_server.is_server_running:
                    box.label(text="Start the OSC server to use drivers", icon='INFO')

# Register
classes = (
    OSC_PT_MappingsPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)