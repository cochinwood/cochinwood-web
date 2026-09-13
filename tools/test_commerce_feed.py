import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from prepare_commerce import (ROOT, issues, policy_content_sha256, records,
                              prepare, public_url, valid_gtin)


def approved_fixture():
    c = json.loads((ROOT/'commerce-preview/config/catalogue.synthetic.json').read_text(encoding='utf-8'))
    # Fictional test configuration only; never written to the actual proposal.
    c['synthetic'] = False
    for p in c['products']:
        p['product_url'] = 'https://www.cochinwood.in/shop/' + p['sku']
        p['actual_product_photo_url'] = 'https://www.cochinwood.in/files/' + p['sku'] + '.webp'
    policy_sources = {
        'delivery_url': ('https://www.cochinwood.in/shipping-policy',
                         'content/pages/shipping-policy.html', ['unloading']),
        'returns_url': ('https://www.cochinwood.in/return-refund-policy',
                        'content/pages/return-refund-policy.html', ['damage_reporting', 'refunds']),
        'cancellation_url': ('https://www.cochinwood.in/terms-and-conditions',
                             'content/pages/terms.html', ['cancellation']),
    }
    c['policies']['reviewed_pages'] = {}
    for field, (url, source, covers) in policy_sources.items():
        c['policies'][field] = url
        c['policies']['reviewed_pages'][field] = {
            'url': url,
            'source_path': source,
            'content_sha256': policy_content_sha256(ROOT/source),
            'version': c['policies']['version'],
            'reviewed_by': 'Synthetic fixture reviewer',
            'reviewed_at': '2026-09-08T12:00:00+05:30',
            'covers': covers,
        }
    c['payment'].update(enabled=True, uat_passed=True, commercial_terms_approved=True)
    c['payment'].update(model='icici_api', callback_verified=True,
                        status_reconciliation_verified=True, refunds_verified=True,
                        final_total_before_commitment=True, purchase_confirmation_verified=True,
                        delivery_estimate_verified=True, billing_address_unrestricted=True)
    for k in c['merchant']: c['merchant'][k] = True
    return c


