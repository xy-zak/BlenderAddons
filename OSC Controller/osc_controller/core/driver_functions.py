import bpy
from . import osc_server
from . import utils

# Functions for Blender drivers to access OSC data
def get_osc_value(address):
    """
    Get the raw OSC value for a given address.
    
    Args:
        address: The OSC address to get the value for
        
    Returns:
        The raw OSC value, or 0.0 if not found
    """
    return osc_server.osc_values_dict.get(address, 0.0)

def get_mapped_osc_value(address):
    """
    Get the mapped OSC value for a given address.
    
    Args:
        address: The OSC address to get the mapped value for
        
    Returns:
        The mapped OSC value, or 0.0 if not found
    """
    return osc_server.mapped_values_dict.get(f"{address}_mapped", 0.0)

# Function for drivers to perform custom remapping
def remap_osc_value(address, out_min, out_max, in_min=None, in_max=None):
    """
    Remap an OSC value from one range to another.
    
    Args:
        address: The OSC address to get the value for
        out_min, out_max: The output range
        in_min, in_max: The input range (optional, defaults to 0-1)
        
    Returns:
        The remapped OSC value
    """
    # Get the raw value
    value = osc_server.osc_values_dict.get(address, 0.0)
    
    # If input range not specified, use standard 0-1
    if in_min is None:
        in_min = 0.0
    if in_max is None:
        in_max = 1.0
        
    # Perform the remapping
    return utils.remap_value(value, in_min, in_max, out_min, out_max)

# Register OSC driver functions globally
def register():
    """Register driver functions in Blender's driver namespace"""
    bpy.app.driver_namespace["get_osc_value"] = get_osc_value
    bpy.app.driver_namespace["get_mapped_osc_value"] = get_mapped_osc_value
    bpy.app.driver_namespace["remap_osc_value"] = remap_osc_value

def unregister():
    """Unregister driver functions from Blender's driver namespace"""
    if "get_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["get_osc_value"]
    if "get_mapped_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["get_mapped_osc_value"]
    if "remap_osc_value" in bpy.app.driver_namespace:
        del bpy.app.driver_namespace["remap_osc_value"]