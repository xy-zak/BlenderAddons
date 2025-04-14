import bpy
from bpy.types import Panel
from ..core import recording

# Recording Panel
class OSC_PT_RecordingPanel(Panel):
    bl_label = "OSC Recording"
    bl_idname = "OSC_PT_RecordingPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'OSC'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.osc_settings
        
        # Recording status and manual control
        box = layout.box()
        row = box.row()
        if recording.is_recording:
            row.operator("osc.toggle_recording", text="Stop Recording", icon='SNAP_FACE')
            row.label(text="Recording Active", icon='REC')
        else:
            row.operator("osc.toggle_recording", text="Start Recording", icon='REC')
            row.label(text="Recording Inactive", icon='SNAP_FACE')
        
        # Frame rate options
        box = layout.box()
        box.label(text="Frame Rate Settings:")
        
        # Keyframe rate
        row = box.row(align=True)
        row.prop(settings, "keyframe_rate", text="Keyframe Rate")
        row.operator("osc.set_scene_fps", text="Set Scene FPS", icon='TIME')
        
        # Current scene FPS
        row = box.row()
        row.label(text=f"Scene Frame Rate: {context.scene.render.fps} fps")
        
        # Auto-stop option
        row = box.row()
        row.prop(settings, "auto_stop_at_end")
        row.label(text=f"End Frame: {context.scene.frame_end}")
        
 # Post-processing section
        box = layout.box()
        box.label(text="Post-Recording Processing:")
        
        # Anti-jitter options
        row = box.row()
        row.prop(settings, "remove_jitter", text="Remove Rogue Keyframes")
        
        if settings.remove_jitter:
            sub_box = box.box()
            row = sub_box.row()
            row.prop(settings, "jitter_threshold", text="Threshold")
            row.label(text="Smaller = More Aggressive")
            
            row = sub_box.row()
            row.operator("osc.remove_jitter", text="Apply Effect", icon='KEYFRAME')
        
        # Smoothing options
        row = box.row()
        row.prop(settings, "post_smooth_keyframes", text="Apply Gaussian Smoothing")
        
        if settings.post_smooth_keyframes:
            sub_box = box.box()
            row = sub_box.row()
            row.prop(settings, "post_smooth_factor", text="Smoothing Factor")
            row.label(text="Higher = Smoother")
            
            row = sub_box.row()
            row.operator("osc.smooth_keyframes", text="Apply Effect", icon='SMOOTHCURVE')
        
        # Interpolation options
        row = box.row()
        row.prop(settings, "interpolate_keyframes", text="Interpolate Missing Frames")
        
        if settings.interpolate_keyframes:
            sub_box = box.box()
            row = sub_box.row()
            row.prop(settings, "interpolation_gap_threshold", text="Max Frame Gap")
            row.label(text="Maximum gap to fill")
            
            row = sub_box.row()
            row.operator("osc.interpolate_keyframes", text="Apply Effect", icon='IPO_BEZIER')
        
        # Explanation text
        col = box.column(align=True)
        col.separator()
        col.label(text="Post-Processing Options:")
        col.label(text="• Rogue Keyframes: Remove outliers that don't follow motion trend")
        col.label(text="• Gaussian Smoothing: Reduce jitter while keeping intentional motion")
        col.label(text="• Interpolate Frames: Remove redundant identical keyframes and")
        col.label(text="  fill gaps with smooth bezier curves")
        
        # Recording instructions
        box = layout.box()
        box.label(text="Send /recordframes 1 to toggle recording via OSC")
        
        # Add record object button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("osc.add_record_object", icon='ADD')
        
        # List record objects
        if len(context.scene.osc_record_objects) == 0:
            box = layout.box()
            box.label(text="No objects set for recording", icon='INFO')
            box.label(text="Add objects to record keyframes for")
        else:
            for idx, rec_obj in enumerate(context.scene.osc_record_objects):
                box = layout.box()
                row = box.row()
                row.prop(rec_obj, "is_active", text="")
                
                if rec_obj.is_active:
                    row.label(text=f"Object {idx+1}")
                else:
                    row.label(text=f"Object {idx+1} (Disabled)")
                
                row.operator("osc.remove_record_object", text="", icon='X').index = idx
                
                box.prop(rec_obj, "target_object")
                
                # Properties to record
                row = box.row()
                row.label(text="Record:")
                row = box.row()
                row.prop(rec_obj, "record_location", toggle=True)
                row.prop(rec_obj, "record_rotation", toggle=True)
                row.prop(rec_obj, "record_scale", toggle=True)
                
                # Custom properties
                row = box.row()
                row.prop(rec_obj, "record_custom_properties", text="Custom Properties")
                
                if rec_obj.record_custom_properties:
                    box.prop(rec_obj, "custom_properties")
                    box.label(text="Enter comma-separated property names")

# Register
classes = (
    OSC_PT_RecordingPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)