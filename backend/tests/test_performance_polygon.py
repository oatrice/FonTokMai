"""
test_performance_polygon.py
----------------------------
Performance micro-benchmarks for H1 fix (polygon useMemo).
Verifies that pre-computing cluster polygons for 15 clusters is fast (<50ms).
Also tests the pure Python equivalent of the polygon path generation logic.
"""
import time
import math
import pytest


def compute_polygon_path(cx: float, cy: float, radius: float, cluster_id: str) -> str:
    """Pure Python equivalent of clusterPolygons useMemo logic in RadarCloudMap.tsx."""
    r = radius * 0.85
    vertices = 8
    seed = ord(cluster_id[-1]) % 5 if cluster_id else 0
    poly_pts = []
    for i in range(vertices):
        angle = (i / vertices) * math.pi * 2
        noise_factor = 1 + math.sin(i * 2.5 + seed) * 0.12
        vx = cx + math.cos(angle) * r * noise_factor
        vy = cy + math.sin(angle) * r * noise_factor
        poly_pts.append(f"{vx:.1f},{vy:.1f}")
    return "M " + " L ".join(poly_pts) + " Z"


def precompute_all_polygons(clusters: list[dict]) -> dict[str, str]:
    """Batch pre-computation: replicate useMemo behavior for N clusters."""
    result = {}
    for c in clusters:
        path = compute_polygon_path(c["cx"], c["cy"], c["radius"], c["id"])
        result[c["id"]] = path
    return result


@pytest.fixture
def sample_clusters():
    return [
        {"id": f"cluster-{i}", "cx": 200 + i * 15, "cy": 300 + i * 10, "radius": 20 + i}
        for i in range(15)
    ]


def test_polygon_precomputation_completes_under_50ms(sample_clusters):
    """H1: Pre-computing 15 cluster polygons must complete in <50ms."""
    start = time.perf_counter()
    result = precompute_all_polygons(sample_clusters)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 50.0, f"Polygon precomputation took {elapsed_ms:.2f}ms — must be <50ms"
    assert len(result) == 15, "All 15 clusters must have computed polygon paths"


def test_polygon_path_contains_all_ids(sample_clusters):
    """All cluster IDs must be present as keys in the computed Map."""
    result = precompute_all_polygons(sample_clusters)
    for c in sample_clusters:
        assert c["id"] in result, f"Missing polygon for cluster {c['id']}"


def test_polygon_path_is_valid_svg_path(sample_clusters):
    """Each computed path must be a valid SVG path string (starts with M, ends with Z)."""
    result = precompute_all_polygons(sample_clusters)
    for cluster_id, path in result.items():
        assert path.startswith("M "), f"Path for {cluster_id} must start with 'M '"
        assert path.endswith(" Z"), f"Path for {cluster_id} must end with ' Z'"
        # Must have 7 " L " separators for 8 vertices
        assert path.count(" L ") == 7, f"Path for {cluster_id} must have 7 L segments"


def test_polygon_path_no_nan_or_inf(sample_clusters):
    """Polygon coordinates must not contain NaN or Infinity (floating-point safety)."""
    result = precompute_all_polygons(sample_clusters)
    for cluster_id, path in result.items():
        assert "nan" not in path.lower(), f"NaN in polygon path for {cluster_id}"
        assert "inf" not in path.lower(), f"Infinity in polygon path for {cluster_id}"


def test_polygon_path_deterministic(sample_clusters):
    """Same input always produces identical polygon paths (no randomness in computation)."""
    result_1 = precompute_all_polygons(sample_clusters)
    result_2 = precompute_all_polygons(sample_clusters)
    for cluster_id in result_1:
        assert result_1[cluster_id] == result_2[cluster_id], \
            f"Polygon for {cluster_id} is not deterministic"


def test_single_cluster_polygon_values():
    """Spot-check specific coordinate values for deterministic polygon."""
    path = compute_polygon_path(cx=260.0, cy=390.0, radius=25.0, cluster_id="cluster-macro")
    assert "M " in path
    assert "Z" in path
    # center at (260, 390), r=25*0.85=21.25, vertex 0: angle=0 → x=260+21.25*noise, y=390
    parts = path.replace("M ", "").replace(" Z", "").split(" L ")
    assert len(parts) == 8
    # First vertex: angle=0, cos=1, sin=0 → noiseFactor=1+sin(0+seed)*0.12, seed='o'=111%5=1
    # noise=1+sin(1)*0.12=1.1010, x0=260+21.25*1.1010≈283.4
    x0, y0 = [float(v) for v in parts[0].split(",")]
    assert abs(x0 - 283.4) < 0.5, f"x0 expected ~283.4, got {x0}"
    assert abs(y0 - 390.0) < 0.5, f"y0 expected ~390.0, got {y0}"
