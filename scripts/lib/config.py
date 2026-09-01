"""Deck configuration loading and management."""

import importlib.util
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import genanki
import jpanki

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
    check_cloze_in_sentence: bool = True
    guid_namespace: str | None = None

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

    def subdeck_name(self, tier: int, female: bool = False) -> str:
        """Return an Anki-sortable subdeck name for this tier.

        Configuration labels historically included their own unpadded tier
        number. Strip that presentation prefix and let jpanki apply the single
        collection-wide numbering policy.
        """
        label = re.sub(r"^Tier\s+\d+\s*-\s*", "", self.tier_names[tier])
        voice_label = " (Female)" if female else ""
        return jpanki.subdeck(
            f"{self.name}{voice_label}", tier, label, total=self.tier_count
        )

    def note_guid(self, sentence: str) -> str:
        """The GUID Anki identifies a note by.

        Keyed on the sentence, so editing one orphans its review history - see
        scripts/migrate_guids.py. A deck that re-uses another deck's sentences
        must also set ``guid_namespace``, or the two mint the same GUID under
        different model IDs and Anki rejects the second import as a notetype
        conflict, landing the deck with zero cards.
        """
        if self.guid_namespace:
            return genanki.guid_for(self.guid_namespace, sentence)
        return genanki.guid_for(sentence)


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
        check_cloze_in_sentence=deck.get("check_cloze_in_sentence", True),
        guid_namespace=deck.get("guid_namespace"),
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
