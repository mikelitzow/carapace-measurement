import cv2
import numpy as np

def segment_carapace(img_bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    L = cv2.GaussianBlur(lab[:, :, 0], (7, 7), 0)
    mask = cv2.threshold(L, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  np.ones((5, 5), np.uint8), iterations=1)

    # keep largest connected component
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num <= 1:
        return np.zeros(mask.shape, dtype=np.uint8)
    largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return (labels == largest).astype(np.uint8) * 255

def estimate_px_per_mm_from_micrometer(img_bgr: np.ndarray, bar_length_mm: float) -> float:
    """
    TODO: implement robust scale-bar detection (Hough lines within ROI).
    Must return px_per_mm.
    """
    raise NotImplementedError