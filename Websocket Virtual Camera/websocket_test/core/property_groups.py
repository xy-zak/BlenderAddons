import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty
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

# Register all property groups
def register():
    bpy.utils.register_class(ServerSettings)
    bpy.utils.register_class(DebugSettings)
    
    bpy.types.Scene.server_settings = bpy.props.PointerProperty(type=ServerSettings)
    bpy.types.Scene.debug_settings = bpy.props.PointerProperty(type=DebugSettings)

# Unregister all property groups
def unregister():
    del bpy.types.Scene.server_settings
    del bpy.types.Scene.debug_settings
    
    bpy.utils.unregister_class(DebugSettings)
    bpy.utils.unregister_class(ServerSettings)