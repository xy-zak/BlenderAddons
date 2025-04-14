import bpy
from bpy.types import Panel
from ..core import websocket_server

# Main panel
class WS_PT_MainPanel(Panel):
    bl_label = "WebSocket Test"
    bl_idname = "WS_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    
    def draw(self, context):
        layout = self.layout
        server_settings = context.scene.server_settings
        debug_settings = context.scene.debug_settings
        
        # Server controls
        box = layout.box()
        box.label(text="Server Settings:")
        
        row = box.row()
        row.prop(server_settings, "ip_address")
        
        row = box.row()
        row.prop(server_settings, "port")
        
        # Server status and control
        row = box.row()
        if websocket_server.is_server_running:
            row.operator("ws.stop_server", icon='PAUSE')
            if server_settings.esp_connected:
                row.label(text="ESP Connected", icon='CHECKMARK')
            else:
                row.label(text="Server Running", icon='PLAY')
        else:
            row.operator("ws.start_server", icon='PLAY')
            row.label(text="Server Stopped", icon='X')
        
        # Connection info
        if websocket_server.is_server_running:
            if server_settings.esp_connected:
                box.label(text=f"Connected to: {server_settings.esp_ip}")
            else:
                box.label(text="Waiting for ESP32 to connect...")
        
        # Test message button
        if websocket_server.is_server_running and server_settings.esp_connected:
            row = box.row()
            row.operator("ws.send_test_message", icon='EXPORT')
        
        # Debug info
        box = layout.box()
        box.prop(debug_settings, "show_debug")
        
        if debug_settings.show_debug:
            # Show connection status
            row = box.row()
            row.label(text=f"Status: {debug_settings.connection_status}")
            
            # Show last message
            box.label(text="Last Message:")
            box.label(text=debug_settings.last_message[:64] + ("..." if len(debug_settings.last_message) > 64 else ""))
            
            # Show message history
            if debug_settings.message_log:
                box.separator()
                box.label(text="Recent Messages:")
                for line in debug_settings.message_log.split("\n"):
                    box.label(text=line)
        
        # ESP32 info
        help_box = layout.box()
        help_box.label(text="ESP32 Example Message:")
        help_box.label(text="{")
        help_box.label(text='  "sensor": "test",')
        help_box.label(text='  "value": 123')
        help_box.label(text="}")

# Register
classes = (
    WS_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)