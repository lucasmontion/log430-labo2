"""
Orders (read-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

from collections import defaultdict
import json

from db import get_sqlalchemy_session, get_redis_conn
from sqlalchemy import desc
from models.order import Order

def get_order_by_id(order_id):
    """Get order by ID from Redis"""
    r = get_redis_conn()
    return r.hgetall(order_id)

def get_orders_from_mysql(limit=9999):
    """Get last X orders"""
    session = get_sqlalchemy_session()
    return session.query(Order).order_by(desc(Order.id)).limit(limit).all()

def get_orders_from_redis(limit=9999):
    """Get last X orders"""
    r = get_redis_conn()
    ids = sorted(r.smembers("orders"), key=int, reverse=True)[:limit]
    orders = []
    for order_id in ids:
        data = r.hgetall(f"order:{order_id}")
        if data:
            data["id"] = int(order_id)
            orders.append(data)
    return orders

def get_highest_spending_users():
    """Get report of best selling products"""
    # TODO: écrivez la méthode
    # triez le résultat par nombre de commandes (ordre décroissant)
    orders = get_orders_from_redis()

    expenses_by_user = defaultdict(float)
    for order in orders:
        expenses_by_user[int(order["user_id"])] += float(order["total_amount"])
    highest_spending_users = sorted(expenses_by_user.items(), key=lambda item: item[1], reverse=True)[:10]
    return highest_spending_users

def get_best_sellers():
    """Get report of best selling products"""
    orders = get_orders_from_redis()
    product_sales = defaultdict(int)

    for order in orders:
        for item in json.loads(order["order_items"]):
            product_sales[int(item["product_id"])] += int(item["quantity"])

    return sorted(product_sales.items(), key=lambda item: item[1], reverse=True)[:10]