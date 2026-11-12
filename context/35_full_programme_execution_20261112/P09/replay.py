"""Детерминированное воспроизведение одного опыта без изменения первичных результатов."""
import argparse,hashlib,json
from pathlib import Path
import programme_builder as b
import evaluate_programmes as e
import canonical_finalists as c

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--programme',required=True);ap.add_argument('--delivery',default='phased',choices=['phased','partial','delayed','none']);ap.add_argument('--scenario',default='base',choices=['base','cautious','bad_season']);ap.add_argument('--response',default='passive',choices=['passive','response10']);ap.add_argument('--mode',choices=['overview','canonical'],default='overview');ap.add_argument('--existing-ssj',action='store_true');ap.add_argument('--save',action='store_true');args=ap.parse_args()
    for pin in json.loads((b.ROOT/'input_pins.json').read_text()):assert hashlib.sha256((b.ROOT/pin['local_path']).read_bytes()).hexdigest()==pin['sha256'],pin['local_path']
    if args.existing_ssj:
        import existing_ssj_transfer as s;s.install();ps=json.loads((b.ROOT/'existing_ssj/programmes.json').read_text());directory=b.ROOT/'existing_ssj';assert args.delivery=='none'
    else:ps=json.loads((b.ROOT/'programmes.json').read_text())['programmes'];directory=b.ROOT/'evaluations'
    p=next(p for p in ps if p['programme_id']==args.programme);name='__'.join([args.programme,args.delivery,args.scenario,args.response]);out=b.ROOT/'replay_runs';out.mkdir(exist_ok=True)
    if args.mode=='overview':
        r=e.evaluate(p,args.delivery,args.scenario,args.response);path=out/(name+'.overview.json');e.export_result(r,path)
        expected=directory/(name+'.json');actualhash=hashlib.sha256(path.read_bytes()).hexdigest();expectedhash=hashlib.sha256(expected.read_bytes()).hexdigest()
        proof=dict(mode='P06_DISJOINT_DATE_COMPONENTS_WITH_ADDITIVE_P06_FINANCE',actual_sha256=actualhash,expected_sha256=expectedhash,byte_identical=actualhash==expectedhash,status=r['status']);assert proof['byte_identical'],proof
        if not args.save:path.unlink() # Только собственная проверенная копия; primary не трогаем.
    else:
        assert args.scenario!='bad_season','bad_season: daily varying coefficient requires separate full bundle contract'
        a,k=b.build_pair(p,args.delivery,args.scenario,args.response);full=b.core.compare(a,k);path=out/(name+'.canonical.json.gz');receipt=c.write_gzip(path,full)
        small=c.projection(full);leaves=c.verify_projection(small,full)
        if args.existing_ssj:
            expected=next(x for x in json.loads((directory/'canonical_receipts.json').read_text()) if x['name']==name)
        else:expected=json.loads((b.ROOT/'ui_results'/(name+'.receipt.json')).read_text())
        proof=dict(mode='P06_FIXED_COMPARE_CANONICAL',actual_sha256=receipt['sha256'],expected_sha256=expected['full']['sha256'],byte_identical=receipt['sha256']==expected['full']['sha256'],projection_sha256=b.digest(small),same_path_leaves=leaves);assert proof['byte_identical'],proof
        if not args.save:path.unlink()
    b.dump(out/(name+'.'+args.mode+'.proof.json'),proof);print(json.dumps(proof,ensure_ascii=False))
if __name__=='__main__':main()
