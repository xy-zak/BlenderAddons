bl_info = {
    "name": "Product Render Setup",
    "author": "Your Name",
    "version": (1, 3),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > Product Render",
    "description": "Set up camera for product renders with different framing options",
    "category": "3D View",
}

import bpy
import math
import time
from mathutils import Vector
from bpy.props import EnumProperty, FloatProperty, PointerProperty

# Constants
CAMERA_PRESETS = [
    ("close", "Close", "Close-up view with 120mm focal length, f/0.8 aperture", 1),
    ("medium", "Medium", "Medium view with 70mm focal length, f/2.4 aperture", 2),
    ("far", "Far", "Far view with 50mm focal length, f/8.0 aperture", 3),
]

FOCUS_PLANE_NAME = "FocusVisualizerPlane"

# Helper functions
def create_camera_for_object(context, focus_object):
    """Create a camera pointed at the focus object"""
    # Create new camera
    camera_data = bpy.data.cameras.new(name="ProductCamera")
    camera_obj = bpy.data.objects.new("ProductCamera", camera_data)
    
    # Link camera to scene
    context.collection.objects.link(camera_obj)
    
    # Calculate position
    obj_location = focus_object.location
    
    # Position camera slightly to the side and above the object
    camera_obj.location = (obj_location.x + 5, obj_location.y - 5, obj_location.z + 2)
    
    # Point camera at object
    direction = obj_location - camera_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera_obj.rotation_euler = rot_quat.to_euler()
    
    # Set up camera constraint to track the object
    constraint = camera_obj.constraints.new('TRACK_TO')
    constraint.target = focus_object
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    
    # Set the camera as active camera
    context.scene.camera = camera_obj
    
    return camera_obj

def create_focus_visualizer(context, location, camera):
    """Create or update a semi-transparent plane at the focus point, facing the camera"""
    # Check if a visualizer plane already exists
    plane = None
    for obj in bpy.data.objects:
        if obj.name == FOCUS_PLANE_NAME or obj.name.startswith(FOCUS_PLANE_NAME):
            plane = obj
            break
    
    # Create a new plane if none exists
    if plane is None:
        bpy.ops.mesh.primitive_plane_add(size=0.5, location=location)
        plane = context.active_object
        plane.name = FOCUS_PLANE_NAME
        
        # Create a new material with transparency
        if FOCUS_PLANE_NAME not in bpy.data.materials:
            mat = bpy.data.materials.new(FOCUS_PLANE_NAME)
            mat.use_nodes = True
            
            # Get the node tree
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            
            # Clear default nodes
            for node in nodes:
                nodes.remove(node)
            
            # Create nodes for semi-transparent material
            node_output = nodes.new(type='ShaderNodeOutputMaterial')
            node_bsdf = nodes.new(type='ShaderNodeBsdfTransparent')
            
            # Set the color to a bright color with low alpha
            node_bsdf.inputs[0].default_value = (0.0, 1.0, 1.0, 0.3)  # Cyan, semi-transparent
            
            # Link nodes
            links.new(node_bsdf.outputs[0], node_output.inputs[0])
            
            # Assign material to the plane
            plane.data.materials.append(mat)
    else:
        # Update existing plane position
        plane.location = location
    
    # Make plane face the camera
    direction = camera.location - location
    rot_quat = direction.to_track_quat('Z', 'Y')
    plane.rotation_euler = rot_quat.to_euler()
    
    # Make sure it's visible
    plane.hide_viewport = False
    plane.hide_render = True  # Don't show in renders
    
    return plane

def remove_focus_visualizer():
    """Remove the focus visualizer plane"""
    for obj in bpy.data.objects:
        if obj.name == FOCUS_PLANE_NAME or obj.name.startswith(FOCUS_PLANE_NAME):
            # Hide the plane instead of deleting it
            obj.hide_viewport = True
            return

