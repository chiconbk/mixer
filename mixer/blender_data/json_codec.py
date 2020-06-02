import json
from typing import Any, Mapping

from mixer.blender_data.proxy import (
    BpyIDProxy,
    BpyIDRefProxy,
    BpyPropertyGroupProxy,
    BpyPropDataCollectionProxy,
    BpyPropStructCollectionProxy,
    BpyStructProxy,
    StructLikeProxy,
)

# https://stackoverflow.com/questions/38307068/make-a-dict-json-from-string-with-duplicate-keys-python/38307621#38307621
# https://stackoverflow.com/questions/31085153/easiest-way-to-serialize-object-in-a-nested-dictionary

struct_like_classes = [BpyIDProxy, BpyIDRefProxy, BpyStructProxy, BpyPropertyGroupProxy]
collection_classes = [
    BpyPropStructCollectionProxy,
    BpyPropDataCollectionProxy,
]
_classes = {c.__name__: c for c in struct_like_classes}
_classes.update({c.__name__: c for c in collection_classes})


def default_optional(obj, option_name: str) -> Mapping[str, Any]:
    option = getattr(obj, option_name, None)
    if option is not None:
        return {option_name: option}
    return {}


def default(obj):
    # called top down
    class_ = obj.__class__
    is_known = issubclass(class_, StructLikeProxy) or issubclass(class_, BpyIDRefProxy) or class_ in collection_classes
    if is_known:
        # Add the proxy class so that the decoder and instanciate the right type
        d = {"__bpy_proxy_class__": class_.__name__}
        d.update({"_data": obj._data})

        # the blendata_path for BpyIDProxy for instance ("cameras", "Camera"), or
        # ("cameras", "Camera", "dof", "focus_object")
        d.update(default_optional(obj, "_blenddata_path"))
        d.update(default_optional(obj, "_ctor_args"))
        return d
    return None


def decode_optional(obj, x, option_name):
    option = x.get(option_name)
    if option is not None:
        setattr(obj, option_name, option)


def decode_hook(x):
    class_name = x.get("__bpy_proxy_class__")
    class_ = _classes.get(class_name)
    if class_ is None:
        return x

    del x["__bpy_proxy_class__"]
    obj = class_()
    obj._data.update(x["_data"])

    decode_optional(obj, x, "_blenddata_path")
    decode_optional(obj, x, "_ctor_args")
    return obj


class Codec:
    def encode(self, obj):
        return json.dumps(obj, default=default)

    def decode(self, message):
        return json.loads(message, object_hook=decode_hook)