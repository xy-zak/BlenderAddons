

bl_info = {
    "name": "Product Render Setup",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),  # Compatible with Blender 3.0 and higher
    "location": "View3D > Sidebar > Product Render",
    "description": "Set up camera for product renders with different framing options",
    "category": "3D View",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
import math
import time
from mathutils import Vector, Matrix
from bpy.props import EnumProperty, FloatProperty, PointerProperty, BoolProperty

# Constants
CAMERA_PRESETS = [
    ("close", "Close", "Close-up view with 120mm focal length, f/0.8 aperture", 1),
    ("medium", "Medium", "Medium view with 70mm focal length, f/2.4 aperture", 2),
    ("far", "Far", "Far view with 50mm focal length, f/8.0 aperture", 3),
]

FOCUS_PLANE_NAME = "FocusVisualizerPlane"
KEY_LIGHT_NAME = "ProductKeyLight"
FILL_LIGHT_NAME = "ProductFillLight"
RIM_LIGHT_NAME = "ProductRimLight"

# Property class
class ProductRenderProperties(bpy.types.PropertyGroup):
    focus_object: PointerProperty(
        name="Focus Object",
        description="Object to focus the camera on",
        type=bpy.types.Object,
    )
    
    # Flag to track manual changes
    manual_camera_settings: BoolProperty(default=False)
    manual_focal_length: FloatProperty(default=70.0)
    manual_aperture: FloatProperty(default=2.4)
    
    # UI expand flags for collapsible sections
    key_light_expand: BoolProperty(default=True)
    fill_light_expand: BoolProperty(default=False)
    rim_light_expand: BoolProperty(default=False)
    
    camera_preset: EnumProperty(
        name="Camera Distance",
        description="Set camera distance and lens settings",
        items=CAMERA_PRESETS,
        default="medium",
        update=lambda self, context: update_camera_preset(self, context)
    )
    
    camera_offset: FloatProperty(
        name="Camera Distance Offset",
        description="Additional distance offset for the camera",
        default=0.0,
        min=-10.0,
        max=10.0,
        step=0.1,
        update=lambda self, context: update_camera_live(self, context)
    )
    
    # These will now offset the object instead of the camera
    camera_h_offset: FloatProperty(
        name="Object Horizontal Offset",
        description="Horizontal offset for the object (left/right)",
        default=0.0,
        min=-5.0,
        max=5.0,
        step=0.1,
        update=lambda self, context: update_camera_live(self, context)
    )
    
    camera_v_offset: FloatProperty(
        name="Object Vertical Offset",
        description="Vertical offset for the object (up/down)",
        default=0.0,
        min=-5.0,
        max=5.0,
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
        update=lambda self, context: update_focus_only(self, context)
    )
    
    # KEY LIGHT Properties
    key_light_strength: FloatProperty(
        name="Key Light Strength",
        description="Strength of the key light",
        default=1200.0,
        min=0.0,
        max=5000.0,
        step=10.0,
        update=lambda self, context: update_key_light(self, context)
    )
    
    key_light_temp: FloatProperty(
        name="Key Light Temperature",
        description="Color temperature of the key light (K)",
        default=5500.0,
        min=1000.0,
        max=10000.0,
        step=100.0,
        update=lambda self, context: update_key_light(self, context)
    )
    
    key_light_size: FloatProperty(
        name="Key Light Size",
        description="Size multiplier for the key light",
        default=1.0,
        min=0.1,
        max=3.0,
        step=0.1,
        update=lambda self, context: update_key_light(self, context)
    )
    
    key_light_offset: FloatProperty(
        name="Key Light Distance",
        description="Adjust distance of the key light from the object",
        default=0.0,
        min=-5.0,
        max=5.0,
        step=0.1,
        update=lambda self, context: update_key_light(self, context)
    )
    
    key_light_h_offset: FloatProperty(
        name="Key Light Horizontal Angle",
        description="Horizontal angle for the key light (degrees)",
        default=45.0,
        min=-180.0,
        max=180.0,
        step=5.0,
        update=lambda self, context: update_key_light(self, context)
    )
    
    key_light_v_offset: FloatProperty(
        name="Key Light Vertical Offset",
        description="Vertical offset for the key light (up/down)",
        default=1.0,
        min=-5.0,
        max=5.0,
        step=0.1,
        update=lambda self, context: update_key_light(self, context)
    )
    
    # FILL LIGHT Properties
    fill_light_strength: FloatProperty(
        name="Fill Light Strength",
        description="Strength of the fill light",
        default=600.0,
        min=0.0,
        max=5000.0,
        step=10.0,
        update=lambda self, context: update_fill_light(self, context)
    )
    
    fill_light_temp: FloatProperty(
        name="Fill Light Temperature",
        description="Color temperature of the fill light (K)",
        default=6000.0,
        min=1000.0,
        max=10000.0,
        step=100.0,
        update=lambda self, context: update_fill_light(self, context)
    )
    
    fill_light_size: FloatProperty(
        name="Fill Light Size",
        description="Size multiplier for the fill light",
        default=1.2,
        min=0.1,
        max=3.0,
        step=0.1,
        update=lambda self, context: update_fill_light(self, context)
    )
    
    fill_light_offset: FloatProperty(
        name="Fill Light Distance",
        description="Adjust distance of the fill light from the object",
        default=0.0,
        min=-5.0,
        max=5.0,
        step=0.1,
        update=lambda self, context: update_fill_light(self, context)
    )
    
    fill_light_h_offset: FloatProperty(
        name="Fill Light Horizontal Angle",
        description="Horizontal angle for the fill light (degrees)",
        default=-45.0,
        min=-180.0,
        max=180.0,
        step=5.0,
        update=lambda self, context: update_fill_light(self, context)
    )
    
    fill_light_v_offset: FloatProperty(
        name="Fill Light Vertical Offset",
        description="Vertical offset for the fill light (up/down)",
        default=0.0,
        min=-5.0,
        max=5.0,
        step=0.1,
        update=lambda self, context: update_fill_light(self, context)
    )
    
    # RIM LIGHT Properties
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
        name="Rim Light Temperature",
        description="Color temperature of the rim light (K)",
        default=5500.0,
        min=1000.0,
        max=10000.0,
        step=100.0,
        update=lambda self, context: update_rim_light(self, context)
    )
    
    rim_light_size: FloatProperty(
        name="Rim Light Size",
        description="Size multiplier for the rim light",
        default=0.8,
        min=0.1,
        max=3.0,
        step=0.1,
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
    
    rim_light_h_offset: FloatProperty(
        name="Rim Light Horizontal Angle",
        description="Horizontal angle for the rim light (degrees)",
        default=180.0,
        min=-180.0,
        max=180.0,
        step=5.0,
        update=lambda self, context: update_rim_light(self, context)
    )
    
    rim_light_v_offset: FloatProperty(
        name="Rim Light Vertical Offset",
        description="Vertical offset for the rim light (up/down)",
        default=1.0,
        min=-5.0,
        max=5.0,
        step=0.1,
        update=lambda self, context: update_rim_light(self, context)
    )
    
    # Store original object position for resetting
    original_obj_location_x: FloatProperty(default=0.0)
    original_obj_location_y: FloatProperty(default=0.0)
    original_obj_location_z: FloatProperty(default=0.0)

# Helper functions
def look_at_target(obj, target_location):
    """Point an object at a target location and set appropriate up vector"""
    direction = target_location - obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')  # -Z is forward in Blender
    obj.rotation_euler = rot_quat.to_euler()

def create_camera_for_object(context, focus_object):
    """Create a camera pointed at the focus object"""
    # Store original object position
    props = context.scene.product_render_props
    props.original_obj_location_x = focus_object.location.x
    props.original_obj_location_y = focus_object.location.y
    props.original_obj_location_z = focus_object.location.z
    
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

def create_focus_visualizer(context, location, camera, object_distance):
    """Create or update a semi-transparent plane at the focus point, facing the camera"""
    # Check if a visualizer plane already exists
    plane = None
    for obj in bpy.data.objects:
        if obj.name == FOCUS_PLANE_NAME or obj.name.startswith(FOCUS_PLANE_NAME):
            plane = obj
            break
    
    # Calculate an appropriate size based on distance to camera
    # This ensures the focus plane remains visible even when far from the camera
    base_size = 0.5
    size_factor = max(1.0, object_distance / 5.0)  # Scale up with distance
    scaled_size = base_size * size_factor
    
    # Create a new plane if none exists
    if plane is None:
        # Save current selection
        selected_objs = context.selected_objects
        active_obj = context.active_object
        
        bpy.ops.mesh.primitive_plane_add(size=scaled_size, location=location)
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
        
        # Restore previous selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_objs:
            obj.select_set(True)
        if active_obj:
            context.view_layer.objects.active = active_obj
    else:
        # Update existing plane position and size
        plane.location = location
        
        # Scale the plane based on distance
        plane.scale = (scaled_size / 0.5, scaled_size / 0.5, scaled_size / 0.5)
    
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

def create_light(context, focus_object, light_name, strength=1000.0, temperature=5500.0, 
                distance_offset=0.0, h_angle=0.0, v_offset=0.0, size_factor=1.0):
    """Create a light at a specified position relative to the object"""
    # Get the camera position
    camera = context.scene.camera
    if not camera or not focus_object:
        return None
    
    # Check if light already exists
    light_obj = None
    for obj in bpy.data.objects:
        if obj.name == light_name and obj.type == 'LIGHT':
            light_obj = obj
            light_data = light_obj.data
            break
    
    # Create new light if it doesn't exist
    if light_obj is None:
        light_data = bpy.data.lights.new(name=light_name, type='AREA')
        light_obj = bpy.data.objects.new(name=light_name, object_data=light_data)
        context.collection.objects.link(light_obj)
    
    # Set light properties
    light_data.energy = strength
    light_data.color = kelvin_to_rgb(temperature)
    light_data.shape = 'RECTANGLE'
    
    # Calculate dimensions based on object size and factor
    obj_dimension = max(focus_object.dimensions.x, focus_object.dimensions.y, focus_object.dimensions.z)
    light_data.size = obj_dimension * size_factor
    light_data.size_y = obj_dimension * 0.5 * size_factor
    
    # Calculate the light position
    obj_location = focus_object.location.copy()
    
    # Convert horizontal angle from degrees to radians
    h_angle_rad = math.radians(h_angle)
    
    # Calculate position using angle and distance
    light_distance = (obj_dimension * 2.0) + distance_offset
    light_location = obj_location.copy()
    light_location.x += math.cos(h_angle_rad) * light_distance
    light_location.y += math.sin(h_angle_rad) * light_distance
    light_location.z += v_offset  # Apply vertical offset
    
    # Update position
    light_obj.location = light_location
    
    # Point light at object
    look_at_target(light_obj, obj_location)
    
    return light_obj

def update_light(context, light_name, focus_object, strength, temperature, 
                distance_offset, h_angle, v_offset, size_factor):
    """Update an existing light's properties"""
    light_obj = None
    for obj in bpy.data.objects:
        if obj.name == light_name and obj.type == 'LIGHT':
            light_obj = obj
            break
    
    if not light_obj or not focus_object:
        return None
    
    # Update light properties
    light_obj.data.energy = strength
    light_obj.data.color = kelvin_to_rgb(temperature)
    
    # Calculate dimensions based on object size and factor
    obj_dimension = max(focus_object.dimensions.x, focus_object.dimensions.y, focus_object.dimensions.z)
    light_obj.data.size = obj_dimension * size_factor
    light_obj.data.size_y = obj_dimension * 0.5 * size_factor
    
    # Calculate the light position
    obj_location = focus_object.location.copy()
    
    # Convert horizontal angle from degrees to radians
    h_angle_rad = math.radians(h_angle)
    
    # Calculate position using angle and distance
    light_distance = (obj_dimension * 2.0) + distance_offset
    light_location = obj_location.copy()
    light_location.x += math.cos(h_angle_rad) * light_distance
    light_location.y += math.sin(h_angle_rad) * light_distance
    light_location.z += v_offset  # Apply vertical offset
    
    # Update position
    light_obj.location = light_location
    
    # Point light at object
    look_at_target(light_obj, obj_location)
    
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

def calculate_camera_position(context, focus_object, preset, camera_obj, offset=0.0, h_offset=0.0, v_offset=0.0, focus_adjustment=0.0):
    """Calculate the optimal camera position based on the preset and move the object instead of the camera for offsets"""
    props = context.scene.product_render_props
    
    # Reset object to original position first
    original_location = Vector((
        props.original_obj_location_x, 
        props.original_obj_location_y, 
        props.original_obj_location_z
    ))
    
    # Get object dimensions and bounding box
    bbox_corners = [focus_object.matrix_world @ Vector(corner) for corner in focus_object.bound_box]
    bbox_center = sum((Vector(corner) for corner in bbox_corners), Vector()) / 8
    
    # Calculate the object's dimensions
    dimensions = focus_object.dimensions
    max_dimension = max(dimensions)
    
    # Set focal length and aperture based on preset only if not manually changed
    camera = camera_obj.data
    
    if not props.manual_camera_settings:
        if preset == "close":
            camera.lens = 120.0
            camera.dof.aperture_fstop = 0.8
            distance_factor = 1.0
            # Store values for future reference
            props.manual_focal_length = 120.0
            props.manual_aperture = 0.8
        elif preset == "medium":
            camera.lens = 70.0
            camera.dof.aperture_fstop = 2.4
            distance_factor = 1.5
            # Store values for future reference
            props.manual_focal_length = 70.0
            props.manual_aperture = 2.4
        else:  # "far"
            camera.lens = 50.0
            camera.dof.aperture_fstop = 8.0
            distance_factor = 2.0
            # Store values for future reference
            props.manual_focal_length = 50.0
            props.manual_aperture = 8.0
    else:
        # Use stored manual values
        camera.lens = props.manual_focal_length
        camera.dof.aperture_fstop = props.manual_aperture
        
        # Set distance factor based on preset
        if preset == "close":
            distance_factor = 1.0
        elif preset == "medium":
            distance_factor = 1.5
        else:  # "far"
            distance_factor = 2.0
    
    # Enable depth of field
    camera.dof.use_dof = True
    
    # Get current camera direction
    direction = (bbox_center - camera_obj.location).normalized()
    
    # Calculate up and right vectors relative to the view direction
    up_vector = Vector((0, 0, 1))
    right_vector = direction.cross(up_vector).normalized()
    
    # Calculate camera distance based on field of view and object size
    fov = math.atan(36.0 / (2 * camera.lens))  # Approximate FOV in radians based on 36mm sensor width
    distance = (max_dimension * distance_factor) / (4 * math.tan(fov / 2))
    
    # Set new camera position with distance offset
    new_camera_position = bbox_center - direction * (distance + offset)
    
    # Update camera position
    camera_obj.location = new_camera_position
    
    # CHANGED: Move the object instead of the camera for horizontal and vertical offsets
    # Calculate object offsets in world space
    obj_offset = Vector((0, 0, 0))
    obj_offset -= right_vector * h_offset  # Moving object left is like moving camera right
    obj_offset.z -= v_offset  # Moving object down is like moving camera up
    
    # Apply offset to object
    focus_object.location = original_location + obj_offset
    
    # Make sure the camera constraint is still targeting the object
    for constraint in camera_obj.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.target = focus_object
    
    # Recalculate bounding box after moving the object
    bbox_corners = [focus_object.matrix_world @ Vector(corner) for corner in focus_object.bound_box]
    
    # Calculate and set focus point based on adjustment
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
    
    # Calculate distance to object for focus visualizer scaling
    object_distance = (camera_obj.location - focus_object.location).length
        
    return focus_point, object_distance

def update_camera_preset(self, context):
    """Handle camera preset changes"""
    # Reset manual flag when preset changes
    self.manual_camera_settings = False
    update_camera_live(self, context)

def update_focus_only(self, context):
    """Update just the focus point without changing other camera settings"""
    props = context.scene.product_render_props
    focus_object = props.focus_object
    camera = context.scene.camera
    
    if not focus_object or not camera or camera.type != 'CAMERA':
        remove_focus_visualizer()
        return
    
    # Set the manual flag to true since user is adjusting focus
    props.manual_camera_settings = True
    
    # Calculate focus point and update camera
    focus_point, object_distance = calculate_camera_position(
        context,
        focus_object, 
        props.camera_preset, 
        camera, 
        props.camera_offset,
        props.camera_h_offset,
        props.camera_v_offset,
        props.focus_adjustment
    )
    
    # Create or update focus visualizer
    if focus_point:
        create_focus_visualizer(context, focus_point, camera, object_distance)

def update_camera_live(self, context):
    """Live update function for camera parameters"""
    props = context.scene.product_render_props
    focus_object = props.focus_object
    camera = context.scene.camera
    
    if not focus_object or not camera or camera.type != 'CAMERA':
        remove_focus_visualizer()
        return
    
    # Calculate focus point and update camera
    focus_point, object_distance = calculate_camera_position(
        context,
        focus_object, 
        props.camera_preset, 
        camera, 
        props.camera_offset,
        props.camera_h_offset,
        props.camera_v_offset,
        props.focus_adjustment
    )
    
    # Create or update focus visualizer
    if focus_point:
        create_focus_visualizer(context, focus_point, camera, object_distance)

def update_key_light(self, context):
    """Update key light settings"""
    props = context.scene.product_render_props
    focus_object = props.focus_object
    
    if not focus_object:
        return
    
    # Check if light exists
    light_exists = False
    for obj in bpy.data.objects:
        if obj.name == KEY_LIGHT_NAME and obj.type == 'LIGHT':
            light_exists = True
            break
    
    # Create or update the key light
    if light_exists:
        update_light(
            context,
            KEY_LIGHT_NAME,
            focus_object,
            props.key_light_strength,
            props.key_light_temp,
            props.key_light_offset,
            props.key_light_h_offset,
            props.key_light_v_offset,
            props.key_light_size
        )
    else:
        create_light(
            context,
            focus_object,
            KEY_LIGHT_NAME,
            props.key_light_strength,
            props.key_light_temp,
            props.key_light_offset,
            props.key_light_h_offset,
            props.key_light_v_offset,
            props.key_light_size
        )

def update_fill_light(self, context):
    """Update fill light settings"""
    props = context.scene.product_render_props
    focus_object = props.focus_object
    
    if not focus_object:
        return
    
    # Check if light exists
    light_exists = False
    for obj in bpy.data.objects:
        if obj.name == FILL_LIGHT_NAME and obj.type == 'LIGHT':
            light_exists = True
            break
    
    # Create or update the fill light
    if light_exists:
        update_light(
            context,
            FILL_LIGHT_NAME,
            focus_object,
            props.fill_light_strength,
            props.fill_light_temp,
            props.fill_light_offset,
            props.fill_light_h_offset,
            props.fill_light_v_offset,
            props.fill_light_size
        )
    else:
        create_light(
            context,
            focus_object,
            FILL_LIGHT_NAME,
            props.fill_light_strength,
            props.fill_light_temp,
            props.fill_light_offset,
            props.fill_light_h_offset,
            props.fill_light_v_offset,
            props.fill_light_size
        )

def update_rim_light(self, context):
    """Update rim light settings"""
    props = context.scene.product_render_props
    focus_object = props.focus_object
    
    if not focus_object:
        return
    
    # Check if light exists
    light_exists = False
    for obj in bpy.data.objects:
        if obj.name == RIM_LIGHT_NAME and obj.type == 'LIGHT':
            light_exists = True
            break
    
    # Create or update the rim light
    if light_exists:
        update_light(
            context,
            RIM_LIGHT_NAME,
            focus_object,
            props.rim_light_strength,
            props.rim_light_temp,
            props.rim_light_offset,
            props.rim_light_h_offset,
            props.rim_light_v_offset,
            props.rim_light_size
        )
    else:
        create_light(
            context,
            focus_object,
            RIM_LIGHT_NAME,
            props.rim_light_strength,
            props.rim_light_temp,
            props.rim_light_offset,
            props.rim_light_h_offset,
            props.rim_light_v_offset,
            props.rim_light_size
        )




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
        
        # KEY LIGHT collapsible section
        key_box = layout.box()
        key_row = key_box.row()
        key_row.prop(props, "key_light_expand", 
                    icon="TRIA_DOWN" if props.key_light_expand else "TRIA_RIGHT", 
                    icon_only=True, emboss=False)
        key_row.label(text="Key Light")
        
        # Show key light settings if expanded
        if props.key_light_expand:
            # Properties section
            props_box = key_box.box()
            props_box.label(text="Properties:")
            props_box.prop(props, "key_light_strength", text="Strength")
            props_box.prop(props, "key_light_temp", text="Temperature")
            props_box.prop(props, "key_light_size", text="Size")
            
            # Position section
            pos_box = key_box.box()
            pos_box.label(text="Position:")
            pos_box.prop(props, "key_light_offset", text="Distance")
            pos_box.prop(props, "key_light_h_offset", text="Horizontal Angle")
            pos_box.prop(props, "key_light_v_offset", text="Vertical Offset")
        
        # FILL LIGHT collapsible section
        fill_box = layout.box()
        fill_row = fill_box.row()
        fill_row.prop(props, "fill_light_expand", 
                     icon="TRIA_DOWN" if props.fill_light_expand else "TRIA_RIGHT", 
                     icon_only=True, emboss=False)
        fill_row.label(text="Fill Light")
        
        # Show fill light settings if expanded
        if props.fill_light_expand:
            # Properties section
            props_box = fill_box.box()
            props_box.label(text="Properties:")
            props_box.prop(props, "fill_light_strength", text="Strength")
            props_box.prop(props, "fill_light_temp", text="Temperature")
            props_box.prop(props, "fill_light_size", text="Size")
            
            # Position section
            pos_box = fill_box.box()
            pos_box.label(text="Position:")
            pos_box.prop(props, "fill_light_offset", text="Distance")
            pos_box.prop(props, "fill_light_h_offset", text="Horizontal Angle")
            pos_box.prop(props, "fill_light_v_offset", text="Vertical Offset")
        
        # RIM LIGHT collapsible section
        rim_box = layout.box()
        rim_row = rim_box.row()
        rim_row.prop(props, "rim_light_expand", 
                    icon="TRIA_DOWN" if props.rim_light_expand else "TRIA_RIGHT", 
                    icon_only=True, emboss=False)
        rim_row.label(text="Rim Light")
        
        # Show rim light settings if expanded
        if props.rim_light_expand:
            # Properties section
            props_box = rim_box.box()
            props_box.label(text="Properties:")
            props_box.prop(props, "rim_light_strength", text="Strength")
            props_box.prop(props, "rim_light_temp", text="Temperature")
            props_box.prop(props, "rim_light_size", text="Size")
            
            # Position section
            pos_box = rim_box.box()
            pos_box.label(text="Position:")
            pos_box.prop(props, "rim_light_offset", text="Distance")
            pos_box.prop(props, "rim_light_h_offset", text="Horizontal Angle")
            pos_box.prop(props, "rim_light_v_offset", text="Vertical Offset")

# UI Panel classes
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
        
        # Camera positioning sliders
        box.label(text="Object Position:")
        box.prop(props, "camera_offset")
        box.prop(props, "camera_h_offset", text="Object Horizontal Offset")
        box.prop(props, "camera_v_offset", text="Object Vertical Offset")
        
        # Reset object position button
        row = box.row()
        row.operator("product.reset_object_position")
        
        # Focus adjustment
        box.label(text="Focus:")
        box.prop(props, "focus_adjustment")
        
        # Camera quick settings
        camera = context.scene.camera
        if camera and camera.type == 'CAMERA':
            layout.separator()
            box = layout.box()
            box.label(text="Current Camera Settings:")
            
            # Use custom property for focal length to maintain when moving camera
            row = box.row()
            row.prop(camera.data, "lens", text="Focal Length")
            
            # Add aperture control
            if hasattr(camera.data.dof, "aperture_fstop"):
                row = box.row()
                row.prop(camera.data.dof, "aperture_fstop", text="Aperture")

class PRODUCT_OT_reset_object_position(bpy.types.Operator):
    """Reset object to its original position"""
    bl_idname = "product.reset_object_position"
    bl_label = "Reset Object Position"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.product_render_props
        focus_object = props.focus_object
        
        if not focus_object:
            self.report({'ERROR'}, "No focus object selected")
            return {'CANCELLED'}
        
        # Reset object to original position
        focus_object.location.x = props.original_obj_location_x
        focus_object.location.y = props.original_obj_location_y
        focus_object.location.z = props.original_obj_location_z
        
        # Reset the offset sliders
        props.camera_h_offset = 0.0
        props.camera_v_offset = 0.0
        
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
        
        # Create key light
        key_light = create_light(
            context, 
            focus_object, 
            KEY_LIGHT_NAME,
            strength=props.key_light_strength,
            temperature=props.key_light_temp,
            distance_offset=props.key_light_offset,
            h_angle=props.key_light_h_offset,
            v_offset=props.key_light_v_offset,
            size_factor=props.key_light_size
        )
        
        # Create fill light
        fill_light = create_light(
            context, 
            focus_object, 
            FILL_LIGHT_NAME,
            strength=props.fill_light_strength,
            temperature=props.fill_light_temp,
            distance_offset=props.fill_light_offset,
            h_angle=props.fill_light_h_offset,
            v_offset=props.fill_light_v_offset,
            size_factor=props.fill_light_size
        )
        
        # Create rim light
        rim_light = create_light(
            context, 
            focus_object, 
            RIM_LIGHT_NAME,
            strength=props.rim_light_strength,
            temperature=props.rim_light_temp,
            distance_offset=props.rim_light_offset,
            h_angle=props.rim_light_h_offset,
            v_offset=props.rim_light_v_offset,
            size_factor=props.rim_light_size
        )
        
        if key_light and fill_light and rim_light:
            self.report({'INFO'}, "Lighting setup created")
            
            # Select the key light
            bpy.ops.object.select_all(action='DESELECT')
            key_light.select_set(True)
            context.view_layer.objects.active = key_light
        
        return {'FINISHED'}

# Operator classes
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
        focus_point, object_distance = calculate_camera_position(
            context,
            focus_object, 
            props.camera_preset, 
            camera, 
            props.camera_offset,
            props.camera_h_offset,
            props.camera_v_offset,
            props.focus_adjustment
        )
        
        # Select the camera
        bpy.ops.object.select_all(action='DESELECT')
        camera.select_set(True)
        context.view_layer.objects.active = camera
        
        return {'FINISHED'}

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
            
    return 0.5  # Continue checking every 0.5 seconds# Product Render Setup Add-on for Blender

        # Registration
classes = (
    ProductRenderProperties,
    PRODUCT_OT_create_camera,
    PRODUCT_OT_create_lights,
    PRODUCT_OT_reset_object_position,
    PRODUCT_PT_render_panel,
    PRODUCT_PT_lighting_panel,
)

def register():
    # Register all classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register properties
    bpy.types.Scene.product_render_props = bpy.props.PointerProperty(type=ProductRenderProperties)
    
    # Debug info to console
    print("Product Render Setup add-on registered successfully")
    print(f"Add-on will be available in View3D > Sidebar > Product Render")
    
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