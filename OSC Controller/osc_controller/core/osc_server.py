import bpy
import threading
from bpy.app import timers
from . import utils
from . import recording
from . import driver_functions

# Global variables
osc_server_thread = None
osc_server_instance = None
is_server_running = False
osc_values_dict = {}  # Dictionary to store the latest OSC values by address
mapped_values_dict = {}  # Dictionary to store the mapped values by address

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
            timers.register(start_render_image)
            return
        
        # Handle record frames command
        if address == "/recordframes" and value == 1.0:
            from . import recording
            if not recording.is_recording:
                print("OSC Controller: Received record command - starting recording")
                timers.register(recording.start_recording)
            else:
                print("OSC Controller: Received record command - stopping recording")
                timers.register(recording.stop_recording)
            return
        
        # Process each mapping
        for idx, mapping in enumerate(bpy.context.scene.osc_mappings):
            if not mapping.is_active or not mapping.target_object:
                continue
            
            # Check if the OSC address matches
            if mapping.osc_address == address:
                # Remap the incoming value from raw range to the remapped range
                mapped_value = utils.remap_value(
                    value, 
                    mapping.raw_min_value, 
                    mapping.raw_max_value,
                    mapping.remap_min_value, 
                    mapping.remap_max_value
                )
                
                # Store the mapped value for driver use
                mapped_values_dict[f"{address}_mapped"] = mapped_value
                
                # Add to queue for execution in the main thread
                timers.register(
                    lambda obj=mapping.target_object, 
                        prop_type=mapping.property_type, 
                        custom_name=mapping.custom_property_name,
                        val=mapped_value: utils.set_object_property(obj, prop_type, custom_name, val)
                )
    except Exception as e:
        print(f"OSC Controller: Error in OSC handler: {str(e)}")

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

# Function to restart OSC server after render completes
def restart_osc_server_after_render():
    print("OSC Controller: Render completed, restarting OSC server")
    bpy.ops.osc.start_server()

# Handler for render completion
def render_complete_handler(scene):
    timers.register(restart_osc_server_after_render, first_interval=0.5)

# Handler for render cancellation
def render_cancel_handler(scene):
    timers.register(restart_osc_server_after_render, first_interval=0.5)

def register():
    """Register render handlers"""
    # Make sure the render handlers are removed before adding them
    # to avoid duplicates if the addon is reloaded
    if render_complete_handler in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(render_complete_handler)
    bpy.app.handlers.render_complete.append(render_complete_handler)
    
    if render_cancel_handler in bpy.app.handlers.render_cancel:
        bpy.app.handlers.render_cancel.remove(render_cancel_handler)
    bpy.app.handlers.render_cancel.append(render_cancel_handler)

def unregister():
    """Unregister render handlers and stop server if running"""
    # Stop OSC server if running
    global osc_server_instance, is_server_running
    if is_server_running and osc_server_instance:
        osc_server_instance.shutdown()
        osc_server_instance = None
        is_server_running = False
    
    # Remove render handlers
    if render_complete_handler in bpy.app.handlers.render_complete:
        bpy.app.handlers.render_complete.remove(render_complete_handler)
    if render_cancel_handler in bpy.app.handlers.render_cancel:
        bpy.app.handlers.render_cancel.remove(render_cancel_handler)