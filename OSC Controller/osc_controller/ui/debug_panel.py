import bpy
from bpy.types import Panel
from ..core import osc_server
from ..core import recording

# Debug UI Panel
class OSC_PT_DebugPanel(Panel):
    bl_label = "OSC Debug"
    bl_idname = "OSC_PT_DebugPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        debug = context.scene.osc_debug
        
        layout.prop(debug, "show_debug")
        
        if debug.show_debug:
            box = layout.box()
            col = box.column()
            col.label(text="Last OSC Address:")
            col.label(text=debug.last_received_address)
            
            col.separator()
            col.label(text="Last OSC Value:")
            col.label(text=debug.last_received_value)
            
            # Show current recording state
            col.separator()
            if recording.is_recording:
                col.label(text="Recording Status: Active", icon='REC')
            else:
                col.label(text="Recording Status: Inactive", icon='SNAP_FACE')
            
            # Show all values option
            col.separator()
            col.prop(debug, "show_all_values")
            
            if debug.show_all_values:
                col.separator()
                col.label(text="All OSC Values:")
                
                if not osc_server.osc_values_dict:
                    col.label(text="No values received yet")
                else:
                    for addr, value in osc_server.osc_values_dict.items():
                        value_box = col.box()
                        value_box.label(text=f"Address: {addr}")
                        value_box.label(text=f"Raw Value: {value}")
                        
                        # Show mapped value if available
                        mapped_key = f"{addr}_mapped"
                        if mapped_key in osc_server.mapped_values_dict:
                            value_box.label(text=f"Mapped Value: {osc_server.mapped_values_dict[mapped_key]}")
                        
                        # Add copy buttons for driver expressions
                        row = value_box.row()
                        raw_op = row.operator("osc.copy_driver_expression", text="Copy Raw", icon='COPYDOWN')
                        raw_op.driver_type = "raw"
                        raw_op.address = addr
                        
                        if mapped_key in osc_server.mapped_values_dict:
                            mapped_op = row.operator("osc.copy_driver_expression", text="Copy Mapped", icon='COPYDOWN')
                            mapped_op.driver_type = "mapped"
                            mapped_op.address = addr

# Register
classes = (
    OSC_PT_DebugPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)