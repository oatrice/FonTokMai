from typing import Any
from pydantic import BaseModel

class DevSettings(BaseModel):
    cluster_min: int = 3
    search_radius: int = 80
    min_dbz: float = 10.0
    dot_threshold: float = 0.6
    flow_mode: str = "average"
    hit_radius: int = 7
    verbose: bool = False
    draw_debug_grid: bool = False
    decay_enabled: bool = True
    prediction_steps: int = 13
    chaikin_iterations: int = 3
    enable_raster_smooth: bool = True
    gaussian_kernel_size: int = 15
    raster_smooth_threshold: int = 80
    enable_hsv_mask: bool = False
    use_skn240_backup: bool = False
    use_local_fixtures: bool = False
    min_ambient_dbz: float = 20.0
    min_ambient_size: int = 15
    show_trajectory: bool = True
    show_backward_trajectory: bool = True
    draw_all_ambient_polygons: bool = False

_global_dev_settings = DevSettings()

def get_dev_settings() -> DevSettings:
    return _global_dev_settings

def update_dev_settings(patch: dict[str, Any]) -> DevSettings:
    global _global_dev_settings
    current_dict = _global_dev_settings.model_dump()
    for k, v in patch.items():
        if k in current_dict:
            current_dict[k] = v
    _global_dev_settings = DevSettings(**current_dict)
    return _global_dev_settings
