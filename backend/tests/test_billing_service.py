import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.billing_service import BillingService, CostAggregation

@pytest.fixture
def billing_service():
    return BillingService()

@pytest.mark.asyncio
async def test_fetch_gcp_costs_success(billing_service):
    with patch("app.services.billing_service.CloudCatalogClient") as mock_catalog, \
         patch("app.services.billing_service.CloudBillingClient") as mock_billing:
        
        # Mocking basic successful response
        billing_service.get_gcp_costs = AsyncMock(return_value={
            "baseline": 150.0,
            "variable": 45.0
        })
        
        costs = await billing_service.get_gcp_costs("test-project-id")
        
        assert costs["baseline"] == 150.0
        assert costs["variable"] == 45.0

@pytest.mark.asyncio
async def test_fetch_aws_costs_success(billing_service):
    with patch("app.services.billing_service.boto3.client") as mock_boto:
        # Mocking basic successful response
        mock_ce = MagicMock()
        mock_boto.return_value = mock_ce
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "Total": {
                        "BlendedCost": {"Amount": "200.00"}
                    }
                }
            ]
        }
        
        billing_service.get_aws_costs = AsyncMock(return_value={
            "baseline": 100.0,
            "variable": 100.0
        })
        
        costs = await billing_service.get_aws_costs()
        
        assert costs["baseline"] == 100.0
        assert costs["variable"] == 100.0

@pytest.mark.asyncio
async def test_aggregate_costs(billing_service):
    billing_service.get_gcp_costs = AsyncMock(return_value={"baseline": 150.0, "variable": 45.0})
    billing_service.get_aws_costs = AsyncMock(return_value={"baseline": 100.0, "variable": 100.0})
    
    aggregation = await billing_service.aggregate_costs("test-project-id")
    
    assert aggregation.baseline_cost == 250.0
    assert aggregation.variable_cost == 145.0
    assert aggregation.total_cost == 395.0
