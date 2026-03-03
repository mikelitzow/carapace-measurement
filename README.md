# CrabMeasure

Desktop app for measuring crab carapace traits from microscope images.
Replaces Image-Pro with a click-through napari workflow suitable for non-technical users.

## Measurements produced (mm)

| Column | Description |
|--------|-------------|
| CW | Carapace width (widest L/R margins) |
| CL | Carapace length (posterior → anterior) |
| RW | Rostrum base width |
| OW | Orbital spine width |
| SL | First lateral spine length (base → tip) |

See [MEASUREMENT_SPEC.md](MEASUREMENT_SPEC.md) for the full click protocol.

---

## Installation (from source)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

Tested with Python 3.10–3.12.

---

## Running from source

```bash
# From the repo root:
python -m src.app

# Or equivalently:
python src/app.py
```

On first launch a **Demo Mode** button will appear if `data/examples/` contains `.tif` files.

---

## Workflow

1. **Open Folder** – pick a folder that contains:
   - One calibration image whose filename includes `micrometer` (e.g. `2mm micrometer.tif`).
   - Any number of carapace images.
2. **Scale calibration** – computed automatically from the micrometer image.
   If auto-detection fails a prompt will ask you to click both ends of the scale bar.
3. **Measure each image** – the checklist on the right guides you through 10 clicks
   (or 12 if `sl_mode = BOTH`).  Completed pairs are drawn as coloured lines.
4. **Next / Back / Clear** – navigate between images or redo clicks.
5. **Autosave** – `outputs/measurements.csv` is written after every image.
   `outputs/qc_overlays/<name>_qc.png` shows annotated overlays for QC.
6. **Resume** – re-opening the same folder resumes where you left off
   (progress stored in `outputs/progress.json`).

### Configuration

Edit `config.yaml` (project root) to change defaults:

```yaml
bar_length_mm: 2.0          # known scale-bar length in mm
micrometer_keyword: micrometer   # filename substring for the calibration image
sl_mode: LEFT               # LEFT | RIGHT | BOTH
```

Settings can also be changed at runtime via the **Settings…** button.

---

## Building a standalone app (PyInstaller)

```bash
pip install pyinstaller
pyinstaller build.spec
```

The distributable folder is created at `dist/CrabMeasure/`.

| OS | Launcher |
|----|----------|
| macOS | `dist/CrabMeasure/CrabMeasure` |
| Windows | `dist\CrabMeasure\CrabMeasure.exe` |

> **Note:** PyInstaller must be run on the same OS as the target platform
> (i.e. build on Windows to produce a Windows binary).

---

## Project layout

```
carapace-measurement/
├── src/
│   ├── app.py          # napari UI entry point
│   ├── config.py       # YAML config loader
│   ├── pipeline.py     # scale-bar detection + segmentation
│   └── measures.py     # distance maths + QC overlay
├── data/
│   └── examples/       # sample TIFF images (demo mode)
├── config.yaml         # user-editable defaults
├── build.spec          # PyInstaller build spec
├── requirements.txt
└── MEASUREMENT_SPEC.md
```

## Output files

```
<input_folder>/
└── outputs/
    ├── measurements.csv        # one row per image
    ├── progress.json           # resume state
    └── qc_overlays/
        └── <stem>_qc.png       # annotated overlay per image
```
