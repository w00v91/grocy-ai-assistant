# Home Assistant Integration (`custom_components/grocy_ai_assistant`)

Custom integration for Home Assistant that connects to the Grocy AI add-on.

## Responsibilities

- Define entities/sensors and config flow
- Expose Home Assistant services
- Communicate with the add-on API via `addon_client.py`

## Key files

- `manifest.json` – integration metadata and version
- `config_flow.py` – setup UI flow
- `sensor.py` / `text.py` – exposed entities
- `panel.py` – panel URL and ingress handling
- `addon_client.py` – API communication with add-on backend

## Architectural rule

No direct Grocy API access in this folder; integrate only through the add-on API.
