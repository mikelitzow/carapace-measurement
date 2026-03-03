"""App configuration – loaded from config.yaml next to the project root."""

from dataclasses import dataclass, asdict
from pathlib import Path

import yaml

_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class Config:
    bar_length_mm: float = 2.0
    micrometer_keyword: str = "micrometer"
    sl_mode: str = "LEFT"   # LEFT | RIGHT | BOTH


def load_config() -> Config:
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE) as fh:
                data = yaml.safe_load(fh) or {}
            cfg = Config()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            return cfg
        except Exception:
            pass
    return Config()


def save_config(cfg: Config) -> None:
    with open(_CONFIG_FILE, "w") as fh:
        yaml.dump(asdict(cfg), fh, default_flow_style=False)
