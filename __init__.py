import math

from bpy_extras.object_utils import world_to_camera_view

import bpy
from mathutils import Matrix, Vector


__author__ = "Gihan Nirmal Maddumage"
__license__ = "GPL-3.0-or-later"
__copyright__ = "2026 Gihan Nirmal Maddumage"
__description__ = "Unified pipeline suite for asset vector normalization, material purging, and camera frustum culling."


def selected_meshes(context):
    return [obj for obj in context.selected_objects if obj.type == 'MESH']


def notify(operator, context, message):
    operator.report({'WARNING'}, message)
    if not bpy.app.background:
        def draw(self, context):
            self.layout.label(text=message, icon='INFO')
        context.window_manager.popup_menu(draw, title="StageTools", icon='INFO')
    return {'CANCELLED'}


class NormalizeOperator:
    axis = 'Z'
    bl_options = {'REGISTER', 'UNDO'}
    angle = 0.0

    def execute(self, context):
        meshes = selected_meshes(context)
        if not meshes:
            return notify(self, context, "Select at least one mesh object")
        if context.mode != 'OBJECT':
            return notify(self, context, "Switch to Object Mode first")
        for obj in meshes:
            if not obj.is_editable or not obj.data.is_editable:
                return notify(self, context, "Selected meshes must be editable local assets")
            if not obj.data.vertices:
                return notify(self, context, "Selected meshes must contain vertices")
            if any(not child.is_editable for child in obj.children_recursive):
                return notify(self, context, "Children must be editable to preserve their placement")
            if obj.parent or obj.constraints or obj.animation_data or obj.modifiers or obj.rigid_body:
                return notify(self, context, "Use static meshes without parents, modifiers, constraints or animation")
            if abs(obj.matrix_world.to_3x3().determinant()) < 1e-12:
                return notify(self, context, "Selected meshes must have nonzero scale")
        rotation = Matrix.Rotation(self.angle, 4, self.axis)
        plans = []
        for obj in meshes:
            world = obj.matrix_world.copy()
            points = (world @ vertex.co for vertex in obj.data.vertices)
            minimum = next(points).copy()
            maximum = minimum.copy()
            for point in points:
                for axis in range(3):
                    minimum[axis] = min(minimum[axis], point[axis])
                    maximum[axis] = max(maximum[axis], point[axis])
            pivot = Vector(((minimum.x + maximum.x) * 0.5,
                            (minimum.y + maximum.y) * 0.5, minimum.z))
            transform = rotation @ Matrix.Translation(-pivot) @ world
            children = [(child, child.matrix_world.copy()) for child in obj.children_recursive]
            plans.append((obj, pivot, transform, children))
        prepared = []
        try:
            for obj, pivot, transform, children in plans:
                mesh = obj.data.copy()
                prepared.append((obj, mesh, pivot, children))
                mesh.transform(transform, shape_keys=True)
                if transform.to_3x3().determinant() < 0:
                    mesh.flip_normals()
                low = Vector(tuple(min(v.co[i] for v in mesh.vertices) for i in range(3)))
                high = Vector(tuple(max(v.co[i] for v in mesh.vertices) for i in range(3)))
                bottom = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
                mesh.transform(Matrix.Translation(-bottom), shape_keys=True)
                mesh.update()
        except (RuntimeError, ValueError, TypeError) as error:
            for _, mesh, _, _ in prepared:
                bpy.data.meshes.remove(mesh)
            return notify(self, context, str(error))
        for obj, mesh, pivot, children in prepared:
            obj.data = mesh
            obj.delta_location = (0.0, 0.0, 0.0)
            obj.delta_rotation_euler = (0.0, 0.0, 0.0)
            obj.delta_rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            obj.delta_scale = (1.0, 1.0, 1.0)
            obj.rotation_mode = 'XYZ'
            obj.matrix_world = Matrix.Translation(pivot)
            obj.data.update()
            context.view_layer.update()
            for child, world in children:
                child.matrix_world = world
                context.view_layer.update()
        self.report({'INFO'}, f"Normalized {len(meshes)} mesh object(s)")
        return {'FINISHED'}


class STAGETOOLS_OT_normalize_ue5(NormalizeOperator, bpy.types.Operator):
    bl_idname = "stage_tools.normalize_ue5"
    bl_label = "Normalize for UE5"
    bl_description = "Set bottom-center origin and bake a -90 degree Z turn"
    angle = math.radians(-90.0)


class STAGETOOLS_OT_normalize_maya(NormalizeOperator, bpy.types.Operator):
    bl_idname = "stage_tools.normalize_maya"
    bl_label = "Normalize for Maya"
    bl_description = "Set bottom-center origin and bake a 90 degree X turn toward Z-forward"
    axis = 'X'
    angle = math.radians(90.0)


class STAGETOOLS_OT_normalize_blender(NormalizeOperator, bpy.types.Operator):
    bl_idname = "stage_tools.normalize_blender"
    bl_label = "Freeze Blender Matrix"
    bl_description = "Set bottom-center origin and bake rotation and scale"



