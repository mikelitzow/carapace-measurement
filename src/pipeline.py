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
