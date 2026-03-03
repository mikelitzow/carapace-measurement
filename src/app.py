"""CrabMeasure – napari-based carapace measurement application."""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

# Make the project root importable regardless of how this module is invoked.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import cv2
import napari
import numpy as np
import pandas as pd
import tifffile
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.config import Config, load_config, save_config
from src.measures import compute_measurements, save_qc_overlay
from src.pipeline import (
    auto_landmarks,
    estimate_px_per_mm_from_micrometer,
    segment_carapace,
)

# ── Constants ──────────────────────────────────────────────────────────────────

DEMO_DIR   = _ROOT / "data" / "examples"
IMAGE_EXTS = {".tif", ".tiff", ".png"}

# Click protocol: (point_name, human_readable_description)
CLICK_PROTOCOL_BASE = [
    ("CW_L",  "CW: Left margin (widest point)"),
    ("CW_R",  "CW: Right margin (widest point)"),
    ("CL_P",  "CL: Posterior margin point"),
    ("CL_A",  "CL: Anterior reference point"),
    ("RW_L",  "RW: Left rostrum base corner"),
    ("RW_R",  "RW: Right rostrum base corner"),
    ("OW_L",  "OW: Left orbital spine tip"),
    ("OW_R",  "OW: Right orbital spine tip"),
    ("SL_B",  "SL: Spine base"),
    ("SL_T",  "SL: Spine tip"),
]
CLICK_PROTOCOL_BOTH = CLICK_PROTOCOL_BASE + [
    ("SL_B2", "SL2: 2nd spine base (other side)"),
    ("SL_T2", "SL2: 2nd spine tip (other side)"),
]

# Colour used for auto-detected points (gold = visually distinct from all measurement colours)
_AUTO_COLOR = "gold"

# napari colour per point name
_PT_COLOR = {
    "CW_L": "limegreen",    "CW_R": "limegreen",
    "CL_P": "orange",       "CL_A": "orange",
    "RW_L": "dodgerblue",   "RW_R": "dodgerblue",
    "OW_L": "violet",       "OW_R": "violet",
    "SL_B": "cyan",         "SL_T": "cyan",
    "SL_B2": "aquamarine",  "SL_T2": "aquamarine",
}

# Lines to draw between paired points (napari colour strings)
_LINE_PAIRS = [
    ("CW_L", "CW_R",   "limegreen"),
    ("CL_P", "CL_A",   "orange"),
    ("RW_L", "RW_R",   "dodgerblue"),
    ("OW_L", "OW_R",   "violet"),
    ("SL_B", "SL_T",   "cyan"),
    ("SL_B2", "SL_T2", "aquamarine"),
]

# Canonical CSV column order (extras appended)
_CSV_COLS = ["file", "px_per_mm", "CW_mm", "CL_mm", "RW_mm", "OW_mm",
             "SL_mm", "SL_L_mm", "SL_R_mm"]


# ── Image loading ──────────────────────────────────────────────────────────────

def _load_image(path: Path) -> np.ndarray:
    """Load TIFF or PNG; return (H, W, 3) uint8 **RGB** array."""
    img = None
    try:
        raw = tifffile.imread(str(path))
        if raw is not None:
            img = raw
    except Exception:
        pass

    if img is None:
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is not None and img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if img is None:
        raise ValueError(f"Cannot load image: {path}")

    # Normalise to uint8
    if img.dtype != np.uint8:
        lo, hi = float(img.min()), float(img.max())
        if hi > lo:
            img = ((img.astype(np.float64) - lo) / (hi - lo) * 255).astype(np.uint8)
        else:
            img = np.zeros_like(img, dtype=np.uint8)

    # Ensure exactly 3 channels (RGB)
    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    elif img.ndim == 3 and img.shape[2] == 1:
        img = np.concatenate([img, img, img], axis=-1)
    elif img.ndim == 3 and img.shape[2] == 4:
        img = img[:, :, :3]
    elif img.ndim == 3 and img.shape[2] > 4:
        img = img[:, :, :3]

    return img  # RGB


# ── CSV helper ─────────────────────────────────────────────────────────────────

def _save_csv(rows: list[dict], path: Path) -> None:
    df = pd.DataFrame(rows)
    ordered = [c for c in _CSV_COLS if c in df.columns]
    extra   = [c for c in df.columns if c not in ordered]
    df[ordered + extra].to_csv(path, index=False)


# ── Main application controller ────────────────────────────────────────────────

