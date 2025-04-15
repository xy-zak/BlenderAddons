import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, FloatProperty
from bpy.types import PropertyGroup

# Server settings
class ServerSettings(PropertyGroup):
    ip_address: StringProperty(
        name="IP Address",
        description="IP Address to bind WebSocket server to",
        default="0.0.0.0"
    )
    
    port: IntProperty(
        name="Port",
        description="Port to listen for WebSocket messages",
        default=8765,
        min=1024,
        max=65535
    )
    
    esp_connected: BoolProperty(
        name="ESP Connected",
        description="Indicates if an ESP client is connected",
        default=False
    )
    
    esp_ip: StringProperty(
        name="ESP IP Address",
        description="IP Address of the connected ESP",
        default=""
    )

# Debug information
class DebugSettings(PropertyGroup):
    show_debug: BoolProperty(
        name="Show Debug Info",
        description="Show WebSocket debug information",
        default=True
    )
    
    last_message: StringProperty(
        name="Last Message",
        default="None"
    )
    
    connection_status: StringProperty(
        name="Connection Status",
        default="Disconnected"
    )
    
    message_log: StringProperty(
        name="Message Log",
        description="Log of recent messages",
        default=""
    )

# Simple update callback for empty transform
def update_empty_transform(self, context):
    """Update the empty's transform when properties change"""
    # This will only be called if the properties exist
    if hasattr(self, 'target_empty') and self.target_empty:
        try:
            if self.target_empty in bpy.data.objects:
                empty = bpy.data.objects[self.target_empty]
                
                # Update the empty's transform
                if hasattr(self, 'empty_loc_x'):
                    empty.location.x = self.empty_loc_x
                if hasattr(self, 'empty_loc_y'):
                    empty.location.y = self.empty_loc_y
                if hasattr(self, 'empty_loc_z'):
                    empty.location.z = self.empty_loc_z
                if hasattr(self, 'empty_rot_x'):
                    empty.rotation_euler.x = self.empty_rot_x
                if hasattr(self, 'empty_rot_y'):
                    empty.rotation_euler.y = self.empty_rot_y
                if hasattr(self, 'empty_rot_z'):
                    empty.rotation_euler.z = self.empty_rot_z
        except:
            # Silently fail - this prevents errors in the UI
            pass

# Camera tracking settings
class CameraTrackingSettings(PropertyGroup):
    target_camera: StringProperty(
        name="Target Camera",
        description="Camera to control with IMU data",
        default=""
    )
    
    target_empty: StringProperty(
        name="Target Empty",
        description="Empty parent of the target camera",
        default=""
    )
    
    track_rotation: BoolProperty(
        name="Track Rotation",
        description="Apply rotation data from IMU to the camera",
        default=True
    )
    
    track_location: BoolProperty(
        name="Track Location",
        description="Apply location data from IMU to the camera",
        default=True
    )
    
    rotation_factor: FloatProperty(
        name="Rotation Factor",
        description="Multiplier for rotation values",
        default=1.0,
        min=0.01,
        max=10.0
    )
    
    location_factor: FloatProperty(
        name="Location Factor",
        description="Multiplier for location values",
        default=1.0,
        min=0.01, 
        max=10.0
    )
    
    # Empty transform properties
    empty_loc_x: FloatProperty(
        name="X",
        description="X location of the empty parent",
        default=0.0,
        update=update_empty_transform
    )
    
    empty_loc_y: FloatProperty(
        name="Y",
        description="Y location of the empty parent",
        default=0.0,
        update=update_empty_transform
    )
    
    empty_loc_z: FloatProperty(
        name="Z",
        description="Z location of the empty parent",
        default=0.0,
        update=update_empty_transform
    )
    
    empty_rot_x: FloatProperty(
        name="X",
        description="X rotation of the empty parent",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION',
        update=update_empty_transform
    )
    
    empty_rot_y: FloatProperty(
        name="Y",
        description="Y rotation of the empty parent",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION',
        update=update_empty_transform
    )
    
    empty_rot_z: FloatProperty(
        name="Z",
        description="Z rotation of the empty parent",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION',
        update=update_empty_transform
    )
    
    last_imu_data: StringProperty(
        name="Last IMU Data",
        default="{}"
    )

# Register all property groups
def register():
    bpy.utils.register_class(ServerSettings)
    bpy.utils.register_class(DebugSettings)
    bpy.utils.register_class(CameraTrackingSettings)
    
    bpy.types.Scene.server_settings = bpy.props.PointerProperty(type=ServerSettings)
    bpy.types.Scene.debug_settings = bpy.props.PointerProperty(type=DebugSettings)
    bpy.types.Scene.camera_tracking = bpy.props.PointerProperty(type=CameraTrackingSettings)

# Unregister all property groups
def unregister():
    del bpy.types.Scene.server_settings
    del bpy.types.Scene.debug_settings
    del bpy.types.Scene.camera_tracking
    
    bpy.utils.unregister_class(CameraTrackingSettings)
    bpy.utils.unregister_class(DebugSettings)
    bpy.utils.unregister_class(ServerSettings)