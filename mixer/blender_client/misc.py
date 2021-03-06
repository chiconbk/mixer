"""
This module defines how we handle Objects identification from the server to clients.

This identification is done with a path, which is a string of the form A/B/C where C is child of B and B is child of A.
Each A, B and C and the name_full property of Objects. So the path encode both parenting and ids.

The issues with this strategy are:
- Parenting information is redundant accross Object: if we have A/B/C and A/B/D, the information of B being child of A
is expressed 2 times. This lead to messages that are bigger than necessary.
- '/' cannot be put in the name of an Object. The issue is that Blender allow this, and we have no qcheck.

We plan to change the strategy to store the name_full of the parent in the command instead.
"""

from mixer.share_data import share_data
import bpy


def get_or_create_path(path, data=None) -> bpy.types.Object:
    index = path.rfind("/")
    if index != -1:
        share_data.pending_parenting.add(path)  # Parenting is resolved after consumption of all messages

    # Create or get object
    elem = path[index + 1 :]
    ob = share_data.blender_objects.get(elem)
    if not ob:
        ob = bpy.data.objects.new(elem, data)
        share_data._blender_objects[ob.name_full] = ob
    return ob


def get_or_create_object_data(path, data):
    return get_or_create_path(path, data)


def get_object_path(obj):
    path = obj.name_full
    while obj.parent:
        obj = obj.parent
        if obj:
            path = obj.name_full + "/" + path
    return path
