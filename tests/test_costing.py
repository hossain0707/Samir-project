import unittest

from app import APP_NAME, DEFAULT_FONT, calculate_cost


class Product(dict):
    pass


class CostingTests(unittest.TestCase):
    def test_windows_safe_brand_and_default_font(self):
        self.assertEqual(APP_NAME, "CBDs")
        self.assertEqual(DEFAULT_FONT, "{Segoe UI} 10")

    def test_workbook_formula_equivalence(self):
        product = Product(purchase_rmb=39, weight_g=380, shipping_rate_kg=780)
        result = calculate_cost(product, total_purchase_rmb=1000, sourcing_rmb=277.56, rate=19.2, retail=30, wholesale=20)
        self.assertAlmostEqual(result.shipping_rmb, 296.4)
        self.assertAlmostEqual(result.sourcing_rmb, 10.82484)
        self.assertAlmostEqual(result.total_rmb, 346.22484)
        self.assertAlmostEqual(result.total_bdt, 6647.517, places=3)
        self.assertAlmostEqual(result.retail_bdt, result.total_bdt * 1.30)
        self.assertAlmostEqual(result.wholesale_bdt, result.total_bdt * 1.20)

    def test_zero_total_purchase_is_safe(self):
        product = Product(purchase_rmb=0, weight_g=0, shipping_rate_kg=0)
        result = calculate_cost(product, 0, 100, 19.2, 30, 20)
        self.assertEqual(result.sourcing_rmb, 0)
        self.assertEqual(result.total_bdt, 0)


if __name__ == '__main__':
    unittest.main()
