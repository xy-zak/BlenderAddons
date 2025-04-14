import bpy
import sys
import os
import threading
from bpy.types import Operator
from ..core import utils
from ..core import osc_server

# Operator to install dependencies
class OSC_OT_InstallDependencies(Operator):
    bl_idname = "osc.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = "Try to install the python-osc library system-wide (fallback)"
    
    def execute(self, context):
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
                utils.dependency_error = ""
                utils.check_pythonosc()  # Update the status after installation
                return {'FINISHED'}
            else:
                error_msg = stderr.decode('utf-8')
                self.report({'ERROR'}, f"Failed to install dependency: {error_msg}")
                utils.dependency_error = f"Installation error: {error_msg}"
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error installing dependency: {str(e)}")
            utils.dependency_error = f"Installation error: {str(e)}"
            return {'CANCELLED'}

# Operator to start OSC server
class OSC_OT_StartServer(Operator):
    bl_idname = "osc.start_server"
    bl_label = "Start OSC Server"
    bl_description = "Start listening for OSC messages"
    
    def execute(self, context):
        # Check if python-osc is available
        if not utils.check_pythonosc():
            self.report({'ERROR'}, "Python-OSC library is not installed")
            utils.dependency_error = "Python-OSC library not installed. Use the Install Dependencies button."
            return {'CANCELLED'}
        
        if osc_server.is_server_running:
            self.report({'WARNING'}, "OSC Server is already running")
            return {'CANCELLED'}
        
        try:
            from pythonosc import dispatcher, osc_server as osc_server_lib
            
            # Create OSC dispatcher
            disp = dispatcher.Dispatcher()
            disp.map("/*", osc_server.osc_handler)  # Map all OSC addresses
            
            # Start OSC server
            settings = context.scene.osc_settings
            ip = settings.ip_address
            port = settings.port
            
            server = osc_server_lib.ThreadingOSCUDPServer((ip, port), disp)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            osc_server.osc_server_instance = server
            osc_server.osc_server_thread = server_thread
            osc_server.is_server_running = True
            
            self.report({'INFO'}, f"OSC Server started at {ip}:{port}")
            return {'FINISHED'}
        except Exception as e:
            error_message = str(e)
            self.report({'ERROR'}, f"Failed to start OSC Server: {error_message}")
            utils.dependency_error = f"Server error: {error_message}"
            return {'CANCELLED'}

# Operator to stop OSC server
class OSC_OT_StopServer(Operator):
    bl_idname = "osc.stop_server"
    bl_label = "Stop OSC Server"
    bl_description = "Stop the OSC server"
    
    def execute(self, context):
        if not osc_server.is_server_running:
            self.report({'WARNING'}, "OSC Server is not running")
            return {'CANCELLED'}
        
        try:
            if osc_server.osc_server_instance:
                osc_server.osc_server_instance.shutdown()
                osc_server.osc_server_instance = None
                osc_server.is_server_running = False
                self.report({'INFO'}, "OSC Server stopped")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to stop OSC Server: {str(e)}")
            return {'CANCELLED'}

# Register
classes = (
    OSC_OT_InstallDependencies,
    OSC_OT_StartServer,
    OSC_OT_StopServer
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)