# Measurement Spec (Fig.2)

## Calibration
- Use micrometer image (filename contains "micrometer").
- Known bar length: 2.0 mm (edit if different).
- Output: px_per_mm.

## Required measurements (mm)
- CW: carapace width (widest points on left/right margins).
- CL: carapace length (posterior margin point to anterior reference point).
- RW: rostrum base width (left/right base corners).
- OW: orbital spine width (left/right orbital spine tips).
- SL: first lateral spine length (base to tip).
  - Side rule: [LEFT | RIGHT | BOTH and average]

## Click protocol (in order)
1. CW_L, CW_R
2. CL_P, CL_A
3. RW_L, RW_R
4. OW_L, OW_R
5. SL_B, SL_T  (and optionally SL_B2, SL_T2 if BOTH)

## Output CSV columns
file, px_per_mm, CW_mm, CL_mm, RW_mm, OW_mm, SL_mm, [optional SL_L_mm, SL_R_mm]