import base64
import json
import os
from typing import Any, Dict

import requests

from grocy_ai_assistant.config.settings import Settings

IMAGE_PROMPT_TEMPLATE = """
Professionelles Produktfoto von '{product_name}' auf rein weißem Hintergrund.
Studiobeleuchtung, scharf, keine Wasserzeichen, fotorealistisch.
"""


class IngredientDetector:
    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _grocy_context(locations: list[Dict[str, Any]] | None = None) -> Dict[str, str]:
        location_labels = [
            f"{int(item.get('id'))}: {str(item.get('name') or '').strip()}"
            for item in (locations or [])
            if item.get("id") is not None
        ]
        return {
            "locations": (
                ", ".join(location_labels)
                if location_labels
                else "1: Kuehlschrank, 2: Vorratsschrank, 3: Tiefkuehler"
            ),
            "units": "1: Stueck, 2: Packung, 3: Gramm, 4: Kilogramm",
        }

    def analyze_product_name(
        self,
        product_name: str,
        locations: list[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        context = self._grocy_context(locations)
        prompt = f"""
        Analysiere das Produkt '{product_name}'.
        Gib NUR ein JSON-Objekt zurueck, das exakt diese Struktur hat:
        {{
          "name": "{product_name}",
          "description": "kurze Beschreibung",
          "location_id": (Waehle aus: {context['locations']}),
          "qu_id_purchase": (Waehle aus: {context['units']}),
          "qu_id_stock": (Waehle aus: {context['units']}),
          "calories": (Geschaetzte Kalorien pro 100g/ml als Zahl)
        }}
        Antworte NUR mit dem JSON, kein Text davor oder danach.
        """

        ollama_payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        response = requests.post(
            self.settings.ollama_url, json=ollama_payload, timeout=60
        )
        response.raise_for_status()
        raw_answer = response.json().get("response")
        return json.loads(raw_answer)

    def generate_recipe_suggestions(
        self,
        selected_products: list[str],
        existing_recipe_titles: list[str],
    ) -> list[Dict[str, Any]]:
        ingredients = ", ".join(selected_products)
        existing = (
            ", ".join(existing_recipe_titles) if existing_recipe_titles else "keine"
        )

        prompt = f"""
        Erstelle Rezeptvorschläge basierend auf diesen verfügbaren Zutaten: {ingredients}.
        Bereits in Grocy vorhandene Rezepte (nicht erneut vorschlagen): {existing}.

        Gib NUR ein JSON-Array mit maximal 5 Einträgen zurück.
        Jeder Eintrag hat exakt diese Struktur:
        {{
          "title": "Rezeptname",
          "reason": "Warum passt es zu den ausgewählten Zutaten"
        }}

        Antworte NUR mit dem JSON-Array, kein Text davor oder danach.
        """

        ollama_payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        response = requests.post(
            self.settings.ollama_url, json=ollama_payload, timeout=60
        )
        response.raise_for_status()
        raw_answer = response.json().get("response")
        parsed = json.loads(raw_answer)
        if isinstance(parsed, list):
            return parsed
        return []

    def generate_product_image(self, product_name: str):
        prompt = IMAGE_PROMPT_TEMPLATE.format(product_name=product_name)
        payload = {
            "prompt": prompt,
            "steps": 20,
            "width": 512,
            "height": 512,
            "cfg_scale": 7,
        }

        response = requests.post(
            self.settings.stable_diffusion_url, json=payload, timeout=60
        )
        response.raise_for_status()
        image_base64 = response.json()["images"][0]

        file_path = f"/data/product_images/{product_name.replace(' ', '_')}.png"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as file:
            file.write(base64.b64decode(image_base64))
        return file_path
