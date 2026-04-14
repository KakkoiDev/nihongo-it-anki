"""Deck configuration loading and management."""

import importlib.util
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DECKS_DIR = PROJECT_ROOT / "decks"


@dataclass
class DeckConfig:
    """Configuration for a single Anki deck."""

    slug: str
    name: str
    model_id: int
    deck_base_id: int
    tier_count: int
    tier_names: dict[int, str]
    tier_sizes: dict[int, int]

    @property
    def data_dir(self) -> Path:
        return DECKS_DIR / self.slug

    def csv_path(self, tier: int) -> Path:
        return self.data_dir / f"tier{tier}-vocabulary.csv"

    def audio_dir(self, tier: int, female: bool = False) -> Path:
        suffix = "-female" if female else ""
        return self.data_dir / f"tier{tier}-audio{suffix}"

    def tier_range(self) -> range:
        return range(1, self.tier_count + 1)

    def get_deck_id(self, tier: int) -> int:
        return self.deck_base_id + tier


def load_deck_config(slug: str) -> DeckConfig:
    """Load a deck configuration from decks/{slug}/deck.toml."""
    config_path = DECKS_DIR / slug / "deck.toml"
    if not config_path.exists():
        raise FileNotFoundError(f"No deck config at {config_path}")

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    deck = raw["deck"]
    tiers = raw["tiers"]

    # TOML keys are strings, convert to int
    tier_names = {int(k): v for k, v in tiers["names"].items()}
    tier_sizes = {int(k): v for k, v in tiers["sizes"].items()}

    return DeckConfig(
        slug=deck["slug"],
        name=deck["name"],
        model_id=deck["model_id"],
        deck_base_id=deck["deck_base_id"],
        tier_count=tiers["count"],
        tier_names=tier_names,
        tier_sizes=tier_sizes,
    )


def list_decks() -> list[str]:
    """Return slugs of all configured decks."""
    if not DECKS_DIR.exists():
        return []
    return sorted(
        d.name
        for d in DECKS_DIR.iterdir()
        if d.is_dir() and (d / "deck.toml").exists()
    )


def load_translations(slug: str) -> dict[str, str]:
    """Load the TRANSLATIONS dict from a deck's translations.py."""
    translations_path = DECKS_DIR / slug / "translations.py"
    if not translations_path.exists():
        return {}

    spec = importlib.util.spec_from_file_location(
        f"decks.{slug}.translations", translations_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {translations_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TRANSLATIONS
