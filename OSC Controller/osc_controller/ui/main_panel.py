import bpy
from bpy.types import Panel
from ..core import osc_server
from ..core import utils
from ..core import recording  # Make sure this import is present

# Main UI Panel
class OSC_PT_MainPanel(Panel):
    bl_label = "OSC Controller"
    bl_idname = "OSC_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.osc_settings
        
        # Server controls
        box = layout.box()
        box.label(text="Server Settings:")
        
        row = box.row()
        row.prop(settings, "ip_address")
        
        row = box.row()
        row.prop(settings, "port")
        
        # Server status and control
        row = box.row()
        if osc_server.is_server_running:
            row.operator("osc.stop_server", icon='PAUSE')
            row.label(text="Server Running", icon='CHECKMARK')
        else:
            row.operator("osc.start_server", icon='PLAY')
            row.label(text="Server Stopped", icon='X')
        
        # Special commands info
        special_box = layout.box()
        special_box.label(text="Special OSC Commands:")
        
        row = special_box.row()
        row.label(text="/renderimage: Start a render (value=1)")
        
        row = special_box.row()
        # Use recording.is_recording here, not osc_server.is_recording
        rec_status = "Status: Recording" if recording.is_recording else "Status: Not Recording"
        row.label(text=f"/recordframes: Toggle recording (value=1) - {rec_status}")
        
        # Add dependency status at the bottom of main panel
        box = layout.box()
        row = box.row()
        if utils.pythonosc_available:
            row.label(text="python-osc: Available", icon='CHECKMARK')
            if "vendor" in utils.pythonosc_path:
                row.label(text="(Bundled)", icon='PACKAGE')
        else:
            row.label(text="python-osc: Not Available", icon='X')
            row = box.row()
            row.operator("osc.install_dependencies", icon='PACKAGE')
            row.label(text="Trying to use bundled version failed")
            
        # Show dependency error if exists
        if utils.dependency_error:
            row = box.row()
            row.label(text=utils.dependency_error, icon='ERROR')

# Register
classes = (
    OSC_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)