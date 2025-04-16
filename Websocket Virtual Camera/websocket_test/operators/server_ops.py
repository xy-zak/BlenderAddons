import bpy
from bpy.types import Operator
import json
import math
import time
from bpy.app import timers

# Import WebSocket modules
def get_websocket_module():
    from ..core import simple_websocket
    return simple_websocket

# Global variables for simulation animation
_simulation_running = False
_animation_start_time = 0
_animation_pattern = "circle"  # Default pattern

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
        websocket = get_websocket_module()
        if websocket.start_server(ip, port):
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
        websocket = get_websocket_module()
        if websocket.stop_server():
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
        websocket = get_websocket_module()
        if websocket.send_test_message():
            self.report({'INFO'}, "Test message sent")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No clients connected")
            return {'CANCELLED'}

# NEW WORKFLOW: Create Shared Origin Empty
class WS_OT_CreateSharedOrigin(Operator):
    bl_idname = "ws.create_shared_origin"
    bl_label = "Add Hybrid Camera Origin"
    bl_description = "Create a shared origin empty for all hybrid cameras"
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        # Allow creation only if no shared origin exists yet
        return not camera_tracking.shared_origin_name or camera_tracking.shared_origin_name not in bpy.data.objects
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        # Create empty object as shared origin
        empty = bpy.data.objects.new("Hybrid_Camera_Origin", None)
        empty.empty_display_type = 'ARROWS'
        empty.empty_display_size = 1.5  # Slightly larger for better visibility
        empty.location = (0, 0, 0)
        empty.rotation_euler = (0, 0, 0)
        
        # Link the empty to the scene
        context.collection.objects.link(empty)
        
        # Store the shared origin name
        camera_tracking.shared_origin_name = empty.name
        
        # Set empty transform properties
        camera_tracking.empty_loc_x = empty.location.x
        camera_tracking.empty_loc_y = empty.location.y
        camera_tracking.empty_loc_z = empty.location.z
        
        # Select the empty
        bpy.ops.object.select_all(action='DESELECT')
        empty.select_set(True)
        context.view_layer.objects.active = empty
        
        self.report({'INFO'}, "Created shared hybrid camera origin")
        return {'FINISHED'}