class STAGETOOLS_OT_prune_materials(bpy.types.Operator):
    bl_idname = 'stage_tools.prune_materials'
    bl_label = 'Purge Duplicate Materials'
    bl_description = 'Merge numeric material variants into existing local masters by name'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'OBJECT':
            return notify(self, context, 'Switch to Object Mode first')
        replacements = {}
        for material in bpy.data.materials:
            if material.library or material.override_library:
                continue
            name = material.name
            while True:
                base, separator, suffix = name.rpartition('.')
                if not separator or len(suffix) < 3 or not suffix.isdecimal():
                    break
                name = base
            master = bpy.data.materials.get(name)
            if master and master != material and not master.library and not master.override_library:
                replacements[material] = master
        changed = skipped = removed = 0
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for slot in obj.material_slots:
                master = replacements.get(slot.material)
                if master is None:
                    continue
                try:
                    if not obj.is_editable or (slot.link == 'DATA' and not obj.data.is_editable):
                        skipped += 1
                        continue
                    slot.material = master
                    changed += 1
                except (AttributeError, RuntimeError, TypeError):
                    skipped += 1
        for material in tuple(bpy.data.materials):
            if material.users == 0 and not material.library and not material.override_library:
                try:
                    bpy.data.materials.remove(material)
                    removed += 1
                except (RuntimeError, TypeError):
                    skipped += 1
        self.report({'WARNING'} if skipped else {'INFO'},
                    f'Remapped {changed} slots; removed {removed} materials; skipped {skipped}')
        return {'FINISHED'}


def camera_poll(self, obj):
    return obj.type == 'CAMERA'


class STAGETOOLS_PG_settings(bpy.types.PropertyGroup):
    camera: bpy.props.PointerProperty(
        name='Camera', type=bpy.types.Object, poll=camera_poll,
        description='Frustum camera; uses the scene camera when empty')


def set_hidden(obj, hidden, view_layer):
    try:
        if obj.hide_viewport != hidden:
            obj.hide_viewport = hidden
    except (AttributeError, RuntimeError, TypeError):
        obj.hide_set(hidden, view_layer=view_layer)
    else:
        obj.hide_set(False, view_layer=view_layer)


class Frustum:
    def __init__(self, scene, camera):
        self.scene = scene
        self.camera = camera
        self.inverse = camera.matrix_world.normalized().inverted()
        frame = camera.data.view_frame(scene=scene)
        self.near = camera.data.clip_start
        self.far = camera.data.clip_end
        self.perspective = camera.data.type == 'PERSP'
        self.left = min(v.x / -v.z if self.perspective else v.x for v in frame)
        self.right = max(v.x / -v.z if self.perspective else v.x for v in frame)
        self.bottom = min(v.y / -v.z if self.perspective else v.y for v in frame)
        self.top = max(v.y / -v.z if self.perspective else v.y for v in frame)

    def outside(self, obj, matrix):
        box = tuple(tuple(v) for v in obj.bound_box)
        if box == ((-1.0, -1.0, -1.0),) * 8:
            return False
        distances = []
        for corner in box:
            world = matrix @ Vector(corner)
            point = self.inverse @ world
            depth = -point.z
            if self.perspective:
                distances.append((point.x - self.left * depth,
                                  self.right * depth - point.x,
                                  point.y - self.bottom * depth,
                                  self.top * depth - point.y,
                                  depth - self.near, self.far - depth))
            else:
                projected = world_to_camera_view(self.scene, self.camera, world)
                distances.append((projected.x, 1 - projected.x,
                                  projected.y, 1 - projected.y,
                                  depth - self.near, self.far - depth))
        return any(all(d[plane] < -1e-6 for d in distances) for plane in range(6))


