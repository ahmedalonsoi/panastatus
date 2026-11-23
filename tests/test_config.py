"""El services.yaml real debe ser válido (si alguien lo rompe, CI falla)."""

from pathlib import Path

import pytest

from panastatus.config import MonitorConfig, load_monitor_config

ROOT = Path(__file__).resolve().parents[1]


def test_services_yaml_es_valido():
    config = load_monitor_config(ROOT / "config" / "services.yaml")
    assert len(config.enabled_services) > 0


def test_categoria_inexistente_se_rechaza():
    with pytest.raises(ValueError, match="categoría"):
        MonitorConfig.model_validate(
            {
                "categories": {"bancos": "Bancos"},
                "services": [
                    {"id": "x1", "name": "X", "category": "nope", "url": "https://x.example"}
                ],
            }
        )


def test_id_duplicado_se_rechaza():
    svc = {"id": "x1", "name": "X", "category": "bancos", "url": "https://x.example"}
    with pytest.raises(ValueError, match="duplicado"):
        MonitorConfig.model_validate({"categories": {"bancos": "B"}, "services": [svc, svc]})
