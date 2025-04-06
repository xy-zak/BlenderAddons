bl_info = {
    "name": "OSC Controller",
    "author": "Zak Silver-Lennard ",
    "version": (1, 1, 2),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > OSC",
    "description": "Control object properties using OSC messages over LAN with keyframe recording (python-osc included)",
    "category": "Object",
}

import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, BoolProperty
from bpy.types import Panel, Operator, PropertyGroup
import sys
import os
import threading
import datetime



# Global variables
osc_server_thread = None
osc_server_instance = None
is_server_running = False
dependency_error = ""
osc_values_dict = {}  # Dictionary to store the latest OSC values by address
mapped_values_dict = {}  # Dictionary to store the mapped values by address
pythonosc_available = False
pythonosc_path = "Not installed"
is_recording = False  # Flag to track recording state
keyframe_timer = None  # Timer for keyframing
smoothing_buffers = {}  # For storing value history for buffer smoothing
last_keyframed_values = {}  # For storing the last keyframed values for threshold smoothing

# Try importing pythonosc, handle gracefully if not available
def check_pythonosc():
    global pythonosc_available, pythonosc_path
    
    try:
        # First try to import normally in case it's already installed
        from pythonosc import dispatcher, osc_server
        pythonosc_available = True
        try:
            import pythonosc
            pythonosc_path = os.path.dirname(pythonosc.__file__)
        except:
            pythonosc_path = "System installation (path unknown)"
        return True
    except ImportError:
        # If not found, try to use the bundled version
        try:
            # Get the directory of the current script
            current_dir = os.path.dirname(os.path.realpath(__file__))
            # Path to the bundled library
            vendor_path = os.path.join(current_dir, "vendor")
            
            # Add to path if not already there
            if vendor_path not in sys.path:
                sys.path.insert(0, vendor_path)
                
            # Try import again
            from pythonosc import dispatcher, osc_server
            pythonosc_available = True
            pythonosc_path = os.path.join(vendor_path, "pythonosc")
            return True
        except ImportError:
            pythonosc_available = False
            pythonosc_path = "Not installed"
            return False

# Initial check for pythonosc
check_pythonosc()

# Data structure to store OSC mappings
class OSCMapping(PropertyGroup):
    target_object: PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        description="Object to be controlled by OSC"
    )
    
    property_types = [
        ('location_x', "Location X", "X Position"),
        ('location_y', "Location Y", "Y Position"),
        ('location_z', "Location Z", "Z Position"),
        ('rotation_x', "Rotation X", "X Rotation"),
        ('rotation_y', "Rotation Y", "Y Rotation"),
        ('rotation_z', "Rotation Z", "Z Rotation"),
        ('scale_x', "Scale X", "X Scale"),
        ('scale_y', "Scale Y", "Y Scale"),
        ('scale_z', "Scale Z", "Z Scale"),
        ('custom_property', "Custom Property", "Use a custom property of the object"),
    ]
    
    property_type: EnumProperty(
        name="Property",
        description="Property to be controlled",
        items=property_types
    )
    
    custom_property_name: StringProperty(
        name="Custom Property Name",
        description="Name of the custom property if 'Custom Property' is selected"
    )
    
    osc_address: StringProperty(
        name="OSC Address",
        description="OSC address pattern (e.g., /position/x)",
        default="/blender/value"
    )
    
    # Raw input range
    raw_min_value: FloatProperty(
        name="Raw Min Value",
        description="Minimum value expected from OSC input",
        default=0.0
    )
    
    raw_max_value: FloatProperty(
        name="Raw Max Value",
        description="Maximum value expected from OSC input",
        default=1.0
    )
    
    # Remapped output range
    remap_min_value: FloatProperty(
        name="Remap Min Value",
        description="Minimum value for remapped output",
        default=0.0
    )
    
    remap_max_value: FloatProperty(
        name="Remap Max Value",
        description="Maximum value for remapped output",
        default=1.0
    )
    
    is_active: BoolProperty(
        name="Active",
        description="Enable/disable this mapping",
        default=True
    )
    
    show_driver_info: BoolProperty(
        name="Show Driver Info",
        description="Show information for creating drivers with this OSC data",
        default=False
    )

# Data structure for objects to record keyframes for
class OSCRecordObject(PropertyGroup):
    target_object: PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        description="Object to record keyframes for"
    )
    
    is_active: BoolProperty(
        name="Active",
        description="Enable/disable recording for this object",
        default=True
    )
    
    record_location: BoolProperty(
        name="Location",
        description="Record keyframes for location",
        default=True
    )
    
    record_rotation: BoolProperty(
        name="Rotation",
        description="Record keyframes for rotation",
        default=True
    )
    
    record_scale: BoolProperty(
        name="Scale",
        description="Record keyframes for scale",
        default=True
    )
    
    record_custom_properties: BoolProperty(
        name="Custom Properties",
        description="Record keyframes for custom properties",
        default=False
    )
    
    custom_properties: StringProperty(
        name="Custom Properties",
        description="Comma-separated list of custom properties to record",
        default=""
    )



# Function to remap a value from one range to another
def remap_value(value, old_min, old_max, new_min, new_max):
    # Handle division by zero case
    if old_min == old_max:
        return new_min
    
    # Calculate what percentage of the old range the value is
    old_range = old_max - old_min
    normalized = (value - old_min) / old_range
    
    # Apply that percentage to the new range
    new_range = new_max - new_min
    return new_min + normalized * new_range

# Helper function to set object property
def set_object_property(obj, prop_type, custom_prop_name, value):
    if not obj:
        return
    
    try:
        if prop_type == 'location_x':
            obj.location[0] = value
        elif prop_type == 'location_y':
            obj.location[1] = value
        elif prop_type == 'location_z':
            obj.location[2] = value
        elif prop_type == 'rotation_x':
            obj.rotation_euler[0] = value
        elif prop_type == 'rotation_y':
            obj.rotation_euler[1] = value
        elif prop_type == 'rotation_z':
            obj.rotation_euler[2] = value
        elif prop_type == 'scale_x':
            obj.scale[0] = value
        elif prop_type == 'scale_y':
            obj.scale[1] = value
        elif prop_type == 'scale_z':
            obj.scale[2] = value
        elif prop_type == 'custom_property':
            if custom_prop_name in obj:
                obj[custom_prop_name] = value
    except Exception as e:
        print(f"OSC Controller: Error setting property: {str(e)}")

# Function to restart OSC server after render completes
def restart_osc_server_after_render():
    print("OSC Controller: Render completed, restarting OSC server")
    bpy.ops.osc.start_server()

# Handler for render completion
def render_complete_handler(scene):
    bpy.app.timers.register(restart_osc_server_after_render, first_interval=0.5)

