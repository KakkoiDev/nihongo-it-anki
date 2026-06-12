"""Migration behavior tests against a real headless Anki collection.

Pins the actual import semantics of the Anki version in the dev environment
(anki python package) for every update scenario this repo ships:

  - re-import of an identical build (idempotence)
  - field/translation edits with unchanged GUID (in-place update)
  - sentence rewrites = GUID change (duplicate creation + migrate_sentences.py)
  - styling/CSS changes to an existing notetype
  - deck renames with stable deck ids
  - audio replacement under the same filename
  - media filename collisions between two different decks

Toy decks are built with genanki using the same guid_for(Sentence) contract
as scripts/create_deck.py. Media content is opaque bytes (Anki does not
parse audio), so fake payloads stand in for mp3s.

Pinned importer behaviors (anki 25.09) that the repo workflow relies on:
  - A note whose incoming mod timestamp equals the existing note's mod is
    logged as "duplicate" and silently skipped, even with
    update_notes=ALWAYS. genanki stamps mod at package-write time, so two
    builds within the same second do not update each other. Tests sleep
    >1s between builds; real rebuilds are naturally minutes apart.
  - Decks are matched by NAME, not by deck id. Renaming a tier in
    deck.toml forks a second deck on import; migrate_deck_names.py exists
    for exactly this.
  - Only media REFERENCED by imported (added/updated) notes is imported.
    On a filename conflict with different content the importer does not
    overwrite: it stores the incoming file under a checksum-suffixed name
    and rewrites the imported notes' [sound:] references. Cross-deck
    filename collisions (it-vocab and it-kundoku both use
    tier{N}_{idx}.mp3) are therefore safe on this Anki version, and audio
    replacement lands whenever the referencing note row updates (newer
    mod is enough; field changes not required).
"""

import csv
import sqlite3
import sys
import time
from pathlib import Path

import genanki
import pytest
from anki.collection import Collection, ImportAnkiPackageRequest
from anki import import_export_pb2 as iep

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import migrate_sentences  # noqa: E402

UPDATE_ALWAYS = iep.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS

MODEL_ID = 1700000001
DECK_ID = 1800000001
OTHER_MODEL_ID = 1700000002
OTHER_DECK_ID = 1800000002


def make_model(model_id=MODEL_ID, css=".card { color: black; }"):
    return genanki.Model(
        model_id,
        "Toy IT Model",
        fields=[{"name": "Sentence"}, {"name": "Translation"}, {"name": "Audio"}],
        templates=[{
            "name": "Card 1",
            "qfmt": "{{Sentence}}{{Audio}}",
            "afmt": "{{FrontSide}}<hr>{{Translation}}",
        }],
        css=css,
    )


def build_apkg(path, rows, deck_id=DECK_ID, deck_name="Toy::Tier 01",
               model=None, media=None):
    """rows: list of (sentence, translation, audio_ref). media: {name: bytes}."""
    model = model or make_model()
    deck = genanki.Deck(deck_id, deck_name)
    for sentence, translation, audio in rows:
        deck.add_note(genanki.Note(
            model=model,
            fields=[sentence, translation, audio],
            guid=genanki.guid_for(sentence),
        ))
    pkg = genanki.Package(deck)
    media_paths = []
    if media:
        media_dir = path.parent / f"{path.stem}-media"
        media_dir.mkdir(exist_ok=True)
        for name, content in media.items():
            p = media_dir / name
            p.write_bytes(content)
            media_paths.append(str(p))
    pkg.media_files = media_paths
    pkg.write_to_file(str(path))
    return path


@pytest.fixture
def col(tmp_path):
    c = Collection(str(tmp_path / "collection.anki2"))
    yield c
    c.close()


def import_pkg(col, apkg_path):
    return col.import_anki_package(ImportAnkiPackageRequest(
        package_path=str(apkg_path),
        options=iep.ImportAnkiPackageOptions(
            merge_notetypes=True,
            update_notes=UPDATE_ALWAYS,
            update_notetypes=UPDATE_ALWAYS,
            with_scheduling=True,
        ),
    ))


def note_count(col):
    return col.db.scalar("SELECT count(*) FROM notes")


def fake_review(col, sentence, reps=3, ivl=10):
    """Stamp review state onto the card of the note with this sentence."""
    nid = col.db.scalar(
        "SELECT id FROM notes WHERE flds LIKE ?", f"{sentence}\x1f%")
    assert nid, f"note not found: {sentence}"
    cid = col.db.scalar("SELECT id FROM cards WHERE nid = ?", nid)
    col.db.execute(
        "UPDATE cards SET reps = ?, ivl = ?, type = 2, queue = 2 WHERE id = ?",
        reps, ivl, cid)
    col.db.execute(
        "INSERT INTO revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type) "
        "VALUES (?, ?, -1, 3, ?, 1, 2500, 5000, 1)",
        int(time.time() * 1000), cid, ivl)
    col.save()
    return nid, cid


