bl_info = {
    "name": "OSC Controller",
    "author": "Zak Silver-Lennard ",
    "version": (1, 0, 4),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > OSC",
    "description": "Control object properties using OSC messages over LAN (python-osc included)",
    "category": "Object",
}

import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, BoolProperty
from bpy.types import Panel, Operator, PropertyGroup
import sys
import os
import threading
import datetime



# Global variables
osc_server_thread = None
osc_server_instance = None
is_server_running = False
dependency_error = ""
osc_values_dict = {}  # Dictionary to store the latest OSC values by address
mapped_values_dict = {}  # Dictionary to store the mapped values by address
pythonosc_available = False
pythonosc_path = "Not installed"

# Try importing pythonosc, handle gracefully if not available
# Try importing pythonosc, handle gracefully if not available
def check_pythonosc():
    global pythonosc_available, pythonosc_path
    
    try:
        # First try to import normally in case it's already installed
        from pythonosc import dispatcher, osc_server
        pythonosc_available = True
        try:
            import pythonosc
            pythonosc_path = os.path.dirname(pythonosc.__file__)
        except:
            pythonosc_path = "System installation (path unknown)"
        return True
    except ImportError:
        # If not found, try to use the bundled version
        try:
            # Get the directory of the current script
            current_dir = os.path.dirname(os.path.realpath(__file__))
            # Path to the bundled library
            vendor_path = os.path.join(current_dir, "vendor")
            
            # Add to path if not already there
            if vendor_path not in sys.path:
                sys.path.insert(0, vendor_path)
                
            # Try import again
            from pythonosc import dispatcher, osc_server
            pythonosc_available = True
            pythonosc_path = os.path.join(vendor_path, "pythonosc")
            return True
        except ImportError:
            pythonosc_available = False
            pythonosc_path = "Not installed"
            return False

# Initial check for pythonosc
check_pythonosc()

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
    
    # Raw input range
    raw_min_value: FloatProperty(
        name="Raw Min Value",
        description="Minimum value expected from OSC input",
        default=0.0
    )
    
    raw_max_value: FloatProperty(
        name="Raw Max Value",
        description="Maximum value expected from OSC input",
        default=1.0
    )
    
    # Remapped output range
    remap_min_value: FloatProperty(
        name="Remap Min Value",
        description="Minimum value for remapped output",
        default=0.0
    )
    
    remap_max_value: FloatProperty(
        name="Remap Max Value",
        description="Maximum value for remapped output",
        default=1.0
    )
    
    is_active: BoolProperty(
        name="Active",
        description="Enable/disable this mapping",
        default=True
    )
    
    show_driver_info: BoolProperty(
        name="Show Driver Info",
        description="Show information for creating drivers with this OSC data",
        default=False
    )

# Function to remap a value from one range to another
def remap_value(value, old_min, old_max, new_min, new_max):
    # Handle division by zero case
    if old_min == old_max:
        return new_min
    
    # Calculate what percentage of the old range the value is
    old_range = old_max - old_min
    normalized = (value - old_min) / old_range
    
    # Apply that percentage to the new range
    new_range = new_max - new_min
    return new_min + normalized * new_range

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
        
        # Store the raw OSC value
        osc_values_dict[address] = value
        
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
                # Remap the incoming value from raw range to the remapped range
                mapped_value = remap_value(
                    value, 
                    mapping.raw_min_value, 
                    mapping.raw_max_value,
                    mapping.remap_min_value, 
                    mapping.remap_max_value
                )
                
                # Store the mapped value for driver use
                mapped_values_dict[f"{address}_mapped"] = mapped_value
                
                # Add to queue for execution in the main thread
                bpy.app.timers.register(
                    lambda obj=mapping.target_object, 
                        prop_type=mapping.property_type, 
                        custom_name=mapping.custom_property_name,
                        val=mapped_value: set_object_property(obj, prop_type, custom_name, val)
                )
    except Exception as e:
        print(f"OSC Controller: Error in OSC handler: {str(e)}")

# Functions for Blender drivers to access OSC data
def get_osc_value(address):
    return osc_values_dict.get(address, 0.0)

def get_mapped_osc_value(address):
    return mapped_values_dict.get(f"{address}_mapped", 0.0)

# Function for drivers to perform custom remapping
def remap_osc_value(address, out_min, out_max, in_min=None, in_max=None):
    # Get the raw value
    value = osc_values_dict.get(address, 0.0)
    
    # If input range not specified, use standard 0-1
    if in_min is None:
        in_min = 0.0
    if in_max is None:
        in_max = 1.0
        
    # Perform the remapping
    return remap_value(value, in_min, in_max, out_min, out_max)

# Register OSC driver functions globally
def register_driver_functions():
    bpy.app.driver_namespace["get_osc_value"] = get_osc_value
    bpy.app.driver_namespace["get_mapped_osc_value"] = get_mapped_osc_value
    bpy.app.driver_namespace["remap_osc_value"] = remap_osc_value

# Operator to install dependencies
class OSC_OT_InstallDependencies(Operator):
    bl_idname = "osc.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = "Try to install the python-osc library system-wide (fallback)"
    
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
                check_pythonosc()  # Update the status after installation
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
        
        # Check if python-osc is available
        if not check_pythonosc():
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

