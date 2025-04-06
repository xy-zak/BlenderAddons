bl_info = {
    "name": "OSC Controller",
    "author": "Claude",
    "version": (1, 0, 1),
    "blender": (2, 80, 0),  # Lower minimum version for better compatibility
    "location": "View3D > Sidebar > OSC",
    "description": "Control object properties using OSC messages over WiFi",
    "category": "Object",
}

import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, BoolProperty
from bpy.types import Panel, Operator, PropertyGroup
import sys
import os
import threading

# Try importing pythonosc, handle gracefully if not available
pythonosc_available = True
try:
    from pythonosc import dispatcher, osc_server
except ImportError:
    pythonosc_available = False

# Global variables
osc_server_thread = None
osc_server_instance = None
is_server_running = False
dependency_error = ""

# Data structure to store OSC mappings
class OSCMapping(PropertyGroup):
    target_object: PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        description="Object to be controlled by OSC"
    )
    
    property_types = [
        ('location_x', "Location X", "X Position"),
        ('location_y', "Location Y", "Y Position"),
        ('location_z', "Location Z", "Z Position"),
        ('rotation_x', "Rotation X", "X Rotation"),
        ('rotation_y', "Rotation Y", "Y Rotation"),
        ('rotation_z', "Rotation Z", "Z Rotation"),
        ('scale_x', "Scale X", "X Scale"),
        ('scale_y', "Scale Y", "Y Scale"),
        ('scale_z', "Scale Z", "Z Scale"),
        ('custom_property', "Custom Property", "Use a custom property of the object"),
    ]
    
    property_type: EnumProperty(
        name="Property",
        description="Property to be controlled",
        items=property_types
    )
    
    custom_property_name: StringProperty(
        name="Custom Property Name",
        description="Name of the custom property if 'Custom Property' is selected"
    )
    
    osc_address: StringProperty(
        name="OSC Address",
        description="OSC address pattern (e.g., /position/x)",
        default="/blender/value"
    )
    
    min_value: FloatProperty(
        name="Min Value",
        description="Minimum value for mapping",
        default=0.0
    )
    
    max_value: FloatProperty(
        name="Max Value",
        description="Maximum value for mapping",
        default=1.0
    )
    
    is_active: BoolProperty(
        name="Active",
        description="Enable/disable this mapping",
        default=True
    )

# Helper function to set object property
def set_object_property(obj, prop_type, custom_prop_name, value):
    if not obj:
        return
    
    try:
        if prop_type == 'location_x':
            obj.location[0] = value
        elif prop_type == 'location_y':
            obj.location[1] = value
        elif prop_type == 'location_z':
            obj.location[2] = value
        elif prop_type == 'rotation_x':
            obj.rotation_euler[0] = value
        elif prop_type == 'rotation_y':
            obj.rotation_euler[1] = value
        elif prop_type == 'rotation_z':
            obj.rotation_euler[2] = value
        elif prop_type == 'scale_x':
            obj.scale[0] = value
        elif prop_type == 'scale_y':
            obj.scale[1] = value
        elif prop_type == 'scale_z':
            obj.scale[2] = value
        elif prop_type == 'custom_property':
            if custom_prop_name in obj:
                obj[custom_prop_name] = value
    except Exception as e:
        print(f"OSC Controller: Error setting property: {str(e)}")

# OSC message handler
def osc_handler(address, *args):
    if not args:
        return
    
    try:
        value = args[0]
        if not isinstance(value, (int, float)):
            return
        
        # Update debug info
        if hasattr(bpy.context.scene, 'osc_debug'):
            debug = bpy.context.scene.osc_debug
            debug.last_received_address = address
            debug.last_received_value = str(value)
        
        # Process each mapping
        for idx, mapping in enumerate(bpy.context.scene.osc_mappings):
            if not mapping.is_active or not mapping.target_object:
                continue
            
            # Check if the OSC address matches
            if mapping.osc_address == address:
                # Map the incoming value from min-max to the property
                mapped_value = mapping.min_value + (value * (mapping.max_value - mapping.min_value))
                
                # Add to queue for execution in the main thread
                bpy.app.timers.register(
                    lambda obj=mapping.target_object, 
                        prop_type=mapping.property_type, 
                        custom_name=mapping.custom_property_name,
                        val=mapped_value: set_object_property(obj, prop_type, custom_name, val)
                )
    except Exception as e:
        print(f"OSC Controller: Error in OSC handler: {str(e)}")

