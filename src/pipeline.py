"""Image processing pipeline: segmentation and scale-bar calibration."""

import cv2
import numpy as np


def segment_carapace(img_bgr: np.ndarray) -> np.ndarray:
    """Return a binary mask (uint8, 0/255) containing the largest foreground object."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    L = cv2.GaussianBlur(lab[:, :, 0], (7, 7), 0)
    _, mask = cv2.threshold(L, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=1)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num <= 1:
        return np.zeros(mask.shape, dtype=np.uint8)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (labels == largest).astype(np.uint8) * 255


# ── Scale-bar detection ────────────────────────────────────────────────────────

def estimate_px_per_mm_from_micrometer(
    img_bgr: np.ndarray,
    bar_length_mm: float = 2.0,
) -> float:
    """
    Detect the scale bar in a micrometer/calibration image and return px/mm.

    Two strategies are attempted in order:
      1. Morphological horizontal-bar detection (filled bars / thick rules).
      2. Probabilistic Hough lines (thin graduated lines / graticules).

    Raises ValueError if both strategies fail.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    w = gray.shape[1]

    bar_px = _detect_filled_bar(gray, w)
    if bar_px is not None:
        return bar_px / bar_length_mm

    bar_px = _detect_hough_bar(gray, w)
    if bar_px is not None:
        return bar_px / bar_length_mm

    raise ValueError(
        "Could not automatically detect scale bar. "
        "Use manual calibration: click both ends of the bar in the viewer."
    )


def _detect_filled_bar(gray: np.ndarray, img_width: int) -> "float | None":
    """Find the widest wide-and-thin connected component (filled scale bar).

    Tries light-bar-on-dark-background first, then dark-bar-on-light-background.
    Returns immediately on the first successful detection so the two polarity
    passes don't cross-contaminate (the background region can have a deceptively
    large aspect ratio when polarity is wrong).
    """
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    total_px = float(gray.size)   # h * w – used to filter out background blobs

    for invert in (False, True):  # False = light bar on dark; True = dark bar on light
        thresh_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
        _, bw = cv2.threshold(blur, 0, 255, thresh_type | cv2.THRESH_OTSU)

        best = 0.0
        # Try progressively smaller minimum bar widths to catch shorter bars
        for frac in (0.05, 0.03, 0.01):
            min_w = max(8, int(img_width * frac))
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_w, 3))
            horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel)

            num, _, stats, _ = cv2.connectedComponentsWithStats(horiz, connectivity=8)
            for i in range(1, num):
                _, _, cw, ch, area = stats[i, :5]
                # Exclude background-filling blobs (>40 % of image) and non-bar shapes
                if (ch > 0 and cw / ch >= 3 and area >= 50
                        and area < total_px * 0.40):
                    best = max(best, float(cw))

        if best > 0:
            return best   # found something with this polarity – no need to flip

    return None


def _detect_hough_bar(gray: np.ndarray, img_width: int) -> "float | None":
    """Return length of the longest near-horizontal Hough line segment."""
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 30, 100)
    min_len = max(20, img_width // 15)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=40, minLineLength=min_len, maxLineGap=15,
    )
    if lines is None:
        return None

    best = 0.0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle < 8 or angle > 172:          # nearly horizontal
            length = float(np.hypot(x2 - x1, y2 - y1))
            best = max(best, length)

    return best if best > 0 else None


# ── Auto landmark detection ────────────────────────────────────────────────────

def auto_landmarks(mask: np.ndarray) -> dict:
    """Auto-detect CW_L, CW_R, CL_P, CL_A from a binary carapace mask.

    Returns a dict with keys 'CW_L', 'CW_R', 'CL_P', 'CL_A'
    (each a (row, col) tuple) and 'confidence' (dict of 0–1 floats).
    Returns an empty dict if detection fails.
    """
    H = mask.shape[0]
    border_h = max(10, int(H * 0.05))   # 5 % row margin – keeps T6-style artifacts out
    result: dict = {}
    confidence: dict = {}

    # ── CW: row of maximum horizontal width (excluding border band) ────────────
    row_widths = np.zeros(H, dtype=np.int32)
    for r in range(border_h, H - border_h):
        cols = np.where(mask[r] > 0)[0]
        if len(cols) >= 2:
            row_widths[r] = int(cols[-1]) - int(cols[0]) + 1

    smooth = np.convolve(row_widths.astype(float), np.ones(21) / 21, mode="same")
    best_row = int(np.argmax(smooth))
    cols = np.where(mask[best_row] > 0)[0]
    if len(cols) < 2:
        return {}

    result["CW_L"] = (best_row, int(cols[0]))
    result["CW_R"] = (best_row, int(cols[-1]))
    band = smooth[max(0, best_row - 30): best_row + 31]
    flat = float(np.min(band) / (np.max(band) + 1e-6))
    cw_conf = round(max(0.5, min(0.95, flat * 1.5)), 2)
    confidence["CW_L"] = cw_conf
    confidence["CW_R"] = cw_conf

    # ── CL: PCA major axis of mask pixels ─────────────────────────────────────
    ys, xs = np.where(mask > 0)
    if len(xs) < 500:
        result["confidence"] = confidence
        return result

    # Sub-sample for speed on large masks
    if len(xs) > 50_000:
        rng = np.random.default_rng(0)
        idx = rng.choice(len(xs), 50_000, replace=False)
        pts = np.stack([xs[idx].astype(float), ys[idx].astype(float)], axis=1)
    else:
        pts = np.stack([xs.astype(float), ys.astype(float)], axis=1)

    mean = pts.mean(axis=0)
    eigvals, eigvecs = np.linalg.eigh(np.cov((pts - mean).T))
    major = eigvecs[:, np.argmax(eigvals)]   # (x-component, y-component)

    # Project ALL mask pixels to find the true extremal points
    all_pts = np.stack([xs.astype(float), ys.astype(float)], axis=1)
    proj = (all_pts - mean) @ major
    pt_min = (int(ys[np.argmin(proj)]), int(xs[np.argmin(proj)]))   # (row, col)
    pt_max = (int(ys[np.argmax(proj)]), int(xs[np.argmax(proj)]))

    # Anterior (CL_A) = narrower end; posterior (CL_P) = wider end.
    # Estimate local width at each extreme by averaging row widths in a ±50 px band.
    def _local_width(pt: tuple, span: int = 50, step: int = 10) -> float:
        ws = []
        for dr in range(-span, span + 1, step):
            r = pt[0] + dr
            if 0 <= r < H:
                c_here = np.where(mask[r] > 0)[0]
                if len(c_here) >= 2:
                    ws.append(int(c_here[-1]) - int(c_here[0]) + 1)
        return float(np.median(ws)) if ws else 0.0

    if _local_width(pt_min) <= _local_width(pt_max):
        cl_a, cl_p = pt_min, pt_max   # narrower end = anterior
    else:
        cl_a, cl_p = pt_max, pt_min

    # Reject CL if either endpoint falls in the border-exclusion zone
    if (cl_p[0] < border_h or cl_p[0] > H - border_h
            or cl_a[0] < border_h or cl_a[0] > H - border_h):
        result["confidence"] = confidence
        return result

    result["CL_P"] = cl_p
    result["CL_A"] = cl_a

    explained = float(eigvals[np.argmax(eigvals)] / (eigvals.sum() + 1e-9))
    cl_conf = round(min(0.9, explained), 2)
    confidence["CL_P"] = cl_conf
    confidence["CL_A"] = cl_conf

    result["confidence"] = confidence
    return result
