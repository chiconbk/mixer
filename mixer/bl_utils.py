"""
This modules defines utilities related to Blender.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import bpy

if TYPE_CHECKING:
    from mixer.bl_properties import MixerProperties
    from mixer.bl_preferences import MixerPreferences


def get_mixer_props() -> MixerProperties:
    return bpy.context.window_manager.mixer


def get_mixer_prefs() -> MixerPreferences:
    return bpy.context.preferences.addons[__package__].preferences