ROWS_V1 = [
    ("テストするためにブランチをチェックアウトしてください。", "Checkout the branch to test.", "[sound:toy_001.mp3]"),
    ("高いキャッシュヒット率は良いことです。", "High cache hit rate is good.", "[sound:toy_002.mp3]"),
    ("まず認識合わせをしましょう。", "Let's align first.", "[sound:toy_003.mp3]"),
]


class TestReimportBasics:
    def test_identical_reimport_is_idempotent(self, col, tmp_path):
        pkg = build_apkg(tmp_path / "v1.apkg", ROWS_V1)
        import_pkg(col, pkg)
        assert note_count(col) == 3
        import_pkg(col, pkg)
        assert note_count(col) == 3

    def test_same_second_rebuild_is_silently_skipped(self, col, tmp_path):
        """Pin the mod-equality shortcut: equal note mod -> no update."""
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1))
        rows_v2 = [(ROWS_V1[0][0], "UPDATED translation.", ROWS_V1[0][2])] + ROWS_V1[1:]
        log = import_pkg(col, build_apkg(tmp_path / "v2.apkg", rows_v2))
        if len(log.log.duplicate) == 3:
            flds = col.db.scalar(
                "SELECT flds FROM notes WHERE flds LIKE ?", f"{ROWS_V1[0][0]}\x1f%")
            assert "UPDATED translation." not in flds, (
                "importer logged duplicate but still updated fields")
        # If the two builds straddled a second boundary the import updates
        # normally; either way the next test covers the >1s path.

    def test_field_edit_same_guid_updates_in_place(self, col, tmp_path):
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1))
        fake_review(col, ROWS_V1[0][0])

        time.sleep(1.2)  # mod-equality shortcut: see module docstring
        rows_v2 = [(ROWS_V1[0][0], "UPDATED translation.", ROWS_V1[0][2])] + ROWS_V1[1:]
        import_pkg(col, build_apkg(tmp_path / "v2.apkg", rows_v2))

        assert note_count(col) == 3
        flds = col.db.scalar(
            "SELECT flds FROM notes WHERE flds LIKE ?", f"{ROWS_V1[0][0]}\x1f%")
        assert "UPDATED translation." in flds
        reps = col.db.scalar(
            "SELECT reps FROM cards WHERE nid = (SELECT id FROM notes WHERE flds LIKE ?)",
            f"{ROWS_V1[0][0]}\x1f%")
        assert reps == 3, "review history must survive a field-only update"


class TestSentenceRewrite:
    OLD = ROWS_V1[0][0]
    NEW = "テストするためにブランチをチェックアウトしてもらえますか？"

    def _map_file(self, tmp_path):
        path = tmp_path / "map.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["tier", "row", "old_guid", "new_guid",
                        "old_sentence", "new_sentence"])
            w.writerow([1, 1, genanki.guid_for(self.OLD),
                        genanki.guid_for(self.NEW), self.OLD, self.NEW])
        return path

    def _v2_rows(self):
        return [(self.NEW, "Can you checkout the branch to test?",
                 ROWS_V1[0][2])] + ROWS_V1[1:]

    def _v2_pkg(self, tmp_path):
        time.sleep(1.2)  # mod-equality shortcut: see module docstring
        return build_apkg(tmp_path / "v2.apkg", self._v2_rows())

    def test_rewrite_without_migration_duplicates(self, col, tmp_path):
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1))
        import_pkg(col, self._v2_pkg(tmp_path))
        assert note_count(col) == 4, "sentence rewrite creates a duplicate note"

    def test_migrate_then_import_preserves_history(self, col, tmp_path):
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1))
        _, cid = fake_review(col, self.OLD)
        col.close()

        db = Path(col.path)
        stats = migrate_sentences.run(db, self._map_file(tmp_path), None, False)
        assert stats["guid_updated"] == 1

        col2 = Collection(str(db))
        try:
            import_pkg(col2, self._v2_pkg(tmp_path))
            assert note_count(col2) == 3, "no duplicate after migration"
            flds = col2.db.scalar(
                "SELECT flds FROM notes WHERE guid = ?", genanki.guid_for(self.NEW))
            assert flds.startswith(self.NEW), "fields updated to new sentence"
            reps = col2.db.scalar("SELECT reps FROM cards WHERE id = ?", cid)
            assert reps == 3, "review history preserved across rewrite"
            assert col2.db.scalar(
                "SELECT count(*) FROM revlog WHERE cid = ?", cid) == 1
        finally:
            col2.close()

    def test_migrate_resolves_already_imported_duplicate(self, col, tmp_path):
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1))
        fake_review(col, self.OLD)
        import_pkg(col, self._v2_pkg(tmp_path))
        assert note_count(col) == 4
        col.close()

        db = Path(col.path)
        stats = migrate_sentences.run(db, self._map_file(tmp_path), None, False)
        assert stats["duplicates_resolved"] == 1
        assert stats["notes_deleted"] == 1

        conn = sqlite3.connect(db)
        try:
            assert conn.execute("SELECT count(*) FROM notes").fetchone()[0] == 3
            reps = conn.execute(
                "SELECT reps FROM cards WHERE nid = "
                "(SELECT id FROM notes WHERE guid = ?)",
                (genanki.guid_for(self.NEW),)).fetchone()[0]
            assert reps == 3, "the reviewed note wins duplicate resolution"
        finally:
            conn.close()

    def test_dry_run_writes_nothing(self, col, tmp_path):
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1))
        col.close()
        db = Path(col.path)
        before = db.read_bytes()
        stats = migrate_sentences.run(db, self._map_file(tmp_path), None, True)
        assert stats["guid_updated"] == 1
        assert db.read_bytes() == before


