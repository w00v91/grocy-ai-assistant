from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeProductRequest(BaseModel):
    name: str = Field(..., min_length=1)
    amount: float = Field(default=1, gt=0)
    best_before_date: str = ""


class ExistingProductAddRequest(BaseModel):
    product_id: int
    product_name: str = Field(..., min_length=1)
    amount: float = Field(default=1, gt=0)
    best_before_date: str = ""


class ShoppingListBestBeforeDateUpdateRequest(BaseModel):
    best_before_date: str = Field(..., min_length=1)


class ShoppingListNoteUpdateRequest(BaseModel):
    note: str = ""


class ProductData(BaseModel):
    name: str
    description: str
    location_id: int
    qu_id_purchase: int
    qu_id_stock: int
    calories: int
    carbohydrates: float | int = 0
    fat: float | int = 0
    protein: float | int = 0
    sugar: float | int = 0


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
    stock_id: int | None = None
    name: str
    picture_url: str = ""
    location_id: int | None = None
    location_name: str = ""
    amount: str = ""
    best_before_date: str = ""


class StockProductConsumeRequest(BaseModel):
    amount: float = Field(default=1, gt=0)


class StockProductUpdateRequest(BaseModel):
    amount: float = Field(..., ge=0)
    best_before_date: str = ""


class LocationResponse(BaseModel):
    id: int
    name: str


class RecipeSuggestionRequest(BaseModel):
    product_ids: list[int] = Field(default_factory=list)
    location_ids: list[int] = Field(default_factory=list)
    soon_expiring_only: bool = False
    expiring_within_days: int = Field(default=3, ge=1, le=30)


class RecipeSuggestionItem(BaseModel):
    recipe_id: int | None = None
    title: str
    source: str
    reason: str = ""
    preparation: str = ""
    ingredients: list[str] = Field(default_factory=list)
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


class ScannerLlavaRequest(BaseModel):
    image_base64: str = Field(..., min_length=1)


class ScannerLlavaResponse(BaseModel):
    success: bool
    product_name: str = ""
    brand: str = ""
    hint: str = ""
    source: str = "ollama_llava"
