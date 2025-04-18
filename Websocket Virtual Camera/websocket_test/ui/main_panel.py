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
        
        # Hybrid camera controls
        box = layout.box()
        box.label(text="Hybrid Camera Setup:")
        
        # Check if shared origin exists
        has_origin = camera_tracking.shared_origin_name and camera_tracking.shared_origin_name in bpy.data.objects
        
        # Create shared origin button or show its name
        if not has_origin:
            row = box.row()
            row.operator("ws.create_shared_origin", icon='EMPTY_AXIS')
        else:
            row = box.row()
            row.label(text=f"Origin: {camera_tracking.shared_origin_name}")
            
            # Origin Location when it exists
            transform_box = box.box()
            transform_box.label(text="Origin Location:")
            
            # Location controls
            col = transform_box.column(align=True)
            row = col.row(align=True)
            row.prop(camera_tracking, "empty_loc_x", text="X")
            row.prop(camera_tracking, "empty_loc_y", text="Y")
            row.prop(camera_tracking, "empty_loc_z", text="Z")
            
            # Add Hybrid Camera button
            row = box.row()
            row.operator("ws.spawn_hybrid_camera", icon='CAMERA_DATA')
            
            # Rename Cameras button
            if len(camera_tracking.cameras) > 0:
                row = box.row()
                row.operator("ws.rename_hybrid_cameras", icon='GREASEPENCIL')
            
            # Camera list with expandable details
            if len(camera_tracking.cameras) > 0:
                camera_box = box.box()
                camera_box.label(text="Hybrid Cameras:")
                
                for i, cam in enumerate(camera_tracking.cameras):
                    # Get the camera object if it exists
                    camera_obj = None
                    if cam.camera_name and cam.camera_name in bpy.data.objects:
                        camera_obj = bpy.data.objects[cam.camera_name]
                    
                    # Camera entry
                    row = camera_box.row(align=True)
                    
                    # Camera ID and expandable UI
                    cam_prop = f"camera_{i}_expanded"
                    if not hasattr(bpy.types.Scene, cam_prop):
                        setattr(bpy.types.Scene, cam_prop, bpy.props.BoolProperty(default=False))
                    
                    expanded = getattr(context.scene, cam_prop, False)
                    icon = 'TRIA_DOWN' if expanded else 'TRIA_RIGHT'
                    
                    # Click to expand/collapse
                    op = row.operator(
                        "wm.context_toggle", 
                        text="", 
                        icon=icon
                    )
                    op.data_path = f"scene.{cam_prop}"
                    
                    # Camera ID
                    row.label(text=cam.cam_id, icon='OUTLINER_DATA_CAMERA')
                    
                    # Remove button
                    op = row.operator("ws.remove_camera_association", text="", icon='TRASH')
                    op.index = i
                    
                    # If expanded, show details
                    if expanded and camera_obj:
                        details_box = camera_box.box()
                        
                        # Location
                        loc_row = details_box.row()
                        loc_row.label(text="Location:")
                        loc_col = details_box.column(align=True)
                        loc_col.label(text=f"X: {camera_obj.location.x:.3f}")
                        loc_col.label(text=f"Y: {camera_obj.location.y:.3f}")
                        loc_col.label(text=f"Z: {camera_obj.location.z:.3f}")
                        
                        # Rotation
                        rot_row = details_box.row()
                        rot_row.label(text="Rotation (degrees):")
                        rot_col = details_box.column(align=True)
                        rot_col.label(text=f"X: {camera_obj.rotation_euler.x * 57.2958:.1f}°")
                        rot_col.label(text=f"Y: {camera_obj.rotation_euler.y * 57.2958:.1f}°")
                        rot_col.label(text=f"Z: {camera_obj.rotation_euler.z * 57.2958:.1f}°")
                        
                        # Camera specific properties
                        if camera_obj.data:
                            cam_row = details_box.row()
                            cam_row.label(text="Camera Properties:")
                            cam_col = details_box.column(align=True)
                            cam_col.label(text=f"Focal Length: {camera_obj.data.lens:.1f}mm")
                            cam_col.label(text=f"Aperture: {camera_obj.data.dof.aperture_fstop:.1f}")
                            
                            # Focus distance
                            if hasattr(camera_obj.data.dof, "focus_distance"):
                                focus_dist = camera_obj.data.dof.focus_distance
                                cam_col.label(text=f"Focus Distance: {focus_dist:.2f}m")
                            
                            # Add buttons for direct rendering and recording
                            btn_row = details_box.row(align=True)
                            
                            # Render button
                            render_op = btn_row.operator("ws.render_from_camera", text="Render", icon='RENDER_STILL')
                            render_op.cam_id = cam.cam_id
                            
                            # Don't show record button if already recording this camera
                            is_recording_this = (camera_tracking.recording_active and 
                                                camera_tracking.recording_camera_id == cam.cam_id)
                                                
                            if is_recording_this:
                                btn_row.operator("ws.stop_camera_recording", text="Stop Recording", icon='PAUSE')
                            else:
                                # Don't enable if another camera is recording
                                record_op = btn_row.operator("ws.start_camera_recording", 
                                                           text="Record", 
                                                           icon='REC',
                                                           enabled=not camera_tracking.recording_active)
                                record_op.cam_id = cam.cam_id
                            
                            # Include time since last calibration
                            last_time = context.scene.camera_tracking.last_imu_data
                            if last_time and last_time != "{}":
                                import json
                                import time
                                try:
                                    data = json.loads(last_time)
                                    if "timestamp" in data:
                                        timestamp = data.get("timestamp", 0) / 1000  # Convert ms to seconds
                                        seconds_elapsed = int(time.time() - timestamp)
                                        minutes = seconds_elapsed // 60
                                        seconds = seconds_elapsed % 60
                                        calibration_text = f"{minutes:02d}:{seconds:02d}"
                                        details_box.label(text=f"Time Since Calibration: {calibration_text}")
                                except:
                                    pass
            else:
                box.label(text="No cameras added. Click 'Spawn Hybrid Camera' to add one.")
        
        # Global Rotation Offset and Tracking settings
        if len(camera_tracking.cameras) > 0 or has_origin:
            settings_box = layout.box()
            settings_box.label(text="Camera Tracking Settings:")
            
            # Rotation offset (always show)
            offset_box = settings_box.box()
            offset_box.label(text="Rotation Offset (degrees):")
            
            # Rotation offset properties
            col = offset_box.column(align=True)
            row = col.row(align=True)
            row.prop(camera_tracking, "rotation_offset_x", text="X")
            row.prop(camera_tracking, "rotation_offset_y", text="Y")
            row.prop(camera_tracking, "rotation_offset_z", text="Z")
            
            # Tracking settings
            tracking_box = settings_box.box()
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
                
            # Recording settings
            if len(camera_tracking.cameras) > 0:
                record_box = settings_box.box()
                record_box.label(text="Camera Recording Settings:")
                
                # Recording status
                if camera_tracking.recording_active:
                    status_row = record_box.row()
                    status_row.alert = True
                    status_row.label(text=f"Recording Active: {camera_tracking.recording_camera_id}", icon='REC')
                    
                    # Stop button
                    status_row.operator("ws.stop_camera_recording", text="Stop", icon='PAUSE')
                    
                    # Show recording frame range
                    frame_row = record_box.row()
                    frame_row.label(text=f"Recording frames: {camera_tracking.recording_start_frame} to {camera_tracking.recording_end_frame}")
                else:
                    # Recording options
                    row = record_box.row()
                    row.prop(camera_tracking, "recording_end_frame", text="End Frame")
                    
                    # Recording properties to include
                    props_row = record_box.row(align=True)
                    props_row.label(text="Record:")
                    props_row.prop(camera_tracking, "record_aperture", text="Aperture", toggle=True)
                    props_row.prop(camera_tracking, "record_focal_length", text="Zoom", toggle=True)
                    props_row.prop(camera_tracking, "record_focus_distance", text="Focus", toggle=True)

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
            
            # Target camera ID for simulation
            row = box.row()
            row.label(text="Target Camera ID:")
            row.prop(debug_settings, "target_cam_id", text="")
            
            row = box.row(align=True)
            if debug_settings.debug_simulation_active:
                row.operator("ws.stop_debug_simulation", icon='PAUSE')
                row.label(text="Simulation Running", icon='PLAY')
            else:
                row.operator("ws.start_debug_simulation", icon='PLAY')
                
            # Single Frame IMU Data
            if not debug_settings.debug_simulation_active:
                box.operator("ws.send_debug_frame", icon='CAMERA_DATA')
                
            # Add additional simulation options
            sim_box = box.box()
            sim_box.label(text="Message Simulation:")
            
            col = sim_box.column()
            
            # Render message simulation
            render_row = col.row(align=True)
            op = render_row.operator("ws.simulate_render_request", icon='RENDER_STILL')
            
            # Record message simulation
            record_row = col.row(align=True)
            
            # Show appropriate button based on recording state
            if context.scene.camera_tracking.recording_active:
                record_row.operator("ws.simulate_record_stop", icon='PAUSE')
            else:
                record_row.operator("ws.simulate_record_start", icon='REC')
        
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
        box.label(text='  "cam_id": "cam1",')  # Added cam_id field
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
        box.label(text='  "cam_id": "cam1",')  # Added cam_id field
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
        box.label(text='  "cam_id": "cam1",')  # Added cam_id field
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
        box.label(text='  "cam_id": "cam1",')  # Added cam_id field
        box.label(text='  "action": "start",')
        box.label(text='  "target": "imu",')
        box.label(text='  "timestamp": 1234567890')
        box.label(text="}")