def create_rim_light(context, focus_object, strength=1000.0, temperature=5500.0, offset=0.0):
    """Create a rim light behind the object, pointed at the camera"""
    # Get the camera and object positions
    camera = context.scene.camera
    if not camera or not focus_object:
        return None
    
    # Calculate the rim light position
    obj_location = focus_object.location
    cam_location = camera.location
    
    # Calculate direction from camera to object
    direction = (obj_location - cam_location).normalized()
    
    # Position the light behind the object (opposite to camera)
    light_distance = (focus_object.dimensions.length * 1.5) + offset
    light_location = obj_location + direction * light_distance
    
    # Raise the light 1 meter up on Z axis
    light_location.z += 1.0
    
    # Create the light
    light_data = bpy.data.lights.new(name="ProductRimLight", type='AREA')
    light_data.energy = strength
    light_data.color = kelvin_to_rgb(temperature)
    light_data.shape = 'RECTANGLE'
    light_data.size = focus_object.dimensions.length
    light_data.size_y = focus_object.dimensions.length / 2
    
    light_obj = bpy.data.objects.new(name="ProductRimLight", object_data=light_data)
    context.collection.objects.link(light_obj)
    
    # Position the light
    light_obj.location = light_location
    
    # Make the light point at the camera instead of the object (180 degree rotation)
    light_to_cam = (cam_location - light_location).normalized()
    rot_quat = light_to_cam.to_track_quat('Z', 'Y')
    light_obj.rotation_euler = rot_quat.to_euler()
    
    return light_obj

def kelvin_to_rgb(temperature):
    """Convert Kelvin temperature to RGB values"""
    # Simple conversion from temperature to RGB
    # Based on approximation from http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
    
    # Clamp temperature to valid range
    temperature = max(min(temperature, 40000), 1000) / 100
    
    # Calculate red
    if temperature <= 66:
        red = 1.0
    else:
        red = temperature - 60
        red = 329.698727446 * (red ** -0.1332047592)
        red = max(min(red / 255, 1.0), 0.0)
    
    # Calculate green
    if temperature <= 66:
        green = temperature
        green = 99.4708025861 * math.log(green) - 161.1195681661
    else:
        green = temperature - 60
        green = 288.1221695283 * (green ** -0.0755148492)
    green = max(min(green / 255, 1.0), 0.0)
    
    # Calculate blue
    if temperature >= 66:
        blue = 1.0
    elif temperature <= 19:
        blue = 0.0
    else:
        blue = temperature - 10
        blue = 138.5177312231 * math.log(blue) - 305.0447927307
        blue = max(min(blue / 255, 1.0), 0.0)
    
    return (red, green, blue)

