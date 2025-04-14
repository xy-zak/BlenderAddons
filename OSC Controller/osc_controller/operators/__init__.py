from . import server_ops
from . import mapping_ops
from . import recording_ops
from . import utility_ops

def register():
    server_ops.register()
    mapping_ops.register()
    recording_ops.register()
    utility_ops.register()

def unregister():
    utility_ops.unregister()
    recording_ops.unregister()
    mapping_ops.unregister()
    server_ops.unregister()