class MerchantPreparationTests(unittest.TestCase):
    def test_valid_policy_urls_without_content_review_evidence_fail(self):
        c = approved_fixture()
        del c['policies']['reviewed_pages']
        self.assertIn('policies.reviewed_pages', {i['field'] for i in issues(c)})

    def test_policy_evidence_must_match_content_route_version_and_topics(self):
        mutations = {
            'content_sha256': '0' * 64,
            'source_path': 'content/pages/privacy.html',
            'version': 'different-version',
            'covers': [],
            'reviewed_by': '   ',
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                c = approved_fixture()
                c['policies']['reviewed_pages']['delivery_url'][field] = value
                evidence_fields = {i['field'] for i in issues(c)}
                self.assertTrue(any(name.startswith('policies.reviewed_pages.delivery_url')
                                    for name in evidence_fields))

    def test_held_unapproved_marine_variants_cannot_enter_feed(self):
        c = approved_fixture()
        for p in c['products']:
            if p['staff_product_key'] == 'prem_marine_gurjan':
                p.update(active=False, product_identity_approved=False, unit_price_paise=None,
                         stock=None, actual_product_photo_url=None, image_approved=False)
        self.assertEqual(issues(c), [])
        offered, _ = records(c)
        self.assertEqual(len(offered), 2)
        self.assertTrue(all(row['id'].startswith('prem_hw_gurjan') for row in offered))

    def test_real_configuration_keeps_launch_blocked_after_price_approval(self):
        c = json.loads((ROOT/'commerce-preview/config/catalogue.proposed.json').read_text(encoding='utf-8'))
        fields = {i['field'] for i in issues(c)}
        self.assertIn('approval', fields)
        self.assertNotIn('tax', fields)
        self.assertFalse(any(field.endswith('.unit_price_paise') for field in fields))
        self.assertIn('products.prem_hw_gurjan_12.stock', fields)
        self.assertIn('delivery.rules', fields)
        self.assertIn('payment.uat_passed', fields)
        with tempfile.TemporaryDirectory() as temp:
            report = prepare(ROOT/'commerce-preview/config/catalogue.proposed.json', temp, release=True)
            self.assertFalse(report['ready_for_merchant_export'])
            self.assertFalse(report['submitted'])
            for name in ('merchant-feed.xml', 'merchant-feed.tsv', 'product-offers.json'):
                self.assertFalse((Path(temp)/name).exists())

    def test_fully_reviewed_fixture_can_generate_consistent_feed(self):
        c = approved_fixture()
        self.assertEqual(issues(c), [])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'fixture.json'; path.write_text(json.dumps(c))
            report = prepare(path, Path(temp)/'out', release=True)
            self.assertTrue(report['ready_for_merchant_export'])
            self.assertFalse(report['submitted'])
            items = ET.parse(Path(temp)/'out/merchant-feed.xml').findall('./channel/item')
            self.assertEqual(len(items), 4)
            data = json.loads((Path(temp)/'out/product-offers.json').read_text())
            ns = {'g':'http://base.google.com/ns/1.0'}
            for item, product in zip(items, data):
                self.assertEqual(item.find('g:price', ns).text, product['offers']['price'] + ' INR')
                self.assertEqual(item.find('g:link', ns).text, product['offers']['url'])
                self.assertEqual(item.find('g:image_link', ns).text, product['image'][0])

    def test_invoice_or_invalid_stock_policy_cannot_generate_fixed_stock_offers(self):
        for policy in ({'mode':'staff_per_invoice','approved':True}, None, {},
                       {'mode':'unknown'}, 'fixed_pool'):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as temp:
                c = approved_fixture()
                c['inventory_policy'] = policy
                self.assertIn('inventory_policy', {i['field'] for i in issues(c)})
                with self.assertRaises(ValueError):
                    records(c)
                path = Path(temp)/'fixture.json'; path.write_text(json.dumps(c))
                output = Path(temp)/'out'
                report = prepare(path, output, release=True)
                self.assertFalse(report['ready_for_merchant_export'])
                for name in ('merchant-feed.xml', 'merchant-feed.tsv', 'product-offers.json'):
                    self.assertFalse((output/name).exists())

    def test_synthetic_fixture_never_eligible_even_if_all_flags_set(self):
        c = approved_fixture(); c['synthetic'] = True
        self.assertIn('synthetic', {i['field'] for i in issues(c)})

    def test_zero_missing_boolean_float_and_negative_price_fail(self):
        for bad in (None, 0, -1, True, 100.5, '100'):
            with self.subTest(bad=bad):
                c = approved_fixture(); c['products'][0]['unit_price_paise'] = bad
                self.assertTrue(any(i['field'].endswith('.unit_price_paise') for i in issues(c)))

    def test_minimum_quantity_price_and_out_of_stock_are_not_misrepresented(self):
        c = approved_fixture(); p = c['products'][0]
        p.update(min_quantity=5, stock=4)
        rows, data = records(c)
        self.assertEqual(rows[0]['price'], '500.00 INR')
        self.assertEqual(rows[0]['availability'], 'out_of_stock')
        self.assertEqual(rows[0]['unit_pricing_measure'], '5 ct')
        self.assertEqual(data[0]['offers']['price'], '500.00')

    def test_missing_image_or_quotation_url_prevents_release(self):
        c = approved_fixture(); p = c['products'][0]
        p.update(actual_product_photo_url=None, product_url='https://www.cochinwood.in/contact')
        fields = {i['field'] for i in issues(c)}
        self.assertIn('products.prem_hw_gurjan_12.actual_product_photo_url', fields)
        self.assertIn('products.prem_hw_gurjan_12.product_url', fields)

    def test_approved_unpublished_family_image_still_requires_public_url(self):
        proposal = json.loads((ROOT/'commerce-preview/config/catalogue.proposed.json').read_text(encoding='utf-8'))
        c = approved_fixture(); p = c['products'][0]
        c['draft_image_evidence'] = proposal['draft_image_evidence']
        p.update(actual_product_photo_url=None, image_approved=True)
        fields = {i['field'] for i in issues(c)}
        self.assertIn('products.prem_hw_gurjan_12.actual_product_photo_url', fields)

    def test_unknown_identifiers_cannot_silently_be_marked_absent(self):
        c = approved_fixture(); c['products'][0]['identifiers_not_assigned'] = False
        self.assertTrue(any(i['field'].endswith('.identifier_exists') for i in issues(c)))

    def test_gtin_checksum_and_zeros(self):
        self.assertTrue(valid_gtin('4006381333931'))
        self.assertFalse(valid_gtin('4006381333932'))
        self.assertFalse(valid_gtin('0000000000000'))

    def test_duplicate_sku_and_excluded_family(self):
        c = approved_fixture(); c['products'][1]['sku'] = c['products'][0]['sku']
        c['products'][0]['staff_product_key'] = 'commercial'
        self.assertTrue(any(i['field'].endswith('.sku') for i in issues(c)))
        self.assertTrue(any(i['field'].endswith('.staff_product_key') for i in issues(c)))

    def test_overlapping_delivery_rules_fail(self):
        c = approved_fixture(); c['delivery']['rules'].append(copy.deepcopy(c['delivery']['rules'][0]))
        c['delivery']['rules'][-1]['id'] = 'different-id'
        self.assertTrue(any(i['field'].endswith('.overlap') for i in issues(c)))

    def test_unverified_bank_or_merchant_each_blocks(self):
        for section in ('payment', 'merchant'):
            c = approved_fixture(); c[section]['enabled'] = False
            self.assertIn(section + '.enabled', {i['field'] for i in issues(c)})

    def test_invoice_payment_is_supported_without_claiming_an_api_connection(self):
        c = approved_fixture()
        c['payment'].update(model='upi_bank_verified_invoice', callback_verified=False,
                            status_reconciliation_verified=False,
                            bank_credit_verification_verified=True, invoice_acceptance_verified=True,
                            late_payment_handling_verified=True)
        self.assertEqual(issues(c), [])
        for field in ('bank_credit_verification_verified', 'invoice_acceptance_verified',
                      'late_payment_handling_verified', 'refunds_verified'):
            with self.subTest(field=field):
                broken = copy.deepcopy(c); broken['payment'][field] = False
                self.assertIn('payment.' + field, {i['field'] for i in issues(broken)})

    def test_quote_only_or_unconfirmed_upi_can_never_be_exported(self):
        for model in (None, '', 'qr_only', 'quote_request', 'razorpay'):
            with self.subTest(model=model):
                c = approved_fixture(); c['payment']['model'] = model
                self.assertIn('payment.model', {i['field'] for i in issues(c)})
        for field in ('callback_verified', 'status_reconciliation_verified', 'refunds_verified',
                      'final_total_before_commitment', 'purchase_confirmation_verified',
                      'delivery_estimate_verified', 'billing_address_unrestricted'):
            with self.subTest(field=field):
                c = approved_fixture(); c['payment'][field] = False
                self.assertIn('payment.' + field, {i['field'] for i in issues(c)})

    def test_blocked_run_removes_stale_feed_without_touching_other_files(self):
        c = approved_fixture()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'fixture.json'; output = Path(temp)/'out'
            path.write_text(json.dumps(c)); prepare(path, output, release=True)
            (output/'keep.txt').write_text('keep')
            c['approval']['status'] = 'pending'; path.write_text(json.dumps(c))
            prepare(path, output, release=True)
            self.assertFalse((output/'merchant-feed.xml').exists())
            self.assertEqual((output/'keep.txt').read_text(), 'keep')

    def test_external_preview_credentials_and_malformed_urls_fail(self):
        for value in ('https://evil.example/product', 'http://www.cochinwood.in/shop/a',
                      'https://user:pass@www.cochinwood.in/shop/a',
                      'https://www.cochinwood.in:invalid/shop/a',
                      'https://www.cochinwood.in/commerce-preview/shop/a'):
            self.assertFalse(public_url(value))

    def test_no_active_product_is_not_a_valid_launch(self):
        c = approved_fixture()
        for p in c['products']: p['active'] = False
        self.assertIn('products.active', {i['field'] for i in issues(c)})

    def test_preview_never_writes_feed_even_with_reviewed_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'fixture.json'; path.write_text(json.dumps(approved_fixture()))
            prepare(path, Path(temp)/'out', release=False)
            self.assertFalse((Path(temp)/'out/merchant-feed.xml').exists())

    def test_malformed_input_invalidates_prior_feed_and_ready_report(self):
        for broken in ('{"products":', '[]', '{"products":[null]}'):
            with self.subTest(broken=broken), tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/'fixture.json'; output = Path(temp)/'out'
                path.write_text(json.dumps(approved_fixture())); prepare(path, output, release=True)
                path.write_text(broken); report = prepare(path, output, release=True)
                self.assertFalse(report['ready_for_merchant_export'])
                self.assertFalse((output/'merchant-feed.xml').exists())
                self.assertFalse(json.loads((output/'readiness.json').read_text())['ready_for_merchant_export'])

    def test_missing_display_field_invalidates_prior_feed(self):
        with tempfile.TemporaryDirectory() as temp:
            c = approved_fixture(); path = Path(temp)/'fixture.json'; output = Path(temp)/'out'
            path.write_text(json.dumps(c)); prepare(path, output, release=True)
            del c['products'][0]['size']; path.write_text(json.dumps(c))
            report = prepare(path, output, release=True)
            self.assertFalse(report['ready_for_merchant_export'])
            self.assertFalse((output/'product-offers.json').exists())

    def test_minimum_offer_outside_delivery_bands_blocks(self):
        c = approved_fixture()
        for p in c['products']: p.update(min_quantity=50, max_quantity=60, stock=100)
        self.assertEqual(sum(i['field'].endswith('.delivery_coverage') for i in issues(c)), 4)

    def test_whitespace_only_brand_and_identifier_block(self):
        c = approved_fixture(); c['products'][0].update(brand='   ', mpn='   ')
        fields = {i['field'] for i in issues(c)}
        self.assertIn('products.prem_hw_gurjan_12.copy', fields)
        self.assertIn('products.prem_hw_gurjan_12.mpn', fields)

    def test_bharat_connect_invoice_payment_model_passes(self):
        c = approved_fixture()
        c['payment'].update(
            provider='bharat-connect-zoho',
            model='bharat_connect_invoice',
            bank_credit_verification_verified=True,
            invoice_acceptance_verified=True,
            late_payment_handling_verified=True,
            refunds_verified=True,
        )
        self.assertEqual(issues(c), [])


if __name__ == '__main__':
    unittest.main()
