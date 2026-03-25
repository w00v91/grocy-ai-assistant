import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import requests

from grocy_ai_assistant.config.settings import Settings
from grocy_ai_assistant.core.text_utils import html_to_plain_text

logger = logging.getLogger(__name__)

IMAGE_PROMPT_TEMPLATE = (
    'Erstelle ein produktbild für "{product_name}".\n'
    "Das Bild soll einen schwarzen leicht glossy hintergrund haben.\n"
    "Es soll professionell wirken und das Produkt gut in szene setzen."
)


class IngredientDetector:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _ollama_timeout_seconds(self) -> int:
        return max(5, min(300, int(self.settings.ollama_timeout_seconds)))

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
          "calories": (Geschaetzte Kalorien pro 100g/ml als Zahl),
          "carbohydrates": (Geschaetzte Kohlenhydrate pro 100g/ml in g als Zahl),
          "fat": (Geschaetztes Fett pro 100g/ml in g als Zahl),
          "protein": (Geschaetztes Protein pro 100g/ml in g als Zahl),
          "sugar": (Geschaetzter Zucker pro 100g/ml in g als Zahl),
          "default_best_before_days": (Geschaetzte Haltbarkeit in Tagen als Zahl, 0 wenn unklar)
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
            self.settings.ollama_url,
            json=ollama_payload,
            timeout=self._ollama_timeout_seconds(),
        )
        response.raise_for_status()
        raw_answer = response.json().get("response")
        if self.settings.debug_mode:
            logger.info("KI-Antwort analyze_product_name: %s", raw_answer)
        parsed = json.loads(raw_answer)

        def _as_number(value: Any) -> float:
            if value is None:
                return 0
            if isinstance(value, (int, float)):
                return value
            normalized = str(value).strip().replace(",", ".")
            try:
                number = float(normalized)
            except ValueError:
                return 0
            return int(number) if number.is_integer() else number

        if not isinstance(parsed, dict):
            return {
                "name": product_name,
                "description": "",
                "location_id": 1,
                "qu_id_purchase": 1,
                "qu_id_stock": 1,
                "calories": 0,
                "carbohydrates": 0,
                "fat": 0,
                "protein": 0,
                "sugar": 0,
                "default_best_before_days": 0,
            }

        carbs_candidate = (
            parsed.get("carbohydrates")
            if parsed.get("carbohydrates") not in (None, "")
            else parsed.get("carbs")
        )

        return {
            **parsed,
            "name": str(parsed.get("name") or product_name).strip() or product_name,
            "description": str(parsed.get("description") or "").strip(),
            "location_id": int(_as_number(parsed.get("location_id"))) or 1,
            "qu_id_purchase": int(_as_number(parsed.get("qu_id_purchase"))) or 1,
            "qu_id_stock": int(_as_number(parsed.get("qu_id_stock"))) or 1,
            "calories": _as_number(parsed.get("calories")),
            "carbohydrates": _as_number(carbs_candidate),
            "fat": _as_number(parsed.get("fat")),
            "protein": _as_number(parsed.get("protein")),
            "sugar": _as_number(parsed.get("sugar")),
            "default_best_before_days": max(
                0, int(_as_number(parsed.get("default_best_before_days")))
            ),
        }

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
            self.settings.ollama_url,
            json=ollama_payload,
            timeout=self._ollama_timeout_seconds(),
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
          "preparation": "Kurze Zubereitungsbeschreibung in 2-4 Sätzen",
          "ingredients": ["Zutat mit Menge, z.B. 2 Tomaten", "..."]
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
            self.settings.ollama_url,
            json=ollama_payload,
            timeout=self._ollama_timeout_seconds(),
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
                text = (
                    text.replace("\\r\\n", "\n")
                    .replace("\\n", "\n")
                    .replace("\\r", "\n")
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                )
                return html_to_plain_text(text)

            def _parse_embedded_recipe_text(text: str) -> Dict[str, Any]:
                if "\n" not in text:
                    return {}

                lines = [line.strip() for line in text.split("\n")]
                compact = [line for line in lines if line]
                if not compact:
                    return {}

                lower_lines = [line.casefold() for line in lines]
                if "zubereitung" not in lower_lines and "zutaten" not in lower_lines:
                    return {}

                title = compact[0]
                reason = ""
                preparation = ""
                ingredients: list[str] = []

                if len(compact) > 1 and compact[1].casefold() not in {
                    "zubereitung",
                    "fehlende produkte",
                }:
                    reason = compact[1]

                if "zutaten" in lower_lines:
                    start_index = lower_lines.index("zutaten") + 1
                    end_index = len(lines)
                    if "zubereitung" in lower_lines[start_index:]:
                        end_index = lower_lines.index("zubereitung", start_index)

                    ingredient_lines = [
                        line for line in lines[start_index:end_index] if line
                    ]
                    ingredients = [
                        line.lstrip("-•* ").strip()
                        for line in ingredient_lines
                        if line.lstrip("-•* ").strip()
                    ]

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
                    "ingredients": ingredients,
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
                raw_ingredients = item.get("ingredients")
                ingredients_list: list[str] = []
                if isinstance(raw_ingredients, list):
                    ingredients_list = [
                        _normalize_text(entry)
                        for entry in raw_ingredients
                        if _normalize_text(entry)
                    ]
                elif isinstance(raw_ingredients, str):
                    ingredients_list = [
                        entry.lstrip("-•* ").strip()
                        for entry in _normalize_text(raw_ingredients).split("\n")
                        if entry.lstrip("-•* ").strip()
                    ]

                parsed_title_blob = _parse_embedded_recipe_text(title)
                if parsed_title_blob:
                    title = parsed_title_blob.get("title") or title
                    reason = reason or parsed_title_blob.get("reason") or ""
                    preparation = (
                        preparation or parsed_title_blob.get("preparation") or ""
                    )
                    ingredients_list = (
                        ingredients_list or parsed_title_blob.get("ingredients") or []
                    )

                normalized.append(
                    {
                        "title": title,
                        "reason": reason,
                        "preparation": preparation,
                        "ingredients": ingredients_list,
                    }
                )
            return normalized
        return []

    def detect_product_from_image(
        self, image_base64: str, *, timeout_seconds: int = 90
    ) -> Dict[str, str]:
        min_confidence = max(
            1, min(100, int(self.settings.scanner_llava_min_confidence))
        )
        prompt = (
            "Erkenne das Hauptprodukt auf dem Bild. "
            f"Antworte NUR wenn du dir zu mindestens {min_confidence} prozent sicher bist "
            "als JSON mit den Feldern product_name, brand und hint. "
            "Antworte ansonsten mit NULL"
        )
        ollama_payload = {
            "model": self.settings.ollama_llava_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "images": [image_base64],
        }

        response = requests.post(
            self.settings.ollama_url,
            json=ollama_payload,
            timeout=max(10, min(120, int(timeout_seconds))),
        )
        response.raise_for_status()
        raw_answer = response.json().get("response")
        if self.settings.debug_mode:
            logger.info("KI-Antwort detect_product_from_image: %s", raw_answer)

        try:
            parsed = json.loads(raw_answer or "{}")
        except json.JSONDecodeError:
            return {"product_name": "", "brand": "", "hint": ""}

        if not isinstance(parsed, dict):
            return {"product_name": "", "brand": "", "hint": ""}

        return {
            "product_name": str(parsed.get("product_name") or "").strip(),
            "brand": str(parsed.get("brand") or "").strip(),
            "hint": str(parsed.get("hint") or "").strip(),
        }

    def generate_product_image(self, product_name: str) -> str:
        if not self.settings.image_generation_enabled:
            return ""

        if not self.settings.openai_api_key:
            logger.warning(
                "Bildgenerierung aktiv, aber openai_api_key fehlt in den Add-on Optionen"
            )
            return ""

        prompt = IMAGE_PROMPT_TEMPLATE.format(product_name=product_name)
        image_payload = self._request_openai_image_payload(prompt)
        image_base64 = str(image_payload.get("b64_json") or "").strip()
        image_url = str(image_payload.get("url") or "").strip()
        if not image_base64 and not image_url:
            raise ValueError("OpenAI Images API lieferte weder b64_json noch url")

        safe_name = (
            re.sub(r"[^a-zA-Z0-9_-]+", "_", product_name).strip("_") or "produkt"
        )
        file_name = f"{safe_name}_{uuid4().hex}.png"
        file_path = Path("/data/product_images") / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if image_base64:
            file_path.write_bytes(base64.b64decode(image_base64))
        else:
            image_response = requests.get(image_url, timeout=90)
            image_response.raise_for_status()
            file_path.write_bytes(image_response.content)
        return str(file_path)

    def _request_openai_image_payload(self, prompt: str) -> Dict[str, Any]:
        configured_model = str(self.settings.openai_image_model or "").strip()
        candidate_models = [configured_model, "dall-e-3", "dall-e-2"]
        models = [model for model in dict.fromkeys(candidate_models) if model]
        last_http_error: requests.HTTPError | None = None

        for index, model in enumerate(models):
            payload = {
                "model": model,
                "prompt": prompt,
                "size": "1024x1024",
            }

            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )

            try:
                response.raise_for_status()
            except requests.HTTPError as error:
                status_code = response.status_code
                if status_code == 403 and index < len(models) - 1:
                    logger.warning(
                        "OpenAI-Bildmodell %s nicht erlaubt (403), versuche Fallbackmodell %s",
                        model,
                        models[index + 1],
                    )
                    last_http_error = error
                    continue
                raise

            data = response.json().get("data") or []
            image_payload = data[0] if isinstance(data, list) and data else {}
            if isinstance(image_payload, dict):
                return image_payload

        if last_http_error is not None:
            raise last_http_error

        raise ValueError("OpenAI Images API lieferte keine Bilddaten")
