import bpy
from bpy.types import Panel

class WS_PT_ErrorPanel(Panel):
    bl_label = "WebSocket Test"
    bl_idname = "WS_PT_ErrorPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="WebSockets Library Not Found", icon='ERROR')
        box.label(text="The required 'websockets' Python")
        box.label(text="library is missing or inaccessible.")
        
        box.separator()
        box.label(text="Please check the addon installation:")
        box.label(text="1. Ensure the 'vendor' folder exists")
        box.label(text="2. Verify 'websockets' is in the vendor folder")
        box.label(text="3. Try reinstalling the addon")

def register():
    bpy.utils.register_class(WS_PT_ErrorPanel)

def unregister():
    bpy.utils.unregister_class(WS_PT_ErrorPanel)