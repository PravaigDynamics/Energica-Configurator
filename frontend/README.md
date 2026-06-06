# Energica Configurator — Frontend

React/Next.js application for the Energica Motorcycle Configurator.

## Quick Start

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

Open `http://localhost:3000/test` to see all four model configurators.

## Environment Variables

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key Files

| File | Purpose |
|------|---------|
| `components/EnergiccaConfigurator.tsx` | Main configurator component |
| `utils/api.ts` | Compositor service API client |
| `styles/energica-theme.css` | Energica design token stylesheet |
| `pages/test.tsx` | QA page with all four models |

## Brand Compliance

All styling uses CSS variables from `energica-theme.css`:
- Colors: `--energica-green`, `--graphite`, `--carbon`, `--racing-red` only
- Fonts: Barlow Condensed (headings/UI) + IBM Plex Sans (body)
- No hardcoded color values in component files
