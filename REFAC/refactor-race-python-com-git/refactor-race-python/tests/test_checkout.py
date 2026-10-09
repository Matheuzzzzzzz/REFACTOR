# test_legacy_checkout.py

import contextlib
import io

import pytest

import legacy_checkout
from legacy_checkout import (
    ORDERS_PROCESSED,
    calculate_coupon_discount,
    calculate_customer_discount,
    calculate_discount,
    calculate_loyalty_points,
    calculate_shipping,
    calculate_subtotal,
    calculate_tax,
    calculate_total_weight,
    find_duplicate_products,
    process_order,
)


def test_regular_customer():
    customer = {
        "name": "Ana",
        "type": "regular"
    }

    items = [
        {
            "name": "Notebook",
            "price": 1000.00,
            "qty": 1,
            "weight": 2
        }
    ]

    result = process_order(
        customer,
        items,
        state="MG"
    )

    assert result["subtotal"] == 1000.00
    assert result["discount"] == 50.00
    assert result["shipping"] == 0
    assert result["tax"] == 66.50
    assert result["total"] == 1016.50


def test_vip_customer():
    customer = {
        "name": "Carlos",
        "type": "vip"
    }

    items = [
        {
            "name": "Monitor",
            "price": 600,
            "qty": 2,
            "weight": 3
        }
    ]

    result = process_order(
        customer,
        items,
        state="SP"
    )

    assert result["subtotal"] == 1200
    assert result["discount"] == 180


def test_coupon():
    customer = {
        "name": "Maria",
        "type": "regular"
    }

    items = [
        {
            "name": "Teclado",
            "price": 200,
            "qty": 2,
            "weight": 1
        }
    ]

    result = process_order(
        customer,
        items,
        coupon="PROMO10",
        state="MG"
    )

    assert result["discount"] == 40


def test_duplicate_products():
    customer = {
        "name": "João",
        "type": "regular"
    }

    items = [
        {"name": "Mouse", "price": 100, "qty": 1, "weight": 0.2},
        {"name": "Mouse", "price": 100, "qty": 1, "weight": 0.2},
        {"name": "Teclado", "price": 200, "qty": 1, "weight": 1}
    ]

    result = process_order(customer, items)

    assert result["duplicate_products"] == ["Mouse"]


# ---------------------------------------------------------------------------
# Testes de caracterização adicionais
# Os valores esperados foram obtidos executando a versão legada original.
# ---------------------------------------------------------------------------

def make_item(price, qty=1, weight=0, name="Produto"):
    return {"name": name, "price": price, "qty": qty, "weight": weight}


def make_customer(customer_type):
    return {"name": "Cliente", "type": customer_type}


