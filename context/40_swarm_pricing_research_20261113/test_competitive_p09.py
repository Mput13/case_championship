#!/usr/bin/env python3
"""Numerical contract tests; no external services or P09 writes."""
import sys
sys.dont_write_bytecode=True
import copy,json,math,unittest
from collections import defaultdict
import competitive_p09_engine as e

class CompetitionTests(unittest.TestCase):
    def setUp(self):e.configure(e.CONFIGURATIONS[1])
    def fragment(self,a='SVX',b='AER'):
        t=e.b.timestamp(e.b.date(2028,7,3),6)
        f,_=e.b.leg(a,b,t,'TEST',e.b.NEW_VARIANT,'test')
        frag=e.b.pair_fragments([f],[],'base',False,'passive')[0]
        return [f],frag
    def test_209_pairs_22_hubs(self):
        self.assertEqual(len(e.MARKETS),209)
        with (e.ROOT/'hub_weights_22.csv').open() as f:
            self.assertEqual(len(list(__import__('csv').DictReader(f))),22)
        for m in e.MARKETS.values():
            self.assertNotIn('WZ',m['direct_competitors'])
            self.assertTrue(0<=m['W_comp_2027']<=m['W_comp_2028']<=1)
    def test_inclusive_value_neutral(self):
        ps=json.loads((e.P09/'programmes.json').read_text())['programmes']
        self.assertEqual(e.neutral_calibration_test(next(p for p in ps if p['programme_id']=='VOG_HYBRID'))['status'],'PASS')
    def test_finite_direct_capacity_and_conservation(self):
        fs,f=self.fragment();nf=e.transform(f,fs)
        for m in nf['markets']:m['potential_journeys']*=100
        direct=[p for p in nf['products'] if p['owner']=='AIR_COMP_DIRECT']
        self.assertTrue(direct)
        for p in direct:p['capacity']=.1
        bundle=dict(flights=fs,markets=nf['markets'],products=nf['products'],choice_model=e.b.p05.coefficients('base'),contracts=[],economic_events=[])
        a=e.b.allocate(bundle,nf['products']);e.verify_allocation(bundle,nf['products'],a)
        ps={p['product_id']:p for p in direct}
        for x in a['allocations']:
            if x['product_id'] in ps:self.assertLessEqual(x['final_choice'],.10000001)
    def test_direct_price_corridor(self):
        fs,f=self.fragment();nf=e.transform(f,fs)
        cp=[p for p in nf['products'] if p['owner']=='AIR_COMP_DIRECT']
        for p in nf['products']:
            if p['owner']=='RW':self.assertLessEqual(p['gross_fare'],min(q['gross_fare'] for q in cp)*1.10+1e-8)
    def test_response_never_raises_or_crosses_floor(self):
        fs,f=self.fragment();old=next(p for p in f['products'] if p.get('outside_component')=='UNREPRESENTED_EXISTING_AIR');m=f['markets'][0]
        e.configure(e.CONFIGURATIONS[3]);passive=e.competitor_products(m,old,False);active=e.competitor_products(m,old,True)
        for p,q in zip(passive,active):
            if p['owner']=='AIR_COMP_DIRECT':
                self.assertLessEqual(q['gross_fare'],p['gross_fare'])
                self.assertGreaterEqual(q['gross_fare']+1e-8,min(p['gross_fare'],q['var_floor_gross']))
    def test_expansion_only_from_q4_2027(self):
        e.configure(e.CONFIGURATIONS[5])
        self.assertEqual(e.expansion_intensity('2027-09-30'),0)
        self.assertEqual(e.expansion_intensity('2027-10-01'),.25)
        self.assertEqual(e.expansion_intensity('2028-01-01'),1)
    def test_zero_new_rw_subsidies(self):
        for m in e.MARKETS.values():self.assertEqual(m['rw_future_support_baseline_rub'],0)
    def test_moscow_city_pool_physical_competitors_and_vat(self):
        fs,f=self.fragment('KGD','SVO');f=e.annotate_physical_markets([f])[0]
        self.assertTrue(all(m['physical_airport_pair']=='KGD-SVO' for m in f['markets']))
        self.assertTrue(all('MOW' in m['demand_pool_id'] for m in f['markets']))
        nf=e.transform(f,fs)
        self.assertTrue(any(p.get('carrier')=='DP' for p in nf['products']))
        for p in nf['products']:
            if p['owner']=='RW':self.assertAlmostEqual(p['net_fare'],p['gross_fare']*.97/1.1)

if __name__=='__main__':unittest.main(verbosity=2)
