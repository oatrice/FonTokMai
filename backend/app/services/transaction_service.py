import logging

# In a real application, we would use a repository or database session
# For zero-PII storage, this function accepts ONLY pseudonymous IDs.
async def save_stripe_transaction(customer_id: str, transaction_id: str, amount: int):
    logging.info(f"Saving zero-PII transaction: {transaction_id} for customer {customer_id} with amount {amount}")
    # Simulate DB saving
    return True
