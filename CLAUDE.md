# HighLow TUI — Developer Notes

## Architecture

```
app.py                         # Textual TUI app (entry point)
core/
  subscription_manager.py      # Schwab websocket → asyncio queue (singleton)
  high_low_ticker.py           # Per-symbol high/low detection engine
  schwab_connection.py         # Auth + raw streaming
  shared_api_client.py         # Singleton Schwab client
config/
  highlight.json               # Thresholds + colors (user-editable at runtime)
tickers/
  tickers.json                 # All streamed symbols
  spy_tickers.json             # Used for SPY A/D calculation
  dow_tickers.json             # Used for DIA A/D calculation
  qqq_tickers.json             # Used for QQQ A/D calculation
```

## Data flow

```
Schwab WS → SchwabConnection.handle_message()
          → SubscriptionManager.handle_highlow()   [throttled to 1 Hz]
          → HighLowTicker.process_stock()
          → asyncio.Queue  {"type": "HIGHLOW_UPDATE", "data": state}
          → app._data_loop()
          → app._apply_highlow_update()
          → app._refresh_ui()
```

## Performance rules — do not break these

- **Widget refs are cached** in `on_mount` as `self._w_*`. Never call `query_one` inside
  `_refresh_ui` or `_refresh_status` — it walks the DOM every call.
- **`await asyncio.sleep(0)`** after `_refresh_ui()` in `_data_loop` is intentional.
  It yields the event loop so Textual can flush renders and handle keyboard input.
  Remove it and the app feels sluggish even at 1 Hz.
- **Tables only rebuild when dirty** (`_highs_dirty` / `_lows_dirty` flags set in
  `_apply_highlow_update`). Don't remove this gate — in a quiet market the tables
  should do zero work per tick.
- **`sorted()` was intentionally removed** from `_apply_highlow_update`. New entries
  always have `ts = time.time()` (the highest timestamp) and are inserted at index 0,
  so the list stays ordered. Don't re-add `sorted()`.
- **`add_columns` must only run in `on_mount`**. `DataTable.clear()` keeps columns.
  Calling `add_columns` after every `clear()` stacks duplicate columns silently.
- **`MAX_TABLE_ROWS = 50`**. A terminal shows ~25 rows per table at most. 200 rows
  means building 4× more Text objects than are ever visible.
- **`compute_highlights` is O(n)** via a two-pass run-size algorithm. Do not replace
  it with a per-row loop (the old `get_highlight_type` was O(n²)).

## Highlight logic (priority order)

1. `flash_high` / `flash_low` — index 0 (most recent entry)
2. `week52_high` / `week52_low` — symbol is at 52-week extreme
3. `yellow` — count == 1 (first occurrence this session)
4. `orange` — symbol appears in ≥ `consecutiveCount+1` contiguous rows
5. `purple` — pct change delta vs. nearest previous same-symbol entry > `significantPercentChange`
6. `default`

Thresholds are in `config/highlight.json` and hot-reloadable via `s` → Settings.

## Rate bars

`highCounts` / `lowCounts` from `HighLowTicker.get_state()` count timestamps in the
last 30s / 1m / 5m / 20m windows. Timestamps are pruned to 1200s (20m) — do not
reduce this or the 20m bar silently becomes a shorter window.

The bars use a mirrored layout: lows grow right→left, highs grow left→right, with the
timeframe label in the center. `make_bar(..., reverse=True)` handles the lows side.

## Index cards

A/D ratio is computed by scanning constituent ticker lists against the live
`percentChange` dict. SPY has ~500 constituents; this runs every tick but is fast
(dict lookups are O(1)).

`indexPrices` in the state gives the raw price. `percentChange["SPY"]` etc. gives
the index's own % change.

## Adding new features

- **New widget**: add to `compose()`, cache ref in `on_mount`, update in `_refresh_ui`.
- **New highlight type**: add to `HIGHLIGHT_STYLES` dict and update `compute_highlights`.
- **New timeframe bar**: add to `RATE_TIMEFRAMES` list; ensure `HighLowTicker.get_state()`
  computes and the pruning window covers it.
- **Settings screen**: edit `SettingsScreen.compose()` and `load_highlight_config()`.
  The screen reloads `highlight.json` on close — no restart needed.
