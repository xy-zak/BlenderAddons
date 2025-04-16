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
                transform_box.label(text="Origin Location:")
                
                # Location only
                col = transform_box.column(align=True)
                row = col.row(align=True)
                row.prop(camera_tracking, "empty_loc_x", text="X")
                row.prop(camera_tracking, "empty_loc_y", text="Y")
                row.prop(camera_tracking, "empty_loc_z", text="Z")
            
            # Rotation offset (new section)
            offset_box = box.box()
            offset_box.label(text="Rotation Offset (degrees):")
            
            # Rotation offset properties
            col = offset_box.column(align=True)
            row = col.row(align=True)
            row.prop(camera_tracking, "rotation_offset_x", text="X")
            row.prop(camera_tracking, "rotation_offset_y", text="Y")
            row.prop(camera_tracking, "rotation_offset_z", text="Z")
            
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

# Debug panel
class WS_PT_DebugPanel(Panel):
    bl_label = "Debug"
    bl_idname = "WS_PT_DebugPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        debug_settings = context.scene.debug_settings
        camera_tracking = context.scene.camera_tracking
        
        # Simulation section
        box = layout.box()
        box.label(text="Simulation Mode:")
        
        row = box.row()
        row.prop(debug_settings, "debug_mode", text="Enable Simulation")
        
        if debug_settings.debug_mode:
            row = box.row()
            row.prop(debug_settings, "require_hybrid", text="Require Hybrid Setup")
            
            row = box.row(align=True)
            if debug_settings.debug_simulation_active:
                row.operator("ws.stop_debug_simulation", icon='PAUSE')
                row.label(text="Simulation Running", icon='PLAY')
            else:
                row.operator("ws.start_debug_simulation", icon='PLAY')
                
            # Single Frame IMU Data
            if not debug_settings.debug_simulation_active:
                box.operator("ws.send_debug_frame", icon='CAMERA_DATA')
        
        # Debug info
        box = layout.box()
        box.prop(debug_settings, "show_debug", text="Show Debug Info")
        
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

# Message formats panel
class WS_PT_MessageFormatsPanel(Panel):
    bl_label = "JSON Message Formats"
    bl_idname = "WS_PT_MessageFormatsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Available Message Types:")

# IMU sub-panel
class WS_PT_IMUMessagePanel(Panel):
    bl_label = "IMU Rotation and Location"
    bl_idname = "WS_PT_IMUMessagePanel"
    bl_parent_id = "WS_PT_MessageFormatsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="{")
        box.label(text='  "type": "IMU",')
        box.label(text='  "rot_x": 0.0,')
        box.label(text='  "rot_y": 0.0,')
        box.label(text='  "rot_z": 0.0,')
        box.label(text='  "loc_x": 0.0,')
        box.label(text='  "loc_y": 0.0,')
        box.label(text='  "loc_z": 0.0,')
        box.label(text='  "timestamp": 1234567890')
        box.label(text="}")

# Aperture/Zoom sub-panel
class WS_PT_ApertureMessagePanel(Panel):
    bl_label = "Aperture, Focal Distance and Zoom"
    bl_idname = "WS_PT_ApertureMessagePanel"
    bl_parent_id = "WS_PT_MessageFormatsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="{")
        box.label(text='  "type": "CAMERA",')
        box.label(text='  "aperture": 2.8,')
        box.label(text='  "focal_length": 50.0,')
        box.label(text='  "focus_distance": 3.0,')
        box.label(text='  "timestamp": 1234567890')
        box.label(text="}")

# Exposure sub-panel
class WS_PT_ExposureMessagePanel(Panel):
    bl_label = "Exposure Dial"
    bl_idname = "WS_PT_ExposureMessagePanel"
    bl_parent_id = "WS_PT_MessageFormatsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="{")
        box.label(text='  "type": "EXPOSURE",')
        box.label(text='  "ev_adjust": 1.5,')
        box.label(text='  "timestamp": 1234567890')
        box.label(text="}")

# Calibration sub-panel
class WS_PT_CalibrationMessagePanel(Panel):
    bl_label = "Calibration Trigger"
    bl_idname = "WS_PT_CalibrationMessagePanel"
    bl_parent_id = "WS_PT_MessageFormatsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="{")
        box.label(text='  "type": "CALIBRATION",')
        box.label(text='  "action": "start",')
        box.label(text='  "target": "imu",')
        box.label(text='  "timestamp": 1234567890')
        box.label(text="}")

# Register
classes = (
    WS_PT_MainPanel,
    WS_PT_DebugPanel,
    WS_PT_MessageFormatsPanel,
    WS_PT_IMUMessagePanel,
    WS_PT_ApertureMessagePanel,
    WS_PT_ExposureMessagePanel,
    WS_PT_CalibrationMessagePanel,
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