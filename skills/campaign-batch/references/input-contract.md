# Campaign input contract · v0.1

Use assets/demo.json as the executable example. No remote assets or model API calls occur.

`brand`: name; six-digit background/ink/accent colours; optional local raster logo; optional font_regular/font_bold font paths (TTF/OTF/TTC first face). System font discovery is a convenience, not a portable font bundle. Supply fonts with appropriate rights; do not redistribute proprietary fonts. SVG text needs matching installed fonts and is not a cross-machine pixel proof.

`events`: nonempty list; each needs id, locale, title, ISO date, IANA timezone, display time as HH:MM ZONE (validated against the date and IANA zone), location, cta. Literal strings are preserved. Id and locale are filename-safe slugs; the pair is unique. Optional edition, category, subtitle, and exactly three labels customize headings. Supply translated strings explicitly; no automatic language/date conversion occurs.

`family`: editorial, signal or ticket. Editorial uses a narrow visual sidebar, signal a full-width lower visual, and ticket a date badge with an admission strip. Signal reverses background/ink. Choose by content: ticket emphasizes dates, signal short headlines, editorial longer title-led announcements. A photo needing a tall frame is poorly suited to ticket's short strip. `image`: local PNG/JPEG/WebP replaces the motif. `focus`: normalized [x,y]; `protect`: normalized [left,top,right,bottom]. A region outside the cover crop triggers contain. There is no subject detector. EXIF orientation applies first.

Working sizes, not current platform-compliance claims: square 1080×1080, portrait 1080×1350, wide 1920×1080. New platform profiles need current official requirements.

Missing glyphs/over-capacity text fail the item. Invalid configuration stops before rendering. Mixed valid/invalid content writes successful files and failed-item report, then exits 2. Check exit code and report; a partial batch is not complete. Empty output directories prevent stale exports masquerading as current files.
