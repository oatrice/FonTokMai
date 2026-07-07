# Requirement Analysis: LINE OA Rich Menu & UI Component Enhancements for FonMaYang

## 1. Introduction & Background
FonMaYang (ฝนมายัง) is a real-time rain forecasting and weather radar monitoring service in Thailand. Currently, users interact with the LINE Official Account (OA) through text commands (e.g., `/rain`, `/rain_pro`, `/mylocation`, `/devmock`) and location sharing.

While functional, text-based commands pose significant usability barriers:
- **High Friction**: Typing slash commands on mobile virtual keyboards is slow and tedious.
- **Error-Prone**: Users frequently mistype commands or location names.
- **Discoverability**: New users are unaware of available features (e.g., `/rain_pro` or simulation commands).

To improve the User Experience (UX), this document analyzes the requirements for introducing a **LINE Rich Menu** and advanced UI components like **Flex Messages** and **Quick Replies**.

---

## 2. Target Audience & Use Cases
- **Daily Commuters**: Quick check on rain forecasts before leaving work/home.
- **Outdoor Workers / Event Planners**: Deep-dive advanced weather alerts and radar image tracking.
- **Developers / Testers**: Simulated weather scenarios (`/devmock`) for validation.

---

## 3. Proposed UI/UX Features

### 3.1. LINE Rich Menu
A persistent, graphical menu displayed at the bottom of the chat screen. We propose a **6-Grid (2 rows x 3 columns)** layout:

```
+------------------------+------------------------+------------------------+
|       🌧️ เช็คฝน        |       🚀 เช็คฝนพิเศษ    |       📍 ส่งพิกัด       |
|      (Check Rain)      |      (Advanced Check)  |     (Share Location)   |
+------------------------+------------------------+------------------------+
|      📂 พิกัดของฉัน     |      ⚙️ ตัวจำลองระบบ     |       ❓ วิธีใช้งาน     |
|     (My Locations)     |    (Simulation Mode)   |      (Help & Guide)    |
+------------------------+------------------------+------------------------+
```

#### Action Specifications per Zone:
1. **เช็คฝน (Check Rain)**:
   - **Type**: Message Action
   - **Text**: `/rain`
   - **Behavior**: Instantly queries the weather prediction for the user's primary/default location.
2. **เช็คฝนพิเศษ (Advanced Check)**:
   - **Type**: Message Action
   - **Text**: `/rain_pro`
   - **Behavior**: Queries advanced weather stats, radar loop, and timeline for the primary location.
3. **ส่งพิกัด (Share Location)**:
   - **Type**: URI Action
   - **URI**: `line://nv/location`
   - **Behavior**: Instantly opens the LINE native location-picker interface. When shared, the webhook registers/updates the user's location.
4. **พิกัดของฉัน (My Locations)**:
   - **Type**: Message Action
   - **Text**: `/mylocation`
   - **Behavior**: Lists all registered locations for the user.
5. **ตัวจำลองระบบ (Simulation Mode)**:
   - **Type**: Postback Action or Message Action
   - **Text**: `/devmock` (or toggles a quick reply menu for `rain`, `clear`, `off`)
   - **Behavior**: Allows developers to simulate rain states.
6. **วิธีใช้งาน (Help & Guide)**:
   - **Type**: Message Action
   - **Text**: `/help`
   - **Behavior**: Responds with a visually pleasing description of how FonMaYang works.

### 3.2. LINE Flex Messages (Alternative to Plain Text)
Currently, responses are raw text. We will introduce **LINE Flex Messages** (JSON-based bubble cards) for:
- **Weather Forecast Card**: Shows temperature, rain probability, and ETA with color-coded gradients (e.g., Red/Orange for imminent rain, Blue/Green for clear skies).
- **Location List**: Displays saved locations as interactive cards with "Check Rain" and "Delete" buttons inside the card.

### 3.3. Quick Reply Buttons
Contextual buttons displayed above the text input bar:
- When a user types `/devmock`, display three Quick Reply buttons: `Rain 🌧️`, `Clear ☀️`, and `Off ❌`.
- When confirming actions (e.g., deleting a location).

---

## 4. Technical Architecture & System Impact

### 4.1. Webhook Upgrades (`line_webhook.py`)
- **Postback Handling**: Update the event parser to handle `PostbackEvent` in addition to `MessageEvent`.
- **Text Command Alias**: Standardize commands so that clicking Rich Menu items (e.g., `/rain`) behaves identically to user typing.

### 4.2. Rich Menu Management
- **Rich Menu API Integration**: A python script or administrative endpoint to programmatically upload the Rich Menu image, define coordinates (bounding boxes), and register it as the default menu for all users.
- **Asset Requirement**: Needs a $2500 \times 1686$ or $2500 \times 843$ PNG image representing the menu design.

### 4.3. Code Components Affected
- [line_webhook.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/routers/line_webhook.py): Webhook entry point.
- [notification.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/services/notification.py): Notification abstraction layer (needs to support Flex Message payloads).
- **[NEW]** `backend/scripts/setup_line_rich_menu.py`: Script to define and upload the Rich Menu design via LINE Messaging SDK.

---

## 5. Non-Functional Requirements
- **Latency**: Opening the location sharing sheet or clicking a menu button should respond within < 1.5 seconds.
- **Reliability**: Rich Menu states must be cached or registered on LINE servers directly (handled by LINE, ensuring 99.9% uptime).
- **Localizability**: Text on the Rich Menu and Flex Messages must support Thai as the primary language.

---

## 6. Verification Plan
- **Mock Tests**: Expand [test_line_integration.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/tests/test_line_integration.py) to simulate postback and quick reply events.
- **Manual Verification**: Run local webhook server (via ngrok/tunneling) to verify button clicks on physical LINE clients.
