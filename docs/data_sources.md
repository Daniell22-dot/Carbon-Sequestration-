# Data Sources

This project never fabricates production data. When a source is unavailable and
no cache exists, the pipeline fails loudly with `DataSourceUnavailableError`.

## Tier 1: authoritative primary sources

### NOAA Global Monitoring Laboratory (CO2)

- URL: https://gml.noaa.gov/ccgg/trends/
- Endpoint used: `https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_{station}.csv`
- Format: monthly CSV with `#` comment lines
- Update frequency: monthly
- Licensing: U.S. Government work, public domain
- Known issues: missing monthly means are encoded as `-9.99`; station coverage
  varies. The parser converts sentinel values to `NaN`.
- Attribution: NOAA Global Monitoring Laboratory, Mauna Loa CO2 records.

### CDR Database (carbon removal projects)

- URL: https://cdrdatabase.com
- Access: no stable public API. Configure `data_sources.cdr.api_endpoint` if you
  have licensed API access, or import a CSV export with
  `load_cdr_projects_csv`.
- Licensing: site terms apply; verify redistribution rights before publishing.
- Known issues: project schemas vary. Required fields are validated and missing
  optional fields are set to null.

### World Bank Open Data

- URL: https://data.worldbank.org
- Endpoint used: `https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}`
- Format: JSON, paginated at 1,000 rows per page
- Update frequency: annual for most climate indicators
- Licensing: World Bank Open Data terms (CC BY 4.0 for most datasets)
- Known issues: `value` is null for missing years; those rows are dropped.

### IEA

- URL: https://www.iea.org/data-and-statistics
- Access: licence-restricted; no open API used here
- Integration: `load_iea_csv` validates a licensed CSV export
- Licensing: IEA terms; do not redistribute raw data

### IPCC AR6 WGIII

- URL: https://www.ipcc.ch/report/ar6/wg3/
- Use: method assessment reference ranges in `src/constants.py`
- Licensing: IPCC reports are generally reusable with attribution

## Tier 2: secondary sources

### OpenAlex

- URL: https://api.openalex.org/works
- Format: JSON
- Update frequency: continuous
- Licensing: CC0 metadata
- Etiquette: supply `OPENALEX_EMAIL` to join the polite pool

### Global Carbon Project

- URL: https://www.globalcarbonproject.org
- Access: CSV downloads; load with `pandas.read_csv` and validate columns

### FAO

- URL: https://www.fao.org/faostat/
- Access: `faostat` package or CSV downloads (not bundled by default)

## Tier 3: supplementary sources

- Carbon market data (Xpansiv, CBL Markets): licensed
- Company disclosures (Climeworks, Carbon Engineering): public reports
- News articles: use only for leads, never as the sole quantitative source

## Provenance

Every cached download writes a sibling `.meta.json` file containing:

```json
{
  "source": "NOAA GML",
  "url": "https://gml.noaa.gov/...",
  "params": {},
  "fetched_at": "2026-01-01T00:00:00+00:00",
  "fetched_at_epoch": 1767225600.0,
  "sha256": "...",
  "bytes": 12345,
  "content_type": "text/csv"
}
```

Processed datasets additionally record row counts and observation periods via
`src.utils.io.write_metadata`.

## Caching policy

- Default TTL: 24 hours for NOAA, 168 hours for CDR/World Bank/OpenAlex.
- Fresh cache entries are reused without a network call.
- Stale cache entries are used only when the network fails, and the fallback is
  logged at WARNING level.
- Use `--force` to bypass a fresh cache deliberately.
