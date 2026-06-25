from unittest.mock import patch

def my_func():
    from os import path
    return path.exists("/")

try:
    with patch("__main__.path"):
        pass
    print("Patching main.path worked")
except Exception as e:
    print(f"Error: {e}")

try:
    with patch("os.path.exists"):
        pass
    print("Patching os.path.exists worked")
except Exception as e:
    print(f"Error: {e}")
