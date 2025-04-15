# ui/__init__.py

def register():
    from . import main_panel
    main_panel.register()

def unregister():
    from . import main_panel
    main_panel.unregister()