# Handler for render cancellation
def render_cancel_handler(scene):
    bpy.app.timers.register(restart_osc_server_after_render, first_interval=0.5)

# Function to insert keyframes for recorded objects
def insert_keyframes():
    """Insert keyframes for recorded objects"""
    print("OSC Controller: Inserting keyframes...")
    for obj_record in bpy.context.scene.osc_record_objects:
        if not obj_record.target_object or not obj_record.is_active:
            continue
            
        target = obj_record.target_object
        frame = bpy.context.scene.frame_current
        print(f"OSC Controller: Adding keyframes for {target.name} at frame {frame}")
        
        # Keyframe location if enabled
        if obj_record.record_location:
            target.keyframe_insert(data_path="location", frame=frame)
            print(f"OSC Controller: Added location keyframes")
        
        # Keyframe rotation if enabled
        if obj_record.record_rotation:
            target.keyframe_insert(data_path="rotation_euler", frame=frame)
            print(f"OSC Controller: Added rotation keyframes")
        
        # Keyframe scale if enabled
        if obj_record.record_scale:
            target.keyframe_insert(data_path="scale", frame=frame)
            print(f"OSC Controller: Added scale keyframes")
        
        # Insert custom property keyframes if applicable
        if obj_record.record_custom_properties and obj_record.custom_properties:
            custom_props = [prop.strip() for prop in obj_record.custom_properties.split(',')]
            for prop_name in custom_props:
                if prop_name in target:
                    target.keyframe_insert(data_path=f'["{prop_name}"]', frame=frame)
                    print(f"OSC Controller: Added custom property keyframe for {prop_name}")

