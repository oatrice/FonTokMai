import inspect
import logging
from typing import Callable, Dict, Any, Optional, Tuple
from fastapi import BackgroundTasks
import os

logger = logging.getLogger("app.services.command_router")

class TelegramCommandRouter:
    def __init__(self):
        self.registry: Dict[str, Dict[str, Any]] = {}

    def bind(
        self,
        prefix: str,
        requires_admin: bool = False,
        task_route: Optional[str] = None,
        loading_text: Optional[str] = None,
        command_override: Optional[str] = None,
        audit_log: bool = False,
        **extra_kwargs
    ):
        """
        Decorator to register a command handler for a prefix.

        audit_log=True → automatically calls log_audit_event("admin_command_executed", ...)
        when the command is dispatched (skipped for developer chat IDs).
        """
        def decorator(func: Callable):
            self.registry[prefix] = {
                "handler": func,
                "requires_admin": requires_admin,
                "task_route": task_route,
                "loading_text": loading_text,
                "command_override": command_override,
                "audit_log": audit_log,
                "extra_kwargs": extra_kwargs
            }
            return func
        return decorator

    def match(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Finds the matching command config for the given text.
        Matches the longest prefix first.
        """
        matched_prefix = None
        for prefix in self.registry:
            if text.startswith(prefix):
                if matched_prefix is None or len(prefix) > len(matched_prefix):
                    matched_prefix = prefix
        if matched_prefix:
            return matched_prefix, self.registry[matched_prefix]
        return None

    async def dispatch(
        self,
        text: str,
        chat_id: int,
        username: str,
        background_tasks: BackgroundTasks,
        check_admin_access_fn: Callable[[int], Any],
        send_telegram_message_fn: Callable[[int, str], Any],
        send_telegram_message_return_id_fn: Callable[[int, str], Any],
        enqueue_task_fn: Callable[[str, dict], Any],
    ) -> bool:
        """
        Dispatches the command to the registered handler.
        Returns True if a command was matched and handled, False otherwise.
        """
        match_result = self.match(text)
        if not match_result:
            return False

        prefix, config = match_result
        logger.info(f"[COMMAND ROUTER] Dispatching prefix='{prefix}' for text='{text}'")

        # 1. Admin access check
        if config["requires_admin"]:
            is_dev_env = os.getenv("ENVIRONMENT", "production").lower() == "development"
            if not is_dev_env:
                has_access = await check_admin_access_fn(chat_id)
                if not has_access:
                    background_tasks.add_task(
                        send_telegram_message_fn, chat_id,
                        "⚠️ ขออภัยครับ คำสั่งนี้ไม่เปิดให้ใช้งานในระบบปัจจุบัน"
                    )
                    return True

        # 2. Immediate feedback loading message
        loading_msg_id = None
        if config["loading_text"]:
            loading_msg_id = await send_telegram_message_return_id_fn(chat_id, config["loading_text"])

        # 3. Offload via Cloud Tasks or fallback to BackgroundTasks
        handler = config["handler"]
        task_route = config["task_route"]
        command_override = config["command_override"]
        extra_kwargs = config["extra_kwargs"]

        # Use command override if provided
        actual_command = command_override if command_override is not None else text

        # Build payload for Cloud Tasks
        payload = {
            "chat_id": chat_id,
            "command": actual_command,
            "username": username,
            "message_id_to_edit": loading_msg_id
        }
        # Add extra args (e.g. show_advanced)
        payload.update(extra_kwargs)

        if task_route:
            # Try to enqueue to Cloud Tasks
            success = await enqueue_task_fn(task_route, payload)
            if success:
                logger.info(f"[COMMAND ROUTER] Successfully enqueued '{task_route}' to Cloud Tasks")
                return True
            else:
                logger.warning(f"[COMMAND ROUTER] Cloud Tasks enqueue failed for '{task_route}', falling back to BackgroundTasks")

        # Fallback: invoke handler locally via BackgroundTasks
        async def run_handler():
            try:
                sig = inspect.signature(handler)
                kwargs = {}
                if "chat_id" in sig.parameters:
                    kwargs["chat_id"] = chat_id
                if "command" in sig.parameters:
                    kwargs["command"] = actual_command
                if "username" in sig.parameters:
                    kwargs["username"] = username
                if "message_id_to_edit" in sig.parameters:
                    kwargs["message_id_to_edit"] = loading_msg_id
                
                # Merge extra_kwargs
                for k, v in extra_kwargs.items():
                    if k in sig.parameters:
                        kwargs[k] = v
                        
                await handler(**kwargs)
            except Exception as e:
                logger.error(f"[COMMAND ROUTER] Error running handler {handler.__name__}: {e}", exc_info=True)

        background_tasks.add_task(run_handler)
        return True

# Global instance of the router
router = TelegramCommandRouter()
