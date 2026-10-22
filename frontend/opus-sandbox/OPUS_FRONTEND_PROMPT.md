# Opus 5.5 build brief — UPWIND landing page

You are the frontend designer and implementer. Build a polished, professional, responsive parallax-scrolling landing page for UPWIND in this isolated folder.

## Work boundary

- Read and write files only inside `frontend/opus-sandbox/`.
- Use only the supplied images in `public/assets/` as product references. Do not inspect or edit the parent application, backend, datasets, scientific code, routes, screenshots, or configuration.
- Keep this app standalone. Do not add API calls, fake map data, or claims that the reference images prove.
- Use the existing React + TypeScript + Vite setup. Prefer CSS and browser APIs; add no dependency unless a concrete need cannot be met without it.

## Product and content

Mission, expressed prominently and accurately: **“UPWIND helps communities understand local air-quality evidence, inspect nearby reported emissions, and share clear, sourced findings.”**

Make a concise page with this sequence:

1. **Hero:** memorable headline, one-sentence mission, primary “Explore the map” action and secondary “Use local sensor data” action. Use the supplied Explorer overview screenshot as the main product image, presented as a crisp interface preview.
2. **How exploration works:** a scroll-driven sequence showing (a) find a place, (b) inspect a dated modeled estimate alongside supporting measurement context, (c) compare a separate documented emissions inventory layer, and (d) share a sourced view. Pair short copy with the supplied overview, place, and sources screenshots. Clearly state that proximity does not establish that a source caused a measurement.
3. **Evidence and limits:** explain that modeled estimates, measurements, and reported inventory records are different evidence types; historical coverage varies by place and year. Do not invent coverage statistics, accuracy, field validation, adoption, or health impact.
4. **Close:** clear links/actions for the Explorer and local-data workflow, followed by a restrained footer.

Use concise real product language, strong type hierarchy, generous whitespace, a restrained palette, and the supplied images. The result should feel editorial, calm, credible, and built for a civic/scientific tool—not a generic startup template.

## Motion and interaction requirements

- Deliver visible, intentional motion: vertical scroll drives a bounded parallax relationship between background/typography and the product imagery; the workflow may pin one visual while its chapters advance, or use an equally clear scroll-linked progression. The movement must visibly change at three scroll positions and reverse smoothly when scrolling upward.
- Add restrained entrance reveals and 120–200 ms hover/focus feedback for links and buttons. Avoid bounce, constant motion, fake map animations, decorative particles, and animation that delays interaction.
- Use `transform` and `opacity` for motion, avoid layout-changing animation, and keep scrolling native. Use `IntersectionObserver` or CSS scroll timelines/progress where practical; avoid per-frame React state updates.
- Respect `prefers-reduced-motion`: remove parallax/pinning and show the complete content in normal document flow. Preserve all links and information.
- All controls must be semantic, keyboard operable, visibly focused, and readable at WCAG AA contrast. Provide useful image alt text.

## Visual and responsive acceptance

- Design desktop first at 1440×900, then verify 1280×800, 768×1024, and 390×844.
- No horizontal overflow, overlapping text, clipped controls, or tiny copy. On mobile, convert pinned/side-by-side scenes into a readable vertical sequence and reduce parallax intensity.
- Use the real supplied screenshots as imagery; do not fabricate a map, sensors, measurements, or statistics.
- Avoid generic purple/blue gradients, glow blobs, glass cards, oversized rounded-card grids, stock imagery, random floating labels, and filler sections. Every visual element must clarify product, evidence, or navigation.
- Keep the page concise. Do not add testimonials, pricing, newsletter forms, or unsupported impact claims.

## Required finish

1. Implement the page; do not return a proposal.
2. Run `npm run build` from this folder and fix build errors.
3. Run `npm run dev` and visually inspect the page at all four viewport sizes. Test scrolling down and back up, all links, keyboard focus, and reduced motion. Capture screenshots in `screenshots/` for desktop, mobile, and at least three different workflow scroll positions; open and inspect the captures.
4. If browser automation is available inside this sandbox, add/run a small focused browser check for responsive overflow, key links, reduced motion, and the changing scroll sequence. Do not modify anything outside this folder to set up tooling.
5. Finish with a brief handoff: files changed, how to run it, checks performed, screenshot paths, and any limitation.
