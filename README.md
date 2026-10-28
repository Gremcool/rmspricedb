# RMS Price Database

Search and compare medicine, consumable and lab-commodity prices across six price lists:
RHIA (June 2026), RMS Master (2024), RMS (2025), South Africa (2022), Sri Lanka (2024), UNICEF Africa.

## Run
```
pip install -r requirements.txt
streamlit run PriceDatabase.py
```
Tested on Streamlit 1.66.1.

## Currency
All lists are shown in USD and RWF at a flat **1 USD = 1,300 RWF** (the rate already used in the
existing lists). RHIA is published in RWF only, so its USD is derived at the same rate.
Change `FX_RWF_PER_USD` in `data_loader.py` if the rate changes.

## Data
- The five original lists are fetched from GitHub (`Gremcool/gremcool/excel_files`); if offline, the
  app falls back to a copy in `data/` with the same file name.
- RHIA is read from `data/RHIA_REIMBURSABLE_MEDICINES_LIST_JUNE-2026-1.xlsx`. To update it, replace
  that file (keep the same sheet layout) or edit the `file` name in `data_loader.py`.
- Rows with no price and exact duplicates are hidden (counts are shown on the Datasets tab).
- Add a new source: add a `SourceSpec` and a parser in `data_loader.py`.

## Files
- `PriceDatabase.py` dashboard
- `data_loader.py` loading, normalising, search
- `styles.py` CSS (also removes Streamlit's header, sidebar, footer and padding)
- `.streamlit/config.toml` dark theme and toolbar settings
