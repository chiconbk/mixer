from collections import namedtuple
from datetime import datetime
import logging
from typing import List, Mapping, Set
from uuid import uuid4

from mixer.blender_data.proxy import BpyBlendProxy
from mixer.blender_data.filter import safe_context

import bpy
from mixer.blender_data.blenddata import BlendData

logger = logging.getLogger(__name__)

ObjectVisibility = namedtuple("ObjectVisibility", ["hide_viewport", "hide_select", "hide_render", "visible_get"])


def object_visibility(o: bpy.types.Object):
    return ObjectVisibility(o.hide_viewport, o.hide_select, o.hide_render, o.visible_get())


class CollectionInfo:
    def __init__(
        self, hide_viewport: bool, instance_offset, children: List[str], parent: List[str], objects: List[str] = None
    ):
        self.hide_viewport = hide_viewport
        self.instance_offset = instance_offset
        self.children = children
        self.parent = parent
        self.objects = objects or []


class SceneInfo:
    def __init__(self, scene: bpy.types.Scene):
        master_collection = scene.collection
        self.children = [x.name_full for x in master_collection.children]
        self.objects = [x.name_full for x in master_collection.objects]
        if not scene.mixer_uuid:
            scene.mixer_uuid = str(uuid4())
        self.mixer_uuid = scene.mixer_uuid


