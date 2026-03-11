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
    variants: list["ProductVariantResponse"] = Field(default_factory=list)


class ShoppingListItemResponse(BaseModel):
    id: int
    amount: str
    product_id: int | None = None
    product_name: str
    note: str = ""
    picture_url: str = ""
    location_name: str = ""
    in_stock: str = ""
    best_before_date: str = ""
    default_amount: str = ""
    calories: str = ""
    carbs: str = ""
    fat: str = ""
    protein: str = ""


class ProductVariantResponse(BaseModel):
    id: Optional[int] = None
    name: str
    picture_url: str = ""
    source: str = "grocy"


class StockProductResponse(BaseModel):
    id: int
    name: str
    location_id: int | None = None
    location_name: str = ""
    amount: str = ""


class LocationResponse(BaseModel):
    id: int
    name: str


class RecipeSuggestionRequest(BaseModel):
    product_ids: list[int] = Field(default_factory=list)
    location_ids: list[int] = Field(default_factory=list)


class RecipeSuggestionItem(BaseModel):
    recipe_id: int | None = None
    title: str
    source: str
    reason: str = ""
    preparation: str = ""
    picture_url: str = ""
    missing_products: list[ProductVariantResponse] = Field(default_factory=list)


class RecipeSuggestionResponse(BaseModel):
    selected_products: list[str] = Field(default_factory=list)
    grocy_recipes: list[RecipeSuggestionItem] = Field(default_factory=list)
    ai_recipes: list[RecipeSuggestionItem] = Field(default_factory=list)


class BarcodeProductResponse(BaseModel):
    barcode: str
    found: bool
    product_name: str = ""
    brand: str = ""
    quantity: str = ""
    ingredients_text: str = ""
    nutrition_grade: str = ""
    source: str = "OpenFoodFacts"