def calculate_camera_position(context, focus_object, preset, camera_obj, offset=0.0, focus_adjustment=0.0):
    """Calculate the optimal camera position based on the preset"""
    # Get object dimensions and bounding box
    bbox_corners = [focus_object.matrix_world @ Vector(corner) for corner in focus_object.bound_box]
    bbox_center = sum((Vector(corner) for corner in bbox_corners), Vector()) / 8
    
    # Calculate the object's dimensions
    dimensions = focus_object.dimensions
    max_dimension = max(dimensions)
    
    # Set focal length based on preset
    camera = camera_obj.data
    if preset == "close":
        camera.lens = 120.0
        camera.dof.aperture_fstop = 0.8
        distance_factor = 1.0
    elif preset == "medium":
        camera.lens = 70.0
        camera.dof.aperture_fstop = 2.4
        distance_factor = 1.5
    else:  # "far"
        camera.lens = 50.0
        camera.dof.aperture_fstop = 8.0
        distance_factor = 2.0
    
    # Enable depth of field
    camera.dof.use_dof = True
    
    # Get current camera direction
    direction = (bbox_center - camera_obj.location).normalized()
    
    # Calculate camera distance based on field of view and object size
    fov = math.atan(36.0 / (2 * camera.lens))  # Approximate FOV in radians based on 36mm sensor width
    # Reduce the distance by approximately half to improve framing
    distance = (max_dimension * distance_factor) / (4 * math.tan(fov / 2))
    
    # Set new camera position
    new_position = bbox_center - direction * (distance + offset)
    camera_obj.location = new_position
    
    # Make sure the camera constraint is still targeting the object
    for constraint in camera_obj.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.target = focus_object
    
    # Calculate and set focus point based on adjustment
    # Instead of using focus_object directly, we'll calculate a custom focus point
    # -1.0 = back of object, 0.0 = center, 1.0 = front of object
    if camera.dof.focus_object != None:
        camera.dof.focus_object = None  # Disconnect the focus object to use distance instead
    
    # Find front and back points in the camera's view direction
    min_dist = float('inf')
    max_dist = float('-inf')
    
    for corner in bbox_corners:
        # Project point onto camera direction
        dist = (corner - camera_obj.location).dot(direction)
        min_dist = min(min_dist, dist)
        max_dist = max(max_dist, dist)
    
    # Interpolate between back and front based on focus_adjustment
    # Convert from -1..1 range to back..front range
    focus_distance = (min_dist + max_dist) / 2  # Default to center
    if focus_adjustment < 0:  # Adjust towards back
        focus_distance = min_dist + (0.5 + focus_adjustment/2) * (max_dist - min_dist)
    elif focus_adjustment > 0:  # Adjust towards front
        focus_distance = min_dist + (0.5 + focus_adjustment/2) * (max_dist - min_dist)
    
    camera.dof.focus_distance = focus_distance
    
    # Calculate focus point in world space for the visualizer
    focus_point = camera_obj.location + direction * focus_distance
    
    # Update the last focus time for the timer - using scene property
    # Initialize if it doesn't exist yet
    if "product_render_last_focus_time" not in context.scene:
        context.scene["product_render_last_focus_time"] = 0.0
    context.scene["product_render_last_focus_time"] = time.time()
    
    # Start the timer if not already running
    if not bpy.app.timers.is_registered(check_focus_visualizer_timer):
        bpy.app.timers.register(
            check_focus_visualizer_timer,
            first_interval=2.0
        )
        
    return focus_point

def update_rim_light(self, context):
    """Update rim light settings"""
    light_obj = None
    for obj in bpy.data.objects:
        if obj.name == "ProductRimLight" and obj.type == 'LIGHT':
            light_obj = obj
            break
    
    if light_obj:
        props = context.scene.product_render_props
        light_obj.data.energy = props.rim_light_strength
        light_obj.data.color = kelvin_to_rgb(props.rim_light_temp)
        
        # Update light position based on offset
        focus_object = props.focus_object
        if focus_object and context.scene.camera:
            # Get original direction from camera to object
            obj_location = focus_object.location
            cam_location = context.scene.camera.location
            direction = (obj_location - cam_location).normalized()
            
            # Calculate new position with offset
            light_distance = (focus_object.dimensions.length * 1.5) + props.rim_light_offset
            light_location = obj_location + direction * light_distance
            
            # Keep the Z elevation
            current_z_offset = light_obj.location.z - obj_location.z
            light_location.z = obj_location.z + current_z_offset
            
            # Update position
            light_obj.location = light_location
            
            # Update rotation to point at camera
            light_to_cam = (cam_location - light_location).normalized()
            rot_quat = light_to_cam.to_track_quat('Z', 'Y')
            light_obj.rotation_euler = rot_quat.to_euler()

def update_camera_live(self, context):
    """Live update function for camera parameters"""
    props = context.scene.product_render_props
    focus_object = props.focus_object
    camera = context.scene.camera
    
    if not focus_object or not camera or camera.type != 'CAMERA':
        remove_focus_visualizer()
        return
    
    # Calculate focus point and update camera
    focus_point = calculate_camera_position(
        context,
        focus_object, 
        props.camera_preset, 
        camera, 
        props.camera_offset,
        props.focus_adjustment
    )
    
    # Create or update focus visualizer
    if focus_point:
        create_focus_visualizer(context, focus_point, camera)