class OSC_OT_SmoothKeyframes(Operator):
    bl_idname = "osc.smooth_keyframes"
    bl_label = "Smooth Keyframes"
    bl_description = "Apply Gaussian smoothing to recorded keyframes"
    
    @classmethod
    def poll(cls, context):
        # Only show this operator if we have record objects
        return len(context.scene.osc_record_objects) > 0
    
    def execute(self, context):
        settings = context.scene.osc_settings
        successful_objects = 0
        
        try:
            for rec_obj in context.scene.osc_record_objects:
                if not rec_obj.target_object or not rec_obj.is_active:
                    continue
                    
                obj = rec_obj.target_object
                fcurves_smoothed = 0
                
                # Get the object's animation data or create it if it doesn't exist
                animation_data = obj.animation_data
                if not animation_data or not animation_data.action:
                    continue
                    
                # Get all FCurves for this object
                action = animation_data.action
                
                # Process location FCurves
                if rec_obj.record_location:
                    for i in range(3):  # x, y, z
                        fcurve = action.fcurves.find('location', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 2:  # Need at least 3 points to smooth
                            # Apply custom smoothing
                            if self.apply_smooth_modifier(fcurve, settings.post_smooth_factor):
                                fcurves_smoothed += 1
                
                # Process rotation FCurves
                if rec_obj.record_rotation:
                    for i in range(3):  # x, y, z
                        fcurve = action.fcurves.find('rotation_euler', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 2:
                            if self.apply_smooth_modifier(fcurve, settings.post_smooth_factor):
                                fcurves_smoothed += 1
                
                # Process scale FCurves
                if rec_obj.record_scale:
                    for i in range(3):  # x, y, z
                        fcurve = action.fcurves.find('scale', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 2:
                            if self.apply_smooth_modifier(fcurve, settings.post_smooth_factor):
                                fcurves_smoothed += 1
                
                # Process custom properties
                if rec_obj.record_custom_properties and rec_obj.custom_properties:
                    custom_props = [prop.strip() for prop in rec_obj.custom_properties.split(',')]
                    for prop_name in custom_props:
                        data_path = f'["{prop_name}"]'
                        fcurve = action.fcurves.find(data_path)
                        if fcurve and len(fcurve.keyframe_points) > 2:
                            if self.apply_smooth_modifier(fcurve, settings.post_smooth_factor):
                                fcurves_smoothed += 1
                
                if fcurves_smoothed > 0:
                    successful_objects += 1
                    
            if successful_objects > 0:
                self.report({'INFO'}, f"Smoothed keyframes on {successful_objects} objects")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "No keyframes found to smooth (need at least 3 keyframes per curve)")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Error while smoothing: {str(e)}")
            return {'CANCELLED'}
    
    def apply_smooth_modifier(self, fcurve, smooth_factor):
        """Apply smoothing to an FCurve manually since Blender doesn't have a GAUSSIAN_SMOOTH modifier"""
        try:
            # First create a backup of the original keyframe points
            original_points = [(p.co.x, p.co.y) for p in fcurve.keyframe_points]
            
            if len(original_points) < 3:
                # Not enough points to smooth
                return False
                
            # Get the smooth width based on the factor
            # Higher factor = more neighbors considered = smoother curve
            kernel_size = max(3, int(3 + (smooth_factor * 2)))
            if kernel_size % 2 == 0:  # Ensure odd kernel size
                kernel_size += 1
                
            # Create a simple Gaussian-like smoothing kernel
            # This is a triangular kernel which approximates a Gaussian
            half = kernel_size // 2
            kernel = []
            for i in range(kernel_size):
                weight = 1.0 - (abs(i - half) / (half + 0.5))
                kernel.append(weight)
                
            # Normalize kernel
            total = sum(kernel)
            kernel = [k / total for k in kernel]
            
            # Apply the smoothing
            # We'll work with a temporary list to avoid affecting values we haven't processed yet
            new_values = []
            
            # For each point, calculate the weighted average of it and its neighbors
            for i in range(len(original_points)):
                weighted_sum = 0
                weights_used = 0
                
                for j in range(-half, half + 1):
                    if 0 <= (i + j) < len(original_points):
                        weight = kernel[j + half]
                        weighted_sum += original_points[i + j][1] * weight
                        weights_used += weight
                
                # Normalize based on weights actually used (for edge cases)
                if weights_used > 0:
                    new_values.append(weighted_sum / weights_used)
                else:
                    new_values.append(original_points[i][1])
                    
            # Apply the new values
            for i, kf in enumerate(fcurve.keyframe_points):
                if i < len(new_values):
                    kf.co.y = new_values[i]
            
            # Update the FCurve
            fcurve.update()
            return True
            
        except Exception as e:
            print(f"OSC Controller: Error smoothing FCurve: {str(e)}")
            return False
        

class OSC_OT_RemoveJitter(Operator):
    bl_idname = "osc.remove_jitter"
    bl_label = "Remove Jitter"
    bl_description = "Remove rogue keyframes that appear to be jitter"
    
    @classmethod
    def poll(cls, context):
        # Only show this operator if we have record objects
        return len(context.scene.osc_record_objects) > 0
    
    def execute(self, context):
        settings = context.scene.osc_settings
        threshold = settings.jitter_threshold
        total_removed = 0
        objects_affected = 0
        
        try:
            for rec_obj in context.scene.osc_record_objects:
                if not rec_obj.target_object or not rec_obj.is_active:
                    continue
                
                obj = rec_obj.target_object
                fcurves_processed = 0
                keyframes_removed = 0
                
                # Get the object's animation data
                animation_data = obj.animation_data
                if not animation_data or not animation_data.action:
                    continue
                
                action = animation_data.action
                
                # Process all selected property types
                curves_to_process = []
                
                # Add location curves
                if rec_obj.record_location:
                    for i in range(3):
                        fcurve = action.fcurves.find('location', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 4:
                            curves_to_process.append(fcurve)
                
                # Add rotation curves
                if rec_obj.record_rotation:
                    for i in range(3):
                        fcurve = action.fcurves.find('rotation_euler', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 4:
                            curves_to_process.append(fcurve)
                
                # Add scale curves
                if rec_obj.record_scale:
                    for i in range(3):
                        fcurve = action.fcurves.find('scale', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 4:
                            curves_to_process.append(fcurve)
                
                # Add custom properties
                if rec_obj.record_custom_properties and rec_obj.custom_properties:
                    custom_props = [prop.strip() for prop in rec_obj.custom_properties.split(',')]
                    for prop_name in custom_props:
                        data_path = f'["{prop_name}"]'
                        fcurve = action.fcurves.find(data_path)
                        if fcurve and len(fcurve.keyframe_points) > 4:
                            curves_to_process.append(fcurve)
                
                # Process each curve to remove jitter
                for fcurve in curves_to_process:
                    removed = self.remove_jitter_from_curve(fcurve, threshold)
                    if removed > 0:
                        keyframes_removed += removed
                        fcurves_processed += 1
                
                if keyframes_removed > 0:
                    objects_affected += 1
                    total_removed += keyframes_removed
            
            if total_removed > 0:
                self.report({'INFO'}, f"Removed {total_removed} jitter keyframes from {objects_affected} objects")
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No jitter keyframes found to remove")
                return {'FINISHED'}
        
        except Exception as e:
            self.report({'ERROR'}, f"Error while removing jitter: {str(e)}")
            return {'CANCELLED'}
    
    def remove_jitter_from_curve(self, fcurve, threshold):
        """Identify and remove keyframes that appear to be jitter outliers"""
        try:
            # Need at least 5 keyframes for this to work effectively
            if len(fcurve.keyframe_points) < 5:
                return 0
            
            # Create a working copy of keyframe points and sort by frame
            keyframes = [(kf.co.x, kf.co.y, i) for i, kf in enumerate(fcurve.keyframe_points)]
            keyframes.sort(key=lambda k: k[0])  # Sort by x (frame)
            
            # Find outliers by comparing each point to its neighbors' trend
            to_remove = []
            
            for i in range(2, len(keyframes) - 2):
                # Get five consecutive points
                p0 = keyframes[i-2][1]  # y value
                p1 = keyframes[i-1][1]
                p2 = keyframes[i][1]    # Current point
                p3 = keyframes[i+1][1]
                p4 = keyframes[i+2][1]
                
                # Calculate expected value based on neighbors
                expected = (p0 + p1 + p3 + p4) / 4.0
                
                # Calculate difference from expected value
                diff = abs(p2 - expected)
                
                # Calculate local range of values to normalize the difference
                local_range = max(p0, p1, p2, p3, p4) - min(p0, p1, p2, p3, p4)
                if local_range == 0:
                    local_range = 0.0001  # Avoid division by zero
                
                # If normalized difference exceeds threshold, mark for removal
                if (diff / local_range) > threshold:
                    to_remove.append(keyframes[i][2])  # Original index
            
            # Remove the marked keyframes (in reverse order to avoid index shifting)
            for idx in sorted(to_remove, reverse=True):
                fcurve.keyframe_points.remove(fcurve.keyframe_points[idx])
            
            # Update the curve
            if to_remove:
                fcurve.update()
            
            return len(to_remove)
        
        except Exception as e:
            print(f"OSC Controller: Error removing jitter: {str(e)}")
            return 0


    # Function that's called each frame during recording
def keyframe_recording_callback():
    print("OSC Controller: Keyframe callback running...")
    if is_recording:
        # Get the current time
        current_time = datetime.datetime.now()
        
        # Get the desired frame rate
        try:
            fps = int(bpy.context.scene.osc_settings.keyframe_rate)
        except:
            fps = 30  # Default to 30 fps if there's an issue
        
        # Calculate time between frames in seconds
        frame_time = 1.0 / fps
        
        # Check if we've reached the end of the frame range
        if bpy.context.scene.osc_settings.auto_stop_at_end:
            current_frame = bpy.context.scene.frame_current
            end_frame = bpy.context.scene.frame_end
            
            if current_frame >= end_frame:
                # Stop recording
                print("OSC Controller: Reached end frame, stopping recording")
                bpy.app.timers.register(stop_recording)
                return None
        
        # Only insert keyframes at the desired rate
        if not hasattr(keyframe_recording_callback, "last_keyframe_time"):
            print("OSC Controller: First keyframe of recording")
            keyframe_recording_callback.last_keyframe_time = current_time
            insert_keyframes()
        else:
            elapsed = (current_time - keyframe_recording_callback.last_keyframe_time).total_seconds()
            if elapsed >= frame_time:
                print(f"OSC Controller: Adding keyframe after {elapsed:.3f}s (target: {frame_time:.3f}s)")
                insert_keyframes()
                keyframe_recording_callback.last_keyframe_time = current_time
        
        return 0.01  # Check again in 10ms (more responsive than waiting a full frame)
    
    # Clean up when recording stops
    if hasattr(keyframe_recording_callback, "last_keyframe_time"):
        del keyframe_recording_callback.last_keyframe_time
    
    print("OSC Controller: Keyframe callback stopping")
    return None  # Stop the timer

# Function to start recording frames
def start_recording():
    global is_recording, keyframe_timer
    
    # Make sure we're not already recording
    if is_recording:
        print("OSC Controller: Already recording, ignoring start request")
        return
        
    is_recording = True
    print("OSC Controller: Starting recording frames")
    
    # Start playing the timeline if it's not already playing
    if not bpy.context.screen.is_animation_playing:
        bpy.ops.screen.animation_play()
        print("OSC Controller: Started animation playback")
    
    # Set up a timer to insert keyframes at the specified rate
    if keyframe_timer is not None and keyframe_timer in bpy.app.timers.get_list():
        try:
            bpy.app.timers.unregister(keyframe_timer)
            print("OSC Controller: Removed existing timer")
        except:
            pass
    
    # Create a new timer
    keyframe_timer = bpy.app.timers.register(keyframe_recording_callback, persistent=True)
    print(f"OSC Controller: Registered new keyframe timer: {keyframe_timer}")

# Function to stop recording frames
def stop_recording():
    global is_recording, keyframe_timer
    is_recording = False
    
    # Stop playing the timeline
    if bpy.context.screen.is_animation_playing:
        bpy.ops.screen.animation_play()
    
    # The keyframe timer will auto-stop when is_recording is False
    if keyframe_timer and keyframe_timer in bpy.app.timers.get_list():
        bpy.app.timers.unregister(keyframe_timer)
    keyframe_timer = None
    
    # Apply jitter removal if enabled
    if bpy.context.scene.osc_settings.remove_jitter:
        bpy.ops.osc.remove_jitter()
    
    # Apply post-smoothing if enabled
    if bpy.context.scene.osc_settings.post_smooth_keyframes:
        bpy.ops.osc.smooth_keyframes()
    
    print("OSC Controller: Stopped recording frames")

# Function to handle the render image command
def start_render_image():
    print("OSC Controller: Starting render")
    # Stop the OSC server before rendering
    bpy.ops.osc.stop_server()
    
    # Add handlers for render completion and cancellation
    bpy.app.handlers.render_complete.append(render_complete_handler)
    bpy.app.handlers.render_cancel.append(render_cancel_handler)
    
    # Start the render
    bpy.ops.render.render('INVOKE_DEFAULT')

# OSC message handler
def osc_handler(address, *args):
    if not args:
        return
    
    try:
        value = args[0]
        if not isinstance(value, (int, float)):
            return
        
        # Store the raw OSC value
        osc_values_dict[address] = value
        
        # Update debug info
        if hasattr(bpy.context.scene, 'osc_debug'):
            debug = bpy.context.scene.osc_debug
            debug.last_received_address = address
            debug.last_received_value = str(value)
        
        # Handle special OSC addresses
        if address == "/renderimage" and value == 1.0:
            # Register the render operation to run in the main thread
            bpy.app.timers.register(start_render_image)
            return
        
        # In the osc_handler function, ensure the recording section is working
        # Handle record frames command
        if address == "/recordframes" and value == 1.0:
            global is_recording
            if not is_recording:
                print("OSC Controller: Received record command - starting recording")
                bpy.app.timers.register(start_recording)
            else:
                print("OSC Controller: Received record command - stopping recording")
                bpy.app.timers.register(stop_recording)
            return
        
        # Process each mapping
        for idx, mapping in enumerate(bpy.context.scene.osc_mappings):
            if not mapping.is_active or not mapping.target_object:
                continue
            
            # Check if the OSC address matches
            if mapping.osc_address == address:
                # Remap the incoming value from raw range to the remapped range
                mapped_value = remap_value(
                    value, 
                    mapping.raw_min_value, 
                    mapping.raw_max_value,
                    mapping.remap_min_value, 
                    mapping.remap_max_value
                )
                
                # Store the mapped value for driver use
                mapped_values_dict[f"{address}_mapped"] = mapped_value
                
                # Add to queue for execution in the main thread
                bpy.app.timers.register(
                    lambda obj=mapping.target_object, 
                        prop_type=mapping.property_type, 
                        custom_name=mapping.custom_property_name,
                        val=mapped_value: set_object_property(obj, prop_type, custom_name, val)
                )
    except Exception as e:
        print(f"OSC Controller: Error in OSC handler: {str(e)}")

# Functions for Blender drivers to access OSC data
def get_osc_value(address):
    return osc_values_dict.get(address, 0.0)

def get_mapped_osc_value(address):
    return mapped_values_dict.get(f"{address}_mapped", 0.0)

# Function for drivers to perform custom remapping
def remap_osc_value(address, out_min, out_max, in_min=None, in_max=None):
    # Get the raw value
    value = osc_values_dict.get(address, 0.0)
    
    # If input range not specified, use standard 0-1
    if in_min is None:
        in_min = 0.0
    if in_max is None:
        in_max = 1.0
        
    # Perform the remapping
    return remap_value(value, in_min, in_max, out_min, out_max)

# Register OSC driver functions globally
def register_driver_functions():
    bpy.app.driver_namespace["get_osc_value"] = get_osc_value
    bpy.app.driver_namespace["get_mapped_osc_value"] = get_mapped_osc_value
    bpy.app.driver_namespace["remap_osc_value"] = remap_osc_value

def initialize_smoothing_buffers(obj, prop_path, initial_value):
    """Initialize or reset a smoothing buffer for a property with an initial value"""
    buffer_key = f"{obj.name}_{prop_path}"
    buffer_size = bpy.context.scene.osc_settings.smoothing_buffer_size
    smoothing_buffers[buffer_key] = [initial_value] * buffer_size
    last_keyframed_values[buffer_key] = initial_value

def get_current_property_value(obj, prop_path):
    """Get the current value of a property using its path"""
    if '.' in prop_path:
        # Handle vector properties like location, rotation, scale
        prop_base, index = prop_path.split('.')
        index = int(index)
        return getattr(obj, prop_base)[index]
    elif '[' in prop_path:
        # Handle custom properties
        prop_name = prop_path.strip('[]"\'')
        return obj[prop_name]
    else:
        # Handle simple properties
        return getattr(obj, prop_path)

def set_property_value(obj, prop_path, value):
    """Set a property value using its path"""
    if '.' in prop_path:
        # Handle vector properties like location, rotation, scale
        prop_base, index = prop_path.split('.')
        index = int(index)
        vector = getattr(obj, prop_base)
        vector[index] = value
    elif '[' in prop_path:
        # Handle custom properties
        prop_name = prop_path.strip('[]"\'')
        obj[prop_name] = value
    else:
        # Handle simple properties
        setattr(obj, prop_path, value)

def get_smoothed_value(obj, prop_path, current_value):
    """Apply smoothing to a value based on settings"""
    settings = bpy.context.scene.osc_settings
    
    if not settings.enable_smoothing:
        return current_value
        
    buffer_key = f"{obj.name}_{prop_path}"
    
    # Initialize buffer if it doesn't exist
    if buffer_key not in smoothing_buffers:
        initialize_smoothing_buffers(obj, prop_path, current_value)
        return current_value
    
    # Get the last keyframed value
    last_value = last_keyframed_values.get(buffer_key, current_value)
    
    # Apply threshold filter if enabled
    if settings.smoothing_method in ('threshold', 'both'):
        # If the change is smaller than the threshold, use the last value
        if abs(current_value - last_value) < settings.smoothing_threshold:
            return last_value
    
    # Apply buffer smoothing if enabled
    if settings.smoothing_method in ('buffer', 'both'):
        # Update the buffer with the new value
        buffer = smoothing_buffers[buffer_key]
        buffer.pop(0)
        buffer.append(current_value)
        
        # Calculate the average of the buffer
        return sum(buffer) / len(buffer)
    
    # If only threshold filtering is used, return the current value
    return current_value

def should_keyframe_property(obj, prop_path, current_value):
    """Determine if a property should be keyframed based on smoothing settings"""
    settings = bpy.context.scene.osc_settings
    
    if not settings.enable_smoothing:
        return True
        
    buffer_key = f"{obj.name}_{prop_path}"
    
    # Initialize if it doesn't exist
    if buffer_key not in last_keyframed_values:
        last_keyframed_values[buffer_key] = current_value
        return True
    
    # Get the last keyframed value
    last_value = last_keyframed_values[buffer_key]
    
    # If threshold filtering is enabled, check if the change is significant
    if settings.smoothing_method in ('threshold', 'both'):
        if abs(current_value - last_value) < settings.smoothing_threshold:
            return False
    
    # Update the last keyframed value
    last_keyframed_values[buffer_key] = current_value
    return True

# Operator to install dependencies
class OSC_OT_InstallDependencies(Operator):
    bl_idname = "osc.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = "Try to install the python-osc library system-wide (fallback)"
    
    def execute(self, context):
        global dependency_error
        
        try:
            import subprocess
            import sys
            
            python_exe = sys.executable
            pip_command = [python_exe, "-m", "pip", "install", "python-osc"]
            
            process = subprocess.Popen(pip_command, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.report({'INFO'}, "Successfully installed python-osc library")
                dependency_error = ""
                check_pythonosc()  # Update the status after installation
                return {'FINISHED'}
            else:
                error_msg = stderr.decode('utf-8')
                self.report({'ERROR'}, f"Failed to install dependency: {error_msg}")
                dependency_error = f"Installation error: {error_msg}"
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error installing dependency: {str(e)}")
            dependency_error = f"Installation error: {str(e)}"
            return {'CANCELLED'}

# Operator to start OSC server
class OSC_OT_StartServer(Operator):
    bl_idname = "osc.start_server"
    bl_label = "Start OSC Server"
    bl_description = "Start listening for OSC messages"
    
    def execute(self, context):
        global osc_server_thread, osc_server_instance, is_server_running, dependency_error
        
        # Check if python-osc is available
        if not check_pythonosc():
            self.report({'ERROR'}, "Python-OSC library is not installed")
            dependency_error = "Python-OSC library not installed. Use the Install Dependencies button."
            return {'CANCELLED'}
        
        if is_server_running:
            self.report({'WARNING'}, "OSC Server is already running")
            return {'CANCELLED'}
        
        try:
            from pythonosc import dispatcher, osc_server
            
            # Create OSC dispatcher
            disp = dispatcher.Dispatcher()
            disp.map("/*", osc_handler)  # Map all OSC addresses
            
            # Start OSC server
            settings = context.scene.osc_settings
            ip = settings.ip_address
            port = settings.port
            
            server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            osc_server_instance = server
            osc_server_thread = server_thread
            is_server_running = True
            
            self.report({'INFO'}, f"OSC Server started at {ip}:{port}")
            return {'FINISHED'}
        except Exception as e:
            error_message = str(e)
            self.report({'ERROR'}, f"Failed to start OSC Server: {error_message}")
            dependency_error = f"Server error: {error_message}"
            return {'CANCELLED'}

# Operator to stop OSC server
class OSC_OT_StopServer(Operator):
    bl_idname = "osc.stop_server"
    bl_label = "Stop OSC Server"
    bl_description = "Stop the OSC server"
    
    def execute(self, context):
        global osc_server_instance, is_server_running
        
        if not is_server_running:
            self.report({'WARNING'}, "OSC Server is not running")
            return {'CANCELLED'}
        
        try:
            if osc_server_instance:
                osc_server_instance.shutdown()
                osc_server_instance = None
                is_server_running = False
                self.report({'INFO'}, "OSC Server stopped")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to stop OSC Server: {str(e)}")
            return {'CANCELLED'}

# Operator to add a new OSC mapping
class OSC_OT_AddMapping(Operator):
    bl_idname = "osc.add_mapping"
    bl_label = "Add New Mapping"
    bl_description = "Add a new OSC to property mapping"
    
    def execute(self, context):
        try:
            mapping = context.scene.osc_mappings.add()
            if context.active_object:
                mapping.target_object = context.active_object
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to add mapping: {str(e)}")
            return {'CANCELLED'}

# Operator to add a new Record Object
class OSC_OT_AddRecordObject(Operator):
    bl_idname = "osc.add_record_object"
    bl_label = "Add Object to Record"
    bl_description = "Add an object to record keyframes for"
    
    def execute(self, context):
        try:
            record_obj = context.scene.osc_record_objects.add()
            if context.active_object:
                record_obj.target_object = context.active_object
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to add record object: {str(e)}")
            return {'CANCELLED'}

# Operator to remove an OSC mapping
class OSC_OT_RemoveMapping(Operator):
    bl_idname = "osc.remove_mapping"
    bl_label = "Remove Mapping"
    bl_description = "Remove the selected OSC mapping"
    
    index: IntProperty()
    
    def execute(self, context):
        try:
            context.scene.osc_mappings.remove(self.index)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to remove mapping: {str(e)}")
            return {'CANCELLED'}

# Operator to remove a Record Object
class OSC_OT_RemoveRecordObject(Operator):
    bl_idname = "osc.remove_record_object"
    bl_label = "Remove Record Object"
    bl_description = "Remove the selected record object"
    
    index: IntProperty()
    
    def execute(self, context):
        try:
            context.scene.osc_record_objects.remove(self.index)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to remove record object: {str(e)}")
            return {'CANCELLED'}

# Operator to copy driver expression to clipboard
class OSC_OT_CopyDriverExpression(Operator):
    bl_idname = "osc.copy_driver_expression"
    bl_label = "Copy Driver Expression"
    bl_description = "Copy driver expression to clipboard"
    
    driver_type: StringProperty()
    address: StringProperty()
    raw_min: FloatProperty(default=0.0)
    raw_max: FloatProperty(default=1.0)
    remap_min: FloatProperty(default=0.0)
    remap_max: FloatProperty(default=1.0)
    
    def execute(self, context):
        try:
            if self.driver_type == "raw":
                expression = f'get_osc_value("{self.address}")'
            elif self.driver_type == "mapped":
                expression = f'get_mapped_osc_value("{self.address}")'
            elif self.driver_type == "custom":
                expression = f'remap_osc_value("{self.address}", {self.remap_min}, {self.remap_max}, {self.raw_min}, {self.raw_max})'
            else:
                raise ValueError("Invalid driver type")
            
            context.window_manager.clipboard = expression
            self.report({'INFO'}, f"Driver expression copied to clipboard: {expression}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to copy expression: {str(e)}")
            return {'CANCELLED'}

# Operator to open documentation URL
class OSC_OT_OpenDocumentation(Operator):
    bl_idname = "osc.open_documentation"
    bl_label = "Open Documentation"
    bl_description = "Open the OSC Controller documentation in a web browser"
    
    url: StringProperty(default="https://github.com/YourUsername/OSCController")
    
    def execute(self, context):
        try:
            import webbrowser
            webbrowser.open(self.url)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open URL: {str(e)}")
            return {'CANCELLED'}

# OSC Server settings
class OSCSettings(PropertyGroup):
    ip_address: StringProperty(
        name="IP Address",
        description="IP Address to bind OSC server to",
        default="0.0.0.0"
    )
    
    port: IntProperty(
        name="Port",
        description="Port to listen for OSC messages",
        default=9001,
        min=1024,
        max=65535
    )
    
    # Add frame rate options
    record_frame_rates = [
        ('12', "12 fps", "Record at 12 frames per second"),
        ('15', "15 fps", "Record at 15 frames per second"),
        ('24', "24 fps", "Record at 24 frames per second"),
        ('30', "30 fps", "Record at 30 frames per second"),
        ('48', "48 fps", "Record at 48 frames per second"),
        ('60', "60 fps", "Record at 60 frames per second"),
    ]
    
    keyframe_rate: EnumProperty(
        name="Keyframe Rate",
        description="Rate at which to record keyframes",
        items=record_frame_rates,
        default='30'
    )
    
    # Post-processing smoothing options
    post_smooth_keyframes: BoolProperty(
        name="Apply Gaussian Smoothing",
        description="Apply smoothing to keyframes after recording stops",
        default=False
    )
    
    post_smooth_factor: FloatProperty(
        name="Smoothing Factor",
        description="Strength of the post-recording smoothing (1.0 = standard)",
        default=1.0,
        min=0.1,
        max=5.0,
        precision=1
    )
    
    remove_jitter: BoolProperty(
        name="Remove Rogue Keyframes",
        description="Remove keyframes that appear to be jitter outliers",
        default=False
    )
    
    jitter_threshold: FloatProperty(
        name="Jitter Threshold",
        description="How much a keyframe must deviate to be considered jitter (smaller = more aggressive)",
        default=0.05,
        min=0.001,
        max=0.5,
        precision=3
    )
    
    # Auto-stop at end of frame range
    auto_stop_at_end: BoolProperty(
        name="Auto-Stop at End Frame",
        description="Automatically stop recording when reaching the end of the frame range",
        default=True
    )
    
    # Auto-stop at end of frame range
    auto_stop_at_end: BoolProperty(
        name="Auto-Stop at End Frame",
        description="Automatically stop recording when reaching the end of the frame range",
        default=True
    )


class OSC_OT_ToggleRecording(Operator):
    bl_idname = "osc.toggle_recording"
    bl_label = "Toggle Recording"
    bl_description = "Start or stop OSC recording"
    
    def execute(self, context):
        global is_recording
        
        if is_recording:
            # Stop recording
            print("OSC Controller: Toggle operator stopping recording")
            stop_recording()
            self.report({'INFO'}, "Stopped recording")
        else:
            # Start recording
            print("OSC Controller: Toggle operator starting recording")
            start_recording()
            self.report({'INFO'}, "Started recording")
            
        return {'FINISHED'}


class OSC_OT_SetSceneFPS(Operator):
    bl_idname = "osc.set_scene_fps"
    bl_label = "Set Scene FPS Now"
    bl_description = "Immediately set Blender's scene frame rate to match the selected keyframe rate"
    
    def execute(self, context):
        try:
            settings = context.scene.osc_settings
            fps = int(settings.keyframe_rate)
            
            # Set the frame rate
            context.scene.render.fps = fps
            
            # Also set the frame step to 1 to ensure smooth playback
            context.scene.frame_step = 1
            
            self.report({'INFO'}, f"Scene frame rate set to {fps} fps")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to set scene frame rate: {str(e)}")
            return {'CANCELLED'}
    
    # Add frame rate options
    record_frame_rates = [
        ('12', "12 fps", "Record at 12 frames per second"),
        ('15', "15 fps", "Record at 15 frames per second"),
        ('24', "24 fps", "Record at 24 frames per second"),
        ('30', "30 fps", "Record at 30 frames per second"),
        ('48', "48 fps", "Record at 48 frames per second"),
        ('60', "60 fps", "Record at 60 frames per second"),
    ]
    
    keyframe_rate: EnumProperty(
        name="Keyframe Rate",
        description="Rate at which to record keyframes",
        items=record_frame_rates,
        default='30'
    )
    
    set_scene_fps: BoolProperty(
        name="Set Scene FPS",
        description="Also change Blender's scene frame rate to match",
        default=False
    )

# OSC Debug Settings
class OSCDebugSettings(PropertyGroup):
    show_debug: BoolProperty(
        name="Show Debug Info",
        description="Show OSC debug information",
        default=False
    )
    
    last_received_address: StringProperty(
        name="Last Received Address",
        default="None"
    )
    
    last_received_value: StringProperty(
        name="Last Received Value",
        default="None"
    )
    
    show_all_values: BoolProperty(
        name="Show All OSC Values",
        description="Show all received OSC values",
        default=False
    )

# Main UI Panel
class OSC_PT_MainPanel(Panel):
    bl_label = "OSC Controller"
    bl_idname = "OSC_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.osc_settings
        
        # Server controls
        box = layout.box()
        box.label(text="Server Settings:")
        
        row = box.row()
        row.prop(settings, "ip_address")
        
        row = box.row()
        row.prop(settings, "port")
        
        # Server status and control
        row = box.row()
        if is_server_running:
            row.operator("osc.stop_server", icon='PAUSE')
            row.label(text="Server Running", icon='CHECKMARK')
        else:
            row.operator("osc.start_server", icon='PLAY')
            row.label(text="Server Stopped", icon='X')
        
        # Special commands info
        special_box = layout.box()
        special_box.label(text="Special OSC Commands:")
        
        row = special_box.row()
        row.label(text="/renderimage: Start a render (value=1)")
        
        row = special_box.row()
        recording_status = "Status: Recording" if is_recording else "Status: Not Recording"
        row.label(text=f"/recordframes: Toggle recording (value=1) - {recording_status}")
        
        # Add dependency status at the bottom of main panel
        box = layout.box()
        row = box.row()
        if pythonosc_available:
            row.label(text="python-osc: Available", icon='CHECKMARK')
            if "vendor" in pythonosc_path:
                row.label(text="(Bundled)", icon='PACKAGE')
        else:
            row.label(text="python-osc: Not Available", icon='X')
            row = box.row()
            row.operator("osc.install_dependencies", icon='PACKAGE')
            row.label(text="Trying to use bundled version failed")
            
        # Show dependency error if exists
        global dependency_error
        if dependency_error:
            row = box.row()
            row.label(text=dependency_error, icon='ERROR')

# Mappings UI Panel
class OSC_PT_MappingsPanel(Panel):
    bl_label = "OSC Mappings"
    bl_idname = "OSC_PT_MappingsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Add mapping button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("osc.add_mapping", icon='ADD')
        
        # List mappings
        if len(context.scene.osc_mappings) == 0:
            box = layout.box()
            box.label(text="No mappings defined", icon='INFO')
        else:
            for idx, mapping in enumerate(context.scene.osc_mappings):
                box = layout.box()
                row = box.row()
                row.prop(mapping, "is_active", text="")
                
                if mapping.is_active:
                    row.label(text=f"Mapping {idx+1}")
                else:
                    row.label(text=f"Mapping {idx+1} (Disabled)")
                
                row.operator("osc.remove_mapping", text="", icon='X').index = idx
                
                box.prop(mapping, "target_object")
                box.prop(mapping, "property_type")
                
                if mapping.property_type == 'custom_property':
                    box.prop(mapping, "custom_property_name")
                
                box.prop(mapping, "osc_address")
                
                # Raw input range
                row = box.row()
                row.label(text="Input Range:")
                
                row = box.row(align=True)
                row.prop(mapping, "raw_min_value", text="Min")
                row.prop(mapping, "raw_max_value", text="Max")
                
                # Remapped output range
                row = box.row()
                row.label(text="Output Range:")
                
                row = box.row(align=True)
                row.prop(mapping, "remap_min_value", text="Min")
                row.prop(mapping, "remap_max_value", text="Max")
                
                # Driver info toggle
                row = box.row()
                row.prop(mapping, "show_driver_info", icon='DRIVER')
                
                # Show driver info if toggled
                if mapping.show_driver_info and is_server_running:
                    driver_box = box.box()
                    driver_box.label(text="Driver Expressions:")
                    
                    # Raw OSC value
                    row = driver_box.row()
                    row.label(text="Raw Value:")
                    raw_op = row.operator("osc.copy_driver_expression", text="Copy", icon='COPYDOWN')
                    raw_op.driver_type = "raw"
                    raw_op.address = mapping.osc_address
                    
                    # Mapped OSC value
                    row = driver_box.row()
                    row.label(text="Mapped Value:")
                    mapped_op = row.operator("osc.copy_driver_expression", text="Copy", icon='COPYDOWN')
                    mapped_op.driver_type = "mapped"
                    mapped_op.address = mapping.osc_address
                    
                    # Custom remap function
                    row = driver_box.row()
                    row.label(text="Custom Remap Function:")
                    custom_op = row.operator("osc.copy_driver_expression", text="Copy", icon='COPYDOWN')
                    custom_op.driver_type = "custom"
                    custom_op.address = mapping.osc_address
                    custom_op.raw_min = mapping.raw_min_value
                    custom_op.raw_max = mapping.raw_max_value
                    custom_op.remap_min = mapping.remap_min_value
                    custom_op.remap_max = mapping.remap_max_value
                    
                    # Current values display
                    driver_box.label(text="Current values:")
                    
                    # Raw value
                    raw_value = osc_values_dict.get(mapping.osc_address, 0.0)
                    driver_box.label(text=f"Raw: {round(raw_value, 4)}")
                    
                    # Mapped value
                    mapped_key = f"{mapping.osc_address}_mapped"
                    mapped_value = mapped_values_dict.get(mapped_key, 0.0)
                    driver_box.label(text=f"Mapped: {round(mapped_value, 4)}")
                    
                    # Example usage
                    driver_box.label(text="Usage: Add a driver, set to Scripted Expression")
                    driver_box.label(text="Paste the copied expression")
                elif mapping.show_driver_info and not is_server_running:
                    box.label(text="Start the OSC server to use drivers", icon='INFO')

# Debug UI Panel
class OSC_PT_DebugPanel(Panel):
    bl_label = "OSC Debug"
    bl_idname = "OSC_PT_DebugPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        debug = context.scene.osc_debug
        
        layout.prop(debug, "show_debug")
        
        if debug.show_debug:
            box = layout.box()
            col = box.column()
            col.label(text="Last OSC Address:")
            col.label(text=debug.last_received_address)
            
            col.separator()
            col.label(text="Last OSC Value:")
            col.label(text=debug.last_received_value)
            
            # Show current recording state
            col.separator()
            if is_recording:
                col.label(text="Recording Status: Active", icon='REC')
            else:
                col.label(text="Recording Status: Inactive", icon='SNAP_FACE')
            
            # Show all values option
            col.separator()
            col.prop(debug, "show_all_values")
            
            if debug.show_all_values:
                col.separator()
                col.label(text="All OSC Values:")
                
                if not osc_values_dict:
                    col.label(text="No values received yet")
                else:
                    for addr, value in osc_values_dict.items():
                        value_box = col.box()
                        value_box.label(text=f"Address: {addr}")
                        value_box.label(text=f"Raw Value: {value}")
                        
                        # Show mapped value if available
                        mapped_key = f"{addr}_mapped"
                        if mapped_key in mapped_values_dict:
                            value_box.label(text=f"Mapped Value: {mapped_values_dict[mapped_key]}")
                        
                        # Add copy buttons for driver expressions
                        row = value_box.row()
                        raw_op = row.operator("osc.copy_driver_expression", text="Copy Raw", icon='COPYDOWN')
                        raw_op.driver_type = "raw"
                        raw_op.address = addr
                        
                        if mapped_key in mapped_values_dict:
                            mapped_op = row.operator("osc.copy_driver_expression", text="Copy Mapped", icon='COPYDOWN')
                            mapped_op.driver_type = "mapped"
                            mapped_op.address = addr

# Plugin Information Panel
class OSC_PT_InfoPanel(Panel):
    bl_label = "Plugin Information"
    bl_idname = "OSC_PT_InfoPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        
        # Plugin version
        version = ".".join(map(str, bl_info["version"]))
        box.label(text=f"Version: {version}")
        
        # Release date (hardcoded since it's not in bl_info)
        box.label(text="Release Date: April 6, 2025")
        
        # Python-OSC library status
        box.label(text="python-osc library:")
        if pythonosc_available:
            box.label(text="Status: Installed", icon='CHECKMARK')
            box.label(text=f"Path: {pythonosc_path}")
        else:
            box.label(text="Status: Not Installed", icon='X')
            box.operator("osc.install_dependencies", icon='PACKAGE')
        
        # Documentation link
        box.separator()
        box.label(text="Documentation:")
        box.operator("osc.open_documentation", icon='URL')
        
        # Special commands info
        box.separator()
        box.label(text="Special OSC Commands:")
        box.label(text="/renderimage (1) - Start a render")
        box.label(text="/recordframes (1) - Toggle frame recording")

# Recording Panel
class OSC_PT_RecordingPanel(Panel):
    bl_label = "OSC Recording"
    bl_idname = "OSC_PT_RecordingPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.osc_settings
        
        # Recording status and manual control
        box = layout.box()
        row = box.row()
        if is_recording:
            row.operator("osc.toggle_recording", text="Stop Recording", icon='SNAP_FACE')
            row.label(text="Recording Active", icon='REC')
        else:
            row.operator("osc.toggle_recording", text="Start Recording", icon='REC')
            row.label(text="Recording Inactive", icon='SNAP_FACE')
        
        # Frame rate options
        box = layout.box()
        box.label(text="Frame Rate Settings:")
        
        # Keyframe rate
        row = box.row(align=True)
        row.prop(settings, "keyframe_rate", text="Keyframe Rate")
        row.operator("osc.set_scene_fps", text="Set Scene FPS", icon='TIME')
        
        # Current scene FPS
        row = box.row()
        row.label(text=f"Scene Frame Rate: {context.scene.render.fps} fps")
        
        # Auto-stop option
        row = box.row()
        row.prop(settings, "auto_stop_at_end")
        row.label(text=f"End Frame: {context.scene.frame_end}")
        
        # Post-processing section
        box = layout.box()
        box.label(text="Post-Recording Processing:")
        
        # Anti-jitter option
        row = box.row()
        row.prop(settings, "remove_jitter")
        
        if settings.remove_jitter:
            row = box.row()
            row.prop(settings, "jitter_threshold")
            row.label(text="Smaller = More Aggressive")
        
        # Smoothing option  
        row = box.row()
        row.prop(settings, "post_smooth_keyframes")
        
        if settings.post_smooth_keyframes:
            row = box.row()
            row.prop(settings, "post_smooth_factor")
            row.label(text="Higher = Smoother")
        
        # Manual processing buttons
        row = box.row(align=True)
        row.operator("osc.remove_jitter", icon='KEYFRAME')
        row.operator("osc.smooth_keyframes", icon='SMOOTHCURVE')
        
        # Explanation text
        col = box.column()
        col.label(text="Anti-jitter removes outlier keyframes that")
        col.label(text="don't follow the overall motion trend.")
        col.label(text="Smoothing reduces minor variations while")
        col.label(text="preserving intentional movements.")
        
        # Recording instructions
        box = layout.box()
        box.label(text="Send /recordframes 1 to toggle recording via OSC")
        
        # Add record object button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("osc.add_record_object", icon='ADD')
        
        # List record objects
        if len(context.scene.osc_record_objects) == 0:
            box = layout.box()
            box.label(text="No objects set for recording", icon='INFO')
            box.label(text="Add objects to record keyframes for")
        else:
            for idx, rec_obj in enumerate(context.scene.osc_record_objects):
                box = layout.box()
                row = box.row()
                row.prop(rec_obj, "is_active", text="")
                
                if rec_obj.is_active:
                    row.label(text=f"Object {idx+1}")
                else:
                    row.label(text=f"Object {idx+1} (Disabled)")
                
                row.operator("osc.remove_record_object", text="", icon='X').index = idx
                
                box.prop(rec_obj, "target_object")
                
                # Properties to record
                row = box.row()
                row.label(text="Record:")
                row = box.row()
                row.prop(rec_obj, "record_location", toggle=True)
                row.prop(rec_obj, "record_rotation", toggle=True)
                row.prop(rec_obj, "record_scale", toggle=True)
                
                # Custom properties
                row = box.row()
                row.prop(rec_obj, "record_custom_properties", text="Custom Properties")
                
                if rec_obj.record_custom_properties:
                    box.prop(rec_obj, "custom_properties")
                    box.label(text="Enter comma-separated property names")

# Register
classes = (
    OSCMapping,
    OSCRecordObject,
    OSCSettings,
    OSCDebugSettings,
    OSC_OT_InstallDependencies,
    OSC_OT_StartServer,
    OSC_OT_StopServer,
    OSC_OT_AddMapping,
    OSC_OT_RemoveMapping,
    OSC_OT_AddRecordObject,
    OSC_OT_RemoveRecordObject,
    OSC_OT_CopyDriverExpression,
    OSC_OT_OpenDocumentation,
    OSC_OT_SetSceneFPS,
    OSC_OT_SmoothKeyframes,
    OSC_OT_RemoveJitter,
    OSC_OT_ToggleRecording,
    OSC_PT_MainPanel,
    OSC_PT_MappingsPanel,
    OSC_PT_RecordingPanel,
    OSC_PT_DebugPanel,
    OSC_PT_InfoPanel,
)

def register():
    # Check for pythonosc library
    check_pythonosc()
    
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.osc_mappings = bpy.props.CollectionProperty(type=OSCMapping)
    bpy.types.Scene.osc_record_objects = bpy.props.CollectionProperty(type=OSCRecordObject)
    bpy.types.Scene.osc_settings = bpy.props.PointerProperty(type=OSCSettings)
    bpy.types.Scene.osc_debug = bpy.props.PointerProperty(type=OSCDebugSettings)
    
    # Register driver functions
    register_driver_functions()
    
    # Make sure the render handlers are removed before adding them
    # to avoid duplicates if the addon is reloaded
    if render_complete_handler in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(render_complete_handler)
    bpy.app.handlers.render_complete.append(render_complete_handler)
    
    if render_cancel_handler in bpy.app.handlers.render_cancel:
        bpy.app.handlers.render_cancel.remove(render_cancel_handler)
    bpy.app.handlers.render_cancel.append(render_cancel_handler)


def unregister():
    # Stop OSC server if running
    global osc_server_instance, is_server_running
    if is_server_running and osc_server_instance:
        osc_server_instance.shutdown()
        osc_server_instance = None
        is_server_running = False
    
    # Remove driver functions from namespace
    if "get_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["get_osc_value"]
    if "get_mapped_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["get_mapped_osc_value"]
    if "remap_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["remap_osc_value"]
    
    # Remove render handlers
    if render_complete_handler in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(render_complete_handler)
    if render_cancel_handler in bpy.app.handlers.render_cancel:
        bpy.app.handlers.render_cancel.remove(render_cancel_handler)
    
    # Stop recording if active
    global is_recording, keyframe_timer
    if is_recording:
        stop_recording()
    
    # Remove the keyframe timer if it exists
    if keyframe_timer and keyframe_timer in bpy.app.timers.get_list():
        bpy.app.timers.unregister(keyframe_timer)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.osc_mappings
    del bpy.types.Scene.osc_record_objects
    del bpy.types.Scene.osc_settings
    del bpy.types.Scene.osc_debug


if __name__ == "__main__":
    register()