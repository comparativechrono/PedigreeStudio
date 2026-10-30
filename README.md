# Pedigree Studio

**A fully offline, browser-based clinical pedigree drawing tool.**

No installation needed. No internet needed. No data leaves your device.

🔗 **[Launch Pedigree Studio](https://pedigreestudio.xyz)**

---

## What is this?

Pedigree Studio is a single HTML file that lets you draw standardised clinical genetics pedigrees directly in your web browser. It was designed for settings where existing tools don't work — prisons, rural clinics, home visits, low-resource environments, or anywhere that patient data shouldn't be sent to a third-party server.

Open the file. Draw a pedigree. Export it. That's it.

---

## Why?

Most pedigree software needs internet access, a server, an institutional licence, or all three. That's fine in a hospital genetics department, but it doesn't help if you're:

- **Taking a family history in a correctional facility** where internet-connected devices aren't permitted
- **Running a genetics clinic in a low- or middle-income country** where commercial subscriptions are unaffordable and connectivity is unreliable
- **Conducting a home visit** with no access to institutional networks
- **Working under strict data governance** (GDPR, HIPAA) where transmitting patient-identifiable family data to external servers is problematic
- **Teaching genetics students** who need to practise pedigree construction without accounts or IT setup

Pedigree Studio removes all of these barriers. The entire application is a single file of about 485 KB with no external dependencies.

---

## Features

### Pedigree symbols
- **Sex**: square (male), circle (female), diamond (unknown or not stated)
- **Pregnancy loss**: triangle, with the sex if known
- **Affected status**: shading in a solid colour, halves, quarters or a pattern, from a 10-colour palette or any colour you type
- **Deceased**: diagonal line through the symbol
- **Proband**: arrow
- **Inside the symbol**: a dot for a carrier, a vertical line for a presymptomatic carrier, P for a pregnancy, D for a donor, S for a surrogate, or a number (or n) for several people
- **Adoption**: brackets, with a dashed line of descent to the adoptive parents
- **No children and infertility**: one or two bars below the couple

### Relationships
- **Partnership lines** between individuals
- **Consanguinity**: double partnership line, drawn automatically when the partners share an ancestor in the pedigree
- **Separation/divorce**: crossed partnership line
- **Child connections**: right-angle descent lines from partnership midpoint
- **Partner lines over people**: when a partner line would pass behind someone (a person with three or more partners), it is drawn up and over them
- **Identical twins**: V-shaped lines with horizontal connecting bar
- **Non-identical twins**: V-shaped lines without bar

### Annotation and labelling
- **Text annotations** below each person (diagnoses, ages, genotypes) with automatic left/right positioning
- **Free text labels** placeable anywhere on the canvas
- **Colour key/legend**: draggable, with editable labels for each colour in use; a long label widens the key or wraps onto more lines, as you choose
- **Automatic generation numbering** (Roman numeral + Arabic) with intelligent repositioning around descent lines

### Interaction
- **Toolbar** with every tool named: add people, connect them, select, draw, undo and redo, the colour key, Tidy, and a File menu for export and settings
- **Add a relative**: with someone selected, add a partner, son, daughter, parents, brother or sister in one click, already joined up, with the pedigree laid out again to make room
- **Birth order**: move someone older or younger along their row of brothers and sisters
- **Couples**: click a relationship line to make it consanguineous or separated, or to add the couple's children (including a pregnancy loss, no children or infertility)
- **Drag and drop** positioning on an infinite pannable, zoomable canvas
- **Group movement**: connected family members move together by default
- **Multi-select**: Shift+click, or Ctrl+A for everyone
- **Touch support**: works on tablets and phones; on a phone the panel becomes a sheet along the bottom of the screen
- **Help**: the ? button (or the ? key) opens a guide with the symbol table, keyboard shortcuts and the references for the nomenclature
- **Tidy**: lays the whole pedigree out again in one go: generations in rows, partners side by side, brothers and sisters together under their parents in the order you drew them, and as few crossing lines as possible. It copes with partners from different generations, people with several partners, children with two sets of parents, large sibships and free-position people (who stay where you put them). Undo puts the previous drawing back

### Data and export
- **PNG export** at 2× resolution for clinical reports and publications
- **SVG export** for documents and posters
- **Pedigree files** (.json) to save, share and open again later; files saved by earlier versions open unchanged
- **Auto-save** to browser localStorage between sessions
- **Zero network requests**: all data stays on the local device, always

---

## Getting started

### Option 1: Use it online, or install it
Visit **[pedigreestudio.xyz](https://pedigreestudio.xyz)**. The page runs entirely in your browser, and once it has been opened the browser keeps a copy, so it opens again without a connection. To keep it as an app, install it from the browser: **Install** in Chrome or Edge, **Add to Home Screen** in Safari on an iPhone or iPad, or in Chrome on Android. Whenever it opens with a connection, it takes the newest version.

### Option 2: Download and use offline
1. Download the HTML file (`index.html`) from this repository
2. Open it in a browser from 2020 or later: Chrome or Edge 80, Firefox 75, Safari 13.1 (iOS 13.4) or Samsung Internet 13, or anything newer
3. That's it. No build step, no dependencies, no configuration.

You can copy the file to a USB drive, email it, upload it to a shared drive, or distribute it however you like.

---

## How to use

### Adding people
Click **Male**, **Female**, **Unknown** or **Loss** on the toolbar; **More** has the adoption symbols, no children, infertility and text labels. The new person is selected, and the selection panel offers **Add a relative**: a partner, son, daughter, parents, brother or sister, each joined up as it is added. The pedigree is laid out again each time to make room, and **Undo** takes the whole step back.

### Drawing relationships yourself
1. **Partners**: click two people
2. **Child**: click a relationship line, then the child
3. **Twins**: choose identical or non-identical in the panel, then click two children of the same couple

### Editing
Click a person to open their panel: notes under the symbol, deceased, proband, shading, the mark inside the symbol, and the symbol itself. Click a relationship line to make it consanguineous or separated, or to add a child of the couple. Click a line of descent to dash it for adoption.

### Tidy
**Tidy** on the toolbar lays the whole pedigree out again. **Undo** puts your own layout back.

### Saving and exporting
Under **File**: **Picture (PNG)**, **Vector (SVG)**, and **Save** and **Open** for pedigree files. Numbering, how people move when dragged, spacing, and whether long entries in the key widen it or wrap are set there too.

### Help
The **?** button opens the help: getting started, the table of symbols with how to draw each one, keyboard shortcuts, and the references for the nomenclature.

---

## Technical details

- **Single file**: HTML + CSS + JavaScript, no external dependencies
- **Size**: about 485 KB (116 KB compressed)
- **Rendering**: DOM elements for persons, SVG for connection lines, Canvas API for image export
- **Storage**: browser localStorage (never transmitted)
- **Fonts**: system font stack only — no web font downloads
- **Compatibility**: browsers from 2020 onwards on any operating system: Chrome and Edge 80, Firefox 75, Safari 13.1 (iOS 13.4), Samsung Internet 13 and later. This is worked out from MDN's browser compatibility data for everything the page uses, and the Studio has been run in Chromium 80, Firefox 75 and a current Chromium; it has not been tested in Safari
- **Offline install** (the website only): `manifest.webmanifest`, `sw.js` and the icons let the copy at pedigreestudio.xyz be installed and opened without a connection. `index.html` does not need them, and does not use them when opened from a file
- **Tests**: `tests/layout/` holds the test pedigrees and scripts used to check Tidy (see its README), `tests/interface/check.py` clicks through the toolbar, the panel and the help, `tests/security/check.py` opens a hostile pedigree file to check that it can neither run code nor reach the network, and `tests/offline/check.py` serves the website locally to check installing, opening without a connection and updating; none of them is needed to run the Studio

---

## Privacy

The Studio's page makes **no network requests** of its own. No analytics, no tracking, no telemetry, no CDN calls, no font downloads. When you open the file from your local disk, the browser has no reason to contact any server at all. When you use the copy at pedigreestudio.xyz, the browser fetches the Studio from there, keeps a copy so that it opens offline, and asks the site for a newer copy each time it opens; those requests fetch only the Studio's own files and carry nothing you have drawn (`tests/offline/check.py` checks that drawing, exporting and saving send nothing).

All pedigree data is stored in your browser's localStorage, which is a local-only storage mechanism that is never shared with any website or server. When you export a session or image, the file is generated entirely on your device. If you open the Studio from your disk, though, the browser keeps one such store for every page opened from disk, so another web page saved on the same computer and opened in the same browser could read it. On a shared computer, clear the canvas and close the tab when you have finished.

A pedigree file someone has sent you is safe to open. The Studio keeps only what a drawing can hold: text stays text, colours must be colours and numbers must be numbers, and it shows text as text. So a file cannot add anything to the page, run code in it or make it fetch anything, and an SVG exported from it cannot either. As a second guard, the page's Content Security Policy tells the browser not to let it load anything or send any request. A policy cannot stop a page from going to another address, so it is the checking and escaping that keep a family's data in. `tests/security/check.py` checks this with a deliberately hostile file.

This architecture was a deliberate design choice for clinical environments where patient-identifiable data must not leave the device.

---

## Citation

If you use Pedigree Studio in academic work, a manuscript describing the tool is in preparation. In the meantime, please cite the repository:

```
Pedigree Studio [Software]. Available at: https://comparativechrono.github.io/PedigreeStudio/
```

---

## Contributing

Issues and pull requests are welcome. The entire application is in a single HTML file, which makes it straightforward to read and modify.

---

## Licence

[To be specified]
