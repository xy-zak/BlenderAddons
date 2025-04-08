from . import main_panel
from . import mappings_panel
from . import recording_panel
from . import debug_panel
from . import info_panel

def register():
    main_panel.register()
    mappings_panel.register()
    recording_panel.register()
    debug_panel.register()
    info_panel.register()

def unregister():
    info_panel.unregister()
    debug_panel.unregister()
    recording_panel.unregister()
    mappings_panel.unregister()
    main_panel.unregister()