from flask import Blueprint, g, jsonify

from auth import gateway

proxy_bp = Blueprint("proxy", __name__, url_prefix="/api/services")


@proxy_bp.get("/users")
@gateway("user-service")  # any signed-in user
def user_service():
    return jsonify(
        service="user-service",
        requestedBy=g.user["username"],
        data=[
            {"id": 1, "name": "Asha", "email": "asha@example.com"},
            {"id": 2, "name": "Ravi", "email": "ravi@example.com"},
            {"id": 3, "name": "Meera", "email": "meera@example.com"},
        ],
    )


@proxy_bp.get("/orders")
@gateway("order-service", allowed_roles=["admin", "manager"])
def order_service():
    return jsonify(
        service="order-service",
        requestedBy=g.user["username"],
        data=[
            {"orderId": "ORD-1001", "item": "Laptop", "amount": 55000, "status": "shipped"},
            {"orderId": "ORD-1002", "item": "Keyboard", "amount": 1800, "status": "processing"},
        ],
    )