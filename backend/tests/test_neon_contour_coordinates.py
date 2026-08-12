import pytest
import numpy as np
import cv2

def test_contour_points_unpacking_coordinates():
    """
    Directly verify that c_orig['pixels'] tuples of (X, Y) map to OpenCV contour points (X, Y),
    where X is horizontal screen coordinate and Y is vertical screen coordinate.
    """
    x1, y1 = 30, 10
    scale = 2.0

    # Cluster with pixels at X=100..120, Y=50..70
    pixels = [(x, y) for x in range(100, 121) for y in range(50, 71)]
    c_orig = {"pixels": pixels}

    # Correct unpacking: for px, py in c_orig["pixels"]
    pts = np.array([[(int((px - x1) * scale), int((py - y1) * scale))] for px, py in c_orig["pixels"]], dtype=np.int32)

    # First point: (100, 50)
    # Expected screen X = (100 - 30) * 2 = 140
    # Expected screen Y = (50 - 10) * 2 = 80
    pt_screen_x = pts[0][0][0]
    pt_screen_y = pts[0][0][1]

    assert pt_screen_x == 140, f"Expected screen X=140, got {pt_screen_x}"
    assert pt_screen_y == 80, f"Expected screen Y=80, got {pt_screen_y}"

    # Verify bounding box of points
    x_box, y_box, w_box, h_box = cv2.boundingRect(pts)
    assert x_box == (100 - 30) * 2
    assert y_box == (50 - 10) * 2
    assert w_box == 20 * 2 + 1
    assert h_box == 20 * 2 + 1
