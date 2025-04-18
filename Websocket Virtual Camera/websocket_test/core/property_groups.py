import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, FloatProperty, CollectionProperty, PointerProperty
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
    
    # Debug simulation settings - renamed to simulation
    debug_mode: BoolProperty(
        name="Enable Simulation",
        description="Enable simulation tools for testing without ESP32",
        default=True
    )
    
    debug_simulation_active: BoolProperty(
        name="Simulation Active",
        description="Indicates if simulation is running",
        default=False
    )
    
    require_hybrid: BoolProperty(
        name="Require Hybrid Setup",
        description="If enabled, simulation tools will only work with hybrid camera setup",
        default=False
    )
    
    # Added for multi-camera simulation
    target_cam_id: StringProperty(
        name="Target Camera ID",
        description="Camera ID to send simulated data to (leave empty for all cameras)",
        default=""
    )

# Single camera association for collection
class CameraAssociation(PropertyGroup):
    cam_id: StringProperty(
        name="Camera ID",
        description="Unique identifier for this camera received from ESP32",
        default="",
        # Add update function to rename camera object when cam_id changes
        update=lambda self, context: rename_camera_object(self, context)
    )
    
    camera_name: StringProperty(
        name="Camera Object",
        description="Blender camera object name",
        default=""
    )
    
    is_setup: BoolProperty(
        name="Is Hybrid Setup",
        description="Whether this camera is set up as a hybrid camera",
        default=False
    )
    
    empty_name: StringProperty(
        name="Origin Empty",
        description="Empty parent object name",
        default=""
    )

# Function to update empty location when properties change
def update_empty_location(self, context):
    """Update the shared origin empty's location when properties change"""
    camera_tracking = context.scene.camera_tracking
    
    # Update the shared origin empty if it exists
    if camera_tracking.shared_origin_name and camera_tracking.shared_origin_name in bpy.data.objects:
        try:
            empty = bpy.data.objects[camera_tracking.shared_origin_name]
            empty.location.x = camera_tracking.empty_loc_x
            empty.location.y = camera_tracking.empty_loc_y
            empty.location.z = camera_tracking.empty_loc_z
        except:
            # Silently fail - this prevents errors in the UI
            pass

def rename_camera_object(self, context):
    """Rename the camera object when cam_id changes"""
    # Only do this if we have a camera object
    if self.camera_name and self.camera_name in bpy.data.objects:
        camera_obj = bpy.data.objects[self.camera_name]
        
        # Rename only if not empty and different from current name
        if self.cam_id and camera_obj.name != self.cam_id:
            camera_obj.name = self.cam_id
            # Update the reference in case Blender changes the name (adds .001, etc.)
            self.camera_name = camera_obj.name

# Camera tracking settings
class CameraTrackingSettings(PropertyGroup):
    # Shared origin empty for all cameras
    shared_origin_name: StringProperty(
        name="Shared Origin",
        description="Name of the shared origin empty for all hybrid cameras",
        default=""
    )
    
    # Collection of cameras
    cameras: CollectionProperty(
        type=CameraAssociation,
        name="Camera Associations"
    )
    
    active_camera_index: IntProperty(
        name="Active Camera Index",
        default=0
    )
    
    # Legacy fields kept for compatibility 
    target_camera: StringProperty(
        name="Target Camera",
        description="Camera to control with IMU data (legacy field)",
        default=""
    )
    
    target_empty: StringProperty(
        name="Target Empty",
        description="Empty parent of the target camera (legacy field)",
        default=""
    )
    
    # Global tracking settings (shared across all cameras)
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
    
    # Empty location properties (shared across all cameras)
    empty_loc_x: FloatProperty(
        name="X",
        description="X location of the empty parent",
        default=0.0,
        update=lambda self, context: update_empty_location(self, context)
    )
    
    empty_loc_y: FloatProperty(
        name="Y",
        description="Y location of the empty parent",
        default=0.0,
        update=lambda self, context: update_empty_location(self, context)
    )
    
    empty_loc_z: FloatProperty(
        name="Z",
        description="Z location of the empty parent",
        default=0.0,
        update=lambda self, context: update_empty_location(self, context)
    )
    
    # Rotation offset properties (shared across all cameras)
    rotation_offset_x: FloatProperty(
        name="X Offset",
        description="X rotation offset applied to camera (degrees)",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION'
    )
    
    rotation_offset_y: FloatProperty(
        name="Y Offset",
        description="Y rotation offset applied to camera (degrees)",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION'
    )
    
    rotation_offset_z: FloatProperty(
        name="Z Offset",
        description="Z rotation offset applied to camera (degrees)",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION'
    )
    
    last_imu_data: StringProperty(
        name="Last IMU Data",
        default="{}"
    )

    recording_active: BoolProperty(
        name="Recording Active",
        description="Whether camera animation recording is active",
        default=False
    )
    
    recording_camera_id: StringProperty(
        name="Recording Camera ID",
        description="ID of the camera currently being recorded",
        default=""
    )
    
    recording_start_frame: IntProperty(
        name="Recording Start Frame",
        description="Frame where recording started",
        default=1
    )
    
    recording_end_frame: IntProperty(
        name="Recording End Frame",
        description="Frame where recording will automatically stop",
        default=250
    )
    
    record_aperture: BoolProperty(
        name="Record Aperture",
        description="Whether to record aperture changes",
        default=True
    )
    
    record_focal_length: BoolProperty(
        name="Record Focal Length",
        description="Whether to record focal length changes",
        default=True
    )
    
    record_focus_distance: BoolProperty(
        name="Record Focus Distance",
        description="Whether to record focus distance changes",
        default=True
    )

# Register all property groups
def register():
    bpy.utils.register_class(CameraAssociation)
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
    bpy.utils.unregister_class(CameraAssociation)