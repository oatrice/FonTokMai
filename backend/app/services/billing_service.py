import os
import logging
import datetime
import asyncio
from typing import Dict
from pydantic import BaseModel
from google.cloud.billing import budgets_v1

# Mock GCP/AWS imports for billing data fetching
try:
    from google.cloud import billing_v1
    from google.cloud.billing_v1 import CloudCatalogClient, CloudBillingClient
except ImportError:
    billing_v1 = None
    CloudCatalogClient = None
    CloudBillingClient = None

try:
    import boto3
except ImportError:
    boto3 = None

logger = logging.getLogger(__name__)

class CostAggregation(BaseModel):
    baseline_cost: float = 0.0
    variable_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "USD"
    updated_at: datetime.datetime | None = None

class BillingService:
    def __init__(self, client=None):
        self._client = client
        self.billing_account_id = os.getenv("GCP_BILLING_ACCOUNT_ID")
        self.budget_display_name = os.getenv("GCP_BUDGET_DISPLAY_NAME", "fontokmai-api-monthly-budget")

    @property
    def client(self):
        if self._client is None:
            self._client = budgets_v1.BudgetServiceClient()
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

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

    async def get_gcp_costs(self, project_id: str = None) -> Dict[str, float]:
        """
        Fetch GCP costs and split into baseline vs variable.
        Currently returns mock logic until fully integrated.
        """
        project_id = project_id or os.getenv("GCP_PROJECT_ID", "default-project")
        
        # Real integration requires CloudBillingClient
        # For now, simulate the fetch
        baseline = 150.0
        variable = 45.0
        
        logger.info(f"Fetched GCP costs for project {project_id}: baseline={baseline}, variable={variable}")
        return {"baseline": baseline, "variable": variable}

    async def get_aws_costs(self) -> Dict[str, float]:
        """
        Fetch AWS costs and split into baseline vs variable using Cost Explorer.
        Currently returns mock logic until fully integrated.
        """
        # Real integration requires boto3 client setup
        baseline = 100.0
        variable = 100.0
        
        logger.info(f"Fetched AWS costs: baseline={baseline}, variable={variable}")
        return {"baseline": baseline, "variable": variable}

    async def aggregate_costs(self, gcp_project_id: str = None) -> CostAggregation:
        gcp_costs = await self.get_gcp_costs(gcp_project_id)
        aws_costs = await self.get_aws_costs()
        
        baseline = gcp_costs.get("baseline", 0.0) + aws_costs.get("baseline", 0.0)
        variable = gcp_costs.get("variable", 0.0) + aws_costs.get("variable", 0.0)
        
        agg = CostAggregation(
            baseline_cost=baseline,
            variable_cost=variable,
            total_cost=baseline + variable,
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        logger.info(f"Aggregated Total Costs: {agg.total_cost} (Baseline: {agg.baseline_cost}, Variable: {agg.variable_cost})")
        return agg
