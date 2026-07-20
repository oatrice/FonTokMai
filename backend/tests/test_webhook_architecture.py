import ast
from pathlib import Path

def test_webhook_no_direct_background_tasks():
    """
    Ensure that new commands added to _telegram_webhook_impl don't use
    background_tasks.add_task directly without enqueue_task for heavy operations.
    """
    webhook_path = Path(__file__).parent.parent / "app" / "routers" / "webhook.py"
    
    content = webhook_path.read_text(encoding="utf-8")
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if "background_tasks.add_task(" in line:
            # Allow sending messages directly (check this line and next 2 lines)
            context = " ".join(lines[i:min(len(lines), i+3)])
            if "send_telegram_message" in context:
                continue
                
            # Allow callback queries because they have a wrapper check
            if "handle_callback_query" in context and "already_answered=True" in context:
                continue

            # Allow local lightweight functions
            if "_do_logout" in context or "_do_bypass" in context or "_do_login" in context:
                continue
            
            # For all other tasks, ensure they are wrapped inside an enqueue_task check
            # This is a simple heuristic: one of the previous 4 lines should contain enqueue_task
            prev_lines = " ".join(lines[max(0, i-4):i])
            if "enqueue_task(" not in prev_lines:
                assert False, (
                    f"Rule Violation at webhook.py line {i+1}: {line.strip()}\n"
                    "All heavy commands in _telegram_webhook_impl MUST be offloaded to CloudTasksService "
                    "via enqueue_task. background_tasks.add_task should only be used as a fallback."
                )
