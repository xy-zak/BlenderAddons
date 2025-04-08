import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, BoolProperty
from bpy.types import PropertyGroup

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

# Data structure for objects to record keyframes for
class OSCRecordObject(PropertyGroup):
    target_object: PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        description="Object to record keyframes for"
    )
    
    is_active: BoolProperty(
        name="Active",
        description="Enable/disable recording for this object",
        default=True
    )
    
    record_location: BoolProperty(
        name="Location",
        description="Record keyframes for location",
        default=True
    )
    
    record_rotation: BoolProperty(
        name="Rotation",
        description="Record keyframes for rotation",
        default=True
    )
    
    record_scale: BoolProperty(
        name="Scale",
        description="Record keyframes for scale",
        default=True
    )
    
    record_custom_properties: BoolProperty(
        name="Custom Properties",
        description="Record keyframes for custom properties",
        default=False
    )
    
    custom_properties: StringProperty(
        name="Custom Properties",
        description="Comma-separated list of custom properties to record",
        default=""
    )

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

    interpolate_keyframes: BoolProperty(
        name="Interpolate Missing Frames",
        description="Fill in missing frames using bezier interpolation after recording",
        default=False
    )

    interpolation_gap_threshold: IntProperty(
        name="Max Frame Gap",
        description="Maximum gap between frames to interpolate (in frames)",
        default=5,
        min=2,
        max=20
    )
    
    # Add frame rate options
    record_frame_rates = [
        ('12', "12 fps", "Record at 12 frames per second"),
        ('15', "15 fps", "Record at 15 frames per second"),
        ('24', "24 fps", "Record at 24 frames per second"),
        ('30', "30 fps", "Record at 30 frames per second"),
        ('48', "48 fps", "Record at 48 frames per second"),
        ('60', "60 fps", "Record at 60 frames per second"),
    ]
    
    keyframe_rate: EnumProperty(
        name="Keyframe Rate",
        description="Rate at which to record keyframes",
        items=record_frame_rates,
        default='30'
    )
    
    # Post-processing smoothing options
    post_smooth_keyframes: BoolProperty(
        name="Apply Gaussian Smoothing",
        description="Apply smoothing to keyframes after recording stops",
        default=False
    )
    
    post_smooth_factor: FloatProperty(
        name="Smoothing Factor",
        description="Strength of the post-recording smoothing (1.0 = standard)",
        default=1.0,
        min=0.1,
        max=5.0,
        precision=1
    )
    
    remove_jitter: BoolProperty(
        name="Remove Rogue Keyframes",
        description="Remove keyframes that appear to be jitter outliers",
        default=False
    )
    
    jitter_threshold: FloatProperty(
        name="Jitter Threshold",
        description="How much a keyframe must deviate to be considered jitter (smaller = more aggressive)",
        default=0.05,
        min=0.001,
        max=0.5,
        precision=3
    )
    
    # Auto-stop at end of frame range
    auto_stop_at_end: BoolProperty(
        name="Auto-Stop at End Frame",
        description="Automatically stop recording when reaching the end of the frame range",
        default=True
    )
    
    # Smoothing related properties
    enable_smoothing: BoolProperty(
        name="Enable Live Smoothing",
        description="Apply smoothing to incoming OSC values",
        default=False
    )
    
    smoothing_method_items = [
        ('buffer', "Buffer", "Average over multiple values"),
        ('threshold', "Threshold", "Only update when change exceeds threshold"),
        ('both', "Both", "Use both buffer and threshold methods"),
    ]
    
    smoothing_method: EnumProperty(
        name="Smoothing Method",
        description="Method to use for smoothing values",
        items=smoothing_method_items,
        default='buffer'
    )
    
    smoothing_buffer_size: IntProperty(
        name="Buffer Size",
        description="Number of values to average for buffer smoothing",
        default=5,
        min=2,
        max=30
    )
    
    smoothing_threshold: FloatProperty(
        name="Threshold",
        description="Minimum change required to update value",
        default=0.01,
        min=0.0001,
        max=1.0,
        precision=4
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

# Register all property groups
def register():
    bpy.utils.register_class(OSCMapping)
    bpy.utils.register_class(OSCRecordObject)
    bpy.utils.register_class(OSCSettings)
    bpy.utils.register_class(OSCDebugSettings)
    
    bpy.types.Scene.osc_mappings = bpy.props.CollectionProperty(type=OSCMapping)
    bpy.types.Scene.osc_record_objects = bpy.props.CollectionProperty(type=OSCRecordObject)
    bpy.types.Scene.osc_settings = bpy.props.PointerProperty(type=OSCSettings)
    bpy.types.Scene.osc_debug = bpy.props.PointerProperty(type=OSCDebugSettings)

# Unregister all property groups
def unregister():
    del bpy.types.Scene.osc_mappings
    del bpy.types.Scene.osc_record_objects
    del bpy.types.Scene.osc_settings
    del bpy.types.Scene.osc_debug
    
    bpy.utils.unregister_class(OSCDebugSettings)
    bpy.utils.unregister_class(OSCSettings)
    bpy.utils.unregister_class(OSCRecordObject)
    bpy.utils.unregister_class(OSCMapping)