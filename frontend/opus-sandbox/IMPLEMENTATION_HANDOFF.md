# Isolated frontend handoff

The sandbox now contains a focused UPWIND landing page pass in `src/App.tsx` and `src/style.css`.

The page uses a warm editorial visual system and one real scroll sequence. The hero presents the national Explorer capture. The pinned desktop story crossfades between the overview, place detail, and documented source layer as scroll progress advances; the chapter text and progress bar move with it. Mobile and reduced-motion modes show every chapter in normal document flow. Links point to `/explore` and `/local` for later integration.

Real screenshots are in `public/assets/`. Verification captures are in `screenshots/`, including desktop, laptop, tablet, mobile, reduced-motion, and three story positions.

Run from this directory:

```bash
npm run dev       # http://127.0.0.1:4178
npm run build
npx playwright test
```

Current verification: 3 Playwright tests pass and the production build passes. The browser checks cover the real routes, scroll progress at 0/50/100%, reversal, mobile overflow, reduced motion, laptop/tablet layouts, and screenshot capture.
