import re

with open("backend/app/services/tmd_radar_processor.py", "r") as f:
    code = f.read()

# 1. Pre-register cloud circles
pre_reg = """        # Avoid drawing text directly over the user pin (define a box around user location)
        drawn_text_boxes.append((ux - int(20 * scale), uy - int(20 * scale), int(40 * scale), int(40 * scale)))
        
        # Pre-register cloud circles as obstacles so trajectory text avoids them
        if show_clouds:
            incoming = [c for c in display_clouds if c.get("approaching", False) and -120 <= c.get("eta_min", 9999) <= 180]
            incoming.sort(key=lambda c: c.get("predicted_dbz", 0), reverse=True)
            
            for c_orig in incoming[:3] + sorted(ambient_clouds, key=lambda c: c.get("dist", 9999))[:8]:
                cx = int((c_orig["cx"] - x1) * scale)
                cy = int((c_orig["cy"] - y1) * scale)
                if c_orig.get("approaching", False):
                    if "pixels" in c_orig and len(c_orig["pixels"]) > 2:
                        import numpy as np
                        pts = np.array([[(int((px - x1) * scale), int((py - y1) * scale))] for px, py in c_orig["pixels"]], dtype=np.int32)
                        import cv2
                        hull = cv2.convexHull(pts)
                        hull_rect = cv2.boundingRect(hull)
                        drawn_text_boxes.append((hull_rect[0] - 5, hull_rect[1] - 5, hull_rect[2] + 10, hull_rect[3] + 10))
                    else:
                        r = int(12 * scale)
                        drawn_text_boxes.append((cx - r, cy - r, 2*r, 2*r))
                else:
                    r = int(10 * scale)
                    drawn_text_boxes.append((cx - r, cy - r, 2*r, 2*r))"""
code = re.sub(r'        # Avoid drawing text directly over the user pin \(define a box around user location\)\n        drawn_text_boxes.append\(\(ux - int\(20 \* scale\), uy - int\(20 \* scale\), int\(40 \* scale\), int\(40 \* scale\)\)\)', pre_reg, code)

# 2. Add bounding boxes in _draw_cloud (approaching)
approaching_draw = """                    cv2.fillPoly(overlay, [hull], color)
                    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
                    cv2.polylines(img, [hull], True, color, max(1, int(2.0 * scale)))
                    drawn_text_boxes.append((hull_rect[0] - 5, hull_rect[1] - 5, hull_rect[2] + 10, hull_rect[3] + 10))
                else:
                    r = int(12 * scale)
                    cv2.circle(img, (cx, cy), r, color, int(1.5 * scale))
                    drawn_text_boxes.append((cx - r, cy - r, 2*r, 2*r))"""
code = re.sub(r'                    cv2.fillPoly\(overlay, \[hull\], color\)\n                    cv2.addWeighted\(overlay, 0.3, img, 0.7, 0, img\)\n                    cv2.polylines\(img, \[hull\], True, color, max\(1, int\(2.0 \* scale\)\)\)\n                else:\n                    cv2.circle\(img, \(cx, cy\), int\(12 \* scale\), color, int\(1.5 \* scale\)\)', approaching_draw, code)

# 3. Add bounding boxes in _draw_cloud (ambient)
ambient_draw = """                    cv2.line(img, p1, p2, color, int(scale * 0.8))
                drawn_text_boxes.append((cx - r, cy - r, 2*r, 2*r))"""
code = re.sub(r'                    cv2.line\(img, p1, p2, color, int\(scale \* 0.8\)\)', ambient_draw, code)

# 4. Trajectory mask and line avoidance
traj_draw = """                        # Clamp to keep trajectory text on screen after shifts
                        tx = max(10, min(img.shape[1] - tw - 5, tx))
                        ty = max(th + 5, min(img.shape[0] - 10, ty))

                        # Draw connector line from dot to text (avoiding text boxes)
                        line_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                        cv2.line(line_mask, (cx, cy), (tx - int(2 * scale), ty + int(2 * scale)), 255, max(1, int(1 * scale)))
                        
                        # Erase the area of existing text boxes so the line goes "behind" them
                        for rx, ry, rw, rh in drawn_text_boxes:
                            pad = int(2 * scale)
                            cv2.rectangle(line_mask, (rx - pad, ry - pad), (rx + rw + pad, ry + rh + pad), 0, -1)
                            
                        # Apply the masked line to the image
                        img[line_mask == 255] = (200, 200, 200)

                        logger.info(f"[DRAW_TEXT] Trajectory '{label}' at ({tx}, {ty})")
                        cv2.putText(img, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35 * scale, (0, 0, 0), int(2.5 * scale))
                        cv2.putText(img, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.35 * scale, (255, 255, 255), int(1 * scale))
                        drawn_text_boxes.append((tx, ty - th, tw, th))
                        
                        # Register the connector line as an obstacle for future texts (like ambient clouds)
                        import math as _m
                        num_segments = max(1, int(_m.hypot(tx - cx, ty - cy) / (8 * scale)))
                        for _j in range(num_segments + 1):
                            px = cx + _j * (tx - cx) // num_segments
                            py = cy + _j * (ty - cy) // num_segments
                            drawn_text_boxes.append((px - int(5 * scale), py - int(5 * scale), int(10 * scale), int(10 * scale)))

                        last_labeled_pt = (cx, cy)"""
code = re.sub(r'                        # Clamp to keep trajectory text on screen after shifts.*?last_labeled_pt = \(cx, cy\)', traj_draw, code, flags=re.DOTALL)

# 5. Swap drawing order!
# Extract clouds block
match_clouds = re.search(r'        if show_clouds:\n.*?(?=        # ── Draw Prediction Trajectory \(Backward Ray\) ──)', code, flags=re.DOTALL)
clouds_block = match_clouds.group(0)

# Extract trajectory block
match_traj = re.search(r'        # ── Draw Prediction Trajectory \(Backward Ray\) ──\n.*?        # Add IDC timestamp overlay', code, flags=re.DOTALL)
traj_block = match_traj.group(0).replace('        # Add IDC timestamp overlay', '')

# Replace both blocks
code = code.replace(clouds_block, '')
code = code.replace(traj_block, traj_block + clouds_block)

with open("backend/app/services/tmd_radar_processor.py", "w") as f:
    f.write(code)

