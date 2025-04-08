import bpy
import os
import sys

# Dictionary for storing smoothing buffers
smoothing_buffers = {}  # For storing value history for buffer smoothing
last_keyframed_values = {}  # For storing the last keyframed values for threshold smoothing

# Function to check if python-osc is available
pythonosc_available = False
pythonosc_path = "Not installed"
dependency_error = ""

def check_pythonosc():
    """
    Check if python-osc is available, either as system install or bundled.
    Returns True if available, False otherwise.
    """
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
            # Path to the bundled library (one level up from core/ and then to vendor/)
            vendor_path = os.path.normpath(os.path.join(current_dir, "..", "vendor"))
            
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

# Function to remap a value from one range to another
def remap_value(value, old_min, old_max, new_min, new_max):
    """
    Remap a value from one range to another.
    
    Args:
        value: The value to remap
        old_min, old_max: The original range
        new_min, new_max: The target range
        
    Returns:
        The remapped value
    """
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
    """
    Set a property value on an object.
    
    Args:
        obj: The target object
        prop_type: Type of property (location_x, rotation_y, etc.)
        custom_prop_name: Name of custom property (if applicable)
        value: Value to set
    """
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

# Functions for smoothing
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

# Perform initial check for pythonosc
check_pythonosc()