"""
app/core/plugins/spec.py — Plugin API v1.0 Specification & Compatibility Contract

Enforces strict plugin API versioning, metadata schema validation, and execution bounds
for third-party skills and OS extensions.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

CURRENT_PLUGIN_API_VERSION = "1.0.0"

class PluginMetadata(BaseModel):
    name: str = Field(..., description="Unique plugin identifier name")
    version: str = Field(..., description="Plugin semantic version string")
    api_version: str = Field(default=CURRENT_PLUGIN_API_VERSION, description="Target JARVIS Plugin API version")
    author: str = Field(default="Community")
    description: str = Field(default="")
    required_permissions: List[str] = Field(default_factory=list)
    timeout_sec: float = Field(default=10.0, description="Maximum allowed execution timeout")

class PluginV1Spec:
    """
    Validation contract for JARVIS v1.0 plugin instances.
    """
    @staticmethod
    def validate_plugin(plugin_obj: Any) -> PluginMetadata:
        if not hasattr(plugin_obj, "metadata"):
            raise ValueError(f"Plugin {getattr(plugin_obj, '__name__', plugin_obj)} is missing 'metadata' attribute.")

        meta_dict = getattr(plugin_obj, "metadata")
        if isinstance(meta_dict, dict):
            metadata = PluginMetadata(**meta_dict)
        elif isinstance(meta_dict, PluginMetadata):
            metadata = meta_dict
        else:
            raise ValueError("Plugin metadata must be a dictionary or PluginMetadata instance.")

        # API Version compatibility check
        major_target = metadata.api_version.split(".")[0]
        major_current = CURRENT_PLUGIN_API_VERSION.split(".")[0]
        if major_target != major_current:
            raise ValueError(
                f"Plugin '{metadata.name}' targets API version v{metadata.api_version}, "
                f"which is incompatible with system API version v{CURRENT_PLUGIN_API_VERSION}"
            )

        return metadata
