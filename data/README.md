# Data

The original project generates a large number of race-level files during the acquisition process. These generated outputs are intentionally not committed to the repository.

The pipeline produces:

- Scraped race classifications under `data/season_<year>/`
- API pit-stop and driver data under `<year>/`
- A merged dataset at `data/f1_complete_dataset.csv`

A small sample of scraped race files is included in `data/sample/`.
