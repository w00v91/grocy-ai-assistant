from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeProductRequest(BaseModel):
    name: str = Field(..., min_length=1)


class ExistingProductAddRequest(BaseModel):
    product_id: int
    product_name: str = Field(..., min_length=1)


class ProductData(BaseModel):
    name: str
    description: str
    location_id: int
    qu_id_purchase: int
    qu_id_stock: int
    calories: int


class AnalyzeProductResponse(BaseModel):
    product_data: ProductData
    success: bool = True


class DashboardSearchResponse(BaseModel):
    success: bool
    action: str
    message: str
    product_id: Optional[int] = None


class ShoppingListItemResponse(BaseModel):
    id: int
    amount: str
    product_name: str
    note: str = ""
    picture_url: str = ""


class ProductVariantResponse(BaseModel):
    id: int
    name: str
    picture_url: str = ""


class StockProductResponse(BaseModel):
    id: int
    name: str
    location_name: str = ""
    amount: str = ""


class RecipeSuggestionRequest(BaseModel):
    product_ids: list[int] = Field(default_factory=list)


class RecipeSuggestionItem(BaseModel):
    title: str
    source: str
    reason: str = ""


class RecipeSuggestionResponse(BaseModel):
    selected_products: list[str] = Field(default_factory=list)
    grocy_recipes: list[RecipeSuggestionItem] = Field(default_factory=list)
    ai_recipes: list[RecipeSuggestionItem] = Field(default_factory=list)
