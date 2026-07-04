# Photo Credits

The `evidence_photo_*.jpg` files in each case folder are real, freely-licensed
photographs (not illustrations), sourced via [Openverse](https://openverse.org)
and [Wikimedia Commons](https://commons.wikimedia.org), with a forensic-style
case/location caption composited on top. All source licenses permit reuse and
derivative works (CC BY, CC BY-SA, CC0, or Public Domain Mark).

None of these photos depict the actual fictional case events described in this
repo's sample text/PDF/CSV files — they are generic real-world photos chosen to
visually match each case's scene type (house exterior/entry, jewelry store,
warehouse, office), then annotated with our fictional case numbers.

| Case | File | Title | Creator | License | Source |
|---|---|---|---|---|---|
| case-01-millbrook-heights | evidence_photo_01.jpg | circle of life | *Brightburn* | CC BY 2.0 | flickr.com/photos/34116579@N04/5722542877 |
| case-01-millbrook-heights | evidence_photo_02.jpg | Antique wooden door | prague.czech.photo | CC BY 2.0 | flickr.com/photos/99424477@N04/11803203285 |
| case-01-millbrook-heights | evidence_photo_03.jpg | Farm house at Night, low light | Otto Phokus | CC BY-SA 2.0 | flickr.com/photos/28429505@N05/3934731956 |
| case-01-millbrook-heights | evidence_photo_04.jpg | 20180924-OSEC-LSC-0943 | USDAgov | Public Domain Mark | flickr.com/photos/41284017@N08/44208171934 |
| case-02-riverside-view | evidence_photo_01.jpg | (residential backyard, daytime) | — | CC BY / CC0 | Openverse (flickr) |
| case-02-riverside-view | evidence_photo_02.jpg | (broken house window) | — | CC BY / CC0 | Openverse (flickr) |
| case-02-riverside-view | evidence_photo_03.jpg | (teal house, porch) | — | CC BY / CC0 | Openverse (flickr) |
| case-02-riverside-view | evidence_photo_04.jpg | (brick semi-detached house, street) | — | CC BY / CC0 | Openverse (flickr) |
| case-03-oakdale-jewelry | evidence_photo_01.jpg | (jewelry store window display) | — | CC BY / CC0 | Openverse (flickr) |
| case-03-oakdale-jewelry | evidence_photo_02.jpg | (broken windows, brick building) | — | CC BY / CC0 | Openverse (flickr) |
| case-03-oakdale-jewelry | evidence_photo_03.jpg | Interior of Sophies Silver jewelry store at Sankt Hansgatan 34, Visby, Sweden | Wikimedia Commons contributor | CC BY-SA 4.0 | commons.wikimedia.org/wiki/File:Interior_of_Sophies_Silver_jewelry_store_at_Sankt_Hansgatan_34,_Visby,_Sweden_3.jpg |
| case-03-oakdale-jewelry | evidence_photo_04.jpg | (daytime storefront street) | — | CC BY / CC0 | Openverse (flickr) |
| case-04-lakeside-arson | evidence_photo_01.jpg | Alexandra Warehouse - Gloucester Docks | — | CC BY-SA | Openverse (flickr) |
| case-04-lakeside-arson | evidence_photo_02.jpg | Hole in the wall | — | CC BY | Openverse (flickr) |
| case-04-lakeside-arson | evidence_photo_03.jpg | Fire damages EA warehouse | — | CC BY | Openverse (flickr) |
| case-04-lakeside-arson | evidence_photo_04.jpg | Warehouse loading dock exterior view | — | CC0 | rawpixel/Openverse |
| case-05-harborview-fraud | evidence_photo_01.jpg | February 5, 2010 - Paperwork | — | CC BY-SA | Openverse (flickr) |
| case-05-harborview-fraud | evidence_photo_02.jpg | arne jacobsen, national bank, copenhagen, 1961-1978 | — | CC BY | Openverse (flickr) |
| case-05-harborview-fraud | evidence_photo_03.jpg | Office cubicle, circa 2001 | — | CC BY | Openverse (flickr) |
| case-05-harborview-fraud | evidence_photo_04.jpg | Clean desk policy | — | CC BY | Openverse (flickr) |

Some Flickr-sourced titles/creators for case-02 were not retained during
generation (the working manifest was cleaned up as scratch data). All were
filtered to CC BY / CC BY-SA / CC0 / Public Domain Mark only, so reuse in this
non-commercial demo/hackathon repo is permitted; if in doubt, drop or replace
the file rather than assume broader rights. Case-04 and case-05 photos were
re-picked to actually match each case's scene type (fire damage/warehouse for
the arson case, office/paperwork for the white-collar fraud case, instead of
generic burglary-style shots).

## Video clips

`cctv_clip_*.mp4` in each case folder use that case's own `evidence_photo_01.jpg`
(the real, licensed photo above) as the camera's background plate, with a
simple animated silhouette, night-vision tint, scanlines, grain, and a
timestamp/camera-ID burn-in composited on top — so the backdrop is genuine
photography rather than a fully synthetic scene. The moving figure itself is
intentionally a simple illustrated silhouette, not real footage: actual
CCTV recordings of real break-ins/fires are not something we can ethically or
legally source for a fictional demo dataset.

## Audio

`audio_statement_*.wav` files are real synthesized speech (macOS `say`) run
through processing that simulates how the recording was captured — light
room reverb for in-person interviews, telephone bandpass filtering for phone
statements, and lower-fidelity bandpass + hiss for anonymous tip-line calls —
rather than a single clean, dry TTS render.
