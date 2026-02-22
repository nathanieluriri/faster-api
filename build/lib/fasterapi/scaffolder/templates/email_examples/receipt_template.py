from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "receipt"
SUBJECT = "Your payment receipt"


def render_html(context: dict[str, Any]) -> str:
    order_id = str(context.get("order_id", "N/A"))
    amount = str(context.get("amount", "$0.00"))
    payment_date = str(context.get("payment_date", "today"))
    return (
        "<h2>Payment Receipt</h2>"
        f"<p>Order ID: <strong>{order_id}</strong></p>"
        f"<p>Amount paid: <strong>{amount}</strong></p>"
        f"<p>Date: {payment_date}</p>"
    )


def render_text(context: dict[str, Any]) -> str:
    order_id = str(context.get("order_id", "N/A"))
    amount = str(context.get("amount", "$0.00"))
    payment_date = str(context.get("payment_date", "today"))
    return f"Receipt for order {order_id}. Amount: {amount}. Date: {payment_date}."
