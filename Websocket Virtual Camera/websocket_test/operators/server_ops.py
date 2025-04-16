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

# Operator to select a camera with eyedropper
class WS_OT_SetActiveCamera(Operator):
    bl_idname = "ws.set_active_camera"
    bl_label = "Select Camera"
    bl_description = "Select a camera to use with IMU data"
    bl_property = "camera_enum"
    
    camera_enum: bpy.props.EnumProperty(
        items=lambda self, context: [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'CAMERA'],
        name="Camera"
    )
    
    def execute(self, context):
        # Set the selected camera name in the settings
        context.scene.camera_tracking.target_camera = self.camera_enum
        return {'FINISHED'}
        
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

# Operator to convert camera to hybrid camera setup
class WS_OT_SetupHybridCamera(Operator):
    bl_idname = "ws.setup_hybrid_camera"
    bl_label = "Setup Hybrid Camera"
    bl_description = "Create an empty parent for the selected camera to use as a hybrid camera setup"
    
    @classmethod
    def poll(cls, context):
        # Check if a camera is set in the target_camera property
        camera_settings = context.scene.camera_tracking
        
        # Only allow if a camera is selected but not already set up
        if camera_settings.target_camera and camera_settings.target_camera in bpy.data.objects:
            # Make sure it's a camera
            if bpy.data.objects[camera_settings.target_camera].type == 'CAMERA':
                # Don't allow setup if already has an empty parent (target_empty is set)
                if not camera_settings.target_empty or camera_settings.target_empty not in bpy.data.objects:
                    return True
        return False
    
    def execute(self, context):
        camera_tracking = context.scene.camera_tracking
        
        # Get the target camera object
        try:
            camera = bpy.data.objects[camera_tracking.target_camera]
            
            # Verify it's a camera
            if camera.type != 'CAMERA':
                self.report({'ERROR'}, f"Object '{camera.name}' is not a camera")
                return {'CANCELLED'}
                
            # Check if camera already has a parent of type EMPTY
            if camera.parent and camera.parent.type == 'EMPTY':
                self.report({'WARNING'}, f"Camera '{camera.name}' already has an empty parent")
                # Set the existing empty as the target
                camera_tracking.target_empty = camera.parent.name
                return {'CANCELLED'}
                
            camera_name = camera.name
            
            # Create empty object as parent
            empty = bpy.data.objects.new(f"{camera_name}_IMU_Origin", None)
            empty.empty_display_type = 'ARROWS'
            empty.empty_display_size = 1.0
            
            # Link the empty to the scene
            context.collection.objects.link(empty)
            
            # Copy camera's current location to empty, but use zero rotation
            empty.location = camera.location.copy()
            empty.rotation_euler = (0, 0, 0)  # Start with zero rotation for empty
            
            # Set empty as camera's parent
            camera.parent = empty
            
            # Reset camera's local transform (it inherits global transform from parent)
            camera.location = (0, 0, 0)
            camera.rotation_euler = (0, 0, 0)  # Make sure camera also has zero local rotation
            
            # Set as target empty
            camera_tracking.target_empty = empty.name
            
            # Set empty transform properties
            camera_tracking.empty_loc_x = empty.location.x
            camera_tracking.empty_loc_y = empty.location.y
            camera_tracking.empty_loc_z = empty.location.z
            
            # Initialize rotation offset properties to zeros
            camera_tracking.rotation_offset_x = 0.0
            camera_tracking.rotation_offset_y = 0.0
            camera_tracking.rotation_offset_z = 0.0
            
            # Select the empty
            bpy.ops.object.select_all(action='DESELECT')
            empty.select_set(True)
            context.view_layer.objects.active = empty
            
            self.report({'INFO'}, f"Camera '{camera_name}' converted to hybrid camera setup")
            return {'FINISHED'}
        except KeyError:
            self.report({'ERROR'}, f"Camera '{camera_tracking.target_camera}' not found")
            return {'CANCELLED'}

# Operator to clear hybrid camera setup
class WS_OT_ClearHybridCamera(Operator):
    bl_idname = "ws.clear_hybrid_camera"
    bl_label = "Clear Hybrid Camera"
    bl_description = "Remove the hybrid camera setup and restore original camera"
    
    @classmethod
    def poll(cls, context):
        # Only show if we have a target camera set
        camera_settings = context.scene.camera_tracking
        return camera_settings.target_camera != ""
    
    def execute(self, context):
        camera_settings = context.scene.camera_tracking
        
        # Check if we have both a camera and empty
        if camera_settings.target_camera and camera_settings.target_empty:
            try:
                # Get camera and empty objects
                if camera_settings.target_camera in bpy.data.objects:
                    camera = bpy.data.objects[camera_settings.target_camera]
                    
                    if camera_settings.target_empty in bpy.data.objects:
                        empty = bpy.data.objects[camera_settings.target_empty]
                        
                        # Store the camera's world transform
                        world_loc = camera.matrix_world.to_translation()
                        world_rot = camera.matrix_world.to_euler()
                        
                        # Remove parent relationship
                        camera.parent = None
                        
                        # Restore camera's world transform
                        camera.location = world_loc
                        camera.rotation_euler = world_rot
                        
                        # Delete the empty
                        bpy.data.objects.remove(empty)
                        
                        self.report({'INFO'}, "Hybrid camera setup cleared")
                    else:
                        self.report({'WARNING'}, "Empty not found - settings cleared")
                
                else:
                    self.report({'WARNING'}, "Camera not found - settings cleared")
                
                # Clear target empty setting but keep camera reference
                camera_settings.target_empty = ""
                
            except Exception as e:
                # If any error occurs, just clear the settings
                self.report({'WARNING'}, f"Error clearing setup: {str(e)}")
                camera_settings.target_empty = ""
        else:
            # Just clear both settings
            camera_settings.target_camera = ""
            camera_settings.target_empty = ""
            self.report({'INFO'}, "Target camera cleared")
            
        return {'FINISHED'}

# Function to generate simulated IMU data
def generate_imu_data(context, pattern="circle"):
    camera_settings = context.scene.camera_tracking
    
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
            ("sidestep", "Side Steps", "Simulate moving side to side")
        ],
        name="Pattern",
        description="Select simulation pattern",
        default="circle"
    )
    
    @classmethod
    def poll(cls, context):
        # Only enable if camera tracking is set up
        camera_settings = context.scene.camera_tracking
        return (camera_settings.target_camera != "" and 
                (camera_settings.target_empty != "" or not context.scene.debug_settings.require_hybrid))
    
    def execute(self, context):
        global _simulation_running, _animation_start_time, _animation_pattern
        
        # Set up simulation
        _simulation_running = True
        _animation_start_time = time.time()
        _animation_pattern = self.pattern
        
        # Start timer
        if not timers.is_registered(simulation_timer):
            timers.register(simulation_timer)
        
        # Update UI
        context.scene.debug_settings.debug_simulation_active = True
        context.scene.debug_settings.connection_status = f"Simulation active: {self.pattern}"
        
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
    
    @classmethod
    def poll(cls, context):
        # Only enable if camera tracking is set up and simulation is not running
        camera_settings = context.scene.camera_tracking
        return (camera_settings.target_camera != "" and 
                (camera_settings.target_empty != "" or not context.scene.debug_settings.require_hybrid) and
                not context.scene.debug_settings.debug_simulation_active)
    
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

# Register all operators
classes = (
    WS_OT_SetActiveCamera,
    WS_OT_StartServer,
    WS_OT_StopServer,
    WS_OT_SendTestMessage,
    WS_OT_SetupHybridCamera,
    WS_OT_ClearHybridCamera,
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