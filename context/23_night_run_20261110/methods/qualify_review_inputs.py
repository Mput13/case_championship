#!/usr/bin/env python3
"""Keep raw-lineage corrections and limited review acceptance explicit."""
import json
import common_demand as m


def main():
    root=m.ROOT
    original=m.rows(root/'inputs/primary-001/dated_evidence.csv')
    corrected=m.rows(root/'inputs/primary-lineage-002/dated_evidence.csv')
    registry=m.rows(root/'inputs/primary-lineage-002/source_registry.csv')
    reg={r['source_snapshot_id']:r for r in registry}
    assert len(reg)==len(registry)
    assert len(original)==len(corrected)==209
    checked=0
    for r in corrected:
        before=original[int(r['original_csv_line'])-2]
        assert all(r[k]==v for k,v in before.items())
        source=reg[r['source_snapshot_id']]
        assert source['source_id']==r['source_id']and source['raw_sha256']==r['html_sha256']
        if r['source_id']in ['svx_schedule','svx_schedule_arr']:checked+=1
    assert checked==129
    old_mapping=m.rows(root/'inputs/data-bridge-001/candidate_addendum_primary17b/candidate_endpoint_mapping.csv')
    new_mapping=m.rows(root/'inputs/primary-lineage-002/candidate_endpoint_mapping.csv')
    assert len(old_mapping)==len(new_mapping)==386
    linked=0
    for r in new_mapping:
        before=old_mapping[int(r['original_mapping_csv_line'])-2]
        assert all(r[k]==v for k,v in before.items())
        if r['source_snapshot_id']:
            assert r['source_snapshot_id']in reg
            assert reg[r['source_snapshot_id']]['raw_sha256']==r['raw_sha256']
            linked+=1
    assert linked==58
    cards=m.rows(root/'inputs/primary-lineage-002/card_snapshot_bindings.csv');assert len(cards)==28
    for r in cards:
        assert r['source_snapshot_id']in reg and r['raw_sha256']==reg[r['source_snapshot_id']]['raw_sha256']
    reviews=[
        dict(artifact='methods-spec-v1',input_commit='344f4425ba3fbb73b45a5cbcd223089e2ca7b5d4',review_commit='b0b0830b1631b92225d67a8183d9a2792ff007cf',verdict='CHANGES',scope='v1terminology; numeric examples scoped passes',current_derivative='2a74 endpoint projection parent closure; legacy label retained',does_not_approve='budgetv2/commonv3/strategyv4/v5'),
        dict(artifact='methods-budget-v2',input_commit='2a74b05179d3619c03fdab3b038fbe7587d85eca',review_commit='2278b184bbc83c590238c9f461581e3b045a11d0',verdict='APPROVE_SCOPED',scope='8bounds/224enumerated inequalities/conditional accounting',current_derivative='cash1Mperiod-boundaries; paymentfirst1.8M; UFA4notfinalcase',does_not_approve='newproducts/prices/supply/wholecompanycash/launch'),
        dict(artifact='model_repair',input_commit='27740ffea0821aa404ecd1013d1bb141613261f3',review_commit='445a5d523d4b57d8c89b2344e1913de2e5f9dc6b',verdict='APPROVE_SCOPED',scope='replay/code/accounting/MR06/adapters',current_derivative='Q(F)policy remains proposal; D-only actualdelta0',does_not_approve='observedOD/fullbudget/MOWairport/launch'),
        dict(artifact='primary_evidence+data_bridge',input_commit='17b4f348f15ea8695688d9435933cb4965568408;abc09bbb8e62d3513749b60b252d4521997acfc3',review_commit='944b16ac2dcde846e29dac2d47e11e5143f9fc2b',verdict='CHANGES',scope='51of52boundedchecks; SVXsnapshotlineageP2',current_derivative='f1774e1f parent metadata projection; original cells retained',does_not_approve='newrawparse/correctionindependence/actualoperation/seats/fare/OD'),
        dict(artifact='primary_lineage_correction',input_commit='f1774e1f66a9483fb618ca6003abd9dc4d8563e1',review_commit='',verdict='PARENT_METADATA_JOIN_CHECKED',scope='snapshot FK and originalcells; methods owner repeated bounded join',current_derivative='209dated/386mapping/28cards verified;129SVXreceiptsbound',does_not_approve='independentcorrectionreview/rawreparse/12clockholds'),
        dict(artifact='methods-common-v3',input_commit='abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe',review_commit='7a868d1282b9c4de012e39e9fc1104d2d7f675e4',verdict='APPROVE_SCOPED_EXACT_abb1',scope='exact common demand+adapter package',current_derivative='151regions andalpha independently matched; fixedlocal-first qualification; sourceHOLDretained',does_not_approve='v4/v5/newKoverinteraction'),
        dict(artifact='methods-strategy-v4',input_commit='c24bbd36356f46763eed5a1654573b6de31adc6b',review_commit='',verdict='MR09_RUNNING',scope='exact mixed/resource/product package',current_derivative='v4 frozen output bytes unchanged; new replay sorts only tail rows',does_not_approve='v5Dguard/Koverinteraction'),
        dict(artifact='cost_kover',input_commit='afadee35ebeefe54a05bdfc5b3e224a370f90e0a',review_commit='d8634187d452343a369f7cec63be50511bb70020',verdict='CHANGES_CKR_P2_TIMEBASE; DAY1_ACCOUNTING_SCOPED_PASS',scope='original MR02 rate/accounting/overlay',current_derivative='87ee52de parenttimebase projection; hubdelayHOLD',does_not_approve='recoveryfeasibility/newderivative/raworactualcash'),
        dict(artifact='cost_kover_timebase_correction',input_commit='87ee52de15c2bdf396d9c06ba600fd413d5ab4a8',review_commit='',verdict='PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY',scope='epoch/40day1arith beforegating/4delayHOLD',current_derivative='methods owner separately recomputed12day1cancellation ledgers and8cash ledgers',does_not_approve='independentcorrectionreview/served-all delay/newportfolioorN delta'),
        dict(artifact='methods-integration-v5',input_commit='SELF_COMMIT_FROM_DELIVERY',review_commit='',verdict='OWNER_CHECKS_ONLY_INDEPENDENT_PENDING',scope='Coverlayjoin;explicit C/Ninteraction;portfoliov2Dguard',current_derivative='separate runs and contracts',does_not_approve='observedOD/wholecompanyeconomics/TEAM_ACCEPTED')]
    context=[]
    for r in m.rows(root/'runs/adapter_v1/market_publication_context.csv'):
        r=dict(r);r['original_v3_source_acceptance']=r.pop('source_acceptance')
        svx=any(x in(r['source_ids']or'').split(';')for x in ['svx_schedule','svx_schedule_arr'])
        context.append(dict(**r,current_source_input='primary-lineage-002'if svx else 'primary-001',
                            original_verdict='SJR_CHANGES_ON17b_RETAINED',
                            current_lineage_scope='CORRECTED_METADATA_FK_OWNER_CHECKED_PARENT_ACCEPTANCE_ONLY'if svx else 'UNCHANGED_SOURCE_SJR_SCOPED_CHECKS_ONLY',
                            raw_reparse='NOT_RUN_HERE',new_independent_correction_review='NOT_RUN',
                            numeric_use='CONTEXT_ONLY_NO_DEMAND_SEAT_FARE_UPGRADE',clock_holds_unchanged=True))
    old=m.OUT
    try:
        m.OUT=root/'runs/admission_v1';m.save('acceptance_matrix.csv',reviews);m.save('market_source_qualification.csv',context)
        m.save('correction_join_checks.json',dict(status='PASS_OWNER_METADATA_JOIN',dated_original_rows_preserved=209,mapping_original_rows_preserved=386,
                                                 svx_receipts_bound=129,cards=28,affected_mapping_bindings=58,
                                                 acceptance='PARENT_METADATA_JOIN_CHECKED_WITH_OWNER_REPETITION; NOT_INDEPENDENT_REVIEW',
                                                 new_raw_parse=False,original_primary_verdict='CHANGES',clock_holds=12))
    finally:m.OUT=old
    print(json.dumps(dict(dated=209,mapping=386,svx=129,cards=28)))


if __name__=='__main__':main()
