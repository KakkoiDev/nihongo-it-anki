# Echo import

Download [agentic-lab-jp-echo.json](agentic-lab-jp-echo.json) and import it in Echo Settings. It contains the Agentic Lab Priority Path deck, once per distinct Japanese sentence rather than once per card template. Pronunciation annotations are kept when they match the authored sentence. No audio, review scheduling or invented register variants are added.

Regenerate from repository root with `node scripts/export_echo.mjs` (Node 18+). `jp-core.mjs` is copied unchanged from JP Core's canonical browser distribution. Provenance records the source CSV, tier and row. Echo imports merge without duplicating existing sentences.

Verify with `node --test scripts/test_echo_export.mjs`.

JP Core browser revision: ee9bfdb8a5b3fc38903ef6fcbcd50fa65d75bdf3.
