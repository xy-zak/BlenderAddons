import bpy
from . import property_groups
from . import osc_server
from . import driver_functions
from . import recording
from . import utils

def register():
    # Register property groups first
    property_groups.register()
    
    # Register OSC server functionality
    osc_server.register()
    
    # Register driver functions
    driver_functions.register()
    
    # Register recording functionality
    recording.register()
    
def unregister():
    # Unregister in reverse order
    recording.unregister()
    driver_functions.unregister()
    osc_server.unregister()
    property_groups.unregister()