# Spawn a new hybrid camera
class WS_OT_SpawnHybridCamera(Operator):
    bl_idname = "ws.spawn_hybrid_camera"
    bl_label = "Spawn Hybrid Camera"
    bl_description = "Spawn a new hybrid camera as a child of the shared origin"
    
    cam_id: bpy.props.StringProperty(
        name="Camera ID",
        description="Unique identifier for this camera",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        # Allow spawning only if shared origin exists
        return camera_tracking.shared_origin_name and camera_tracking.shared_origin_name in bpy.data.objects
    
    def invoke(self, context, event):
        # Auto-generate camera ID based on existing cameras
        camera_tracking = context.scene.camera_tracking
        next_id = 1
        
        # Find the next available camera ID number
        existing_ids = set()
        for cam in camera_tracking.cameras:
            if cam.cam_id.startswith("cam"):
                try:
                    num = int(cam.cam_id[3:])
                    existing_ids.add(num)
                except ValueError:
                    pass
        
        # Find first unused number
        while next_id in existing_ids:
            next_id += 1
        
        # Set default camera ID
        self.cam_id = f"cam{next_id}"
        
        # Show dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        # Check if this camera ID already exists
        for cam in camera_tracking.cameras:
            if cam.cam_id == self.cam_id:
                self.report({'WARNING'}, f"Camera ID '{self.cam_id}' already exists")
                return {'CANCELLED'}
        
        try:
            # Get the shared origin
            shared_origin = bpy.data.objects[camera_tracking.shared_origin_name]
            
            # Create a new camera
            camera_data = bpy.data.cameras.new(name=f"{self.cam_id}_data")
            camera = bpy.data.objects.new(f"{self.cam_id}", camera_data)
            
            # Link the camera to the scene
            context.collection.objects.link(camera)
            
            # Set camera as child of the shared origin
            camera.parent = shared_origin
            
            # Set initial local transform (offset slightly for visibility)
            # Find how many cameras we already have to offset each one
            camera_count = len(camera_tracking.cameras)
            offset_x = (camera_count % 3) * 0.5 - 0.5  # -0.5, 0, 0.5 pattern
            offset_y = -(camera_count // 3) * 0.5      # Move back in rows
            camera.location = (offset_x, offset_y, 0)
            camera.rotation_euler = (0, 0, 0)
            
            # Add new camera association
            new_cam = camera_tracking.cameras.add()
            new_cam.cam_id = self.cam_id
            new_cam.camera_name = camera.name
            new_cam.is_setup = True  # Already set up as hybrid
            new_cam.empty_name = shared_origin.name
            
            # Set active index to the new camera
            camera_tracking.active_camera_index = len(camera_tracking.cameras) - 1
            
            # Select the new camera
            bpy.ops.object.select_all(action='DESELECT')
            camera.select_set(True)
            context.view_layer.objects.active = camera
            
            self.report({'INFO'}, f"Spawned hybrid camera '{self.cam_id}'")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error spawning hybrid camera: {str(e)}")
            return {'CANCELLED'}

# Operator to remove a camera association
class WS_OT_RemoveCameraAssociation(Operator):
    bl_idname = "ws.remove_camera_association"
    bl_label = "Remove"
    bl_description = "Remove this camera association and delete the camera object"
    
    index: bpy.props.IntProperty(
        name="Index",
        description="Index of the camera association to remove",
        default=0
    )
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        if self.index >= 0 and self.index < len(camera_tracking.cameras):
            # Get the camera being removed
            cam = camera_tracking.cameras[self.index]
            cam_id = cam.cam_id
            camera_name = cam.camera_name
            
            # Delete the camera object
            if camera_name and camera_name in bpy.data.objects:
                camera_obj = bpy.data.objects[camera_name]
                camera_data = camera_obj.data
                bpy.data.objects.remove(camera_obj)
                # Also remove the camera data
                if isinstance(camera_data, bpy.types.Camera):
                    bpy.data.cameras.remove(camera_data)
            
            # Remove the camera association
            camera_tracking.cameras.remove(self.index)
            
            # Adjust active index
            if camera_tracking.active_camera_index >= len(camera_tracking.cameras):
                camera_tracking.active_camera_index = max(0, len(camera_tracking.cameras) - 1)
            
            self.report({'INFO'}, f"Removed camera '{cam_id}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Invalid camera index")
            return {'CANCELLED'}

# Operator to edit camera ID
class WS_OT_EditCameraID(Operator):
    bl_idname = "ws.edit_camera_id"
    bl_label = "Edit Camera ID"
    bl_description = "Edit the ID of this camera"
    
    index: bpy.props.IntProperty(
        name="Index",
        description="Index of the camera association to edit",
        default=0
    )
    
    new_id: bpy.props.StringProperty(
        name="New Camera ID",
        description="New identifier for this camera",
        default=""
    )
    
    def invoke(self, context, event):
        camera_tracking = context.scene.camera_tracking
        
        if self.index >= 0 and self.index < len(camera_tracking.cameras):
            # Set current ID as default
            self.new_id = camera_tracking.cameras[self.index].cam_id
            
            # Show dialog
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            self.report({'ERROR'}, "Invalid camera index")
            return {'CANCELLED'}
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        if self.index >= 0 and self.index < len(camera_tracking.cameras):
            # Check if this ID would be a duplicate
            for i, cam in enumerate(camera_tracking.cameras):
                if i != self.index and cam.cam_id == self.new_id:
                    self.report({'WARNING'}, f"Camera ID '{self.new_id}' already exists")
                    return {'CANCELLED'}
            
            # Store old values
            old_id = camera_tracking.cameras[self.index].cam_id
            camera_name = camera_tracking.cameras[self.index].camera_name
            
            # Update the camera ID
            camera_tracking.cameras[self.index].cam_id = self.new_id
            
            # Rename the camera object to match the new ID
            if camera_name and camera_name in bpy.data.objects:
                camera_obj = bpy.data.objects[camera_name]
                camera_obj.name = self.new_id
                camera_tracking.cameras[self.index].camera_name = camera_obj.name
            
            self.report({'INFO'}, f"Updated camera ID from '{old_id}' to '{self.new_id}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Invalid camera index")
            return {'CANCELLED'}

class WS_OT_ResetIDsDirect(Operator):
    bl_idname = "ws.reset_ids_direct"
    bl_label = "Reset IDs Directly"
    bl_description = "Reset all camera IDs to default (cam1, cam2, etc.)"
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        return len(camera_tracking.cameras) > 0
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        for i, cam in enumerate(camera_tracking.cameras):
            # Generate default name
            new_id = f"cam{i+1}"
            old_id = cam.cam_id
            
            # Update ID
            cam.cam_id = new_id
            
            # Rename the camera object to match
            if cam.camera_name and cam.camera_name in bpy.data.objects:
                camera_obj = bpy.data.objects[cam.camera_name]
                camera_obj.name = new_id
                # Update reference since name might change due to Blender's naming system
                cam.camera_name = camera_obj.name
        
        self.report({'INFO'}, "Reset all camera IDs to defaults")
        return {'FINISHED'}

# Operator to open a rename dialog for cameras
class WS_OT_RenameHybridCameras(Operator):
    bl_idname = "ws.rename_hybrid_cameras"
    bl_label = "Rename Cameras"
    bl_description = "Rename one or all hybrid cameras"
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        return len(camera_tracking.cameras) > 0
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        camera_tracking = context.scene.camera_tracking
        
        # Help text
        layout.label(text="Edit camera IDs:")
        
        # Camera list with editable names
        for i, cam in enumerate(camera_tracking.cameras):
            row = layout.row(align=True)
            
            # Camera number label
            row.label(text=f"Camera {i+1}:")
            
            # Editable ID field
            row.prop(cam, "cam_id", text="")
            
            # Display camera object name
            if cam.camera_name and cam.camera_name in bpy.data.objects:
                row.label(text=cam.camera_name)
        
        # Reset to default names button - now calls direct reset function instead of operator
        row = layout.row()
        row.operator("ws.reset_ids_direct", text="Reset to Default IDs", icon='LOOP_BACK')

# Operator to reset camera IDs to default (cam1, cam2, etc.)
class WS_OT_ResetCameraIDs(Operator):
    bl_idname = "ws.reset_camera_ids"
    bl_label = "Reset Camera IDs"
    bl_description = "Reset all camera IDs to default (cam1, cam2, etc.)"
    
    @classmethod
    def poll(cls, context):
        camera_tracking = context.scene.camera_tracking
        return len(camera_tracking.cameras) > 0
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        for i, cam in enumerate(camera_tracking.cameras):
            # Generate default name
            new_id = f"cam{i+1}"
            old_id = cam.cam_id
            
            # Update ID
            cam.cam_id = new_id
            
            # Rename the camera object to match
            if cam.camera_name and cam.camera_name in bpy.data.objects:
                camera_obj = bpy.data.objects[cam.camera_name]
                camera_obj.name = new_id
                # Update reference since name might change due to Blender's naming system
                cam.camera_name = camera_obj.name
        
        self.report({'INFO'}, "Reset all camera IDs to defaults")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        camera_tracking = context.scene.camera_tracking
        
        if self.index >= 0 and self.index < len(camera_tracking.cameras):
            # Set current ID as default
            self.new_id = camera_tracking.cameras[self.index].cam_id
            
            # Show dialog
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            self.report({'ERROR'}, "Invalid camera index")
            return {'CANCELLED'}
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        if self.index >= 0 and self.index < len(camera_tracking.cameras):
            # Check if this ID would be a duplicate
            for i, cam in enumerate(camera_tracking.cameras):
                if i != self.index and cam.cam_id == self.new_id:
                    self.report({'WARNING'}, f"Camera ID '{self.new_id}' already exists")
                    return {'CANCELLED'}
            
            # Store old values
            old_id = camera_tracking.cameras[self.index].cam_id
            camera_name = camera_tracking.cameras[self.index].camera_name
            
            # Update the camera ID
            camera_tracking.cameras[self.index].cam_id = self.new_id
            
            # Rename the camera object to match the new ID
            if camera_name and camera_name in bpy.data.objects:
                camera_obj = bpy.data.objects[camera_name]
                camera_obj.name = self.new_id
                camera_tracking.cameras[self.index].camera_name = camera_obj.name
            
            self.report({'INFO'}, f"Updated camera ID from '{old_id}' to '{self.new_id}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Invalid camera index")
            return {'CANCELLED'}

# Function to generate simulated IMU data
def generate_imu_data(context, pattern="circle"):
    camera_settings = context.scene.camera_tracking
    debug_settings = context.scene.debug_settings
    
    # Get elapsed time since start
    elapsed = time.time() - _animation_start_time
    
    # Base values
    rot_x = 0.0
    rot_y = 0.0
    rot_z = 0.0
    loc_x = 0.0
    loc_y = 0.0
    loc_z = 0.0
    
    # Generate different patterns based on the selection
    if pattern == "circle":
        # Circular motion
        angle = elapsed * 0.5  # slower rotation
        rot_x = 15 * math.sin(angle)  # 15 degree tilt
        rot_y = 15 * math.cos(angle)  # 15 degree tilt
        rot_z = 5 * math.sin(angle * 2)  # slight roll
        
    elif pattern == "shake":
        # Random shaking
        from random import uniform
        rot_x = uniform(-5, 5)
        rot_y = uniform(-5, 5)
        rot_z = uniform(-2, 2)
        loc_x = uniform(-0.05, 0.05)
        loc_y = uniform(-0.05, 0.05)
        loc_z = uniform(-0.02, 0.02)
        
    elif pattern == "pan":
        # Panning motion
        rot_y = 45 * math.sin(elapsed * 0.3)  # 45 degree pan left/right
        
    elif pattern == "tilt":
        # Tilting motion
        rot_x = 30 * math.sin(elapsed * 0.3)  # 30 degree tilt up/down
        
    elif pattern == "roll":
        # Rolling motion
        rot_z = 20 * math.sin(elapsed * 0.3)  # 20 degree roll
        
    elif pattern == "sidestep":
        # Side to side movement
        loc_x = 0.3 * math.sin(elapsed * 1.0)
    
    elif pattern == "orbital":
        # Orbital camera - moves in a circle while rotating to look at center
        radius = 0.5  # Radius of the circular path
        angle = elapsed * 0.3  # Speed of orbit
        
        # Move in a circle in XY plane
        loc_x = radius * math.cos(angle)
        loc_y = radius * math.sin(angle)
        
        # Optional: add small vertical motion
        loc_z = 0.1 * math.sin(angle * 2)
        
        # Calculate rotation to always face center
        # For Y rotation (yaw), face the center
        rot_y = math.degrees(math.atan2(loc_y, loc_x)) + 180
        
        # For X rotation (pitch), point slightly down when high, up when low
        rot_x = -15 * math.sin(angle * 2)
        
        # Add slight roll for dramatic effect
        rot_z = 5 * math.sin(angle * 3)
    
    # Create simulated IMU data
    data = {
        "type": "IMU",
        "rot_x": rot_x,
        "rot_y": rot_y,
        "rot_z": rot_z,
        "loc_x": loc_x,
        "loc_y": loc_y,
        "loc_z": loc_z,
        "timestamp": int(time.time() * 1000)
    }
    
    # Add camera ID if specified
    if debug_settings.target_cam_id:
        data["cam_id"] = debug_settings.target_cam_id
    
    return data

# Timer function to simulate IMU data
def simulation_timer():
    global _simulation_running, _animation_pattern
    
    if not _simulation_running:
        return None  # Stop timer
    
    # Generate and process IMU data
    websocket = get_websocket_module()
    data = generate_imu_data(bpy.context, _animation_pattern)
    
    # Process the IMU data directly
    websocket.process_imu_data(data)
    
    # Update debug info
    bpy.context.scene.debug_settings.last_message = json.dumps(data)
    
    # Add to message history
    if hasattr(websocket, "message_history"):
        websocket.message_history.insert(0, json.dumps(data))
        if len(websocket.message_history) > websocket.MAX_MESSAGE_HISTORY:
            websocket.message_history.pop()
        
        # Update message log
        log = "\n".join([f"[{i+1}] {msg[:100]}..." for i, msg in enumerate(websocket.message_history[:5])])
        bpy.context.scene.debug_settings.message_log = log
    
    # Continue timer
    return 0.05  # 20 fps simulation

# Operator to start simulation
class WS_OT_StartSimulation(Operator):
    bl_idname = "ws.start_debug_simulation"
    bl_label = "Start Simulation"
    bl_description = "Start simulating IMU data for testing without ESP32"
    
    pattern: bpy.props.EnumProperty(
        items=[
            ("circle", "Circular Motion", "Simulate circular motion of the camera"),
            ("shake", "Handheld Shake", "Simulate handheld camera shake"),
            ("pan", "Panning", "Simulate panning left and right"),
            ("tilt", "Tilting", "Simulate tilting up and down"),
            ("roll", "Rolling", "Simulate rolling motion"),
            ("sidestep", "Side Steps", "Simulate moving side to side"),
            ("orbital", "Orbital Camera", "Simulate camera moving in circle while always looking at center")
        ],
        name="Pattern",
        description="Select simulation pattern",
        default="circle"
    )
    
    @classmethod
    def poll(cls, context):
        # Only enable if at least one camera is set up
        camera_tracking = context.scene.camera_tracking
        return len(camera_tracking.cameras) > 0
    
    def execute(self, context):
        global _simulation_running, _animation_start_time, _animation_pattern
        
        # Get the target camera ID from the debug_settings
        target_cam_id = context.scene.debug_settings.target_cam_id
        
        # Set up simulation
        _simulation_running = True
        _animation_start_time = time.time()
        _animation_pattern = self.pattern
        
        # Start timer
        if not timers.is_registered(simulation_timer):
            timers.register(simulation_timer)
        
        # Update UI
        context.scene.debug_settings.debug_simulation_active = True
        
        if target_cam_id:
            context.scene.debug_settings.connection_status = f"Simulation active: {self.pattern} for camera ID: {target_cam_id}"
        else:
            context.scene.debug_settings.connection_status = f"Simulation active: {self.pattern} for all cameras"
        
        self.report({'INFO'}, f"Started simulation: {self.pattern}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

# Operator to stop simulation
class WS_OT_StopSimulation(Operator):
    bl_idname = "ws.stop_debug_simulation"
    bl_label = "Stop Simulation"
    bl_description = "Stop simulating IMU data"
    
    @classmethod
    def poll(cls, context):
        # Only enable if simulation is running
        return context.scene.debug_settings.debug_simulation_active
    
    def execute(self, context):
        global _simulation_running
        
        # Stop simulation
        _simulation_running = False
        
        # Update UI
        context.scene.debug_settings.debug_simulation_active = False
        context.scene.debug_settings.connection_status = "Simulation stopped"
        
        self.report({'INFO'}, "Stopped simulation")
        return {'FINISHED'}

# Operator to send a single frame of simulated data
class WS_OT_SendSimulatedFrame(Operator):
    bl_idname = "ws.send_debug_frame"
    bl_label = "Send Single Frame"
    bl_description = "Send a single frame of simulated IMU data"
    
    rot_x: bpy.props.FloatProperty(
        name="Rotation X",
        description="X rotation in degrees",
        default=0.0,
        min=-180.0,
        max=180.0
    )
    
    rot_y: bpy.props.FloatProperty(
        name="Rotation Y",
        description="Y rotation in degrees",
        default=0.0,
        min=-180.0,
        max=180.0
    )
    
    rot_z: bpy.props.FloatProperty(
        name="Rotation Z",
        description="Z rotation in degrees",
        default=0.0,
        min=-180.0,
        max=180.0
    )
    
    loc_x: bpy.props.FloatProperty(
        name="Location X",
        description="X location offset",
        default=0.0,
        min=-1.0,
        max=1.0
    )
    
    loc_y: bpy.props.FloatProperty(
        name="Location Y",
        description="Y location offset",
        default=0.0,
        min=-1.0,
        max=1.0
    )
    
    loc_z: bpy.props.FloatProperty(
        name="Location Z",
        description="Z location offset",
        default=0.0,
        min=-1.0,
        max=1.0
    )
    
    cam_id: bpy.props.StringProperty(
        name="Camera ID",
        description="ID of the camera to target (leave empty for all cameras)",
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        # Only enable if cameras exist and simulation is not running
        camera_tracking = context.scene.camera_tracking
        
        if context.scene.debug_settings.debug_simulation_active:
            return False
        
        return len(camera_tracking.cameras) > 0
    
    def execute(self, context):
        # Create IMU data
        data = {
            "type": "IMU",
            "rot_x": self.rot_x,
            "rot_y": self.rot_y,
            "rot_z": self.rot_z,
            "loc_x": self.loc_x,
            "loc_y": self.loc_y,
            "loc_z": self.loc_z,
            "timestamp": int(time.time() * 1000)
        }
        
        # Add camera ID if specified
        if self.cam_id:
            data["cam_id"] = self.cam_id
            
        # Process IMU data
        websocket = get_websocket_module()
        websocket.process_imu_data(data)
        
        # Update debug info
        bpy.context.scene.debug_settings.last_message = json.dumps(data)
        
        # Add to message history
        if hasattr(websocket, "message_history"):
            websocket.message_history.insert(0, json.dumps(data))
            if len(websocket.message_history) > websocket.MAX_MESSAGE_HISTORY:
                websocket.message_history.pop()
            
            # Update message log
            log = "\n".join([f"[{i+1}] {msg[:100]}..." for i, msg in enumerate(websocket.message_history[:5])])
            bpy.context.scene.debug_settings.message_log = log
        
        self.report({'INFO'}, "Sent simulated frame")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

# Define all classes in the order they will be registered
classes = (
    WS_OT_StartServer,
    WS_OT_StopServer,
    WS_OT_SendTestMessage,
    WS_OT_CreateSharedOrigin,
    WS_OT_SpawnHybridCamera,
    WS_OT_RenameHybridCameras,
    WS_OT_ResetIDsDirect,
    WS_OT_ResetCameraIDs,
    WS_OT_EditCameraID,
    WS_OT_RemoveCameraAssociation,
    WS_OT_StartSimulation,
    WS_OT_StopSimulation,
    WS_OT_SendSimulatedFrame,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)