from . import server_ops
from . import render_ops

def register():
    # Register server operators
    server_ops.register()
    render_ops.register()

def unregister():
    # Unregister in reverse order
    render_ops.unregister()
    server_ops.unregister()