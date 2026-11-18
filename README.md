# RMS Price Database

Search and compare medicine, consumable and lab prices across your price lists. Search is instant and predictive,
results show USD or RWF, **Compare lists** puts every matching product side by side across all lists, and a shortlist
lets you keep and rank your own picks. Light and dark themes. An admin adds lists or uploads a whole database from a
hidden panel in the page footer.

## Using the page
- **Search:** suggestions with result counts appear as you type, and a faint completion appears inside the box (press
  Tab to accept it). Click the empty box to see recent and popular searches.
- **Results:** every matching price, one per line, with the lowest marked. Tabs filter by list.
- **Compare lists:** the same search as a table. Each row is one product (grouped automatically by ingredient, strength
  and form) and each column is a price list, with the lowest price in green. Click a row to see every option behind it.
  "Only products in 2+ lists" hides products that only one list sells.
  A gap of 10 times or more is marked with a warning: it usually means a different pack size, not a real price
  difference, because the lists do not all quote prices per tablet.
- **Shortlist:** press + on any price to keep it, then open Shortlist (top right) to rank your picks.
- **List colours:** every price list has its own colour, shown as a tinted background behind its name wherever it
  appears (results, tabs, the comparison table, the shortlist), so you can see at a glance where a price comes from.
- **Tour:** a short animated walkthrough (a cursor types, clicks and compares on a miniature of the real screen). It opens
  once on a visitor's first visit. The **?** button in the top bar and the **Watch** links under the three steps open it
  again. Its text and scenes are in the `Tour` section of `index.html`; it uses sample products, not live data.

## Run
```
pip install -r requirements.txt
streamlit run PriceDatabase.py
```

## How it is built
| File | Job |
|---|---|
| `PriceDatabase.py` | Streamlit shell: loads the page and the hidden **Admin** panel (add lists, upload a database, remove, backup), optional password |
| `index.html` | The whole interface as one HTML page (search, results, compare, tour, theme). Edit it like any web page. The RMS logo is embedded in it (a light and a dark version), so no image files need uploading |
| `database.py` | SQLite storage: `datasets` (one row per list) and `prices` |
| `importer.py` | Recognises each file's layout and cleans it |
| `fx.py` | Looks up the live USD to RWF rate, with safe fallbacks |
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

## Currency and the live exchange rate
The rate shown under the USD / RWF switch is looked up online, at most once an hour, from free services that publish
the market rate (Google has no public service for this): the Currency API on jsDelivr, the same data on Cloudflare,
then ExchangeRate-API. The last good rate is saved in the database. Next to the rate the page tells you what it is:

- **no note**: a live rate (hover it to see the source and date)
- **(last saved)**: the services could not be reached, so the previous rate is being used
- **(fixed rate)**: the services could not be reached and no rate was saved yet, so 1 USD = 1,300 RWF is used

Each list keeps the price it was published in and only the other currency is converted. The five USD lists show their
USD price as published and RWF = USD x the rate. RHIA is published in RWF, so its RWF price is as published and USD =
RWF / the rate. (The RWF column inside those five files was the USD price x 1,300 rounded up to a whole franc, which is
why small prices looked a little high in RWF before.) The exported CSVs use the same rate.

The admin panel (Lists tab) shows the rate in use and, if the lookup failed, the reason. The app needs to be able to
reach the internet for a live rate. `importer.FX_RWF_PER_USD` (1,300) is only used when a file is imported, to fill the
second price column in the database; it is never shown.

## If something looks wrong
- **The page says "Loading prices…" and stays there:** the page itself needs nothing from the internet, so this means
  its data did not arrive. Reload once; if it persists, the message that replaces it (or a red box above the page)
  names the problem. Please send me that message.
- **"The price database could not be opened":** the app folder may be read-only or on a synced drive (Google Drive,
  OneDrive). The app then tries a private copy in the system temp folder automatically. Keep the project in a normal
  local folder when running it on your computer.
- **A yellow notice at the top says a file is missing or older (database.py, fx.py):** the files in GitHub are not all from the same
  version. The app still works, but the live exchange rate stays off until the named file is uploaded. Upload it (or, easiest,
  every top-level file from this folder together, letting them overwrite) and reload the page; the app picks up the new file
  by itself. If the notice is still there after a minute, use Manage app > Reboot app.
- **The Admin link does nothing:** open the app with `?admin=1` at the end of the address and scroll to the bottom; a plain Admin button appears there.
- Tested on Streamlit 1.40 and 1.67, with pandas 2 and 3.

## Uploading to GitHub (Streamlit Community Cloud runs straight from your repo)
Every file the app reads must be in the repository. Put these **files** at the top level, next to `PriceDatabase.py`:

`PriceDatabase.py`, `database.py`, `importer.py`, `fx.py`, `index.html`, `pricedb.sqlite`, `requirements.txt`

That is enough to run the app; no folder is required. `datasets/` (the original Excel files) and `.streamlit/` are
optional extras. On GitHub: **Add file > Upload files**, drag the files in, **Commit changes**, then open the repo's file
list and check that all seven files above are there. Streamlit Cloud redeploys on its own; if the page looks stale, use
**Manage app > Reboot app**.

Because Streamlit Cloud resets its disk on restart, keep `pricedb.sqlite` in GitHub as your master copy, and replace it
with the file from **Admin > Backup > Download database** after you add or change lists in the app.

## Keeping the repository tidy
The app uses only the files in this folder. Anything else sitting in the repository can be deleted, in particular leftovers
from older versions: `data_loader.py`, `styles.py`, `ui/` (the old place of index.html), `__pycache__/`. Files that belong to a
different project (for example `app.py`, `Procfile`, `pbc_*`) are not used by this app, but check they are not used by
something else before deleting them.
