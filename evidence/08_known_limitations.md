# Known Limitations

- RAG modules are present but out of scope for PS-1 to PS-5.
- External production sources are disabled by default to avoid unapproved live
  crawling from a fresh checkout.
- Audio, PDF, image, and YouTube adapters support deterministic sidecar
  fallbacks; full Whisper/scanned-PDF OCR production services require external
  binaries or credentials.
- The current embedding model is 384-dimensional (`all-MiniLM-L6-v2`). The
  problem statement mentions 768 dimensions; this implementation uses the
  deployed 384-dimensional model consistently across schema, loaders, and tests.
- Top-200 ingredient density provenance is not complete yet. UOM normalization
  enforces the canonical unit set, but production density coverage still needs a
  curated `data/reference/top_200_ingredient_density.csv` with source
  provenance before PS-4 can be called fully production-complete.
