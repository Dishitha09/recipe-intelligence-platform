# Multi-Source Ingestion Proof Artifacts

This folder contains small, reviewer-facing artifacts used to verify the
non-web source adapters:

- `youtube/`: downloaded transcript sidecar text.
- `pdf/`: cookbook text used to build a small PDF fixture.
- `datasets/`: structured dataset CSV rows.
- `images/`: OCR sidecar text for a recipe card image.
- `audio/`: transcript sidecar text for an audio source.
- `csv/`: manual CSV upload rows.

Run the ingestion proof with:

```bash
python -m services.acquisition.multisource_recipe_ingestion
```

These files prove adapter coverage. They are intentionally small; large-scale
collection should use the same adapters with approved source files and batch
limits.
