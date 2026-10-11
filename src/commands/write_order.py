"""
Orders (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from models.product import Product
from models.order_item import OrderItem
from models.order import Order
from queries.read_order import get_orders_from_mysql
from db import get_sqlalchemy_session, get_redis_conn
import json

def add_order(user_id: int, items: list):
    """Insert order with items in MySQL, keep Redis in sync"""
    if not user_id or not items:
        raise ValueError("Vous devez indiquer au moins 1 utilisateur et 1 item pour chaque commande.")

    try:
        product_ids = []
        for item in items:
            product_ids.append(int(item['product_id']))
    except Exception as e:
        print(e)
        raise ValueError(f"L'ID Article n'est pas valide: {item['product_id']}")
    session = get_sqlalchemy_session()
    r = get_redis_conn()

    try:
        products_query = session.query(Product).filter(Product.id.in_(product_ids)).all()
        price_map = {product.id: product.price for product in products_query}
        total_amount = 0
        order_items_data = []
        
        for item in items:
            pid = int(item["product_id"])
            qty = float(item["quantity"])

            if not qty or qty <= 0:
                raise ValueError(f"Vous devez indiquer une quantité superieure à zéro.")

            if pid not in price_map:
                raise ValueError(f"Article ID {pid} n'est pas dans la base de données.")

            unit_price = price_map[pid]
            total_amount += unit_price * qty
            order_items_data.append({
                'product_id': pid,
                'quantity': qty,
                'unit_price': unit_price
            })
        
        new_order = Order(user_id=user_id, total_amount=total_amount)
        session.add(new_order)
        session.flush() 
        
        order_id = new_order.id

        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
            session.add(order_item)

        session.commit()

        add_order_to_redis(order_id, user_id, total_amount, order_items_data)

        return order_id

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_order(order_id: int):
    """Delete order in MySQL, keep Redis in sync"""
    session = get_sqlalchemy_session()
    r = get_redis_conn()
    try:
        order = session.query(Order).filter(Order.id == order_id).first()
        
        if order:
            session.delete(order)
            session.commit()

            # TODO: supprimer la commande à Redis
            delete_order_from_redis(order_id)
            return 1  
        else:
            return 0  
            
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def add_order_to_redis(order_id, user_id, total_amount, items):
    """Insert order to Redis"""
    r = get_redis_conn()
    item_data = []
    for item in items:
        item_data.append({
            "id": item.get("id", None),
            "order_id": order_id,
            "product_id": int(item["product_id"]),
            "quantity": float(item["quantity"]),
            "unit_price": float(item.get("unit_price", 0.0))
        })
        r.incr(f"product:{int(item['product_id'])}", int(item["quantity"]))
    
    r.hset(f"order:{order_id}", mapping={
        "user_id": user_id,
        "total_amount": total_amount,
        "order_items": json.dumps(item_data)
    })
    
    r.sadd("orders", order_id)


def delete_order_from_redis(order_id):
    """Delete order from Redis"""
    r = get_redis_conn()
    
    items = r.hget(f"order:{order_id}", "order_items")
    json_items = json.loads(items) if items else []
    for item in json_items:
        r.decr(f"product:{int(item['product_id'])}", int(item["quantity"]))
    
    r.srem("orders", order_id)
    r.delete(f"order:{order_id}")
    pass

def sync_all_orders_to_redis():
    """ Sync orders from MySQL to Redis """
    # redis
    r = get_redis_conn()
    orders_in_redis = r.scard("orders")
    rows_added = 0
    try:
        if orders_in_redis == 0:
            # mysql
            orders_from_mysql = []
            orders_from_mysql = get_orders_from_mysql()
            for order in orders_from_mysql:
                items = [
                    {"id": i.id, "product_id": i.product_id, "quantity": i.quantity, "unit_price": i.unit_price}
                    for i in order.order_items
                ]
                add_order_to_redis(order.id, order.user_id, order.total_amount, items)
            rows_added = len(orders_from_mysql)
        else:
            print('Redis already contains orders, no need to sync!')
    except Exception as e:
        print(e)
        return 0
    finally:
        return orders_in_redis + rows_added