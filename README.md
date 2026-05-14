# Pedigree Studio

**A fully offline, browser-based clinical pedigree drawing tool.**

No installation. No internet. No data leaves your device.

🔗 **[Launch Pedigree Studio](https://comparativechrono.github.io/PedigreeStudio/)**

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

Pedigree Studio removes all of these barriers. The entire application is a single file under 100 KB with zero external dependencies.

---

## Features

### Pedigree symbols
- **Sex**: square (male), circle (female), diamond (unknown)
- **Miscarriage/SAb**: triangle with optional sex label
- **Affected status**: solid fill or quartered fill from a 10-colour palette
- **Deceased**: diagonal line through symbol
- **Proband**: arrow indicator
- **Centre symbols**: S (multiple individuals) or P (pregnancy)

### Relationships
- **Partnership lines** between individuals
- **Consanguinity**: double partnership line
- **Separation/divorce**: crossed partnership line
- **Child connections**: right-angle descent lines from partnership midpoint
- **Identical twins**: V-shaped lines with horizontal connecting bar
- **Non-identical twins**: V-shaped lines without bar

### Annotation and labelling
- **Text annotations** below each person (diagnoses, ages, genotypes) with automatic left/right positioning
- **Free text labels** placeable anywhere on the canvas
- **Colour key/legend**: draggable, with editable labels for each colour in use
- **Automatic generation numbering** (Roman numeral + Arabic) with intelligent repositioning around descent lines

### Interaction
- **Drag and drop** positioning on an infinite pannable, zoomable canvas
- **Group movement**: connected family members move together by default
- **Multi-select**: rubber-band selection or Shift+click
- **Touch support**: fully responsive on tablets and phones
- **Partnership type cycling**: click an existing partnership line to change between normal, consanguineous, and separated

### Data and export
- **PNG export** at 2× resolution for clinical reports and publications
- **JSON session save/load** for archival, transfer, and later editing
- **Auto-save** to browser localStorage between sessions
- **Zero network requests**: all data stays on the local device, always

---

## Getting started

### Option 1: Use online (still runs locally)
Visit **[comparativechrono.github.io/PedigreeStudio](https://comparativechrono.github.io/PedigreeStudio/)**. The page loads once and then runs entirely in your browser — you can disconnect from the internet and it will continue to work.

### Option 2: Download and use offline
1. Download the HTML file from this repository
2. Open it in any modern browser (Chrome, Firefox, Safari, Edge)
3. That's it. No build step, no dependencies, no configuration.

You can copy the file to a USB drive, email it, upload it to a shared drive, or distribute it however you like.

---

## How to use

### Adding people
Select a shape (male, female, unknown, or miscarriage) in the side panel and click **Add Person**. The person appears on the canvas and can be dragged into position.

### Drawing relationships
1. Select the **Partner** tool and click two people to draw a partnership line
2. Select the **Child** tool, click a partnership line, then click a person to connect them as a child
3. Select the **Twin** tool and click two children of the same partnership to link them as twins

### Editing properties
Click on a person to select them. The properties panel shows options for annotation text, deceased status, proband designation, centre symbol (S/P), fill mode and colour, and shape changes.

### Changing partnership type
Click an existing partnership line while in **Move** mode to select it. Use the **Partnership Type** buttons in the panel to switch between Normal, Consanguineous, and Separated. You'll also be offered the option to delete the partnership.

### Exporting
- **Export Image**: saves a PNG of the pedigree
- **Save Session**: exports a JSON file you can reload later
- **Load Session**: imports a previously saved JSON file

---

## Technical details

- **Single file**: HTML + CSS + JavaScript, no external dependencies
- **Size**: ~95 KB
- **Rendering**: DOM elements for persons, SVG for connection lines, Canvas API for image export
- **Storage**: browser localStorage (never transmitted)
- **Fonts**: system font stack only — no web font downloads
- **Compatibility**: any modern browser on any operating system

---

## Privacy

Pedigree Studio makes **zero network requests**. No analytics, no tracking, no telemetry, no CDN calls, no font downloads. When you open the file from your local disk, the browser has no reason to contact any server at all.

All pedigree data is stored in your browser's localStorage, which is a local-only storage mechanism that is never shared with any website or server. When you export a session or image, the file is generated entirely on your device.

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
