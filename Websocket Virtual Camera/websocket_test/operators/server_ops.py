import bpy
from bpy.types import Operator

# Import WebSocket modules
def get_websocket_module():
    from ..core import simple_websocket
    return simple_websocket

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
            
            # Copy camera's current transform to empty
            empty.location = camera.location.copy()
            empty.rotation_euler = camera.rotation_euler.copy()
            
            # Set empty as camera's parent
            camera.parent = empty
            
            # Reset camera's local transform (it inherits global transform from parent)
            camera.location = (0, 0, 0)
            camera.rotation_euler = (0, 0, 0)
            
            # Set as target empty
            camera_tracking.target_empty = empty.name
            
            # Set empty transform properties
            camera_tracking.empty_loc_x = empty.location.x
            camera_tracking.empty_loc_y = empty.location.y
            camera_tracking.empty_loc_z = empty.location.z
            camera_tracking.empty_rot_x = empty.rotation_euler.x
            camera_tracking.empty_rot_y = empty.rotation_euler.y
            camera_tracking.empty_rot_z = empty.rotation_euler.z
            
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

# Operator to update empty transform from UI
class WS_OT_UpdateEmptyTransform(Operator):
    bl_idname = "ws.update_empty_transform"
    bl_label = "Update Transform"
    bl_description = "Update the empty transform from UI values"
    
    @classmethod
    def poll(cls, context):
        # Only show if we have a target empty
        camera_settings = context.scene.camera_tracking
        return camera_settings.target_empty != "" and camera_settings.target_empty in bpy.data.objects
    
    def execute(self, context):
        camera_settings = context.scene.camera_tracking
        
        if camera_settings.target_empty:
            try:
                # Get empty object
                empty = bpy.data.objects[camera_settings.target_empty]
                
                # Update location
                empty.location.x = camera_settings.empty_loc_x
                empty.location.y = camera_settings.empty_loc_y
                empty.location.z = camera_settings.empty_loc_z
                
                # Update rotation
                empty.rotation_euler.x = camera_settings.empty_rot_x
                empty.rotation_euler.y = camera_settings.empty_rot_z
                empty.rotation_euler.z = camera_settings.empty_rot_y
                
                self.report({'INFO'}, "Empty transform updated")
                return {'FINISHED'}
            except KeyError:
                self.report({'ERROR'}, "Empty not found")
                camera_settings.target_empty = ""
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "No target empty set")
            return {'CANCELLED'}


# Register all operators
classes = (
    WS_OT_SetActiveCamera,  # New operator for eyedropper functionality
    WS_OT_StartServer,
    WS_OT_StopServer,
    WS_OT_SendTestMessage,
    WS_OT_SetupHybridCamera,
    WS_OT_ClearHybridCamera,
    WS_OT_UpdateEmptyTransform,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)