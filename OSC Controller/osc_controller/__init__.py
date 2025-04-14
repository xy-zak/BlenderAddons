bl_info = {
    "name": "OSC Controller",
    "author": "Zak Silver-Lennard",
    "version": (1, 1, 2),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > OSC",
    "description": "Control object properties using OSC messages over LAN with keyframe recording (python-osc included)",
    "category": "Object",
}

import bpy
import sys
import os

# Add the addon directory to sys.path
# This allows us to import the bundled pythonosc module
__current_dir = os.path.dirname(os.path.realpath(__file__))
if __current_dir not in sys.path:
    sys.path.append(__current_dir)

# Import submodules
from . import core
from . import operators
from . import ui

# Define registration functions
def register():
    # Register property groups first
    core.register()
    
    # Register operators
    operators.register()
    
    # Register UI panels
    ui.register()
    
def unregister():
    # Unregister in reverse order
    ui.unregister()
    operators.unregister()
    core.unregister()

if __name__ == "__main__":
    register()