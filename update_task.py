import re
with open("/Users/oatrice/.gemini/antigravity/brain/4212bc90-86db-42db-8a58-0b3e54003a44/task.md", "r") as f:
    content = f.read()

# Update Phase 2 to completed
content = content.replace("[/] **Phase 2: Data Seam - Global Radar Cache (MR 2)**", "[x] **Phase 2: Data Seam - Global Radar Cache (MR 2)**")
content = content.replace("- [ ] Create `RadarFrameCache` deep module to encapsulate dict.", "- [x] Create `RadarFrameCache` deep module to encapsulate dict.")
content = content.replace("- [ ] Expose standard cache interfaces (`get`, `set`, `invalidate`).", "- [x] Expose standard cache interfaces (`get`, `set`, `invalidate`).")
content = content.replace("- [ ] Replace tuple-based state variables with strongly-typed `RadarCacheEntry` dataclass.", "- [x] Replace tuple-based state variables with strongly-typed `RadarCacheEntry` dataclass.")

# Mark Phase 3 as in progress
content = content.replace("[ ] **Phase 3: Core Structural - NowcastPort & Adapters (MR 3)**", "[/] **Phase 3: Core Structural - NowcastPort & Adapters (MR 3)**")
content = content.replace("- [ ] Create `NowcastPort` protocol representing expected inputs and outputs for any prediction system.", "- [/] Create `NowcastPort` protocol representing expected inputs and outputs for any prediction system.")

with open("/Users/oatrice/.gemini/antigravity/brain/4212bc90-86db-42db-8a58-0b3e54003a44/task.md", "w") as f:
    f.write(content)
