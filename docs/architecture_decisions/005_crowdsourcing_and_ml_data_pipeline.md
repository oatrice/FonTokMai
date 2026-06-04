# ADR 005: Crowdsourcing & ML Data Pipeline Strategy

## Context
One of the major issues with short-term rain forecasting (Nowcasting) via radar is anomalies such as "Virga" (ฝนตกไม่ถึงพื้น) or radar clutter, leading to False Positives. Relying purely on raw weather APIs (Tomorrow.io, RainViewer, Rainbow) is insufficient because these APIs do not have ground truth sensors at every user's location.

To mitigate this, we need to transition from a purely rule-based alerting system to an ML-augmented system (Batch G). However, supervised Machine Learning requires high-quality labeled data (Features + Targets).

## Decision
We implemented a **Crowdsourced Ground Truth Mechanism** seamlessly integrated into the Telegram UX.

1. **Interactive Feedback (Targets):** Every rain alert now includes an inline button `❌ แจ้งเตือนผิดพลาด (ฝนไม่ตกจริง)`. When clicked, it logs a `false_alarm` record into the `user_feedbacks` database.
2. **Context Embedding (Features Context):** The Telegram callback payload is strictly limited to 64 bytes. To circumvent this, we map API endpoints to shortcodes (e.g., `tomorrow` -> `t`) and embed the predicted max rain directly into the callback data (e.g., `fb_falsealarm_13.0_100.0_t_1.5`).
3. **Future Extensibility (Batch G):** For robust ML training, summarizing features in 64 bytes is insufficient. In future iterations (Issue #40), the system will dump the raw, full JSON response from the APIs into a dedicated `alert_logs` Firestore collection upon alerting. The callback data will then embed the document ID (`log_id`). When a user reports a false alarm, the exact `log_id` is updated, creating a perfect `(Features, Target=0)` dataset seamlessly.

## Consequences
- **Positive:** We are instantly building a high-value proprietary dataset of false alarms tied directly to Thai geographic coordinates.
- **Positive:** Users feel heard when they report inaccuracies, improving UX.
- **Negative/Risk:** If the dataset is imbalanced (users only click the button when it's wrong, but don't explicitly validate when it's right), the ML model might require semi-supervised handling or assumption of implicit true positives if no feedback is provided.

## Status
- Initial inline button and context embedding: **Implemented (Batch E)**.
- Full JSON logging (`alert_logs`): **Planned (Batch G)**.
