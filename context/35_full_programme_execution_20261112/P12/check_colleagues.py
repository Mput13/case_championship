"""Run project checker with its output boundary redirected to P12; never adopt refs."""
import importlib.util,json,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
repo=P.parents[2]
spec=importlib.util.spec_from_file_location('project_colleague_checker',repo/'scripts/check_colleague_updates.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.BASE=P/'qa/colleague_update';m.BASE.mkdir(parents=True,exist_ok=True)
if not (m.BASE/'colleague_refs.json').exists():shutil.copyfile(repo/'context/16_agent_research/colleague_refs.json',m.BASE/'colleague_refs.json')
m.main()