# Render trigger sub-panel
class WS_PT_RenderMessagePanel(Panel):
    bl_label = "Render Trigger"
    bl_idname = "WS_PT_RenderMessagePanel"
    bl_parent_id = "WS_PT_MessageFormatsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="{")
        box.label(text='  "type": "RENDER",')
        box.label(text='  "cam_id": "cam1",')
        box.label(text='  "action": "trigger",')
        box.label(text='  "timestamp": 1234567890')
        box.label(text="}")

# Recording sub-panel
class WS_PT_RecordMessagePanel(Panel):
    bl_label = "Recording Control"
    bl_idname = "WS_PT_RecordMessagePanel"
    bl_parent_id = "WS_PT_MessageFormatsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WebSocket'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="{")
        box.label(text='  "type": "RECORD",')
        box.label(text='  "cam_id": "cam1",')
        box.label(text='  "action": "start",  // or "stop"')
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
    WS_PT_RenderMessagePanel,
    WS_PT_RecordMessagePanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Add a property to track server state
    bpy.types.Scene.server_running = bpy.props.BoolProperty(default=False)
    
    # Register dynamic properties for camera expansion states
    for i in range(10):  # Pre-register enough for typical use (10 cameras)
        cam_prop = f"camera_{i}_expanded"
        if not hasattr(bpy.types.Scene, cam_prop):
            setattr(bpy.types.Scene, cam_prop, bpy.props.BoolProperty(default=False))

def unregister():
    # Clean up dynamic properties
    for attr in dir(bpy.types.Scene):
        if attr.startswith("camera_") and attr.endswith("_expanded"):
            delattr(bpy.types.Scene, attr)
            
    if hasattr(bpy.types.Scene, "server_running"):
        del bpy.types.Scene.server_running
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)