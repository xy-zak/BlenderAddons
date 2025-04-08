import bpy
from bpy.types import Panel
from ..core import utils

# Plugin Information Panel
class OSC_PT_InfoPanel(Panel):
    bl_label = "Plugin Information"
    bl_idname = "OSC_PT_InfoPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Get the bl_info from the main __init__.py
        from .. import bl_info
        
        box = layout.box()
        
        # Plugin version
        version = ".".join(map(str, bl_info["version"]))
        box.label(text=f"Version: {version}")
        
        # Release date (hardcoded since it's not in bl_info)
        box.label(text="Release Date: April 6, 2025")
        
        # Python-OSC library status
        box.label(text="python-osc library:")
        if utils.pythonosc_available:
            box.label(text="Status: Installed", icon='CHECKMARK')
            box.label(text=f"Path: {utils.pythonosc_path}")
        else:
            box.label(text="Status: Not Installed", icon='X')
            box.operator("osc.install_dependencies", icon='PACKAGE')
        
        # Documentation link
        box.separator()
        box.label(text="Documentation:")
        box.operator("osc.open_documentation", icon='URL')
        
        # Special commands info
        box.separator()
        box.label(text="Special OSC Commands:")
        box.label(text="/renderimage (1) - Start a render")
        box.label(text="/recordframes (1) - Toggle frame recording")

# Register
classes = (
    OSC_PT_InfoPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)