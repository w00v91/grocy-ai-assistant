import base64
import json
import logging
import os
from typing import Any, Dict

import requests

from grocy_ai_assistant.config.settings import Settings

logger = logging.getLogger(__name__)

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
        if self.settings.debug_mode:
            logger.info("KI-Antwort analyze_product_name: %s", raw_answer)
        return json.loads(raw_answer)

    def suggest_similar_products(self, product_name: str) -> list[Dict[str, Any]]:
        prompt = f"""
        Der Nutzer hat nach '{product_name}' gesucht.
        Das ist vermutlich kein vollständiger Produktname.

        Schlage bis zu 8 realistische, ähnlich klingende Lebensmittel vor
        (z. B. bei 'apf' => 'Apfel', 'Apfelessig', ...).

        Gib NUR ein JSON-Array zurück.
        Jeder Eintrag muss exakt diese Struktur haben:
        {{
          "name": "Produktname"
        }}

        WICHTIG:
        - Nur sinnvolle Lebensmittel oder Getränke
        - Keine Fantasiebegriffe
        - Keine zusätzlichen Felder
        - Kein Text außerhalb von JSON
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
        if self.settings.debug_mode:
            logger.info("KI-Antwort suggest_similar_products: %s", raw_answer)
        parsed = json.loads(raw_answer)

        if not isinstance(parsed, list):
            return []

        suggestions: list[Dict[str, Any]] = []
        seen_names: set[str] = set()
        for item in parsed:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            normalized_name = name.casefold()
            if not name or normalized_name in seen_names:
                continue
            suggestions.append({"name": name})
            seen_names.add(normalized_name)
            if len(suggestions) >= 8:
                break

        return suggestions

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
          "reason": "Warum passt es zu den ausgewählten Zutaten",
          "preparation": "Kurze Zubereitungsbeschreibung in 2-4 Sätzen"
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
        if self.settings.debug_mode:
            logger.info("KI-Antwort generate_recipe_suggestions: %s", raw_answer)
        parsed = json.loads(raw_answer)
        if isinstance(parsed, dict):
            parsed = [parsed]

        if isinstance(parsed, list):
            normalized: list[Dict[str, Any]] = []

            def _normalize_text(value: Any) -> str:
                text = str(value or "").strip()
                return (
                    text.replace("\\r\\n", "\n")
                    .replace("\\n", "\n")
                    .replace("\\r", "\n")
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                )

            def _parse_embedded_recipe_text(text: str) -> Dict[str, str]:
                if "\n" not in text:
                    return {}

                lines = [line.strip() for line in text.split("\n")]
                compact = [line for line in lines if line]
                if not compact:
                    return {}

                lower_lines = [line.casefold() for line in lines]
                if "zubereitung" not in lower_lines and "fehlende produkte" not in lower_lines:
                    return {}

                title = compact[0]
                reason = ""
                preparation = ""

                if len(compact) > 1 and compact[1].casefold() not in {
                    "zubereitung",
                    "fehlende produkte",
                }:
                    reason = compact[1]

                if "zubereitung" in lower_lines:
                    start_index = lower_lines.index("zubereitung") + 1
                    end_index = len(lines)
                    if "fehlende produkte" in lower_lines[start_index:]:
                        end_index = lower_lines.index("fehlende produkte", start_index)

                    preparation_lines = [
                        line for line in lines[start_index:end_index] if line
                    ]
                    preparation = "\n".join(preparation_lines)

                return {
                    "title": title,
                    "reason": reason,
                    "preparation": preparation,
                }

            for item in parsed:
                if not isinstance(item, dict):
                    continue

                title = _normalize_text(item.get("title"))
                reason = _normalize_text(item.get("reason"))
                preparation = _normalize_text(
                    item.get("preparation")
                    or item.get("details")
                    or item.get("description")
                    or ""
                )

                parsed_title_blob = _parse_embedded_recipe_text(title)
                if parsed_title_blob:
                    title = parsed_title_blob.get("title") or title
                    reason = reason or parsed_title_blob.get("reason") or ""
                    preparation = preparation or parsed_title_blob.get("preparation") or ""

                normalized.append(
                    {
                        "title": title,
                        "reason": reason,
                        "preparation": preparation,
                    }
                )
            return normalized
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
