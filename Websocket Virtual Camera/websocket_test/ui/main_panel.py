# main_panel.py
import bpy
from bpy.types import Panel

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
        camera_tracking = context.scene.camera_tracking
        
        # Server controls
        box = layout.box()
        box.label(text="Server Settings:")
        
        row = box.row()
        row.prop(server_settings, "ip_address")
        
        row = box.row()
        row.prop(server_settings, "port")
        
        # Server status and control
        row = box.row()
        if hasattr(bpy.context.scene, "server_running") and bpy.context.scene.server_running:
            row.operator("ws.stop_server", icon='PAUSE')
            if server_settings.esp_connected:
                row.label(text="ESP Connected", icon='CHECKMARK')
            else:
                row.label(text="Server Running", icon='PLAY')
        else:
            row.operator("ws.start_server", icon='PLAY')
            row.label(text="Server Stopped", icon='X')
        
        # Connection info
        if hasattr(bpy.context.scene, "server_running") and bpy.context.scene.server_running:
            if server_settings.esp_connected:
                box.label(text=f"Connected to: {server_settings.esp_ip}")
            else:
                box.label(text="Waiting for ESP32 to connect...")
        
        # Test message button
        if hasattr(bpy.context.scene, "server_running") and bpy.context.scene.server_running and server_settings.esp_connected:
            row = box.row()
            row.operator("ws.send_test_message", icon='EXPORT')
        
        # Camera tracking settings
        box = layout.box()
        box.label(text="Hybrid Camera Setup:")

        # Add camera selection button
        row = box.row()
        row.prop(camera_tracking, "target_camera", text="Camera")
        row.operator("ws.set_active_camera", text="", icon='EYEDROPPER')
        
        # Camera selection buttons
        row = box.row(align=True)
        # Added these two lines for the buttons
        row.operator("ws.setup_hybrid_camera", icon='CAMERA_DATA')
        row.operator("ws.clear_hybrid_camera", icon='X')
        
        # Show target camera info if set
        if camera_tracking.target_camera:
            box.label(text=f"Target Camera: {camera_tracking.target_camera}")
            
            if camera_tracking.target_empty:
                box.label(text=f"Origin Empty: {camera_tracking.target_empty}")
                
                # Empty transform
                transform_box = box.box()
                transform_box.label(text="Origin Transform:")
                
                # Location
                col = transform_box.column(align=True)
                col.label(text="Location:")
                row = col.row(align=True)
                row.prop(camera_tracking, "empty_loc_x", text="X")
                row.prop(camera_tracking, "empty_loc_y", text="Y")
                row.prop(camera_tracking, "empty_loc_z", text="Z")
                
                # Rotation
                col = transform_box.column(align=True)
                col.label(text="Rotation:")
                row = col.row(align=True)
                row.prop(camera_tracking, "empty_rot_x", text="X")
                row.prop(camera_tracking, "empty_rot_y", text="Y")
                row.prop(camera_tracking, "empty_rot_z", text="Z")
                
                # Update button
                transform_box.operator("ws.update_empty_transform", icon='TRANSFORM')
            
            # Tracking settings
            tracking_box = box.box()
            tracking_box.label(text="IMU Tracking Settings:")
            
            # Enable/disable tracking
            row = tracking_box.row()
            row.prop(camera_tracking, "track_rotation", toggle=True)
            row.prop(camera_tracking, "track_location", toggle=True)
            
            # Factors
            col = tracking_box.column(align=True)
            if camera_tracking.track_rotation:
                col.prop(camera_tracking, "rotation_factor")
            if camera_tracking.track_location:
                col.prop(camera_tracking, "location_factor")
        
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
        help_box.label(text="ESP32 IMU Message Format:")
        help_box.label(text="{")
        help_box.label(text='  "type": "IMU",')
        help_box.label(text='  "rot_x": 0.0,')
        help_box.label(text='  "rot_y": 0.0,')
        help_box.label(text='  "rot_z": 0.0,')
        help_box.label(text='  "loc_x": 0.0,')
        help_box.label(text='  "loc_y": 0.0,')
        help_box.label(text='  "loc_z": 0.0,')
        help_box.label(text='  "timestamp": 1234567890')
        help_box.label(text="}")

# Register
classes = (
    WS_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Add a property to track server state
    bpy.types.Scene.server_running = bpy.props.BoolProperty(default=False)

def unregister():
    if hasattr(bpy.types.Scene, "server_running"):
        del bpy.types.Scene.server_running
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)