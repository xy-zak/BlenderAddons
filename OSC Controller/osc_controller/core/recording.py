import bpy
import datetime
from bpy.app import timers

# Recording globals
is_recording = False  # Flag to track recording state
keyframe_timer = None  # Timer for keyframing

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
                timers.register(stop_recording)
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
    if keyframe_timer is not None and keyframe_timer in timers.get_list():
        try:
            timers.unregister(keyframe_timer)
            print("OSC Controller: Removed existing timer")
        except:
            pass
    
    # Create a new timer
    keyframe_timer = timers.register(keyframe_recording_callback, persistent=True)
    print(f"OSC Controller: Registered new keyframe timer: {keyframe_timer}")

# Function to stop recording frames
def stop_recording():
    global is_recording, keyframe_timer
    is_recording = False
    
    # Stop playing the timeline
    if bpy.context.screen.is_animation_playing:
        bpy.ops.screen.animation_play()
    
    # The keyframe timer will auto-stop when is_recording is False
    if keyframe_timer and keyframe_timer in timers.get_list():
        timers.unregister(keyframe_timer)
    keyframe_timer = None
    
    # Apply jitter removal if enabled
    if bpy.context.scene.osc_settings.remove_jitter:
        bpy.ops.osc.remove_jitter()
    
    # Apply interpolation if enabled
    if bpy.context.scene.osc_settings.interpolate_keyframes:
        bpy.ops.osc.interpolate_keyframes()
    
    # Apply post-smoothing if enabled
    if bpy.context.scene.osc_settings.post_smooth_keyframes:
        bpy.ops.osc.smooth_keyframes()
    
    print("OSC Controller: Stopped recording frames")

def register():
    """Register recording functionality"""
    pass  # No specific registration required for this module

def unregister():
    """Unregister recording functionality"""
    global is_recording, keyframe_timer
    
    # Stop recording if active
    if is_recording:
        stop_recording()
    
    # Remove the keyframe timer if it exists
    if keyframe_timer and keyframe_timer in timers.get_list():
        timers.unregister(keyframe_timer)