# Timer for hiding the focus visualizer when not interacting
def check_focus_visualizer_timer():
    """Timer function to hide the focus visualizer when not in use"""
    # This function will hide the focus visualizer when slider interaction stops
    # Check all scenes for the property
    for scene in bpy.data.scenes:
        if "product_render_last_focus_time" in scene:
            last_time = scene["product_render_last_focus_time"]
            current_time = time.time()
            
            # If more than 2 seconds have passed since last interaction, hide the visualizer
            if current_time - last_time > 2.0:
                remove_focus_visualizer()
                return None  # Remove the timer
            
    return 0.5  # Continue checking every 0.5 seconds

# Classes
class ProductRenderProperties(bpy.types.PropertyGroup):
    focus_object: PointerProperty(
        name="Focus Object",
        description="Object to focus the camera on",
        type=bpy.types.Object,
    )
    
    camera_preset: EnumProperty(
        name="Camera Distance",
        description="Set camera distance and lens settings",
        items=CAMERA_PRESETS,
        default="medium"
    )
    
    camera_offset: FloatProperty(
        name="Camera Offset",
        description="Additional distance offset for the camera",
        default=0.0,
        min=-10.0,
        max=10.0,
        step=0.1,
        update=lambda self, context: update_camera_live(self, context)
    )
    
    focus_adjustment: FloatProperty(
        name="Focus Adjustment",
        description="Adjust focus point from back (-1.0) to front (1.0) of object",
        default=0.0,
        min=-1.0,
        max=1.0,
        step=0.05,
        update=lambda self, context: update_camera_live(self, context)
    )
    
    rim_light_strength: FloatProperty(
        name="Rim Light Strength",
        description="Strength of the rim light",
        default=1000.0,
        min=0.0,
        max=5000.0,
        step=10.0,
        update=lambda self, context: update_rim_light(self, context)
    )
    
    rim_light_temp: FloatProperty(
        name="Light Temperature",
        description="Color temperature of the rim light (K)",
        default=5500.0,
        min=1000.0,
        max=10000.0,
        step=100.0,
        update=lambda self, context: update_rim_light(self, context)
    )
    
    rim_light_offset: FloatProperty(
        name="Rim Light Distance",
        description="Adjust distance of the rim light from the object",
        default=0.0,
        min=-5.0,
        max=5.0,
        step=0.1,
        update=lambda self, context: update_rim_light(self, context)
    )

class PRODUCT_OT_create_camera(bpy.types.Operator):
    """Create a camera pointing at the selected object"""
    bl_idname = "product.create_camera"
    bl_label = "Create Camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.product_render_props
        focus_object = props.focus_object
        
        if not focus_object:
            self.report({'ERROR'}, "Please select a focus object first")
            return {'CANCELLED'}
        
        camera = create_camera_for_object(context, focus_object)
        calculate_camera_position(
            context,
            focus_object, 
            props.camera_preset, 
            camera, 
            props.camera_offset,
            props.focus_adjustment
        )
        
        # Select the camera
        bpy.ops.object.select_all(action='DESELECT')
        camera.select_set(True)
        context.view_layer.objects.active = camera
        
        return {'FINISHED'}

class PRODUCT_OT_update_camera(bpy.types.Operator):
    """Update camera settings based on the selected preset"""
    bl_idname = "product.update_camera"
    bl_label = "Update Camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.product_render_props
        focus_object = props.focus_object
        camera = context.scene.camera
        
        if not focus_object:
            self.report({'ERROR'}, "Please select a focus object first")
            return {'CANCELLED'}
            
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "No active camera found")
            return {'CANCELLED'}
        
        calculate_camera_position(
            context,
            focus_object, 
            props.camera_preset, 
            camera, 
            props.camera_offset,
            props.focus_adjustment
        )
        
        return {'FINISHED'}

