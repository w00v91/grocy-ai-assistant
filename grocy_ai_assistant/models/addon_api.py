from __future__ import annotations

from pydantic import BaseModel, Field


class AddonHealthResponse(BaseModel):
    success: bool = True
    status: str = "ok"
    service: str = "grocy_ai_assistant"
    addon_version: str
    required_integration_version: str


class AddonCapabilitiesResponse(BaseModel):
    success: bool = True
    api_version: str = "v1"
    service: str = "grocy_ai_assistant"
    features: dict[str, bool] = Field(default_factory=dict)
    endpoints: list[str] = Field(default_factory=list)
    defaults: dict[str, str | int | bool] = Field(default_factory=dict)


class AddonCatalogRebuildResponse(BaseModel):
    success: bool = True
    refreshed_locations: int = 0
    refreshed_product_images: int = 0
    prefetched_recipe_suggestions: int = 0

