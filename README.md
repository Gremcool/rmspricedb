# RMS Price Database

Search and compare medicine, consumable and lab prices across your price lists. Search is instant (it
runs in the browser), results show USD or RWF, and a compare drawer ranks products side by side.
Light and dark themes. New lists can be added from the app.

## Run
```
pip install -r requirements.txt
streamlit run PriceDatabase.py
```

## How it is built
| File | Job |
|---|---|
| `PriceDatabase.py` | Streamlit shell: loads the page, the **Manage** dialog (upload / remove / backup), optional password |
| `ui/index.html` | The whole interface as one HTML page (search, results, compare, theme). Edit it like any web page |
| `database.py` | SQLite storage: `datasets` (one row per list) and `prices` |
| `importer.py` | Recognises each file's layout and cleans it |
| `pricedb.sqlite` | The database, already filled with your six lists |
| `datasets/` | The original Excel files. Used only to rebuild the database if `pricedb.sqlite` is missing or empty |

## Adding or updating a list
Click **Manage** (top right) → **Add or update a list** and upload an Excel or CSV file.

- The six existing layouts (RHIA, RMS Master, RMS 2025, South Africa, Sri Lanka, UNICEF) are recognised by
  their columns, so renamed files still work.
- Any other file needs a product or description column and a price column named like `Unit Price (USD)` or
  `Unit Price (RWF)`. Pack, category and note columns are optional. If the price column does not say its
  currency, the app asks.
- Uploading a list with the same name **replaces** it, which is how you update a list with a newer file.
- Rows with no price and exact duplicates are left out (the counts are shown under Manage > Lists).

## Keeping changes (important on free hosting)
Changes are saved to `pricedb.sqlite` on the server's disk. Free hosts such as Streamlit Community Cloud
reset that disk when the app restarts. To keep a change:
1. **Manage > Backup > Download database**
2. Replace `pricedb.sqlite` in your GitHub repo with that file.

If your host has a persistent volume mounted at `/data`, the app uses it automatically and nothing needs
committing.

## Admin password (optional but recommended if the app is public)
Without a password, anyone who opens the app can use Manage. To require one, set `admin_password` in
`.streamlit/secrets.toml` (see `secrets.toml.example`) or set the `RMS_ADMIN_PASSWORD` environment variable.

## Currency
Every list is shown in USD and RWF at a flat **1 USD = 1,300 RWF**, the rate your existing lists already use.
RHIA is published in RWF only, so its USD is derived at the same rate. To change the rate, edit
`FX_RWF_PER_USD` in `importer.py` and re-import the lists.

## Uploading to GitHub
Upload the **contents** of this folder, including `pricedb.sqlite`, `datasets/`, `ui/` and `.streamlit/`.
(`.streamlit` starts with a dot and is easy to miss; the app also works without it.)