# Operator to install dependencies
class OSC_OT_InstallDependencies(Operator):
    bl_idname = "osc.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = "Install the required python-osc library"
    
    def execute(self, context):
        global dependency_error
        
        try:
            import subprocess
            import sys
            
            python_exe = sys.executable
            pip_command = [python_exe, "-m", "pip", "install", "python-osc"]
            
            process = subprocess.Popen(pip_command, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.report({'INFO'}, "Successfully installed python-osc library")
                dependency_error = ""
                global pythonosc_available
                pythonosc_available = True
                try:
                    from pythonosc import dispatcher, osc_server
                except ImportError:
                    pythonosc_available = False
                    dependency_error = "Failed to import python-osc after installation"
                return {'FINISHED'}
            else:
                error_msg = stderr.decode('utf-8')
                self.report({'ERROR'}, f"Failed to install dependency: {error_msg}")
                dependency_error = f"Installation error: {error_msg}"
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error installing dependency: {str(e)}")
            dependency_error = f"Installation error: {str(e)}"
            return {'CANCELLED'}

# Operator to start OSC server
class OSC_OT_StartServer(Operator):
    bl_idname = "osc.start_server"
    bl_label = "Start OSC Server"
    bl_description = "Start listening for OSC messages"
    
    def execute(self, context):
        global osc_server_thread, osc_server_instance, is_server_running, dependency_error
        
        if not pythonosc_available:
            self.report({'ERROR'}, "Python-OSC library is not installed")
            dependency_error = "Python-OSC library not installed. Use the Install Dependencies button."
            return {'CANCELLED'}
        
        if is_server_running:
            self.report({'WARNING'}, "OSC Server is already running")
            return {'CANCELLED'}
        
        try:
            from pythonosc import dispatcher, osc_server
            
            # Create OSC dispatcher
            disp = dispatcher.Dispatcher()
            disp.map("/*", osc_handler)  # Map all OSC addresses
            
            # Start OSC server
            settings = context.scene.osc_settings
            ip = settings.ip_address
            port = settings.port
            
            server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            osc_server_instance = server
            osc_server_thread = server_thread
            is_server_running = True
            
            self.report({'INFO'}, f"OSC Server started at {ip}:{port}")
            return {'FINISHED'}
        except Exception as e:
            error_message = str(e)
            self.report({'ERROR'}, f"Failed to start OSC Server: {error_message}")
            dependency_error = f"Server error: {error_message}"
            return {'CANCELLED'}

# Operator to stop OSC server
class OSC_OT_StopServer(Operator):
    bl_idname = "osc.stop_server"
    bl_label = "Stop OSC Server"
    bl_description = "Stop the OSC server"
    
    def execute(self, context):
        global osc_server_instance, is_server_running
        
        if not is_server_running:
            self.report({'WARNING'}, "OSC Server is not running")
            return {'CANCELLED'}
        
        try:
            if osc_server_instance:
                osc_server_instance.shutdown()
                osc_server_instance = None
                is_server_running = False
                self.report({'INFO'}, "OSC Server stopped")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to stop OSC Server: {str(e)}")
            return {'CANCELLED'}

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

# OSC Server settings
class OSCSettings(PropertyGroup):
    ip_address: StringProperty(
        name="IP Address",
        description="IP Address to bind OSC server to",
        default="0.0.0.0"
    )
    
    port: IntProperty(
        name="Port",
        description="Port to listen for OSC messages",
        default=9001,
        min=1024,
        max=65535
    )

# OSC Debug Settings
class OSCDebugSettings(PropertyGroup):
    show_debug: BoolProperty(
        name="Show Debug Info",
        description="Show OSC debug information",
        default=False
    )
    
    last_received_address: StringProperty(
        name="Last Received Address",
        default="None"
    )
    
    last_received_value: StringProperty(
        name="Last Received Value",
        default="None"
    )

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
        if is_server_running:
            row.operator("osc.stop_server", icon='PAUSE')
            row.label(text="Server Running", icon='CHECKMARK')
        else:
            row.operator("osc.start_server", icon='PLAY')
            row.label(text="Server Stopped", icon='X')
            
        # Show dependency error if exists
        global dependency_error
        if dependency_error:
            row = box.row()
            row.label(text=dependency_error, icon='ERROR')
            row = box.row()
            row.operator("osc.install_dependencies", icon='PACKAGE')

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
                
                row = box.row(align=True)
                row.prop(mapping, "min_value")
                row.prop(mapping, "max_value")

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

# Register
classes = (
    OSCMapping,
    OSCSettings,
    OSCDebugSettings,
    OSC_OT_InstallDependencies,
    OSC_OT_StartServer,
    OSC_OT_StopServer,
    OSC_OT_AddMapping,
    OSC_OT_RemoveMapping,
    OSC_PT_MainPanel,
    OSC_PT_MappingsPanel,
    OSC_PT_DebugPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.osc_mappings = bpy.props.CollectionProperty(type=OSCMapping)
    bpy.types.Scene.osc_settings = bpy.props.PointerProperty(type=OSCSettings)
    bpy.types.Scene.osc_debug = bpy.props.PointerProperty(type=OSCDebugSettings)

def unregister():
    # Stop OSC server if running
    global osc_server_instance, is_server_running
    if is_server_running and osc_server_instance:
        osc_server_instance.shutdown()
        osc_server_instance = None
        is_server_running = False
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.osc_mappings
    del bpy.types.Scene.osc_settings
    del bpy.types.Scene.osc_debug

if __name__ == "__main__":
    register()