class ShareData:
    def __init__(self):
        self.runId = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.session_id = 0  # For logging and debug
        self.client = None

        # as received fom LIST_ALL_CLIENTS
        self.client_ids: List[Mapping[str, str]] = None

        self.isLocal = False
        self.localServerProcess = None
        self.selected_objects_names = []
        self.depsgraph = None

        self.current_statistics = None
        self.current_stats_timer = None
        self.auto_save_statistics = False
        self.statistics_directory = None

        self.clear_room_data()

    def clear_room_data(self):
        # equivalent to handlers set
        self.current_room: str = None

        self.objects_added: Set(str) = set()
        self.objects_removed: Set(str) = set()
        self.collections_added: Set(str) = set()
        self.collections_removed: Set(str) = set()
        self.scenes_added: List[str] = []
        self.scenes_removed: List[str] = []
        self.scenes_renamed: List[str, str] = []

        # key : collection name
        self.objects_added_to_collection: Mapping(str, str) = {}
        self.objects_removed_from_collection: Mapping(str, str) = {}
        self.collections_added_to_collection: Set(str, str) = set()
        self.collections_removed_from_collection: Set(str, str) = set()

        # key : scene name
        self.objects_added_to_scene: Mapping(str, str) = {}
        self.objects_removed_from_scene: Mapping(str, str) = {}
        self.collections_added_to_scene: Set(str, str) = set()
        self.collections_removed_from_scene: Set(str, str) = set()

        # All non master collections
        self.collections_info: Mapping[str, CollectionInfo] = {}

        # Master collections
        self.scenes_info: Mapping[str, SceneInfo] = {}

        self.objects_reparented = set()
        self.objects_parents = {}
        self.objects_renamed = {}
        self.objects_transformed = set()
        self.objects_transforms = {}
        self.objects_visibility_changed: Set[str] = set()
        self.objects_visibility: Mapping[str, ObjectVisibility] = {}

        self.old_objects: Mapping[str, bpy.types.Object] = {}

        # {object_path: [collection_name]}
        self.restore_to_collections: Mapping[str, List[str]] = {}

        self._blender_objects = {}
        self._blender_objects_dirty = True

        self._blender_materials = {}
        self._blender_materials_dirty = True

        self._blender_meshes = {}
        self._blender_meshes_dirty = True

        self._blender_grease_pencils = {}
        self._blender_grease_pencils_dirty = True

        self._blender_cameras = {}
        self._blender_cameras_dirty = True

        self._blender_lights = {}
        self._blender_lights_dirty = True

        self._blender_collections: Mapping[str, bpy.types.Collection] = {}
        self._blender_collections_dirty = True

        self.pending_parenting = set()

        self.proxy = None

    def leave_current_room(self):
        if self.client is not None:
            self.client.leave_room(share_data.current_room)
        self.clear_room_data()

        self._blender_scenes: Mapping[str, bpy.types.Scene] = {}
        self.blender_scenes_dirty = True

    def clear_before_state(self):
        # These objects contain the "before" state when entering the update_post handler
        # They must be empty before the first update so that the whole scene is sent
        self.old_objects = {}
        self.collections_info = {}
        self.scenes_info = {}

        if self.proxy:
            self.proxy.load(safe_context)

    def set_dirty(self):
        self.blender_objects_dirty = True
        self.blender_materials_dirty = True
        self.blender_meshes_dirty = True
        self.blender_grease_pencils_dirty = True
        self.blender_cameras_dirty = True
        self.blender_lights_dirty = True
        self.blender_collections_dirty = True
        self.blender_scenes_dirty = True
        BlendData.instance().set_dirty()

    def get_blender_property(self, property, property_dirty, elems):
        if not property_dirty:
            return property
        property = {x.name_full: x for x in elems}
        property_dirty = False
        return property

    @property
    def blender_objects(self):
        if not self.blender_objects_dirty:
            return self._blender_objects
        self._blender_objects = {x.name_full: x for x in bpy.data.objects}
        self.blender_objects_dirty = False
        return self._blender_objects

    @property
    def blender_objects_dirty(self):
        return self._blender_objects_dirty

    @blender_objects_dirty.setter
    def blender_objects_dirty(self, value):
        # TODO use only BlendData
        self._blender_objects_dirty = value
        if value:
            BlendData.instance().collection("objects").set_dirty()

    @property
    def blender_materials(self):
        if not self.blender_materials_dirty:
            return self._blender_materials
        self._blender_materials = {x.name_full: x for x in bpy.data.materials}
        self.blender_materials_dirty = False
        return self._blender_materials

    @property
    def blender_materials_dirty(self):
        return self._blender_materials_dirty

    @blender_materials_dirty.setter
    def blender_materials_dirty(self, value):
        self._blender_materials_dirty = value
        if value:
            BlendData.instance().collection("materials").set_dirty()

    @property
    def blender_meshes(self):
        if not self.blender_meshes_dirty:
            return self._blender_meshes
        self._blender_meshes = {x.name_full: x for x in bpy.data.meshes}
        self.blender_meshes_dirty = False
        return self._blender_meshes

    @property
    def blender_meshes_dirty(self):
        return self._blender_meshes_dirty

    @blender_meshes_dirty.setter
    def blender_meshes_dirty(self, value):
        self._blender_meshes_dirty = value
        if value:
            BlendData.instance().collection("meshes").set_dirty()

    @property
    def blender_grease_pencils(self):
        if not self.blender_grease_pencils_dirty:
            return self._blender_grease_pencils
        self._blender_grease_pencils = {x.name_full: x for x in bpy.data.grease_pencils}
        self.blender_grease_pencils_dirty = False
        return self._blender_grease_pencils

    @property
    def blender_grease_pencils_dirty(self):
        return self._blender_grease_pencils_dirty

    @blender_grease_pencils_dirty.setter
    def blender_grease_pencils_dirty(self, value):
        self._blender_grease_pencils_dirty = value
        if value:
            BlendData.instance().collection("grease_pencils").set_dirty()

    @property
    def blender_cameras(self):
        if not self.blender_cameras_dirty:
            return self._blender_cameras
        self._blender_cameras = {x.name_full: x for x in bpy.data.cameras}
        self.blender_cameras_dirty = False
        return self._blender_cameras

    @property
    def blender_cameras_dirty(self):
        return self._blender_cameras_dirty

    @blender_cameras_dirty.setter
    def blender_cameras_dirty(self, value):
        self._blender_cameras_dirty = value
        if value:
            BlendData.instance().collection("cameras").set_dirty()

    @property
    def blender_lights(self):
        if not self.blender_lights_dirty:
            return self._blender_lights
        self._blender_lights = {x.name_full: x for x in bpy.data.lights}
        self.blender_lights_dirty = False
        return self._blender_lights

    @property
    def blender_lights_dirty(self):
        return self._blender_lights_dirty

    @blender_lights_dirty.setter
    def blender_lights_dirty(self, value):
        self._blender_lights_dirty = value
        if value:
            BlendData.instance().collection("lights").set_dirty()

    @property
    def blender_collections(self):
        if not self.blender_collections_dirty:
            return self._blender_collections
        self._blender_collections = {x.name_full: x for x in bpy.data.collections}
        self.blender_collections_dirty = False
        return self._blender_collections

    @property
    def blender_collections_dirty(self):
        return self._blender_collections_dirty

    @blender_collections_dirty.setter
    def blender_collections_dirty(self, value):
        self._blender_collections_dirty = value
        if value:
            BlendData.instance().collection("collections").set_dirty()

    @property
    def blender_scenes(self):
        if not self.blender_scenes_dirty:
            return self._blender_scenes
        self._blender_scenes = {x.name_full: x for x in bpy.data.scenes}
        self.blender_scenes_dirty = False
        return self._blender_scenes

    @property
    def blender_scenes_dirty(self):
        return self._blender_scenes_dirty

    @blender_scenes_dirty.setter
    def blender_scenes_dirty(self, value):
        self._blender_scenes_dirty = value
        if value:
            BlendData.instance().collection("scenes").set_dirty()

    def clear_changed_frame_related_lists(self):
        self.objects_transformed.clear()

    def clear_lists(self):
        """
        Clear the lists that record change between previous and current state
        """
        self.scenes_added.clear()
        self.scenes_removed.clear()

        self.collections_added.clear()
        self.collections_removed.clear()

        self.collections_added_to_collection.clear()
        self.collections_removed_from_collection.clear()
        self.objects_added_to_collection.clear()
        self.objects_removed_from_collection.clear()

        self.objects_added_to_scene.clear()
        self.objects_removed_from_scene.clear()
        self.collections_added_to_scene.clear()
        self.collections_removed_from_scene.clear()

        self.objects_reparented.clear()
        self.objects_renamed.clear()
        self.objects_visibility_changed.clear()
        self.clear_changed_frame_related_lists()

    def update_scenes_info(self):
        self.scenes_info = {scene.name_full: SceneInfo(scene) for scene in self.blender_scenes.values()}

    def update_collections_info(self):
        self.collections_info = {}

        # All non master collections
        for collection in self.blender_collections.values():
            if not self.collections_info.get(collection.name_full):
                collection_info = CollectionInfo(
                    collection.hide_viewport,
                    collection.instance_offset,
                    [x.name_full for x in collection.children],
                    None,
                )
                self.collections_info[collection.name_full] = collection_info
            for child in collection.children:
                collection_info = CollectionInfo(
                    child.hide_viewport,
                    child.instance_offset,
                    [x.name_full for x in child.children],
                    collection.name_full,
                )
                self.collections_info[child.name_full] = collection_info

        # Store non master collections objects
        for collection in self.blender_collections.values():
            self.collections_info[collection.name_full].objects = [x.name_full for x in collection.objects]

    def update_objects_info(self):
        self.old_objects = self.blender_objects

        self.objects_transforms = {}
        for obj in self.blender_objects.values():
            self.objects_transforms[obj.name_full] = obj.matrix_local.copy()

    def update_current_data(self):
        self.update_scenes_info()
        self.update_collections_info()
        self.update_objects_info()
        self.objects_visibility = {x.name_full: object_visibility(x) for x in self.blender_objects.values()}
        self.objects_parents = {
            x.name_full: x.parent.name_full if x.parent is not None else "" for x in self.blender_objects.values()
        }

        if self.proxy:
            # TODO do not reload, but update the diff. Temporary quick and dirty
            self.proxy.load(safe_context)

    def set_experimental_sync(self, experimental_sync: bool):
        if experimental_sync:
            logger.warning("Experimental sync in ON")
            self.proxy = BpyBlendProxy()
        else:
            if self.proxy:
                logger.warning("Experimental sync in OFF")
                self.proxy = None

    def use_experimental_sync(self):
        return self.proxy is not None


share_data = ShareData()