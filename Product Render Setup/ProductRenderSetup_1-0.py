bl_info = {
    "name": "Product Render Setup",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > Product Render",
    "description": "Set up camera for product renders with different framing options",
    "category": "3D View",
}

import bpy
import math
from mathutils import Vector
from bpy.props import EnumProperty, FloatProperty, PointerProperty

# Camera distance presets
CAMERA_PRESETS = [
    ("close", "Close", "Close-up view with 120mm focal length, f/0.8 aperture", 1),
    ("medium", "Medium", "Medium view with 70mm focal length, f/2.4 aperture", 2),
    ("far", "Far", "Far view with 50mm focal length, f/8.0 aperture", 3),
]

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
        step=0.1
    )

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

def calculate_camera_position(focus_object, preset, camera_obj, offset=0.0):
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
        distance_factor = 1.0  # Reduced from 2.0
    elif preset == "medium":
        camera.lens = 70.0
        camera.dof.aperture_fstop = 2.4
        distance_factor = 1.5  # Reduced from 3.0
    else:  # "far"
        camera.lens = 50.0
        camera.dof.aperture_fstop = 8.0
        distance_factor = 2.0  # Reduced from 4.0
    
    # Enable depth of field
    camera.dof.use_dof = True
    camera.dof.focus_object = focus_object
    
    # Calculate camera distance based on field of view and object size
    fov = math.atan(36.0 / (2 * camera.lens))  # Approximate FOV in radians based on 36mm sensor width
    # Reduce the distance by approximately half to improve framing
    distance = (max_dimension * distance_factor) / (4 * math.tan(fov / 2))
    
    # Get current camera direction
    direction = (bbox_center - camera_obj.location).normalized()
    
    # Set new camera position
    new_position = bbox_center - direction * (distance + offset)
    camera_obj.location = new_position
    
    # Make sure the camera constraint is still targeting the object
    for constraint in camera_obj.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.target = focus_object

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
        calculate_camera_position(focus_object, props.camera_preset, camera, props.camera_offset)
        
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
        
        calculate_camera_position(focus_object, props.camera_preset, camera, props.camera_offset)
        
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
        
        # Update camera button
        row = layout.row()
        row.operator("product.update_camera")
        
        # Camera quick settings
        camera = context.scene.camera
        if camera and camera.type == 'CAMERA':
            layout.separator()
            box = layout.box()
            box.label(text="Current Camera Settings:")
            box.prop(camera.data, "lens", text="Focal Length")
            box.prop(camera.data.dof, "aperture_fstop", text="Aperture")

classes = (
    ProductRenderProperties,
    PRODUCT_OT_create_camera,
    PRODUCT_OT_update_camera,
    PRODUCT_PT_render_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.product_render_props = bpy.props.PointerProperty(type=ProductRenderProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.product_render_props

if __name__ == "__main__":
    register()