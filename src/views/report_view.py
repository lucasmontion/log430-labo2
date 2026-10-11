"""
Report view
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from controllers.order_controller import get_report_highest_spending_users
from controllers.product_controller import get_report_best_sellers
from views.template_view import get_template, get_param

def show_highest_spending_users():
    """ Show report of highest spending users """
    spenders = get_report_highest_spending_users()

    rows = [f"""
                <li>Nom: {name}, Montant: {amount:.2f}</li>
            """ for name, amount in spenders]
    return get_template(f"""
            <h2>Les plus gros acheteurs</h2>
            <ul>
                {"".join(rows)}
            </ul>
            
        """)


def show_best_sellers():
    """ Show report of best selling products """
    sellers = get_report_best_sellers()

    rows = [f"""
                <li>Nom: {name}, Quantité vendue: {amount}</li>
            """ for name, amount in sellers]
    return get_template(f"""
            <h2>Les articles les plus vendus</h2>
            <ul>
                {"".join(rows)}
            </ul>
        """)