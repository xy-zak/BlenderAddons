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

# Add the vendor directory to the Python path
vendor_dir = os.path.join(__current_dir, "vendor")
if vendor_dir not in sys.path:
    sys.path.insert(0, vendor_dir)

# Import core modules that don't depend on websockets
from . import core

# Store the registration state
websockets_available = False

def register():
    global websockets_available
    
    # Register property groups (doesn't require websockets)
    core.register_properties()
    
    # Try to import websockets
    try:
        import websockets
        websockets_available = True
        
        # Only import and register modules that require websockets if available
        from . import operators
        from . import ui
        
        # Register the rest of the addon
        core.register_websocket()
        operators.register()
        ui.register()
        
        print("WebSocket Test: Addon fully registered with websockets support")
    except ImportError as e:
        print(f"WebSocket Test: websockets library not available - {e}")
        print("WebSocket Test: Only basic functionality will be available")
        
        # Register limited UI with error message
        from . import ui_error
        ui_error.register()
    
def unregister():
    global websockets_available
    
    if websockets_available:
        # Import these modules only if they were registered
        from . import operators
        from . import ui
        
        # Unregister in reverse order
        ui.unregister()
        operators.unregister()
        core.unregister_websocket()
    else:
        # Unregister error UI
        from . import ui_error
        ui_error.unregister()
    
    # Always unregister property groups
    core.unregister_properties()

if __name__ == "__main__":
    register()