class STAGETOOLS_OT_isolate_frustum(bpy.types.Operator):
    bl_idname = 'stage_tools.isolate_frustum'
    bl_label = 'Isolate Frustum View'
    bl_description = 'Hide objects only when every evaluated mesh instance is outside the camera'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'OBJECT':
            return notify(self, context, 'Switch to Object Mode first')
        camera = context.scene.stage_tools.camera or context.scene.camera
        if camera is None or context.view_layer.objects.get(camera.name) != camera:
            return notify(self, context, 'Choose a camera in the active view layer')
        if camera.data.type not in {'PERSP', 'ORTHO'}:
            return notify(self, context, 'Use a perspective or orthographic camera')
        objects = [obj for obj in context.view_layer.objects
                   if obj.type == 'MESH' or obj.is_instancer]
        if not objects:
            return notify(self, context, 'No meshes or instancers in the active view layer')
        states = [(obj, obj.hide_viewport, obj.hide_get(view_layer=context.view_layer))
                  for obj in objects]
        skipped = hidden = 0
        try:
            for obj in objects:
                try:
                    set_hidden(obj, False, context.view_layer)
                except (AttributeError, RuntimeError, TypeError):
                    skipped += 1
            context.view_layer.update()
            depsgraph = context.evaluated_depsgraph_get()
            frustum = Frustum(context.scene, camera.evaluated_get(depsgraph))
            decisions = {}
            protected_sources = set()
            targets = {obj.as_pointer(): obj for obj in objects}
            for instance in depsgraph.object_instances:
                evaluated = instance.object
                if evaluated.type != 'MESH':
                    continue
                owner = instance.parent.original if instance.is_instance and instance.parent else evaluated.original
                key = owner.as_pointer()
                outside = frustum.outside(evaluated, instance.matrix_world)
                if instance.is_instance and not outside:
                    protected_sources.add(evaluated.original.as_pointer())
                if key not in targets:
                    continue
                decisions[key] = decisions.get(key, True) and outside
            for key, outside in decisions.items():
                outside = outside and key not in protected_sources
                try:
                    set_hidden(targets[key], outside, context.view_layer)
                    hidden += int(outside)
                except (AttributeError, RuntimeError, TypeError):
                    skipped += 1
            context.view_layer.update()
        except Exception as error:
            for obj, viewport, local in states:
                try:
                    if obj.hide_viewport != viewport:
                        obj.hide_viewport = viewport
                    obj.hide_set(local, view_layer=context.view_layer)
                except (AttributeError, RuntimeError, TypeError):
                    pass
            return notify(self, context, f'Isolation failed: {error}')
        self.report({'WARNING'} if skipped else {'INFO'},
                    f'Hidden {hidden} objects; {skipped} visibility changes unavailable')
        return {'FINISHED'}


class STAGETOOLS_OT_clear_frustum(bpy.types.Operator):
    bl_idname = 'stage_tools.clear_frustum'
    bl_label = 'Clear View Isolation'
    bl_description = 'Clear object viewport hiding; excluded collections remain excluded'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        skipped = 0
        for obj in bpy.data.objects:
            try:
                if obj.hide_viewport:
                    obj.hide_viewport = False
                if context.view_layer.objects.get(obj.name) == obj:
                    obj.hide_set(False, view_layer=context.view_layer)
            except (AttributeError, RuntimeError, TypeError):
                try:
                    obj.hide_set(False, view_layer=context.view_layer)
                except (RuntimeError, TypeError):
                    skipped += 1
        context.view_layer.update()
        self.report({'WARNING'} if skipped else {'INFO'},
                    f'View isolation cleared; {skipped} objects unavailable')
        return {'FINISHED'}


class VIEW3D_PT_stage_tools(bpy.types.Panel):
    bl_label = 'StageTools Engine'
    bl_idname = 'VIEW3D_PT_stage_tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'StageTools'

    def draw(self, context):
        box = self.layout.box()
        box.label(text='Asset Vector Normalizer', icon='MESH_DATA')
        if not selected_meshes(context) or context.mode != 'OBJECT':
            row = box.row()
            row.alert = True
            row.label(text='Select meshes in Object Mode', icon='ERROR')
        box.operator('stage_tools.normalize_ue5')
        box.operator('stage_tools.normalize_maya')
        box.operator('stage_tools.normalize_blender')
        box.label(text='Static meshes; location retained')
        box = self.layout.box()
        box.label(text='Material Network Pruner', icon='MATERIAL')
        box.operator('stage_tools.prune_materials')
        box.label(text='Numeric suffixes merge by name')
        box = self.layout.box()
        box.label(text='Camera Frustum Isolator', icon='CAMERA_DATA')
        box.prop(context.scene.stage_tools, 'camera')
        if not (context.scene.stage_tools.camera or context.scene.camera):
            row = box.row()
            row.alert = True
            row.label(text='Choose a camera', icon='ERROR')
        box.operator('stage_tools.isolate_frustum')
        box.operator('stage_tools.clear_frustum')
        box.label(text='Instances share owner visibility')
        box.label(text='Re-run after scene or camera changes')


CLASSES = (
    STAGETOOLS_PG_settings,
    STAGETOOLS_OT_normalize_ue5,
    STAGETOOLS_OT_normalize_maya,
    STAGETOOLS_OT_normalize_blender,
    STAGETOOLS_OT_prune_materials,
    STAGETOOLS_OT_isolate_frustum,
    STAGETOOLS_OT_clear_frustum,
    VIEW3D_PT_stage_tools,
)


def register():
    registered = []
    try:
        for cls in CLASSES:
            bpy.utils.register_class(cls)
            registered.append(cls)
        bpy.types.Scene.stage_tools = bpy.props.PointerProperty(type=STAGETOOLS_PG_settings)
    except Exception:
        for cls in reversed(registered):
            bpy.utils.unregister_class(cls)
        raise


def unregister():
    if hasattr(bpy.types.Scene, 'stage_tools'):
        del bpy.types.Scene.stage_tools
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
