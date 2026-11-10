#!/usr/bin/env python3
"""Bounded MR02 self-checks; explicitly not independent acceptance."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
import overlay as o


def dataset(network='H_UFA_8', scenario='base'):
    definition = json.loads((o.ROOT / 'scenario_definitions.json').read_text())
    select = lambda r: r['profile'] == definition['profile'] and r['network'] == network
    legs = [r for r in o.readcsv(o.INPUTS / 'tsiri_flights.csv') if select(r)]
    sales = []
    for line, r in enumerate(o.readcsv(o.INPUTS / 'tsiri_sales.csv'), 2):
        if select(r) and r['scenario'] == scenario:
            sales.append({**r, '_source_csv_line': line, '_journey_id': f'tsiri-sales-line-{line}'})
    caps = {r['flight_id']: r for r in o.readcsv(o.INPUTS / 'tsiri_capacity.csv') if select(r) and r['scenario'] == scenario}
    baseline = next(r for r in o.readcsv(o.INPUTS / 'tsiri_comparison.csv') if select(r) and r['scenario'] == scenario)
    return definition, legs, sales, caps, baseline


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.definition, self.legs, self.sales, self.caps, self.baseline = dataset()

    def policy(self, id):
        return copy.deepcopy(next(x for x in self.definition['scenarios'] if x['id'] == id))

    def run_policy(self, id, definition=None):
        return o.apply(self.legs, self.sales, self.caps, self.baseline, self.policy(id), definition or self.definition)

    def test_01_pinned_bytes(self):
        for file in ['source_manifest.json', 'reference_input_manifest.json']:
            manifest = json.loads((o.ROOT / file).read_text())
            for r in manifest['sources']:
                path = o.ROOT / r['local_path']
                if r.get('publication') == 'LOCAL_IGNORED_ONLY' and not path.exists():
                    continue  # raw optional on a fresh clone; recipe and hash remain.
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), r['sha256'], str(path))

    def test_02_no_kover_exact_economic_baseline(self):
        s, _, _, _ = self.run_policy('no_kover')
        self.assertEqual(s['contribution_after_overlay_before_unknown_rub'], float(self.baseline['contribution_before_base_fleet_opportunity']))
        self.assertEqual(s['overlay_delta_before_unknown_rub'], 0)
        self.assertEqual(s['lost_net_revenue_rub'], 0)

    def test_03_zero_duration_episode(self):
        d = copy.deepcopy(self.definition)
        d['episode']['end_utc_exclusive'] = d['episode']['start_utc']
        s, _, _, _ = self.run_policy('cancel_pretravel_no_protection', d)
        self.assertEqual(s['affected_physical_legs'], 0)
        self.assertEqual(s['overlay_delta_before_unknown_rub'], 0)

    def test_04_real_two_legs_one_lost_fare(self):
        _, _, js, _ = self.run_policy('cancel_pretravel_no_protection')
        r = next(r for r in js if r['origin'] == 'ARH' and r['destination'] == 'MRV')
        self.assertEqual(r['affected_leg_count'], 2)
        self.assertAlmostEqual(r['unserved_endpoint_journeys'], 39.79900399544, places=8)
        self.assertAlmostEqual(r['lost_net_revenue_rub'], 501467.45034255, places=5)
        self.assertAlmostEqual(r['lost_net_revenue_rub'], r['unserved_endpoint_journeys'] * float(r['fare_once_rub']), places=6)

    def test_05_cancel_each_of_two_legs_same_lost_itinerary(self):
        r = next(r for r in self.sales if r['origin'] == 'ARH' and r['destination'] == 'MRV' and r['day'] == '1')
        a, b = r['flight_ids'].split(';')
        self.assertEqual(o.lost_journeys([r], {a}), o.lost_journeys([r], {b}))
        self.assertEqual(o.lost_journeys([r], {a, b}), [r])

    def test_06_shared_capacity_conserved_every_policy(self):
        for policy in self.definition['scenarios']:
            _, legs, _, _ = self.run_policy(policy['id'])
            for r in legs:
                self.assertLessEqual(r['remaining_occupied'], r['remaining_capacity'] + o.TOL)
                self.assertGreaterEqual(r['remaining_occupied'], -o.TOL)

    def test_07_overbooking_rejected(self):
        leg = self.legs[0]
        sale = {'flight_ids': leg['id'], 'sold_journeys': '60'}
        with self.assertRaisesRegex(ValueError, 'shared seat capacity exceeded'):
            o.validate_capacity([sale, sale], [leg], {leg['id']: 100})

    def test_08_half_open_interval(self):
        leg = self.legs[0]
        t = o.instant(leg, 'departure')
        d = dict(self.definition['episode'], start_utc=t.isoformat(), end_utc_exclusive=(t + o.timedelta(minutes=1)).isoformat())
        self.assertTrue(o.hits(leg, d))
        d.update(start_utc=(t - o.timedelta(minutes=1)).isoformat(), end_utc_exclusive=t.isoformat())
        self.assertFalse(o.hits(leg, d))

    def test_09_delay_keeps_fare_and_seats(self):
        s, legs, js, _ = self.run_policy('delay_bank_next_day_fare_retained')
        self.assertEqual(s['lost_net_revenue_rub'], 0)
        self.assertEqual(s['unserved_endpoint_journeys'], 0)
        self.assertEqual(s['overlay_delta_before_unknown_rub'], 0)
        self.assertTrue(any(r['retained_net_fare_rub'] > 0 for r in js))
        for r in legs:
            if r['action'] == 'delay':
                self.assertGreaterEqual(r['conditional_actual_departure_utc'], self.definition['episode']['end_utc_exclusive'])

    def test_10_delay_within_closure_rejected(self):
        policy = self.policy('delay_bank_next_day_fare_retained')
        policy['delay_minutes'] = 1
        with self.assertRaisesRegex(ValueError, 'still in restriction'):
            o.apply(self.legs, self.sales, self.caps, self.baseline, policy, self.definition)

    def test_11_delay_beyond_horizon_rejected(self):
        policy = self.policy('delay_bank_next_day_fare_retained')
        policy['delay_minutes'] = 1440 * 8
        with self.assertRaisesRegex(ValueError, 'outside tested weekly horizon'):
            o.apply(self.legs, self.sales, self.caps, self.baseline, policy, self.definition)

    def test_12_retained_crew_and_unknown_full_budget(self):
        a, _, _, _ = self.run_policy('no_kover')
        b, _, _, _ = self.run_policy('cancel_usage_billed_sensitivity')
        self.assertEqual(a['crew_cost_retained_rub'], b['crew_cost_retained_rub'])
        self.assertEqual(b['saved_crew_rub'], 0)
        self.assertIsNone(b['full_budget_profit_rub'])
        self.assertIsNone(b['actual_full_cash_peak_rub'])

    def test_13_cash_refund_not_second_expense(self):
        s, _, _, es = self.run_policy('cancel_pretravel_no_protection')
        refund = next(e for e in es if e['event'] == 'refund_precollected_net_fare_once')
        self.assertEqual(refund['delta_pnl_rub'], 0)
        self.assertAlmostEqual(refund['delta_cash_rub'], -6496147.739848063, places=5)
        self.assertAlmostEqual(sum(e['delta_pnl_rub'] for e in es), 854454.44680853, places=5)
        self.assertAlmostEqual(sum(e['delta_cash_rub'] for e in es), s['overlay_delta_before_unknown_rub'], places=5)
        self.assertAlmostEqual(s['additional_cash_peak_timing_stress_rub'], 6078104.30319147, places=5)

    def test_14_restrictions_removed_preserves_other_risks(self):
        a, _, _, _ = self.run_policy('no_kover')
        b, _, _, _ = self.run_policy('restrictions_removed_other_risks_retained')
        self.assertEqual(a['contribution_after_overlay_before_unknown_rub'], b['contribution_after_overlay_before_unknown_rub'])
        self.assertTrue(self.definition['other_risks']['preserve_author_bundle'])
        self.assertGreater(len(self.definition['other_risks']['remaining']), 0)
        self.assertGreater(o.parameters('base')[0]['deicing_probability'], 0)

    def test_15_impossible_avoidable_share_rejected(self):
        d = copy.deepcopy(self.definition)
        d['avoidability_profiles']['fuel_and_unstarted_pax_only']['crew'] = 1.01
        with self.assertRaisesRegex(ValueError, 'invalid avoidable share'):
            self.run_policy('cancel_pretravel_no_protection', d)

    def test_16_old_migration_restoration_unknown(self):
        policy = self.policy('cancel_pretravel_no_protection')
        policy['old_migration_restored_fraction'] = 1
        with self.assertRaisesRegex(ValueError, 'protected-inventory adapter'):
            o.apply(self.legs, self.sales, self.caps, self.baseline, policy, self.definition)

    def test_17_direct_control_has_no_ufa_exposure(self):
        d, legs, sales, caps, baseline = dataset('D_case')
        s, _, _, _ = o.apply(legs, sales, caps, baseline, self.policy('cancel_pretravel_no_protection'), d)
        self.assertEqual(s['affected_physical_legs'], 0)
        self.assertEqual(s['overlay_delta_before_unknown_rub'], 0)

    def test_18_narrow_cancel_reports_template_gap(self):
        d = copy.deepcopy(self.definition)
        # Cancel only first UFA departure; no invented automatic rotation cascade.
        leg = self.legs[0]
        d['episode']['start_utc'] = o.instant(leg, 'departure').isoformat()
        d['episode']['end_utc_exclusive'] = (o.instant(leg, 'departure') + o.timedelta(minutes=1)).isoformat()
        s, _, _, _ = self.run_policy('cancel_pretravel_no_protection', d)
        self.assertEqual(s['template_rotation_status'], 'UNRESOLVED_TEMPLATE_DISCONTINUITY')


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Boundaries)
    names = [test.id().split('.')[-1] for test in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    failed = {test.id().split('.')[-1]: detail for test, detail in result.failures + result.errors}
    o.writejson(o.ROOT / 'checks.json', dict(result='PASS' if result.wasSuccessful() else 'FAIL',
        test_count=result.testsRun, checks=[dict(id=name, status='FAIL' if name in failed else 'PASS') for name in names],
        failure_details=failed, scope='bounded author/export arithmetic and conditional stress self-checks',
        independent_review='PENDING; self-checks are not independent acceptance', market_launch='NOT_ACCEPTED'))
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