class TestStyleAndStructure:
    def test_css_update_behavior(self, col, tmp_path):
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1))
        v2 = build_apkg(tmp_path / "v2.apkg", ROWS_V1,
                        model=make_model(css=".card { color: red; }"))
        import_pkg(col, v2)
        nt = col.models.get(col.models.id_for_name("Toy IT Model"))
        assert "red" in nt["css"], (
            "notetype CSS should update on re-import with update_notetypes=ALWAYS")

    def test_deck_rename_same_id(self, col, tmp_path):
        import_pkg(col, build_apkg(tmp_path / "v1.apkg", ROWS_V1,
                                   deck_name="Toy::Tier 01"))
        fake_review(col, ROWS_V1[0][0])
        import_pkg(col, build_apkg(tmp_path / "v2.apkg", ROWS_V1,
                                   deck_name="Toy::Tier 01 - Renamed"))
        names = [d.name for d in col.decks.all_names_and_ids()]
        renamed_exists = any("Renamed" in n for n in names)
        old_exists = any(n.endswith("Tier 01") for n in names)
        # Pinned: the importer matches decks by NAME, not id. A rename in
        # deck.toml FORKS a second deck; existing cards stay in the old one.
        # migrate_deck_names.py is the remediation for real collections.
        assert renamed_exists and old_exists, (
            f"deck-rename fork behavior changed, update MIGRATE docs: {names}")
        assert note_count(col) == 3


def sound_file(col, sentence):
    flds = col.db.scalar(
        "SELECT flds FROM notes WHERE flds LIKE ?", f"{sentence}\x1f%")
    ref = flds.split("\x1f")[2]
    return ref.removeprefix("[sound:").removesuffix("]")


class TestMedia:
    def test_audio_replacement_via_rebuild_reimport(self, col, tmp_path):
        """The supported audio-fix path from tts-audio-debugging.md:
        rebuild the apkg with the fixed mp3 and re-import. The importer
        stores conflicting content under a checksum-suffixed name and
        rewrites the note reference; the old file stays behind as an
        orphan (Tools > Check Media cleans it)."""
        v1 = build_apkg(tmp_path / "v1.apkg", ROWS_V1,
                        media={"toy_001.mp3": b"AUDIO_V1"})
        import_pkg(col, v1)
        media_dir = Path(col.media.dir())
        assert (media_dir / sound_file(col, ROWS_V1[0][0])).read_bytes() == b"AUDIO_V1"

        time.sleep(1.2)  # mod-equality shortcut: see module docstring
        v2 = build_apkg(tmp_path / "v2.apkg", ROWS_V1,
                        media={"toy_001.mp3": b"AUDIO_V2_FIXED"})
        import_pkg(col, v2)
        new_ref = sound_file(col, ROWS_V1[0][0])
        assert (media_dir / new_ref).read_bytes() == b"AUDIO_V2_FIXED", (
            "re-imported audio must reach the note via checksum-renamed file")

    def test_media_collision_between_two_decks(self, col, tmp_path):
        """it-vocab and it-kundoku both name audio tier{N}_{idx}.mp3. Pin
        that importing both decks does NOT corrupt audio: the second
        deck's conflicting file lands under a checksum-suffixed name with
        its note reference rewritten, and the first deck's file survives."""
        rows_a = [(s, t, "[sound:tier1_001.mp3]") for s, t, _ in ROWS_V1[:1]]
        deck_a = build_apkg(tmp_path / "a.apkg", rows_a,
                            media={"tier1_001.mp3": b"DECK_A_AUDIO"})
        import_pkg(col, deck_a)
        media_dir = Path(col.media.dir())
        assert (media_dir / "tier1_001.mp3").read_bytes() == b"DECK_A_AUDIO"

        other_model = make_model(model_id=OTHER_MODEL_ID)
        rows_b = [("API之応答遅い", "The API response is slow", "[sound:tier1_001.mp3]")]
        deck_b = build_apkg(tmp_path / "b.apkg", rows_b,
                            deck_id=OTHER_DECK_ID, deck_name="OtherToy::Tier 01",
                            model=other_model,
                            media={"tier1_001.mp3": b"DECK_B_AUDIO"})
        import_pkg(col, deck_b)

        assert (media_dir / "tier1_001.mp3").read_bytes() == b"DECK_A_AUDIO", (
            "deck A audio clobbered: importer collision behavior changed, "
            "media filenames need deck-slug namespacing")
        b_file = sound_file(col, "API之応答遅い")
        assert b_file != "tier1_001.mp3", "deck B ref should be checksum-renamed"
        assert (media_dir / b_file).read_bytes() == b"DECK_B_AUDIO"
