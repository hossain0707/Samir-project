import os
import tempfile
import unittest
from pathlib import Path

from app import (
    APP_NAME,
    DEFAULT_FONT,
    calculate_cost,
    calculate_partner_settlement,
    generate_batch_code,
    generate_sku,
    store_product_image,
)


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

    def test_batch_code_format(self):
        self.assertEqual(generate_batch_code("China-CBDS", "2026-08-24"), "CBDS-20260824")

    def test_sku_format_matches_business_rule(self):
        self.assertEqual(generate_sku(380, "Pink", 1272), "380P1272")
        self.assertEqual(generate_sku(75.4, "", 99.5), "075X100")

    def test_partner_settlement_balance(self):
        self.assertEqual(calculate_partner_settlement(10_000, 3_000, 1_000), 12_000)
        self.assertEqual(calculate_partner_settlement(0, 0, 1_000), -1_000)

    def test_product_image_is_copied_to_managed_storage(self):
        previous = os.environ.get("LOCALAPPDATA")
        try:
            with tempfile.TemporaryDirectory() as temporary:
                os.environ["LOCALAPPDATA"] = temporary
                source = Path(temporary) / "source.png"
                source.write_bytes(b"test-image")
                stored = Path(store_product_image(str(source)))
                self.assertTrue(stored.is_file())
                self.assertEqual(stored.parent.name, "product_images")
                self.assertEqual(stored.read_bytes(), b"test-image")
        finally:
            if previous is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = previous


if __name__ == '__main__':
    unittest.main()
