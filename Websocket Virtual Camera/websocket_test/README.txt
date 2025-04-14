websocket_test/
├── __init__.py                 # Main addon registration
├── core/
│   ├── __init__.py             # Core module initialization
│   ├── property_groups.py      # Property definitions
│   └── websocket_server.py     # WebSocket server implementation
├── operators/
│   ├── __init__.py             # Operators module initialization
│   └── server_ops.py           # Server operators
├── ui/
│   ├── __init__.py             # UI module initialization
│   └── main_panel.py           # Main UI panel
├── ui_error.py                 # Error UI for missing dependencies
└── vendor/                     # Third-party libraries folder
    ├── __init__.py             # Empty file to make the folder a package
    └── [websockets library files]  # All files from the websockets package