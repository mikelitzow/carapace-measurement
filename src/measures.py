import numpy as np

def dist_mm(p1_xy, p2_xy, px_per_mm: float) -> float:
    p1 = np.array(p1_xy, dtype=float)
    p2 = np.array(p2_xy, dtype=float)
    return float(np.linalg.norm(p2 - p1) / px_per_mm)