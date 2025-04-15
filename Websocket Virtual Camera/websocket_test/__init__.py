bl_info = {
    "name": "WebSocket Test",
    "author": "Zak Silver-Lennard",
    "version": (1, 0, 0),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > WebSocket",
    "description": "Simple WebSocket server for testing ESP32 communication",
    "category": "Development",
}

import bpy
import sys
import os

# Get the addon directory
__current_dir = os.path.dirname(os.path.realpath(__file__))

# Register without checking for websockets
def register():
    # Import core modules
    from . import core
    
    # Register property groups
    core.register_properties()
    
    # Import and register other modules
    from . import operators
    from . import ui
    
    # Register the rest of the addon
    core.register_websocket()
    operators.register()
    ui.register()
    
    print("WebSocket Test: Addon fully registered")
    
def unregister():
    # Import these modules only if they were registered
    from . import operators
    from . import ui
    from . import core
    
    # Unregister in reverse order
    ui.unregister()
    operators.unregister()
    core.unregister_websocket()
    
    # Always unregister property groups
    core.unregister_properties()

if __name__ == "__main__":
    register()