# Operator to open documentation URL
class OSC_OT_OpenDocumentation(Operator):
    bl_idname = "osc.open_documentation"
    bl_label = "Open Documentation"
    bl_description = "Open the OSC Controller documentation in a web browser"
    
    url: StringProperty(default="https://github.com/YourUsername/OSCController")
    
    def execute(self, context):
        try:
            import webbrowser
            webbrowser.open(self.url)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open URL: {str(e)}")
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
    
    show_all_values: BoolProperty(
        name="Show All OSC Values",
        description="Show all received OSC values",
        default=False
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
        
        # Add dependency status at the bottom of main panel
        box = layout.box()
        row = box.row()
        if pythonosc_available:
            row.label(text="python-osc: Available", icon='CHECKMARK')
            if "vendor" in pythonosc_path:
                row.label(text="(Bundled)", icon='PACKAGE')
        else:
            row.label(text="python-osc: Not Available", icon='X')
            row = box.row()
            row.operator("osc.install_dependencies", icon='PACKAGE')
            row.label(text="Trying to use bundled version failed")
            
        # Show dependency error if exists
        global dependency_error
        if dependency_error:
            row = box.row()
            row.label(text=dependency_error, icon='ERROR')

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
                if mapping.show_driver_info and is_server_running:
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
                    raw_value = osc_values_dict.get(mapping.osc_address, 0.0)
                    driver_box.label(text=f"Raw: {round(raw_value, 4)}")
                    
                    # Mapped value
                    mapped_key = f"{mapping.osc_address}_mapped"
                    mapped_value = mapped_values_dict.get(mapped_key, 0.0)
                    driver_box.label(text=f"Mapped: {round(mapped_value, 4)}")
                    
                    # Example usage
                    driver_box.label(text="Usage: Add a driver, set to Scripted Expression")
                    driver_box.label(text="Paste the copied expression")
                elif mapping.show_driver_info and not is_server_running:
                    box.label(text="Start the OSC server to use drivers", icon='INFO')

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
            
            # Show all values option
            col.separator()
            col.prop(debug, "show_all_values")
            
            if debug.show_all_values:
                col.separator()
                col.label(text="All OSC Values:")
                
                if not osc_values_dict:
                    col.label(text="No values received yet")
                else:
                    for addr, value in osc_values_dict.items():
                        value_box = col.box()
                        value_box.label(text=f"Address: {addr}")
                        value_box.label(text=f"Raw Value: {value}")
                        
                        # Show mapped value if available
                        mapped_key = f"{addr}_mapped"
                        if mapped_key in mapped_values_dict:
                            value_box.label(text=f"Mapped Value: {mapped_values_dict[mapped_key]}")
                        
                        # Add copy buttons for driver expressions
                        row = value_box.row()
                        raw_op = row.operator("osc.copy_driver_expression", text="Copy Raw", icon='COPYDOWN')
                        raw_op.driver_type = "raw"
                        raw_op.address = addr
                        
                        if mapped_key in mapped_values_dict:
                            mapped_op = row.operator("osc.copy_driver_expression", text="Copy Mapped", icon='COPYDOWN')
                            mapped_op.driver_type = "mapped"
                            mapped_op.address = addr

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
        
        box = layout.box()
        
        # Plugin version
        version = ".".join(map(str, bl_info["version"]))
        box.label(text=f"Version: {version}")
        
        # Release date (hardcoded since it's not in bl_info)
        box.label(text="Release Date: April 2, 2025")
        
        # Python-OSC library status
        box.label(text="python-osc library:")
        if pythonosc_available:
            box.label(text="Status: Installed", icon='CHECKMARK')
            box.label(text=f"Path: {pythonosc_path}")
        else:
            box.label(text="Status: Not Installed", icon='X')
            box.operator("osc.install_dependencies", icon='PACKAGE')
        
        # Documentation link
        box.separator()
        box.label(text="Documentation:")
        box.operator("osc.open_documentation", icon='URL')

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
    OSC_OT_CopyDriverExpression,
    OSC_OT_OpenDocumentation,
    OSC_PT_MainPanel,
    OSC_PT_MappingsPanel,
    OSC_PT_DebugPanel,
    OSC_PT_InfoPanel,
)

def register():
    # Check for pythonosc library
    check_pythonosc()
    
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.osc_mappings = bpy.props.CollectionProperty(type=OSCMapping)
    bpy.types.Scene.osc_settings = bpy.props.PointerProperty(type=OSCSettings)
    bpy.types.Scene.osc_debug = bpy.props.PointerProperty(type=OSCDebugSettings)
    
    # Register driver functions
    register_driver_functions()

def unregister():
    # Stop OSC server if running
    global osc_server_instance, is_server_running
    if is_server_running and osc_server_instance:
        osc_server_instance.shutdown()
        osc_server_instance = None
        is_server_running = False
    
    # Remove driver functions from namespace
    if "get_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["get_osc_value"]
    if "get_mapped_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["get_mapped_osc_value"]
    if "remap_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["remap_osc_value"]
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.osc_mappings
    del bpy.types.Scene.osc_settings
    del bpy.types.Scene.osc_debug

if __name__ == "__main__":
    register()