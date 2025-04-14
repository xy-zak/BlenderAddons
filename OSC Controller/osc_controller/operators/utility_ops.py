import bpy
import webbrowser
from bpy.types import Operator
from bpy.props import StringProperty

# Operator to open documentation URL
class OSC_OT_OpenDocumentation(Operator):
    bl_idname = "osc.open_documentation"
    bl_label = "Open Documentation"
    bl_description = "Open the OSC Controller documentation in a web browser"
    
    url: StringProperty(default="https://github.com/YourUsername/OSCController")
    
    def execute(self, context):
        try:
            webbrowser.open(self.url)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open URL: {str(e)}")
            return {'CANCELLED'}

# Register
classes = (
    OSC_OT_OpenDocumentation,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)