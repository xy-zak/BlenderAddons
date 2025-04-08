# OSC Controller for Blender

## Overview
The OSC Controller addon has been reorganized into a modular structure for better maintainability and organization. This addon allows you to control Blender object properties using OSC messages over a network, with keyframe recording capabilities.

## File Structure
The addon now follows this organizational structure:

```
osc_controller/
├── __init__.py                 # Main addon registration file
├── ui/                         # UI-related modules
│   ├── __init__.py             # Package initialization
│   ├── main_panel.py           # Main panel UI
│   ├── mappings_panel.py       # Mappings panel UI
│   ├── recording_panel.py      # Recording panel UI
│   ├── debug_panel.py          # Debug panel UI
│   └── info_panel.py           # Plugin info panel UI
├── operators/                  # Operator classes
│   ├── __init__.py             # Package initialization
│   ├── server_ops.py           # Server start/stop operators
│   ├── mapping_ops.py          # Mapping-related operators
│   ├── recording_ops.py        # Recording-related operators
│   └── utility_ops.py          # Utility operators (docs, drivers)
├── core/                       # Core functionality
│   ├── __init__.py             # Package initialization
│   ├── osc_server.py           # OSC server logic and variables
│   ├── property_groups.py      # Property definitions
│   ├── driver_functions.py     # Driver-related functionality
│   ├── recording.py            # Recording-related functions
│   └── utils.py                # Utility functions
└── vendor/                     # Third-party dependencies
    └── pythonosc/              # Bundled python-osc library
```

## Installation
1. Download the addon by cloning this repository or downloading it as a ZIP file
2. In Blender, go to Edit > Preferences > Add-ons
3. Click "Install..." and select the ZIP file
4. Enable the addon by checking the checkbox next to "Object: OSC Controller"

## Features
- Control object properties using OSC messages over LAN
- Map OSC values to any object property with custom range mapping
- Record keyframes in real-time with adjustable frame rates
- Post-processing tools for keyframe smoothing and jitter removal
- Built-in driver support for advanced animation control
- Bundled python-osc library (no external dependencies required)

## Special OSC Commands
- `/renderimage 1`: Start a Blender render
- `/recordframes 1`: Toggle keyframe recording on/off

## Development Notes
- Each UI panel is now in a separate file for easier maintenance
- Core functionality is separated from user interface code
- Common utilities are consolidated in the utils.py file
- Global variables are properly scoped in their respective modules
- The addon still works as a standalone .zip file for easy distribution

## Customization
To customize or extend this addon, follow these guidelines:
- Add new UI panels in the `ui/` directory
- Add new operators in the `operators/` directory
- Add new core functionality in the `core/` directory
- Update the respective `__init__.py` files to register new classes

To add a new feature:
1. Create a new file in the appropriate directory
2. Define your classes/functions in that file
3. Add a register/unregister function in your file
4. Import and call your register/unregister function from the appropriate `__init__.py`