class CrabMeasureApp:
    def __init__(self) -> None:
        self.cfg = load_config()

        # Session state
        self.folder: Path | None         = None
        self.carapace_images: list[Path] = []
        self.current_idx: int            = 0
        self.px_per_mm: float            = 0.0

        # Per-image click state: point_name -> (row, col)
        self.clicks: dict[str, tuple]    = {}
        self.protocol: list[tuple[str, str]] = []

        # Persisted progress
        self.all_rows: list[dict]         = []
        self.completed_files: set[str]    = set()
        self.progress_file: Path | None   = None
        self.csv_path: Path | None        = None

        # napari layer references
        self.viewer: napari.Viewer | None = None
        self._img_layer    = None
        self._seg_layer    = None
        self._pts_layer    = None
        self._shapes_layer = None
        self._prev_n_pts: int = 0

        # Names of clicks that were placed automatically (not by the user)
        self._auto_clicks: set[str] = set()

        self._panel: "ControlPanel | None" = None

    # ── Launch ────────────────────────────────────────────────────────────────

    def run(self) -> None:
        warnings.filterwarnings("ignore")
        self.viewer = napari.Viewer(title="CrabMeasure")
        self._panel = ControlPanel(self)
        self.viewer.window.add_dock_widget(
            self._panel, area="right", name="CrabMeasure Controls"
        )

        demo_ready = DEMO_DIR.exists() and any(DEMO_DIR.glob("*.tif"))
        if demo_ready:
            self._panel.set_status(
                "Demo images found in data/examples/.\n"
                "Click 'Demo Mode' to start, or 'Open Folder' for your own images."
            )
        else:
            self._panel.set_status("Click 'Open Folder' to begin.")

        napari.run()

    # ── Folder / session setup ────────────────────────────────────────────────

    def open_folder(self, folder: Path | None = None) -> None:
        if folder is None:
            dlg = QFileDialog()
            dlg.setFileMode(QFileDialog.Directory)
            dlg.setOption(QFileDialog.ShowDirsOnly, True)
            if dlg.exec_():
                folder = Path(dlg.selectedFiles()[0])
            else:
                return

        self.folder = folder
        all_imgs = sorted(p for p in folder.iterdir()
                          if p.suffix.lower() in IMAGE_EXTS)

        kw = self.cfg.micrometer_keyword.lower()
        micro_imgs    = [p for p in all_imgs if kw in p.name.lower()]
        carapace_imgs = [p for p in all_imgs if kw not in p.name.lower()]

        if not micro_imgs:
            QMessageBox.warning(
                None, "No micrometer image",
                f"No image with '{kw}' in its filename was found.\n"
                "Add a calibration image or change the keyword in Settings.",
            )
            return

        # Prepare output directories
        out_dir = folder / "outputs"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "qc_overlays").mkdir(exist_ok=True)
        self.csv_path      = out_dir / "measurements.csv"
        self.progress_file = out_dir / "progress.json"

        # Load existing progress and offer to resume
        self.completed_files = set()
        self.all_rows        = []
        self.px_per_mm       = 0.0
        if self.progress_file.exists():
            try:
                with open(self.progress_file) as fh:
                    prog = json.load(fh)
                n_done = len(prog.get("completed", []))
                if n_done:
                    ans = QMessageBox.question(
                        None, "Resume session?",
                        f"Found progress: {n_done} image(s) already measured.\n"
                        "Resume from where you left off?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if ans == QMessageBox.Yes:
                        self.completed_files = set(prog.get("completed", []))
                        self.all_rows        = prog.get("measurements", [])
                        self.px_per_mm       = prog.get("px_per_mm", 0.0)
            except Exception:
                pass

        # Auto-calibrate
        if self.px_per_mm <= 0:
            self._panel.set_status("Computing scale calibration…")
            for mp in micro_imgs:
                try:
                    img_rgb = _load_image(mp)
                    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                    self.px_per_mm = estimate_px_per_mm_from_micrometer(
                        img_bgr, self.cfg.bar_length_mm
                    )
                    self._panel.set_status(
                        f"Scale: {self.px_per_mm:.2f} px/mm  ({mp.name})"
                    )
                    break
                except Exception:
                    pass

        if self.px_per_mm <= 0:
            self._run_manual_calibration(micro_imgs[0], carapace_imgs)
            return  # will continue via callback

        self._start_session(carapace_imgs)

    def _run_manual_calibration(
        self, micro_path: Path, carapace_imgs: list[Path]
    ) -> None:
        """Show micrometer image; user clicks bar endpoints, then confirms."""
        img_rgb = _load_image(micro_path)
        self.viewer.layers.clear()
        self.viewer.add_image(img_rgb, name=micro_path.stem)

        pts = self.viewer.add_points(
            name="Scale bar – click BOTH ends",
            size=14, face_color="red", ndim=2,
        )
        pts.mode = "add"
        self._panel.set_status(
            f"MANUAL CALIBRATION\n"
            f"Click BOTH ENDS of the {self.cfg.bar_length_mm:.1f} mm scale bar,\n"
            "then click 'Confirm Calibration'."
        )
        self._panel.show_calibration_button(True)

        def _confirm() -> None:
            if len(pts.data) < 2:
                QMessageBox.warning(
                    None, "Need 2 points",
                    "Please click both ends of the scale bar first."
                )
                return
            p1, p2 = pts.data[0], pts.data[1]
            self.px_per_mm = float(
                np.linalg.norm(p2 - p1) / self.cfg.bar_length_mm
            )
            self._panel.show_calibration_button(False)
            self._panel.set_status(
                f"Manual calibration: {self.px_per_mm:.2f} px/mm"
            )
            self._start_session(carapace_imgs)

        self._panel._calibration_cb = _confirm

    def _start_session(self, carapace_imgs: list[Path]) -> None:
        self.carapace_images = carapace_imgs
        self.protocol = (
            CLICK_PROTOCOL_BOTH if self.cfg.sl_mode == "BOTH"
            else CLICK_PROTOCOL_BASE
        )

        remaining = [p for p in carapace_imgs if p.name not in self.completed_files]
        if not remaining:
            QMessageBox.information(
                None, "All done!",
                f"All images in this folder are already measured.\n\n"
                f"Results: {self.csv_path}",
            )
            return

        self.current_idx = next(
            i for i, p in enumerate(self.carapace_images)
            if p.name not in self.completed_files
        )
        self._panel.update_panel()
        self._load_current_image()

    # ── Image display ─────────────────────────────────────────────────────────

    def _load_current_image(self) -> None:
        if self.current_idx >= len(self.carapace_images):
            self._show_completion()
            return

        img_path = self.carapace_images[self.current_idx]
        self._panel.set_status(f"Loading {img_path.name}…")
        self.clicks       = {}
        self._prev_n_pts  = 0

        img_rgb = _load_image(img_path)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        try:
            mask = segment_carapace(img_bgr)
        except Exception:
            mask = np.zeros(img_rgb.shape[:2], dtype=np.uint8)

        # Rebuild all layers from scratch
        self.viewer.layers.clear()

        self._img_layer = self.viewer.add_image(img_rgb, name=img_path.stem)

        labeled = (mask > 0).astype(np.int32)
        self._seg_layer = self.viewer.add_labels(
            labeled, name="Segmentation", opacity=0.25
        )

        self._shapes_layer = self.viewer.add_shapes(name="Lines", ndim=2)

        self._pts_layer = self.viewer.add_points(
            name="Measurements", size=14, face_color="red", ndim=2
        )
        self._pts_layer.mode = "add"
        self._pts_layer.events.data.connect(self._on_pts_data_changed)

        # ── Auto-detect CW and CL ──────────────────────────────────────────────
        self._auto_clicks = set()
        try:
            auto = auto_landmarks(mask)
            initial_pts: list[list[float]] = []
            for name, _ in self.protocol:
                if name in auto:
                    r, c = auto[name]
                    self.clicks[name] = (r, c)
                    self._auto_clicks.add(name)
                    initial_pts.append([float(r), float(c)])
                else:
                    break   # stop at first gap – keeps protocol order intact
            if initial_pts:
                # Set _prev_n_pts BEFORE writing .data so the event is a no-op
                self._prev_n_pts = len(initial_pts)
                self._pts_layer.data = np.array(initial_pts, dtype=float)
                self._refresh_point_visuals()
                self._update_lines()
        except Exception:
            pass   # auto-detection failure is non-fatal

        self.viewer.reset_view()
        self._panel.update_panel()

        # Build status message
        auto_groups = []
        if "CW_L" in self._auto_clicks and "CW_R" in self._auto_clicks:
            auto_groups.append("CW")
        if "CL_P" in self._auto_clicks and "CL_A" in self._auto_clicks:
            auto_groups.append("CL")
        n_remain = len(self.protocol) - len(self._auto_clicks)
        if auto_groups:
            self._panel.set_status(
                f"Image {self.current_idx + 1}/{len(self.carapace_images)}: "
                f"{img_path.name}\n"
                f"Auto-detected: {' + '.join(auto_groups)} (gold). "
                f"{n_remain} click{'s' if n_remain != 1 else ''} remaining."
            )
        else:
            self._panel.set_status(
                f"Image {self.current_idx + 1} / {len(self.carapace_images)}:  "
                f"{img_path.name}"
            )

    # ── Click capture ─────────────────────────────────────────────────────────

    def _on_pts_data_changed(self, event=None) -> None:
        if self._pts_layer is None:
            return
        n = len(self._pts_layer.data)
        if n <= self._prev_n_pts:
            return  # removal or no-op

        while self._prev_n_pts < n:
            step = self._prev_n_pts
            if step >= len(self.protocol):
                # Discard any click beyond the protocol length
                self._pts_layer.data = self._pts_layer.data[: len(self.protocol)]
                self._prev_n_pts = len(self.protocol)
                break
            name  = self.protocol[step][0]
            point = tuple(self._pts_layer.data[step].tolist())  # (row, col)
            self.clicks[name] = point
            self._prev_n_pts += 1

        self._refresh_point_visuals()
        self._update_lines()
        self._panel.update_panel()

        if len(self.clicks) == len(self.protocol):
            QTimer.singleShot(250, self._finish_current_image)

    def _refresh_point_visuals(self) -> None:
        if self._pts_layer is None or len(self._pts_layer.data) == 0:
            return

        n = len(self._pts_layer.data)
        colors = []
        labels = []
        for i in range(n):
            name = self.protocol[i][0] if i < len(self.protocol) else ""
            if name in self._auto_clicks:
                colors.append(_AUTO_COLOR)
            else:
                colors.append(_PT_COLOR.get(name, "red"))
            labels.append(name)
        try:
            self._pts_layer.face_color = colors
            self._pts_layer.text = {
                "string":      labels,
                "size":        10,
                "color":       "white",
                "translation": np.array([-18, 6]),
            }
            self._pts_layer.refresh()
        except Exception:
            pass

    def _update_lines(self) -> None:
        if self._shapes_layer is None:
            return

        # Clear existing lines
        try:
            n = len(self._shapes_layer.data)
            if n > 0:
                self._shapes_layer.selected_data = set(range(n))
                self._shapes_layer.remove_selected()
        except Exception:
            pass

        line_data, line_colors = [], []
        for k1, k2, color in _LINE_PAIRS:
            if k1 in self.clicks and k2 in self.clicks:
                r1, c1 = self.clicks[k1]
                r2, c2 = self.clicks[k2]
                line_data.append(np.array([[r1, c1], [r2, c2]]))
                line_colors.append(color)

        if line_data:
            try:
                self._shapes_layer.add(
                    line_data,
                    shape_type="line",
                    edge_color=line_colors,
                    edge_width=3,
                )
            except Exception:
                pass

    # ── Finish / save ─────────────────────────────────────────────────────────

    def _finish_current_image(self) -> None:
        if len(self.clicks) < len(self.protocol):
            return  # guard against premature trigger

        img_path     = self.carapace_images[self.current_idx]
        measurements = compute_measurements(self.clicks, self.px_per_mm, self.cfg.sl_mode)

        row = {
            "file":       img_path.name,
            "px_per_mm":  round(self.px_per_mm, 4),
            **{k: round(v, 4) for k, v in measurements.items()},
        }
        self.all_rows = [r for r in self.all_rows if r["file"] != img_path.name]
        self.all_rows.append(row)
        self.completed_files.add(img_path.name)

        _save_csv(self.all_rows, self.csv_path)

        try:
            img_bgr  = cv2.cvtColor(_load_image(img_path), cv2.COLOR_RGB2BGR)
            qc_path  = (
                self.folder / "outputs" / "qc_overlays" / f"{img_path.stem}_qc.png"
            )
            save_qc_overlay(img_bgr, self.clicks, measurements, qc_path)
        except Exception:
            pass

        self._save_progress()

        if self._pts_layer:
            self._pts_layer.mode = "pan_zoom"  # freeze – no accidental extra clicks

        mm = measurements
        self._panel.set_status(
            "Saved!\n"
            f"CW {mm.get('CW_mm', 0):.2f}  CL {mm.get('CL_mm', 0):.2f}  "
            f"RW {mm.get('RW_mm', 0):.2f}  OW {mm.get('OW_mm', 0):.2f}  "
            f"SL {mm.get('SL_mm', 0):.2f} mm\n"
            "Press Next to continue."
        )
        self._panel.update_panel()

    def _save_progress(self) -> None:
        if not self.progress_file:
            return
        try:
            with open(self.progress_file, "w") as fh:
                json.dump(
                    {
                        "folder":       str(self.folder),
                        "px_per_mm":    self.px_per_mm,
                        "completed":    list(self.completed_files),
                        "measurements": self.all_rows,
                    },
                    fh, indent=2,
                )
        except Exception:
            pass

    # ── Navigation ────────────────────────────────────────────────────────────

    def next_image(self) -> None:
        self.current_idx += 1
        # Skip over already-completed images
        while (
            self.current_idx < len(self.carapace_images)
            and self.carapace_images[self.current_idx].name in self.completed_files
        ):
            self.current_idx += 1

        if self.current_idx >= len(self.carapace_images):
            self._show_completion()
        else:
            self._load_current_image()

    def prev_image(self) -> None:
        if self.current_idx > 0:
            self.current_idx -= 1
        self._load_current_image()

    def clear_clicks(self) -> None:
        self.clicks = {}
        self._auto_clicks = set()
        if self._pts_layer is not None:
            try:
                self._pts_layer.data = np.empty((0, 2))
                self._pts_layer.mode = "add"
            except Exception:
                pass
            self._prev_n_pts = 0
        if self._shapes_layer is not None:
            try:
                n = len(self._shapes_layer.data)
                if n > 0:
                    self._shapes_layer.selected_data = set(range(n))
                    self._shapes_layer.remove_selected()
            except Exception:
                pass
        self._panel.update_panel()

    def _show_completion(self) -> None:
        n = len(self.all_rows)
        QMessageBox.information(
            None, "Session complete",
            f"All {n} image(s) measured!\n\nResults saved to:\n{self.csv_path}",
        )


# ── Control panel widget ───────────────────────────────────────────────────────

class ControlPanel(QWidget):
    def __init__(self, app: CrabMeasureApp) -> None:
        super().__init__()
        self.app = app
        self._calibration_cb = None
        self._build_ui()
        self.setMinimumWidth(240)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setSpacing(6)
        outer.setContentsMargins(4, 4, 4, 4)

        title = QLabel("CrabMeasure")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        outer.addWidget(title)

        # Session buttons
        sg = QGroupBox("Session")
        sl = QVBoxLayout(sg)
        self.btn_open     = QPushButton("Open Folder")
        self.btn_settings = QPushButton("Settings…")
        self.btn_open.clicked.connect(lambda: self.app.open_folder())
        self.btn_settings.clicked.connect(self._show_settings)
        sl.addWidget(self.btn_open)
        if DEMO_DIR.exists():
            self.btn_demo = QPushButton("Demo Mode")
            self.btn_demo.clicked.connect(lambda: self.app.open_folder(DEMO_DIR))
            sl.addWidget(self.btn_demo)
        sl.addWidget(self.btn_settings)
        outer.addWidget(sg)

        # Status label
        self.status_lbl = QLabel("Open a folder to begin.")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("font-size:11px; padding:4px;")
        outer.addWidget(self.status_lbl)

        # Manual-calibration confirm (hidden until needed)
        self.btn_confirm_cal = QPushButton("Confirm Calibration")
        self.btn_confirm_cal.setVisible(False)
        self.btn_confirm_cal.clicked.connect(self._do_confirm_cal)
        outer.addWidget(self.btn_confirm_cal)

        # Progress
        self.progress_lbl = QLabel("")
        self.progress_lbl.setAlignment(Qt.AlignCenter)
        self.progress_lbl.setStyleSheet("font-weight:bold;")
        outer.addWidget(self.progress_lbl)

        # Click-protocol checklist
        proto_group = QGroupBox("Click Protocol")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(270)
        inner = QWidget()
        self.proto_layout = QVBoxLayout(inner)
        self.proto_layout.setSpacing(1)
        scroll.setWidget(inner)
        QVBoxLayout(proto_group).addWidget(scroll)
        outer.addWidget(proto_group)

        # Navigation
        ng = QGroupBox("Navigation")
        nl = QVBoxLayout(ng)
        self.btn_next  = QPushButton("Next")
        self.btn_back  = QPushButton("Back")
        self.btn_clear = QPushButton("Clear Clicks")
        self.btn_next.clicked.connect(self.app.next_image)
        self.btn_back.clicked.connect(self.app.prev_image)
        self.btn_clear.clicked.connect(self.app.clear_clicks)
        nl.addWidget(self.btn_next)
        nl.addWidget(self.btn_back)
        nl.addWidget(self.btn_clear)
        outer.addWidget(ng)

        # Live measurements
        mg = QGroupBox("Measurements (mm)")
        ml = QVBoxLayout(mg)
        self.meas_lbl = QLabel("—")
        self.meas_lbl.setWordWrap(True)
        self.meas_lbl.setStyleSheet("font-family:monospace; font-size:11px;")
        ml.addWidget(self.meas_lbl)
        outer.addWidget(mg)

        outer.addStretch()

    # ── Panel helpers ──────────────────────────────────────────────────────────

    def set_status(self, msg: str) -> None:
        self.status_lbl.setText(msg)

    def show_calibration_button(self, show: bool) -> None:
        self.btn_confirm_cal.setVisible(show)

    def _do_confirm_cal(self) -> None:
        if self._calibration_cb:
            self._calibration_cb()

    def update_panel(self) -> None:
        app = self.app
        if not app.carapace_images:
            return

        n_total = len(app.carapace_images)
        n_done  = len(app.completed_files)
        self.progress_lbl.setText(
            f"Image {app.current_idx + 1} / {n_total}   ({n_done} done)"
        )

        # Rebuild checklist
        while self.proto_layout.count():
            item = self.proto_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        n_clicked = len(app.clicks)
        for i, (name, desc) in enumerate(app.protocol):
            done    = name in app.clicks
            is_auto = name in app._auto_clicks
            is_next = (i == n_clicked) and not done
            if done:
                if is_auto:
                    prefix, style = "✓A", "color:#FFC107; font-size:10px;"
                else:
                    prefix, style = "✓",  "color:#4caf50; font-size:10px;"
            elif is_next:
                prefix, style = "→", "color:#ffeb3b; font-weight:bold; font-size:10px;"
            else:
                prefix, style = "○", "color:#888; font-size:10px;"
            lbl = QLabel(f"{prefix} {desc}")
            lbl.setStyleSheet(style)
            self.proto_layout.addWidget(lbl)

        # Live measurement readout
        if app.clicks and app.px_per_mm > 0:
            try:
                meas  = compute_measurements(app.clicks, app.px_per_mm, app.cfg.sl_mode)
                lines = [f"{k:>10}: {v:6.2f}" for k, v in sorted(meas.items())]
                self.meas_lbl.setText("\n".join(lines) or "—")
            except Exception:
                self.meas_lbl.setText("—")
        else:
            self.meas_lbl.setText("—")

    def _show_settings(self) -> None:
        dlg = SettingsDialog(self.app.cfg, self)
        if dlg.exec_():
            self.app.cfg = dlg.get_config()
            save_config(self.app.cfg)
            self.app.protocol = (
                CLICK_PROTOCOL_BOTH if self.app.cfg.sl_mode == "BOTH"
                else CLICK_PROTOCOL_BASE
            )


# ── Settings dialog ────────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, cfg: Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CrabMeasure Settings")
        form = QFormLayout(self)

        self.bar_spin = QDoubleSpinBox()
        self.bar_spin.setRange(0.01, 1000.0)
        self.bar_spin.setDecimals(2)
        self.bar_spin.setSuffix(" mm")
        self.bar_spin.setValue(cfg.bar_length_mm)
        form.addRow("Scale bar length:", self.bar_spin)

        self.kw_edit = QLineEdit(cfg.micrometer_keyword)
        form.addRow("Micrometer filename keyword:", self.kw_edit)

        self.sl_combo = QComboBox()
        self.sl_combo.addItems(["LEFT", "RIGHT", "BOTH"])
        self.sl_combo.setCurrentText(cfg.sl_mode)
        form.addRow("Lateral spine side:", self.sl_combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_config(self) -> Config:
        return Config(
            bar_length_mm=self.bar_spin.value(),
            micrometer_keyword=self.kw_edit.text().strip(),
            sl_mode=self.sl_combo.currentText(),
        )


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    CrabMeasureApp().run()


if __name__ == "__main__":
    main()
