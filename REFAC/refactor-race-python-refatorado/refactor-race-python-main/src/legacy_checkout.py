"""Processamento de pedidos.

Refatorado a partir da versão legada preservando o comportamento observável:
valores retornados, mensagens impressas e o registro em ORDERS_PROCESSED.
"""

from collections import Counter

ORDERS_PROCESSED = []

# --- Tipos de cliente -------------------------------------------------------
CUSTOMER_VIP = "vip"
CUSTOMER_EMPLOYEE = "employee"
CUSTOMER_REGULAR = "regular"

# --- Descontos por tipo de cliente ------------------------------------------
VIP_DISCOUNT_RATE = 0.10
VIP_HIGH_VALUE_DISCOUNT_RATE = 0.15
VIP_HIGH_VALUE_THRESHOLD = 1000
EMPLOYEE_DISCOUNT_RATE = 0.20
REGULAR_DISCOUNT_RATE = 0.05
REGULAR_DISCOUNT_THRESHOLD = 800

# --- Cupons -----------------------------------------------------------------
COUPON_PROMO10 = "PROMO10"
COUPON_PROMO20 = "PROMO20"
COUPON_VIP50 = "VIP50"
PROMO10_RATE = 0.10
PROMO20_RATE = 0.20
PROMO20_MIN_SUBTOTAL = 500
VIP50_FLAT_DISCOUNT = 50

MAX_DISCOUNT_RATE = 0.25

# --- Frete ------------------------------------------------------------------
FREE_SHIPPING_MIN_SUBTOTAL = 500
REGIONAL_SHIPPING_STATES = frozenset({"MG", "SP", "RJ", "ES"})
REGIONAL_SHIPPING_BASE = 20
REGIONAL_SHIPPING_PER_KG = 0.4
NATIONAL_SHIPPING_BASE = 35
NATIONAL_SHIPPING_PER_KG = 0.6
EXPRESS_SHIPPING_MULTIPLIER = 1.8

# --- Impostos ---------------------------------------------------------------
TAX_RATES = {
    "MG": 0.07,
    "SP": 0.09,
    "RJ": 0.08,
    "ES": 0.07,
}
DEFAULT_TAX_RATE = 0.12

# --- Pontos de fidelidade ---------------------------------------------------
VIP_POINTS_DIVISOR = 5
DEFAULT_POINTS_DIVISOR = 10


def calculate_subtotal(items):
    """Soma preço x quantidade dos itens com quantidade positiva.

    Usa acumulação explícita (e não sum()) para manter exatamente os mesmos
    resultados de ponto flutuante da versão original.
    """
    subtotal = 0
    for item in items:
        if item["qty"] > 0:
            subtotal += item["price"] * item["qty"]
    return subtotal


def calculate_total_weight(items):
    """Soma peso x quantidade de todos os itens (peso ausente vale 0)."""
    total_weight = 0
    for item in items:
        total_weight += item.get("weight", 0) * item["qty"]
    return total_weight


def calculate_customer_discount(customer_type, subtotal):
    """Desconto concedido de acordo com o tipo de cliente."""
    if customer_type == CUSTOMER_VIP:
        is_high_value = subtotal >= VIP_HIGH_VALUE_THRESHOLD
        rate = VIP_HIGH_VALUE_DISCOUNT_RATE if is_high_value else VIP_DISCOUNT_RATE
        return subtotal * rate
    if customer_type == CUSTOMER_EMPLOYEE:
        return subtotal * EMPLOYEE_DISCOUNT_RATE
    if customer_type == CUSTOMER_REGULAR and subtotal >= REGULAR_DISCOUNT_THRESHOLD:
        return subtotal * REGULAR_DISCOUNT_RATE
    return 0


def calculate_coupon_discount(coupon, customer_type, subtotal):
    """Desconto adicional concedido pelo cupom informado."""
    if coupon == COUPON_PROMO10:
        return subtotal * PROMO10_RATE
    if coupon == COUPON_PROMO20 and subtotal >= PROMO20_MIN_SUBTOTAL:
        return subtotal * PROMO20_RATE
    if coupon == COUPON_VIP50 and customer_type == CUSTOMER_VIP:
        return VIP50_FLAT_DISCOUNT
    return 0


def calculate_discount(customer_type, coupon, subtotal):
    """Desconto total (cliente + cupom), limitado ao máximo permitido."""
    discount = calculate_customer_discount(customer_type, subtotal)
    discount += calculate_coupon_discount(coupon, customer_type, subtotal)
    return min(discount, subtotal * MAX_DISCOUNT_RATE)


def calculate_shipping(subtotal, weight, state, express):
    """Frete: grátis acima do mínimo (exceto expresso), senão por região e peso."""
    if subtotal >= FREE_SHIPPING_MIN_SUBTOTAL and not express:
        return 0

    if state in REGIONAL_SHIPPING_STATES:
        shipping = REGIONAL_SHIPPING_BASE + weight * REGIONAL_SHIPPING_PER_KG
    else:
        shipping = NATIONAL_SHIPPING_BASE + weight * NATIONAL_SHIPPING_PER_KG

    if express:
        shipping = shipping * EXPRESS_SHIPPING_MULTIPLIER
    return shipping


def calculate_tax(discounted_value, state):
    """Imposto incidente sobre o valor já com desconto, conforme o estado."""
    return discounted_value * TAX_RATES.get(state, DEFAULT_TAX_RATE)


def calculate_loyalty_points(customer_type, amount):
    """Pontos de fidelidade (parte inteira) sobre o valor total do pedido."""
    divisor = (
        VIP_POINTS_DIVISOR
        if customer_type == CUSTOMER_VIP
        else DEFAULT_POINTS_DIVISOR
    )
    return int(amount / divisor)


def find_duplicate_products(items):
    """Nomes de produtos repetidos, na ordem da primeira ocorrência."""
    name_counts = Counter(item["name"] for item in items)
    return [name for name, count in name_counts.items() if count > 1]


def print_order_summary(customer_name, subtotal, discount, shipping, tax, total):
    """Imprime o resumo do pedido processado."""
    print("Pedido processado para " + customer_name)
    print("Subtotal:", subtotal)
    print("Desconto:", discount)
    print("Frete:", shipping)
    print("Imposto:", tax)
    print("TOTAL:", total)


def process_order(customer, items, coupon="", state="MG", express=False):
    """Processa um pedido, registra-o em ORDERS_PROCESSED e o devolve."""
    customer_type = customer["type"]

    subtotal = calculate_subtotal(items)
    discount = calculate_discount(customer_type, coupon, subtotal)
    discounted_value = subtotal - discount

    shipping = calculate_shipping(
        subtotal, calculate_total_weight(items), state, express
    )
    tax = calculate_tax(discounted_value, state)

    amount = discounted_value + shipping + tax
    total = round(amount, 2)

    order = {
        "customer": customer["name"],
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "shipping": round(shipping, 2),
        "tax": round(tax, 2),
        "total": total,
        "points": calculate_loyalty_points(customer_type, amount),
        "duplicate_products": find_duplicate_products(items),
    }

    ORDERS_PROCESSED.append(order)
    print_order_summary(customer["name"], subtotal, discount, shipping, tax, total)

    return order
