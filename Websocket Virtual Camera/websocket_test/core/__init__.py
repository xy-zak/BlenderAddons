from . import property_groups

def register_properties():
    """Register property groups (doesn't require websockets)"""
    property_groups.register()

def register_websocket():
    """Register websocket-dependent functionality"""
    from . import websocket_server
    websocket_server.register()

def unregister_properties():
    """Unregister property groups"""
    property_groups.unregister()

def unregister_websocket():
    """Unregister websocket-dependent functionality"""
    from . import websocket_server
    websocket_server.unregister()