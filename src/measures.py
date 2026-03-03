"""Measurement helpers: distance, aggregation, and QC overlay rendering."""

from pathlib import Path

import cv2
import numpy as np

# ── Measurement pair definitions ───────────────────────────────────────────────
# (measurement_name, left_key, right_key, BGR_colour_for_QC_line)
MEASURE_PAIRS = [
    ("CW", "CW_L", "CW_R",   (0, 200, 0)),
    ("CL", "CL_P", "CL_A",   (0, 100, 255)),
    ("RW", "RW_L", "RW_R",   (255, 100, 0)),
    ("OW", "OW_L", "OW_R",   (200, 0, 200)),
    ("SL", "SL_B", "SL_T",   (200, 200, 0)),
]

# Point-label → BGR colour used in QC overlay
_POINT_COLORS_BGR = {
    "CW_L": (0, 200, 0),    "CW_R": (0, 200, 0),
    "CL_P": (0, 100, 255),  "CL_A": (0, 100, 255),
    "RW_L": (255, 100, 0),  "RW_R": (255, 100, 0),
    "OW_L": (200, 0, 200),  "OW_R": (200, 0, 200),
    "SL_B": (200, 200, 0),  "SL_T": (200, 200, 0),
    "SL_B2": (0, 200, 200), "SL_T2": (0, 200, 200),
}


def dist_mm(p1_rc, p2_rc, px_per_mm: float) -> float:
    """Euclidean distance between two (row, col) points in millimetres."""
    p1 = np.array(p1_rc, dtype=float)
    p2 = np.array(p2_rc, dtype=float)
    return float(np.linalg.norm(p2 - p1) / px_per_mm)


def compute_measurements(
    clicks: dict,          # name -> (row, col)
    px_per_mm: float,
    sl_mode: str = "LEFT", # LEFT | RIGHT | BOTH
) -> dict:
    """Return {measurement_mm_key: value} for all completed pairs."""
    out: dict[str, float] = {}
    for mname, k1, k2, _ in MEASURE_PAIRS:
        if k1 in clicks and k2 in clicks:
            out[f"{mname}_mm"] = dist_mm(clicks[k1], clicks[k2], px_per_mm)

    if sl_mode == "BOTH" and all(k in clicks for k in ("SL_B2", "SL_T2")):
        sl1 = dist_mm(clicks["SL_B"],  clicks["SL_T"],  px_per_mm)
        sl2 = dist_mm(clicks["SL_B2"], clicks["SL_T2"], px_per_mm)
        out["SL_L_mm"] = sl1
        out["SL_R_mm"] = sl2
        out["SL_mm"]   = (sl1 + sl2) / 2.0

    return out


def save_qc_overlay(
    img_bgr: np.ndarray,
    clicks: dict,          # name -> (row, col)
    measurements: dict,
    out_path: Path,
) -> None:
    """Write an annotated PNG to *out_path* with points, lines, and measurements."""
    vis = img_bgr.copy()
    h, w = vis.shape[:2]
    radius    = max(6, min(h, w) // 120)
    thickness = max(2, radius // 3)
    font      = cv2.FONT_HERSHEY_SIMPLEX
    fscale    = max(0.4, min(h, w) / 1200)

    # Draw measurement lines
    for _, k1, k2, color in MEASURE_PAIRS:
        if k1 in clicks and k2 in clicks:
            r1, c1 = clicks[k1]
            r2, c2 = clicks[k2]
            cv2.line(vis, (int(c1), int(r1)), (int(c2), int(r2)), color, thickness)

    if "SL_B2" in clicks and "SL_T2" in clicks:
        r1, c1 = clicks["SL_B2"]
        r2, c2 = clicks["SL_T2"]
        cv2.line(vis, (int(c1), int(r1)), (int(c2), int(r2)), (0, 200, 200), thickness)

    # Draw labelled points
    for name, (row, col) in clicks.items():
        color = _POINT_COLORS_BGR.get(name, (255, 255, 255))
        cv2.circle(vis, (int(col), int(row)), radius, color, -1)
        cv2.circle(vis, (int(col), int(row)), radius + 2, (0, 0, 0), 1)
        tx, ty = int(col) + radius + 3, int(row) + 4
        cv2.putText(vis, name, (tx, ty), font, fscale, (0, 0, 0), 3)
        cv2.putText(vis, name, (tx, ty), font, fscale, color, 1)

    # Measurement summary in top-left corner
    y_off = int(fscale * 40)
    for key, val in sorted(measurements.items()):
        text = f"{key}: {val:.3f} mm"
        cv2.putText(vis, text, (8, y_off), font, fscale, (0, 0, 0), 3)
        cv2.putText(vis, text, (8, y_off), font, fscale, (255, 255, 255), 1)
        y_off += int(fscale * 36)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)
