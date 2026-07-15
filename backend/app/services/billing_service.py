import os
import logging
from google.cloud.billing import budgets_v1

logger = logging.getLogger(__name__)

class BillingService:
    def __init__(self):
        self.client = budgets_v1.BudgetServiceClient()
        self.billing_account_id = os.getenv("GCP_BILLING_ACCOUNT_ID")
        self.budget_display_name = os.getenv("GCP_BUDGET_DISPLAY_NAME", "fontokmai-api-monthly-budget")

    async def update_budget(self, amount: float) -> bool:
        if not self.billing_account_id:
            logger.error("GCP_BILLING_ACCOUNT_ID is not configured in environment variables.")
            return False

        try:
            import asyncio
            parent = f"billingAccounts/{self.billing_account_id}"
            
            def _find_and_update():
                budgets = self.client.list_budgets(parent=parent)
                target_budget = None
                for budget in budgets:
                    if budget.display_name == self.budget_display_name:
                        target_budget = budget
                        break
                        
                if not target_budget:
                    logger.error(f"Budget with display name '{self.budget_display_name}' not found.")
                    return False
                    
                target_budget.amount.specified_amount.units = int(amount)
                target_budget.amount.specified_amount.nanos = int(round((amount - int(amount)) * 1e9))
                
                from google.protobuf import field_mask_pb2
                update_mask = field_mask_pb2.FieldMask(paths=["amount"])
                
                self.client.update_budget(budget=target_budget, update_mask=update_mask)
                logger.info(f"Successfully updated GCP budget '{self.budget_display_name}' to {amount} THB")
                return True

            return await asyncio.to_thread(_find_and_update)
        except Exception as e:
            logger.error(f"Failed to update GCP budget: {e}", exc_info=True)
            return False

    async def get_budget(self) -> float | None:
        if not self.billing_account_id:
            logger.error("GCP_BILLING_ACCOUNT_ID is not configured in environment variables.")
            return None

        try:
            import asyncio
            parent = f"billingAccounts/{self.billing_account_id}"
            
            def _find():
                budgets = self.client.list_budgets(parent=parent)
                for budget in budgets:
                    if budget.display_name == self.budget_display_name:
                        units = budget.amount.specified_amount.units
                        nanos = budget.amount.specified_amount.nanos
                        return float(units) + (float(nanos) / 1e9)
                return None

            return await asyncio.to_thread(_find)
        except Exception as e:
            logger.error(f"Failed to get GCP budget: {e}", exc_info=True)
            return None
