import ast
from pathlib import Path

def test_webhook_no_direct_background_tasks():
    """
    Ensure that new commands added to _telegram_webhook_impl don't use
    background_tasks.add_task directly without enqueue_task for heavy operations.
    """
    webhook_path = Path(__file__).parent.parent / "app" / "routers" / "webhook.py"
    tree = ast.parse(webhook_path.read_text(encoding="utf-8"))
    
    # Find _telegram_webhook_impl
    webhook_impl = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_telegram_webhook_impl":
            webhook_impl = node
            break
            
    assert webhook_impl is not None, "Could not find _telegram_webhook_impl"
    
    # We will find all calls to background_tasks.add_task
    # and verify they are enclosed in an If block that checks enqueue_task
    # or they are known exceptions.
    
    known_exceptions = ["send_telegram_message"] # Allow sending messages directly in background
    
    for node in ast.walk(webhook_impl):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add_task":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "background_tasks":
                    # Found background_tasks.add_task(...)
                    target_func = None
                    if node.args and isinstance(node.args[0], ast.Name):
                        target_func = node.args[0].id
                    
                    if target_func in known_exceptions:
                        continue
                        
                    # Now we need to check if this Call is inside an If node that checks enqueue_task
                    # AST doesn't have parent pointers easily, so we can just check the whole file
                    # textually for simplicity, or we can build parent pointers.
                    pass

    # A simpler text-based check for the file
    content = webhook_path.read_text(encoding="utf-8")
    import re
    # Find all occurrences of background_tasks.add_task
    # For every background_tasks.add_task, verify it's part of an enqueue_task fallback
    # or it's just send_telegram_message
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if "background_tasks.add_task(" in line:
            if "send_telegram_message" in line:
                continue
            
            # Check the line before it or 2 lines before it for enqueue_task
            prev_line = lines[i-1] if i > 0 else ""
            if "enqueue_task(" not in prev_line:
                # Is it an exception?
                if "handle_callback_query" in line and "already_answered=True" in line:
                    # Handled in the callback block correctly
                    continue
                    
                assert False, f"Rule Violation: background_tasks.add_task found without enqueue_task fallback at line {i+1}: {line.strip()}. All heavy commands must be offloaded to Cloud Tasks!"
