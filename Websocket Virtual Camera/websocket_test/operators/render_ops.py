# render_ops.py
import bpy
from bpy.types import Operator
import json
import time
from bpy.app import timers

# Import WebSocket modules
def get_websocket_module():
    from ..core import simple_websocket
    return simple_websocket

# Operator to trigger a render from a specific camera
class WS_OT_RenderFromCamera(Operator):
    bl_idname = "ws.render_from_camera"
    bl_label = "Render from Camera"
    bl_description = "Trigger a render from the selected camera"
    
    cam_id: bpy.props.StringProperty(
        name="Camera ID",
        description="ID of the camera to render from",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        # Only enable if we have cameras
        return len(camera_tracking.cameras) > 0
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        # Find the camera with matching ID
        target_camera = None
        for cam in camera_tracking.cameras:
            if cam.cam_id == self.cam_id and cam.camera_name in bpy.data.objects:
                target_camera = bpy.data.objects[cam.camera_name]
                break
        
        if not target_camera:
            self.report({'WARNING'}, f"Camera with ID '{self.cam_id}' not found")
            return {'CANCELLED'}
        
        try:
            # Set as active camera for the current scene
            context.scene.camera = target_camera
            
            # Trigger render
            bpy.ops.render.render('INVOKE_DEFAULT')
            
            self.report({'INFO'}, f"Rendering from camera '{self.cam_id}'")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error rendering: {str(e)}")
            return {'CANCELLED'}

# Timer function to monitor animation playback end
def check_animation_end():
    scene = bpy.context.scene
    camera_tracking = scene.camera_tracking
    
    # Check if we're still recording
    if not camera_tracking.recording_active:
        return None  # Stop timer
    
    # Check if we've reached the end frame
    if scene.frame_current >= camera_tracking.recording_end_frame:
        # Stop recording
        camera_tracking.recording_active = False
        
        # Stop animation playback
        if bpy.context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=False)
        
        # Send notification to ESP
        websocket = get_websocket_module()
        
        # Create message
        message = {
            "type": "RECORD",
            "status": "stopped",
            "reason": "end_frame_reached",
            "cam_id": camera_tracking.recording_camera_id,
            "timestamp": int(bpy.time.time() * 1000)
        }
        
        # Convert to JSON and send
        json_str = json.dumps(message)
        
        # Send to all clients
        for client in websocket.connected_clients.copy():
            try:
                if client in websocket.client_handshake_complete and websocket.client_handshake_complete[client]:
                    frame = websocket.encode_frame(json_str)
                    client.send(frame)
            except:
                pass
        
        # Log the action
        print(f"WebSocket Test: Recording stopped at frame {scene.frame_current}")
        
        return None  # Stop timer
    
    # Continue timer
    return 0.5  # Check every half second

# Handler for frame change during recording
def record_camera_handler(scene):
    # Only process if recording is active
    if not scene.camera_tracking.recording_active:
        return
    
    camera_tracking = scene.camera_tracking
    cam_id = camera_tracking.recording_camera_id
    
    # Find the camera with matching ID
    target_camera = None
    for cam in camera_tracking.cameras:
        if cam.cam_id == cam_id and cam.camera_name in bpy.data.objects:
            target_camera = bpy.data.objects[cam.camera_name]
            break
    
    if not target_camera:
        print(f"WebSocket Test: Recording camera '{cam_id}' not found")
        return
    
    # Current frame
    frame = scene.frame_current
    
    # Debug output to confirm we're getting called
    print(f"Recording camera '{cam_id}' at frame {frame} - pos: {target_camera.location}, rot: {target_camera.rotation_euler}")
    
    # Insert keyframes for location and rotation using current values
    target_camera.keyframe_insert(data_path="location", frame=frame)
    target_camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    
    # Insert keyframes for camera properties
    if target_camera.data:
        # Focal length (zoom)
        if camera_tracking.record_focal_length:
            target_camera.data.keyframe_insert(data_path="lens", frame=frame)
        
        # Aperture
        if camera_tracking.record_aperture and hasattr(target_camera.data.dof, "aperture_fstop"):
            target_camera.data.dof.keyframe_insert(data_path="aperture_fstop", frame=frame)
        
        # Focus distance
        if camera_tracking.record_focus_distance and hasattr(target_camera.data.dof, "focus_distance"):
            target_camera.data.dof.keyframe_insert(data_path="focus_distance", frame=frame)

