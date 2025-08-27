from typing import Any
from onshape_api.api.api_base import Api
from onshape_api.paths.api_path import api_path
from onshape_api.paths.doc_path import InstancePath


def get_workspace_parts(api: Api, instance_path: InstancePath) -> dict:
    """Gets all parts in a workspace with their metadata including materials."""
    return api.get(api_path("parts", instance_path, InstancePath))


def get_part_metadata(api: Api, part_path: str) -> dict:
    """Gets metadata for a specific part."""
    return api.get(api_path("parts", part_path))