def run_order(customer_type, items, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return process_order(make_customer(customer_type), items, **kwargs)


# (tipo, itens, argumentos, subtotal, desconto, frete, imposto, total, pontos)
ORDER_SCENARIOS = [
    pytest.param("vip", [make_item(500)], {}, 500, 50.0, 0, 31.5, 481.5, 96,
                 id="vip_below_1000_gets_10_percent"),
    pytest.param("vip", [make_item(1000)], {}, 1000, 150.0, 0, 59.5, 909.5, 181,
                 id="vip_at_1000_gets_15_percent"),
    pytest.param("employee", [make_item(200)], {}, 200, 40.0, 20.0, 11.2, 191.2, 19,
                 id="employee_gets_20_percent"),
    pytest.param("regular", [make_item(799)], {}, 799, 0, 0, 55.93, 854.93, 85,
                 id="regular_below_800_gets_no_discount"),
    pytest.param("regular", [make_item(800)], {}, 800, 40.0, 0, 53.2, 813.2, 81,
                 id="regular_at_800_gets_5_percent"),
    pytest.param("guest", [make_item(1000)], {}, 1000, 0, 0, 70.0, 1070.0, 107,
                 id="unknown_customer_type_gets_no_discount"),
    pytest.param("regular", [make_item(200)], {"coupon": "PROMO10"},
                 200, 20.0, 20.0, 12.6, 212.6, 21, id="promo10_gives_10_percent"),
    pytest.param("regular", [make_item(499)], {"coupon": "PROMO20"},
                 499, 0, 20.0, 34.93, 553.93, 55,
                 id="promo20_ignored_below_500"),
    pytest.param("regular", [make_item(500)], {"coupon": "PROMO20"},
                 500, 100.0, 0, 28.0, 428.0, 42,
                 id="promo20_applies_at_500"),
    pytest.param("vip", [make_item(200)], {"coupon": "VIP50"},
                 200, 50.0, 20.0, 10.5, 180.5, 36,
                 id="vip50_gives_flat_50_to_vip"),
    pytest.param("regular", [make_item(200)], {"coupon": "VIP50"},
                 200, 0, 20.0, 14.0, 234.0, 23,
                 id="vip50_ignored_for_non_vip"),
    pytest.param("regular", [make_item(200)], {"coupon": "ABC"},
                 200, 0, 20.0, 14.0, 234.0, 23, id="unknown_coupon_is_ignored"),
    pytest.param("regular", [make_item(200)], {"coupon": "promo10"},
                 200, 0, 20.0, 14.0, 234.0, 23,
                 id="coupon_is_currently_case_sensitive"),
    pytest.param("employee", [make_item(1000)], {"coupon": "PROMO20"},
                 1000, 250.0, 0, 52.5, 802.5, 80,
                 id="discount_is_capped_at_25_percent"),
    pytest.param("vip", [make_item(100)], {"coupon": "VIP50"},
                 100, 25.0, 20.0, 5.25, 100.25, 20,
                 id="flat_coupon_is_also_capped_at_25_percent"),
    pytest.param("regular", [make_item(500, weight=2)], {},
                 500, 0, 0, 35.0, 535.0, 53, id="free_shipping_from_500"),
    pytest.param("regular", [make_item(499, weight=2)], {},
                 499, 0, 20.8, 34.93, 554.73, 55,
                 id="regional_shipping_uses_weight"),
    pytest.param("regular", [make_item(499, weight=2)], {"state": "BA"},
                 499, 0, 36.2, 59.88, 595.08, 59,
                 id="other_states_use_national_shipping"),
    pytest.param("regular", [make_item(500, weight=2)], {"express": True},
                 500, 0, 37.44, 35.0, 572.44, 57,
                 id="express_shipping_is_never_free"),
    pytest.param("regular", [make_item(100, weight=2)],
                 {"state": "BA", "express": True},
                 100, 0, 65.16, 12.0, 177.16, 17,
                 id="express_multiplies_national_shipping"),
    pytest.param("regular", [make_item(100)], {"state": "SP"},
                 100, 0, 20.0, 9.0, 129.0, 12, id="sp_tax_is_9_percent"),
    pytest.param("regular", [make_item(100)], {"state": "RJ"},
                 100, 0, 20.0, 8.0, 128.0, 12, id="rj_tax_is_8_percent"),
    pytest.param("regular", [make_item(100)], {"state": "ES"},
                 100, 0, 20.0, 7.0, 127.0, 12, id="es_tax_is_7_percent"),
    pytest.param("regular", [make_item(100)], {"state": "BA"},
                 100, 0, 35.0, 12.0, 147.0, 14,
                 id="other_states_tax_is_12_percent"),
    pytest.param("vip", [make_item(100)], {},
                 100, 10.0, 20.0, 6.3, 116.3, 23,
                 id="vip_points_use_divisor_5"),
    pytest.param("regular", [make_item(100)], {},
                 100, 0, 20.0, 7.0, 127.0, 12,
                 id="regular_points_use_divisor_10"),
    pytest.param("regular", [], {}, 0, 0, 20.0, 0.0, 20.0, 2,
                 id="empty_order_still_pays_base_shipping"),
]


@pytest.mark.parametrize(
    "customer_type, items, kwargs, subtotal, discount, shipping, tax, total, points",
    ORDER_SCENARIOS,
)
def test_order_totals_match_legacy_behavior(
    customer_type, items, kwargs, subtotal, discount, shipping, tax, total, points
):
    result = run_order(customer_type, items, **kwargs)

    assert result["subtotal"] == subtotal
    assert result["discount"] == discount
    assert result["shipping"] == shipping
    assert result["tax"] == tax
    assert result["total"] == total
    assert result["points"] == points


def test_items_with_non_positive_quantity_are_ignored_in_subtotal():
    items = [make_item(100, qty=0, weight=5), make_item(50, qty=2, weight=1)]

    result = run_order("regular", items)

    assert result["subtotal"] == 100
    assert result["shipping"] == 20.8


def test_item_without_weight_counts_as_zero_weight():
    items = [{"name": "Servico", "price": 100, "qty": 1}]

    result = run_order("regular", items)

    assert result["shipping"] == 20.0


def test_duplicate_products_are_listed_once_in_order_of_first_occurrence():
    items = [
        make_item(10, name="A"),
        make_item(10, name="B"),
        make_item(10, name="A"),
        make_item(10, name="B"),
        make_item(10, name="A"),
    ]

    result = run_order("regular", items)

    assert result["duplicate_products"] == ["A", "B"]


def test_order_without_repeated_products_has_no_duplicates():
    items = [make_item(10, name="A"), make_item(10, name="B")]

    assert run_order("regular", items)["duplicate_products"] == []


def test_processed_order_is_registered_in_global_history():
    before = len(ORDERS_PROCESSED)

    result = run_order("regular", [make_item(100)])

    assert len(ORDERS_PROCESSED) == before + 1
    assert ORDERS_PROCESSED[-1] == result


def test_order_summary_is_printed_with_unrounded_values():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        process_order(make_customer("regular"), [make_item(100)])

    assert output.getvalue().splitlines() == [
        "Pedido processado para Cliente",
        "Subtotal: 100",
        "Desconto: 0",
        "Frete: 20.0",
        "Imposto: 7.000000000000001",
        "TOTAL: 127.0",
    ]


# ---------------------------------------------------------------------------
# Testes unitários das funções extraídas
# ---------------------------------------------------------------------------

def test_calculate_subtotal_sums_only_positive_quantities():
    items = [make_item(10, qty=2), make_item(99, qty=0), make_item(5, qty=-1)]

    assert calculate_subtotal(items) == 20


def test_calculate_total_weight_multiplies_weight_by_quantity():
    items = [make_item(1, qty=3, weight=2), {"name": "x", "price": 1, "qty": 4}]

    assert calculate_total_weight(items) == 6


def test_customer_discount_for_each_customer_type():
    assert calculate_customer_discount("vip", 1000) == 150
    assert calculate_customer_discount("vip", 999) == pytest.approx(99.9)
    assert calculate_customer_discount("employee", 100) == 20
    assert calculate_customer_discount("regular", 800) == 40
    assert calculate_customer_discount("regular", 799) == 0
    assert calculate_customer_discount("other", 5000) == 0


def test_coupon_discount_rules():
    assert calculate_coupon_discount("PROMO10", "regular", 100) == 10
    assert calculate_coupon_discount("PROMO20", "regular", 500) == 100
    assert calculate_coupon_discount("PROMO20", "regular", 499) == 0
    assert calculate_coupon_discount("VIP50", "vip", 100) == 50
    assert calculate_coupon_discount("VIP50", "regular", 100) == 0
    assert calculate_coupon_discount("", "vip", 100) == 0


def test_total_discount_never_exceeds_25_percent_of_subtotal():
    assert calculate_discount("employee", "PROMO20", 1000) == 250


def test_shipping_is_free_at_threshold_unless_express():
    assert calculate_shipping(500, 10, "MG", express=False) == 0
    assert calculate_shipping(500, 10, "MG", express=True) == pytest.approx(43.2)


def test_shipping_depends_on_region_and_weight():
    assert calculate_shipping(100, 10, "SP", express=False) == 24
    assert calculate_shipping(100, 10, "BA", express=False) == 41


def test_tax_rate_by_state_with_default():
    assert calculate_tax(100, "MG") == pytest.approx(7)
    assert calculate_tax(100, "AM") == pytest.approx(12)


def test_loyalty_points_truncate_and_vip_earns_more():
    assert calculate_loyalty_points("vip", 109.9) == 21
    assert calculate_loyalty_points("regular", 109.9) == 10


def test_find_duplicate_products_returns_each_name_once():
    items = [make_item(1, name="M"), make_item(1, name="M"), make_item(1, name="M")]

    assert find_duplicate_products(items) == ["M"]


def test_module_exposes_orders_history_as_list():
    assert isinstance(legacy_checkout.ORDERS_PROCESSED, list)
