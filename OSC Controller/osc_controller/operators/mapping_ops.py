import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty, FloatProperty

# Operator to add a new OSC mapping
class OSC_OT_AddMapping(Operator):
    bl_idname = "osc.add_mapping"
    bl_label = "Add New Mapping"
    bl_description = "Add a new OSC to property mapping"
    
    def execute(self, context):
        try:
            mapping = context.scene.osc_mappings.add()
            if context.active_object:
                mapping.target_object = context.active_object
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to add mapping: {str(e)}")
            return {'CANCELLED'}

# Operator to remove an OSC mapping
class OSC_OT_RemoveMapping(Operator):
    bl_idname = "osc.remove_mapping"
    bl_label = "Remove Mapping"
    bl_description = "Remove the selected OSC mapping"
    
    index: IntProperty()
    
    def execute(self, context):
        try:
            context.scene.osc_mappings.remove(self.index)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to remove mapping: {str(e)}")
            return {'CANCELLED'}

# Operator to copy driver expression to clipboard
class OSC_OT_CopyDriverExpression(Operator):
    bl_idname = "osc.copy_driver_expression"
    bl_label = "Copy Driver Expression"
    bl_description = "Copy driver expression to clipboard"
    
    driver_type: StringProperty()
    address: StringProperty()
    raw_min: FloatProperty(default=0.0)
    raw_max: FloatProperty(default=1.0)
    remap_min: FloatProperty(default=0.0)
    remap_max: FloatProperty(default=1.0)
    
    def execute(self, context):
        try:
            if self.driver_type == "raw":
                expression = f'get_osc_value("{self.address}")'
            elif self.driver_type == "mapped":
                expression = f'get_mapped_osc_value("{self.address}")'
            elif self.driver_type == "custom":
                expression = f'remap_osc_value("{self.address}", {self.remap_min}, {self.remap_max}, {self.raw_min}, {self.raw_max})'
            else:
                raise ValueError("Invalid driver type")
            
            context.window_manager.clipboard = expression
            self.report({'INFO'}, f"Driver expression copied to clipboard: {expression}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to copy expression: {str(e)}")
            return {'CANCELLED'}

# Register
classes = (
    OSC_OT_AddMapping,
    OSC_OT_RemoveMapping,
    OSC_OT_CopyDriverExpression
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)