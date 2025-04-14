import bpy
from bpy.types import Operator
from bpy.props import IntProperty, EnumProperty, BoolProperty
from ..core import recording

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

# Operator to toggle recording state
class OSC_OT_ToggleRecording(Operator):
    bl_idname = "osc.toggle_recording"
    bl_label = "Toggle Recording"
    bl_description = "Start or stop OSC recording"
    
    def execute(self, context):
        if recording.is_recording:
            # Stop recording
            print("OSC Controller: Toggle operator stopping recording")
            recording.stop_recording()
            self.report({'INFO'}, "Stopped recording")
        else:
            # Start recording
            print("OSC Controller: Toggle operator starting recording")
            recording.start_recording()
            self.report({'INFO'}, "Started recording")
            
        return {'FINISHED'}

# Operator to set scene FPS to match recording FPS
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

#keyframe interpolation
class OSC_OT_InterpolateKeyframes(Operator):
    bl_idname = "osc.interpolate_keyframes"
    bl_label = "Interpolate Missing Frames"
    bl_description = "Fill in missing frames using bezier interpolation"
    
    @classmethod
    def poll(cls, context):
        # Only show this operator if we have record objects
        return len(context.scene.osc_record_objects) > 0
    
    def execute(self, context):
        settings = context.scene.osc_settings
        gap_threshold = settings.interpolation_gap_threshold
        total_added = 0
        total_removed = 0
        objects_affected = 0
        
        try:
            for rec_obj in context.scene.osc_record_objects:
                if not rec_obj.target_object or not rec_obj.is_active:
                    continue
                
                obj = rec_obj.target_object
                fcurves_processed = 0
                changes_made = 0
                
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
                        if fcurve and len(fcurve.keyframe_points) > 2:
                            curves_to_process.append(fcurve)
                
                # Add rotation curves
                if rec_obj.record_rotation:
                    for i in range(3):
                        fcurve = action.fcurves.find('rotation_euler', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 2:
                            curves_to_process.append(fcurve)
                
                # Add scale curves
                if rec_obj.record_scale:
                    for i in range(3):
                        fcurve = action.fcurves.find('scale', index=i)
                        if fcurve and len(fcurve.keyframe_points) > 2:
                            curves_to_process.append(fcurve)
                
                # Add custom properties
                if rec_obj.record_custom_properties and rec_obj.custom_properties:
                    custom_props = [prop.strip() for prop in rec_obj.custom_properties.split(',')]
                    for prop_name in custom_props:
                        data_path = f'["{prop_name}"]'
                        fcurve = action.fcurves.find(data_path)
                        if fcurve and len(fcurve.keyframe_points) > 2:
                            curves_to_process.append(fcurve)
                
                # Process each curve to interpolate missing frames
                for fcurve in curves_to_process:
                    changes = self.interpolate_missing_frames(fcurve, gap_threshold)
                    if changes > 0:
                        changes_made += changes
                        fcurves_processed += 1
                
                if changes_made > 0:
                    objects_affected += 1
                    total_added += changes_made
            
            if total_added > 0:
                self.report({'INFO'}, f"Processed {total_added} keyframes across {objects_affected} objects (removed identical frames and added interpolated frames)")
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No gaps or identical keyframes found that need processing")
                return {'FINISHED'}
        
        except Exception as e:
            self.report({'ERROR'}, f"Error while interpolating: {str(e)}")
            return {'CANCELLED'}
    
    def interpolate_missing_frames(self, fcurve, gap_threshold):
        """Add bezier-interpolated keyframes in gaps between existing keyframes and handle identical keyframes"""
        try:
            # Need at least 2 keyframes to interpolate between
            if len(fcurve.keyframe_points) < 2:
                return 0
            
            # Create a working copy of keyframe points and sort by frame
            keyframes = [(kf.co.x, kf.co.y, i) for i, kf in enumerate(fcurve.keyframe_points)]
            keyframes.sort(key=lambda k: k[0])  # Sort by x (frame)
            
            # First, identify sequences of identical keyframes
            identical_sequences = []
            current_sequence = []
            
            for i in range(len(keyframes) - 1):
                current_value = keyframes[i][1]
                next_value = keyframes[i+1][1]
                
                # Check if the values are identical (within a small epsilon for floating-point comparison)
                if abs(current_value - next_value) < 0.0001:
                    if not current_sequence:
                        current_sequence = [i]  # Start a new sequence
                    current_sequence.append(i+1)
                else:
                    # End of a sequence
                    if current_sequence:
                        if len(current_sequence) > 1:  # Only consider sequences of 2+ identical keyframes
                            identical_sequences.append(current_sequence)
                        current_sequence = []
            
            # Add the last sequence if it exists
            if current_sequence and len(current_sequence) > 1:
                identical_sequences.append(current_sequence)
            
            # Get indices to remove (keep first and last keyframe of each identical sequence)
            indices_to_remove = []
            for sequence in identical_sequences:
                # Keep first and last of sequence, remove the middle ones
                indices_to_remove.extend([keyframes[idx][2] for idx in sequence[1:-1]])
            
            # Remove identical keyframes (in reverse order to avoid index shifting)
            removed_count = 0
            for idx in sorted(indices_to_remove, reverse=True):
                fcurve.keyframe_points.remove(fcurve.keyframe_points[idx - removed_count])
                removed_count += 1
            
            # Refresh the keyframes list after removing identical ones
            if removed_count > 0:
                fcurve.update()
                keyframes = [(kf.co.x, kf.co.y, i) for i, kf in enumerate(fcurve.keyframe_points)]
                keyframes.sort(key=lambda k: k[0])
            
            # Now look for gaps and interpolate
            frames_added = 0
            new_keyframes = []
            
            for i in range(len(keyframes) - 1):
                current_frame = int(keyframes[i][0])
                next_frame = int(keyframes[i+1][0])
                
                # Check if there's a gap larger than threshold
                frame_gap = next_frame - current_frame
                if frame_gap > gap_threshold:
                    # Calculate how many frames to add
                    frames_to_add = frame_gap - 1  # -1 because we don't count start/end frames
                    
                    # Get the handle positions for bezier interpolation
                    # We'll use the actual handle positions if available for better curves
                    p0 = (keyframes[i][0], keyframes[i][1])      # Start point
                    p3 = (keyframes[i+1][0], keyframes[i+1][1])  # End point
                    
                    # Generate frames
                    for j in range(1, frames_to_add + 1):
                        # Calculate bezier interpolation at this point
                        t = j / (frames_to_add + 1)  # Normalized time parameter (0-1)
                        
                        # Simple cubic bezier interpolation
                        frame = current_frame + j
                        # Calculate a mid-point value using bezier interpolation
                        value = self.bezier_interpolate(p0[1], p3[1], t)
                        
                        new_keyframes.append((frame, value))
                        frames_added += 1
            
            # Add all the new keyframes
            for frame, value in new_keyframes:
                kf = fcurve.keyframe_points.insert(frame, value)
                # Set the interpolation mode to bezier
                kf.interpolation = 'BEZIER'
            
            # Update the curve
            if new_keyframes or removed_count > 0:
                fcurve.update()
            
            return frames_added + removed_count  # Return total count of changes (frames added + identical frames removed)
        
        except Exception as e:
            print(f"OSC Controller: Error interpolating frames: {str(e)}")
            return 0
        
        def bezier_interpolate(self, start_value, end_value, t):
            """Simple bezier interpolation between two values"""
            # For a simple curve, we can use a basic cubic interpolation
            # In a more complex implementation, we'd use the actual handle positions
            return start_value + (end_value - start_value) * (3 * t**2 - 2 * t**3)

# Register
classes = (
    OSC_OT_AddRecordObject,
    OSC_OT_RemoveRecordObject,
    OSC_OT_ToggleRecording,
    OSC_OT_SetSceneFPS,
    OSC_OT_SmoothKeyframes,
    OSC_OT_RemoveJitter,
    OSC_OT_InterpolateKeyframes
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)