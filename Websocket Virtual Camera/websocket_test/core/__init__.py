# core/__init__.py
def register_properties():
    """Register property groups (doesn't require websockets)"""
    from . import property_groups
    property_groups.register()

def register_websocket():
    """Register websocket-dependent functionality"""
    from . import simple_websocket
    simple_websocket.register()

def unregister_properties():
    """Unregister property groups"""
    from . import property_groups
    property_groups.unregister()

def unregister_websocket():
    """Unregister websocket-dependent functionality"""
    from . import simple_websocket
    simple_websocket.unregister()