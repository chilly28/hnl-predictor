# Automatic soft-factor signals

Future automatic providers (news, club statements, social media) write JSON
files here, e.g. `news.json`:

```json
{"factors": [
  {"team": "rijeka", "date": "2026-10-14", "type": "media",
   "note": "Negative press around the club", "adjustment": -10,
   "confidence": 0.6, "source": "https://..."}
]}
```

Same fields and caps as `data/soft_factors.yaml`; `confidence` (0–1) scales
the adjustment and the site marks these as "auto". Implement the
`SignalProvider` protocol in `hnl_predictor/soft_factors.py`.
