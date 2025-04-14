import bpy
from bpy.types import Operator
from ..core import websocket_server

# Operator to start WebSocket server
class WS_OT_StartServer(Operator):
    bl_idname = "ws.start_server"
    bl_label = "Start Server"
    bl_description = "Start the WebSocket server for testing"
    
    def execute(self, context):
        # Get server settings
        settings = context.scene.server_settings
        ip = settings.ip_address
        port = settings.port
        
        # Start the server
        if websocket_server.start_server(ip, port):
            self.report({'INFO'}, f"WebSocket server started at {ip}:{port}")
            context.scene.debug_settings.connection_status = f"Server running at {ip}:{port}"
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to start WebSocket server")
            return {'CANCELLED'}

# Operator to stop WebSocket server
class WS_OT_StopServer(Operator):
    bl_idname = "ws.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the WebSocket server"
    
    def execute(self, context):
        if websocket_server.stop_server():
            self.report({'INFO'}, "WebSocket server stopped")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "WebSocket server is not running")
            return {'CANCELLED'}

# Operator to send a test message
class WS_OT_SendTestMessage(Operator):
    bl_idname = "ws.send_test_message"
    bl_label = "Send Test Message"
    bl_description = "Send a test message to connected clients"
    
    def execute(self, context):
        if websocket_server.send_test_message():
            self.report({'INFO'}, "Test message sent")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No clients connected")
            return {'CANCELLED'}

# Register all operators
classes = (
    WS_OT_StartServer,
    WS_OT_StopServer,
    WS_OT_SendTestMessage,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)