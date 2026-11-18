# RMS Price Database

Search and compare medicine, consumable and lab prices across your price lists. Search is instant (it
runs in the browser), results show USD or RWF, and a compare drawer ranks products side by side.
Light and dark themes. An admin adds lists or uploads a whole database from a hidden panel in the page footer.

## Run
```
pip install -r requirements.txt
streamlit run PriceDatabase.py
```

## How it is built
| File | Job |
|---|---|
| `PriceDatabase.py` | Streamlit shell: loads the page and the hidden **Admin** panel (add lists, upload a database, remove, backup), optional password |
| `index.html` | The whole interface as one HTML page (search, results, compare, theme). Edit it like any web page |
| `database.py` | SQLite storage: `datasets` (one row per list) and `prices` |
| `importer.py` | Recognises each file's layout and cleans it |
| `pricedb.sqlite` | The database, already filled with your six lists |
| `datasets/` | The original Excel files. Used only to rebuild the database if `pricedb.sqlite` is missing or empty |

## The admin panel (hidden)
There is no admin button for visitors. At the very bottom of the page there is a faint **Admin** link (or press
Ctrl+Shift+A, or open the app with `?admin=1` to get a plain Admin button under the page). It opens a panel with four tabs:

- **Lists**: what is in the database, and removing a list.
- **Add a list**: upload an Excel or CSV file. The six existing layouts (RHIA, RMS Master, RMS 2025, South Africa,
  Sri Lanka, UNICEF) are recognised by their columns, so renamed files still work. Any other file needs a product or
  description column and a price column named like `Unit Price (USD)` or `Unit Price (RWF)`; pack, category and note
  columns are optional, and if the price column does not say its currency the app asks. Uploading a list with the same
  name replaces it, which is how you update a list with a newer file.
- **Upload database**: replace everything with a whole `.sqlite` file, for example the `pricedb.sqlite` you downloaded
  from Backup. The file is checked first (it must be a valid RMS price database) and you confirm before anything changes.
  The previous database is kept next to it as `pricedb.previous`.
- **Backup**: download the database or all prices as CSV.

Rows with no price and exact duplicates are left out when importing (the counts are shown under Lists).

## Admin password (strongly recommended)
A hidden link is not security. Without a password, anyone who finds the link can change the data, and the panel says
so. To require one, set `admin_password` in `.streamlit/secrets.toml` (see `secrets.toml.example`), in the Secrets
settings on Streamlit Community Cloud (Manage app > Settings > Secrets), or set the `RMS_ADMIN_PASSWORD` environment
variable. After 5 wrong attempts the panel locks until the page is reloaded.

## Keeping changes (important on free hosting)
Changes are saved to `pricedb.sqlite` on the server's disk. Free hosts such as Streamlit Community Cloud
reset that disk when the app restarts. To keep a change:
1. **Admin > Backup > Download database**
2. Replace `pricedb.sqlite` in your GitHub repo with that file.

If your host has a persistent volume mounted at `/data`, the app uses it automatically and nothing needs
committing.

## Currency
Every list is shown in USD and RWF at a flat **1 USD = 1,300 RWF**, the rate your existing lists already use.
RHIA is published in RWF only, so its USD is derived at the same rate. To change the rate, edit
`FX_RWF_PER_USD` in `importer.py` and re-import the lists.

## If something looks wrong
- **The page says "Loading prices…" and stays there:** the page itself needs nothing from the internet, so this means
  its data did not arrive. Reload once; if it persists, the message that replaces it (or a red box above the page)
  names the problem. Please send me that message.
- **"The price database could not be opened":** the app folder may be read-only or on a synced drive (Google Drive,
  OneDrive). The app then tries a private copy in the system temp folder automatically. Keep the project in a normal
  local folder when running it on your computer.
- **The Admin link does nothing:** open the app with `?admin=1` at the end of the address and scroll to the bottom; a plain Admin button appears there.
- Tested on Streamlit 1.40 and 1.67, with pandas 2 and 3.

## Uploading to GitHub (Streamlit Community Cloud runs straight from your repo)
Every file the app reads must be in the repository. Put these **files** at the top level, next to `PriceDatabase.py`:

`PriceDatabase.py`, `database.py`, `importer.py`, `index.html`, `pricedb.sqlite`, `requirements.txt`

That is enough to run the app; no folder is required. `datasets/` (the original Excel files) and `.streamlit/` are
optional extras. On GitHub: **Add file > Upload files**, drag the files in, **Commit changes**, then open the repo's file
list and check that all six files above are there. Streamlit Cloud redeploys on its own; if the page looks stale, use
**Manage app > Reboot app**.

Because Streamlit Cloud resets its disk on restart, keep `pricedb.sqlite` in GitHub as your master copy, and replace it
with the file from **Admin > Backup > Download database** after you add or change lists in the app.
