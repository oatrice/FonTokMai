import sys

with open("backend/app/services/tmd_radar/tracking.py", "r") as f:
    content = f.read()

# First change morphological closing from (9, 9) to (25, 25)
content = content.replace("kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))", 
                          "kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))")
content = content.replace("mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))",
                          "mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))")

# Then change the cluster_priority function
old_priority = """    def cluster_priority(c):
        # Tiered dBZ: >35=3, >25=2, else=1
        dbz_tier = 3 if c.predicted_dbz >= 35.0 else (2 if c.predicted_dbz >= 25.0 else 1)
        # Closer is better, so negate distance
        # Larger is better
        return (dbz_tier, -c.dist_to_user, c.size)
    
    ambient.sort(key=cluster_priority, reverse=True)"""

new_priority = """    def cluster_priority(c):
        # Continuous composite score instead of strict tiers.
        # This prevents a far cloud with slightly higher dBZ from dominating closer clouds with clear rain.
        # - dBZ is very important, weight by 3.0
        # - Distance is important, subtract it
        # - Size matters, but we use square root to prevent massive clouds from completely overshadowing everything
        import math
        dbz_score = c.predicted_dbz * 3.0
        size_score = math.sqrt(c.size) * 5.0
        return (dbz_score + size_score - c.dist_to_user)
    
    ambient.sort(key=cluster_priority, reverse=True)"""

content = content.replace(old_priority, new_priority)

with open("backend/app/services/tmd_radar/tracking.py", "w") as f:
    f.write(content)