# Operator to start recording camera animation
class WS_OT_StartCameraRecording(Operator):
    bl_idname = "ws.start_camera_recording"
    bl_label = "Start Camera Recording"
    bl_description = "Start recording camera animation keyframes"
    
    cam_id: bpy.props.StringProperty(
        name="Camera ID",
        description="ID of the camera to record",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        # Only enable if we have cameras and not already recording
        return len(camera_tracking.cameras) > 0 and not camera_tracking.recording_active
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        scene = context.scene
        
        # Find the camera with matching ID
        target_camera = None
        for cam in camera_tracking.cameras:
            if cam.cam_id == self.cam_id and cam.camera_name in bpy.data.objects:
                target_camera = bpy.data.objects[cam.camera_name]
                break
        
        if not target_camera:
            self.report({'WARNING'}, f"Camera with ID '{self.cam_id}' not found")
            return {'CANCELLED'}
        
        try:
            # Set up recording
            camera_tracking.recording_active = True
            camera_tracking.recording_camera_id = self.cam_id
            camera_tracking.recording_start_frame = scene.frame_current
            
            # If no ESP is connected and debug mode is enabled, start simulation
            if (not context.scene.server_settings.esp_connected and 
                context.scene.debug_settings.debug_mode):
                ensure_simulation_running(self.cam_id)
            
            # Insert initial keyframes now (important for first frame)
            # Insert keyframes for location and rotation
            target_camera.keyframe_insert(data_path="location", frame=scene.frame_current)
            target_camera.keyframe_insert(data_path="rotation_euler", frame=scene.frame_current)
            
            # Insert keyframes for camera properties
            if target_camera.data:
                # Focal length (zoom)
                if camera_tracking.record_focal_length:
                    target_camera.data.keyframe_insert(data_path="lens", frame=scene.frame_current)
                
                # Aperture
                if camera_tracking.record_aperture and hasattr(target_camera.data.dof, "aperture_fstop"):
                    target_camera.data.dof.keyframe_insert(data_path="aperture_fstop", frame=scene.frame_current)
                
                # Focus distance
                if camera_tracking.record_focus_distance and hasattr(target_camera.data.dof, "focus_distance"):
                    target_camera.data.dof.keyframe_insert(data_path="focus_distance", frame=scene.frame_current)
            
            # Add frame change handler if not already added
            if record_camera_handler not in bpy.app.handlers.frame_change_post:
                bpy.app.handlers.frame_change_post.append(record_camera_handler)
            
            # Start animation playback
            if not context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
            
            # Start timer to check for end frame
            if not timers.is_registered(check_animation_end):
                timers.register(check_animation_end)
            
            self.report({'INFO'}, f"Started recording camera '{self.cam_id}'")
            
            # Force a redraw of the UI to show the recording status
            for area in bpy.context.screen.areas:
                area.tag_redraw()
                
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error starting recording: {str(e)}")
            return {'CANCELLED'}

# Operator to stop recording camera animation
class WS_OT_StopCameraRecording(Operator):
    bl_idname = "ws.stop_camera_recording"
    bl_label = "Stop Camera Recording"
    bl_description = "Stop recording camera animation keyframes"
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        # Only enable if we're currently recording
        return camera_tracking.recording_active
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        try:
            # Stop recording
            camera_tracking.recording_active = False
            
            # Remove frame change handler
            if record_camera_handler in bpy.app.handlers.frame_change_post:
                bpy.app.handlers.frame_change_post.remove(record_camera_handler)
            
            # Stop animation playback
            if context.screen.is_animation_playing:
                bpy.ops.screen.animation_cancel(restore_frame=False)
            
            self.report({'INFO'}, f"Stopped recording camera '{camera_tracking.recording_camera_id}'")
            
            # Reset recording camera
            cam_id = camera_tracking.recording_camera_id
            camera_tracking.recording_camera_id = ""
            
            # Send notification to ESP
            websocket = get_websocket_module()
            
            # Create message
            message = {
                "type": "RECORD",
                "status": "stopped",
                "reason": "user_stopped",
                "cam_id": cam_id,
                "timestamp": int(bpy.time.time() * 1000)
            }
            
            # Convert to JSON and send
            json_str = json.dumps(message)
            
            # Send to all clients
            for client in websocket.connected_clients.copy():
                try:
                    if client in websocket.client_handshake_complete and websocket.client_handshake_complete[client]:
                        frame = websocket.encode_frame(json_str)
                        client.send(frame)
                except:
                    pass
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error stopping recording: {str(e)}")
            return {'CANCELLED'}
        

# Operator to simulate a render request
class WS_OT_SimulateRenderRequest(Operator):
    bl_idname = "ws.simulate_render_request"
    bl_label = "Simulate Render Request"
    bl_description = "Simulate a render request from an ESP32"
    
    cam_id: bpy.props.StringProperty(
        name="Camera ID",
        description="ID of the camera to render from",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        # Only enable if we have cameras
        return len(camera_tracking.cameras) > 0
    
    def execute(self, context):
        # Get WebSocket module
        websocket = get_websocket_module()
        
        # Create render request data
        data = {
            "type": "RENDER",
            "cam_id": self.cam_id,
            "action": "trigger",
            "timestamp": int(time.time() * 1000)
        }
        
        # Process the request directly
        websocket.process_render_request(data)
        
        # Update debug info
        context.scene.debug_settings.last_message = json.dumps(data)
        
        # Add to message history
        if hasattr(websocket, "message_history"):
            websocket.message_history.insert(0, json.dumps(data))
            if len(websocket.message_history) > websocket.MAX_MESSAGE_HISTORY:
                websocket.message_history.pop()
            
            # Update message log
            log = "\n".join([f"[{i+1}] {msg[:100]}..." for i, msg in enumerate(websocket.message_history[:5])])
            context.scene.debug_settings.message_log = log
        
        self.report({'INFO'}, f"Simulated render request for camera '{self.cam_id}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Pre-populate camera ID from target cam field
        self.cam_id = context.scene.debug_settings.target_cam_id
        
        # If empty, use first camera
        if not self.cam_id and len(context.scene.camera_tracking.cameras) > 0:
            self.cam_id = context.scene.camera_tracking.cameras[0].cam_id
            
        # Show dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

# Operator to simulate a record start request
class WS_OT_SimulateRecordStartRequest(Operator):
    bl_idname = "ws.simulate_record_start"
    bl_label = "Simulate Record Start"
    bl_description = "Simulate a record start request from an ESP32"
    
    cam_id: bpy.props.StringProperty(
        name="Camera ID",
        description="ID of the camera to start recording",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        # Only enable if we have cameras and not recording
        return len(camera_tracking.cameras) > 0 and not camera_tracking.recording_active
    
    def execute(self, context):
        # Get WebSocket module
        websocket = get_websocket_module()
        
        # Create record request data
        data = {
            "type": "RECORD",
            "cam_id": self.cam_id,
            "action": "start",
            "timestamp": int(time.time() * 1000)
        }
        
        # Update debug info before processing
        context.scene.debug_settings.last_message = json.dumps(data)
        context.scene.debug_settings.connection_status = f"Simulating record start for camera '{self.cam_id}'"
        
        # Process the request directly
        websocket.process_record_request(data)
        
        # Add to message history
        if hasattr(websocket, "message_history"):
            websocket.message_history.insert(0, json.dumps(data))
            if len(websocket.message_history) > websocket.MAX_MESSAGE_HISTORY:
                websocket.message_history.pop()
            
            # Update message log
            log = "\n".join([f"[{i+1}] {msg[:100]}..." for i, msg in enumerate(websocket.message_history[:5])])
            context.scene.debug_settings.message_log = log
        
        # Force a redraw of the UI
        for area in bpy.context.screen.areas:
            area.tag_redraw()
        
        self.report({'INFO'}, f"Simulated record start for camera '{self.cam_id}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Pre-populate camera ID from target cam field
        self.cam_id = context.scene.debug_settings.target_cam_id
        
        # If empty, use first camera
        if not self.cam_id and len(context.scene.camera_tracking.cameras) > 0:
            self.cam_id = context.scene.camera_tracking.cameras[0].cam_id
            
        # Show dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

# Operator to simulate a record stop request
class WS_OT_SimulateRecordStopRequest(Operator):
    bl_idname = "ws.simulate_record_stop"
    bl_label = "Simulate Record Stop"
    bl_description = "Simulate a record stop request from an ESP32"
    
    @classmethod
    def poll(cls, context):
        # Only enable if we're currently recording
        return context.scene.camera_tracking.recording_active
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        cam_id = camera_tracking.recording_camera_id
        
        # Get WebSocket module
        websocket = get_websocket_module()
        
        # Create record request data
        data = {
            "type": "RECORD",
            "cam_id": cam_id,
            "action": "stop",
            "timestamp": int(time.time() * 1000)
        }
        
        # Process the request directly
        websocket.process_record_request(data)
        
        # Update debug info
        context.scene.debug_settings.last_message = json.dumps(data)
        
        # Add to message history
        if hasattr(websocket, "message_history"):
            websocket.message_history.insert(0, json.dumps(data))
            if len(websocket.message_history) > websocket.MAX_MESSAGE_HISTORY:
                websocket.message_history.pop()
            
            # Update message log
            log = "\n".join([f"[{i+1}] {msg[:100]}..." for i, msg in enumerate(websocket.message_history[:5])])
            context.scene.debug_settings.message_log = log
        
        self.report({'INFO'}, f"Simulated record stop for camera '{cam_id}'")
        return {'FINISHED'}
    
def ensure_simulation_running(cam_id):
    """Make sure simulation is running when recording starts for testing purposes"""
    import bpy
    
    # Only proceed if debug_mode is enabled
    if not bpy.context.scene.debug_settings.debug_mode:
        return
    
    # Get the server_ops module for simulation
    try:
        from . import server_ops
        
        # Check if simulation is already running
        if not server_ops._simulation_running:
            # Set the target camera ID
            bpy.context.scene.debug_settings.target_cam_id = cam_id
            
            # Start a new simulation with default circle pattern
            server_ops._simulation_running = True
            server_ops._animation_start_time = server_ops.time.time()
            server_ops._animation_pattern = "circle"
            
            # Start the timer if not already running
            if not bpy.app.timers.is_registered(server_ops.simulation_timer):
                bpy.app.timers.register(server_ops.simulation_timer)
            
            # Update UI to reflect simulation status
            bpy.context.scene.debug_settings.debug_simulation_active = True
            bpy.context.scene.debug_settings.connection_status = f"Simulation active for recording camera: {cam_id}"
            
            print(f"WebSocket Test: Started simulation for recording camera '{cam_id}'")
    
    except (ImportError, AttributeError) as e:
        print(f"WebSocket Test: Error starting simulation for recording: {str(e)}")

# Define all classes for registration
classes = (
    WS_OT_RenderFromCamera,
    WS_OT_StartCameraRecording,
    WS_OT_StopCameraRecording,
    WS_OT_SimulateRenderRequest,
    WS_OT_SimulateRecordStartRequest,
    WS_OT_SimulateRecordStopRequest,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    # Remove handlers
    if record_camera_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(record_camera_handler)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)