class PRODUCT_OT_create_lights(bpy.types.Operator):
    """Create lighting setup for product rendering"""
    bl_idname = "product.create_lights"
    bl_label = "Create Lights"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.product_render_props
        focus_object = props.focus_object
        
        if not focus_object:
            self.report({'ERROR'}, "Please select a focus object first")
            return {'CANCELLED'}
            
        if not context.scene.camera:
            self.report({'ERROR'}, "No camera found. Please create a camera first.")
            return {'CANCELLED'}
        
        # Create rim light
        light = create_rim_light(
            context, 
            focus_object, 
            strength=props.rim_light_strength,
            temperature=props.rim_light_temp,
            offset=props.rim_light_offset
        )
        
        if light:
            self.report({'INFO'}, "Lighting setup created")
            
            # Select the light
            bpy.ops.object.select_all(action='DESELECT')
            light.select_set(True)
            context.view_layer.objects.active = light
        
        return {'FINISHED'}

class PRODUCT_PT_render_panel(bpy.types.Panel):
    """Panel for product render setup"""
    bl_label = "Product Render Setup"
    bl_idname = "PRODUCT_PT_render_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Product Render'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.product_render_props
        
        # Focus object selection
        layout.prop(props, "focus_object")
        
        # Create camera button
        row = layout.row()
        row.operator("product.create_camera")
        
        layout.separator()
        
        # Camera preset selection
        box = layout.box()
        box.label(text="Camera Settings:")
        box.prop(props, "camera_preset", expand=True)
        box.prop(props, "camera_offset")
        box.prop(props, "focus_adjustment")
        
        # Update camera button (for preset changes)
        row = layout.row()
        row.operator("product.update_camera", text="Update Preset")
        
        # Camera quick settings
        camera = context.scene.camera
        if camera and camera.type == 'CAMERA':
            layout.separator()
            box = layout.box()
            box.label(text="Current Camera Settings:")
            box.prop(camera.data, "lens", text="Focal Length")
            box.prop(camera.data.dof, "aperture_fstop", text="Aperture")

class PRODUCT_PT_lighting_panel(bpy.types.Panel):
    """Panel for product lighting setup"""
    bl_label = "Lighting Setup"
    bl_idname = "PRODUCT_PT_lighting_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Product Render'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.product_render_props
        
        # Create lights button
        row = layout.row()
        row.operator("product.create_lights")
        
        layout.separator()
        
        # Light adjustment sliders
        box = layout.box()
        box.label(text="Rim Light Settings:")
        box.prop(props, "rim_light_strength")
        box.prop(props, "rim_light_temp")
        box.prop(props, "rim_light_offset")
        
        # Display current light info if it exists
        rim_light = None
        for obj in bpy.data.objects:
            if obj.name == "ProductRimLight" and obj.type == 'LIGHT':
                rim_light = obj
                break
        
        if rim_light:
            layout.separator()
            box = layout.box()
            box.label(text="Light Information:")
            box.label(text=f"Position: {rim_light.location.x:.2f}, {rim_light.location.y:.2f}, {rim_light.location.z:.2f}")
            box.label(text=f"Size: {rim_light.data.size:.2f} x {rim_light.data.size_y:.2f}")
            # Show distance to object
            if props.focus_object:
                distance = (rim_light.location - props.focus_object.location).length
                box.label(text=f"Distance to object: {distance:.2f}m")

# Registration
classes = (
    ProductRenderProperties,
    PRODUCT_OT_create_camera,
    PRODUCT_OT_update_camera,
    PRODUCT_OT_create_lights,
    PRODUCT_PT_render_panel,
    PRODUCT_PT_lighting_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.product_render_props = bpy.props.PointerProperty(type=ProductRenderProperties)
    # We'll initialize the timer property when it's first needed, not during registration

def unregister():
    # Remove any running timers
    if bpy.app.timers.is_registered(check_focus_visualizer_timer):
        bpy.app.timers.unregister(check_focus_visualizer_timer)
    
    # Remove focus visualizer
    remove_focus_visualizer()
    
    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Remove custom properties
    del bpy.types.Scene.product_render_props
    
    # Clean up custom properties from all scenes
    for scene in bpy.data.scenes:
        if "product_render_last_focus_time" in scene:
            del scene["product_render_last_focus_time"]

if __name__ == "__main__":
    register()