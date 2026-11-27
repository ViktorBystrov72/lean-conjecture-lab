"""Recreate the numerical experiment in a new directory, with a fixed library and source pin."""
import argparse
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE=Path(__file__).resolve().parent
STUDY=HERE.parents[1]
HISTORY=STUDY/'search-history'

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def add_once(code,marker,replacement):
    if code.count(marker)!=1:raise ValueError(f'Unexpected physical optimizer source: {marker}')
    return code.replace(marker,replacement,1)

def build(work):
    code=(HISTORY/'packing.cpp').read_text()
    anchor='double cost(const Vec& x,double weight,unsigned fixed, Vec& grad) {'
    code=add_once(code,anchor,'#include "rack_terms.inc"\n'+anchor)
    anchor='    for(int i=0;i<n;i++) if(fixed&(1u<<i)) grad[3*i+2]=0;'
    code=add_once(code,anchor,'    apply_fields(x,weight,grad,cost);\n'+anchor)
    code+='\n#include "rack_exports.inc"\n'
    src=work/'conditioned.cpp';src.write_text(code)
    flags=['-dynamiclib'] if platform.system()=='Darwin' else ['-shared','-fPIC']
    subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O3',*flags,'-I',HERE,src,'-o',work/'packing.dylib'],check=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path,help='new run directory')
    ap.add_argument('--smoke',action='store_true',help='exercise the free-start and LP code paths with local historical data')
    ap.add_argument('--source',type=Path,help='optional local Git clone with the pinned Mira revision, for leaf mode')
    ap.add_argument('--mira-seed',type=Path,help='optional numerical six-tilt seed from the preceding search')
    a=ap.parse_args()
    work=a.output.resolve();work.mkdir(parents=True,exist_ok=False);build(work)
    env=dict(os.environ,PACK18_RUN=str(work),OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',OMP_NUM_THREADS='1')
    def run(file,*params):
        subprocess.run([sys.executable,HERE/file,*map(str,params)],cwd=work,env=env,check=True)
    def rack(k,seed,n,out,extra=()):
        run('rack_search.py','--orbit',k,'--seed',seed,'--count',n,'--out',out,*extra)
    def lp(k,seed,n,out,files):
        run('chart_lp.py','--orbit',k,'--seed',seed,'--count',n,'--out',out,*files)
    seeds=sorted((HISTORY/'seeds').glob('*.json'))
    if a.smoke:
        rack(55,553241,6,'pilot55')
        lp(55,553284,20,'chart55',seeds)
        return
    audit=load_module('audit_replay',STUDY/'audit'/'replay.py')
    source=audit.source_files(a.source.resolve() if a.source else None,work)
    if a.mira_seed:
        mira=a.mira_seed.resolve()
    else:
        import json
        import math
        from fractions import Fraction
        def value(pair):
            a0,b0=map(Fraction,pair)
            return float(a0)+float(b0)*math.sqrt(7)
        raw=json.loads((source/'six-tilt18.json').read_text())
        c=(1+math.sqrt(7))/4
        s=(math.sqrt(7)-1)/4
        poses=[[value(x),value(y),math.atan(s/c) if t else 0.] for _,t,x,y in raw['centers']]
        mira=work/'mira-six-tilt.json'
        mira.write_text(json.dumps({'side':(7+math.sqrt(7))/2,'squares':poses}))
    seeds=sorted(seeds+[mira],key=lambda p:p.name)
    jobs=[(55,553241,500,'pilot55'),(55,553242,3800,'scratch55'),(137,1373247,1200,'scratch137'),
          (92,923249,1200,'scratch92'),(53,533251,1200,'scratch53'),(82,823246,1800,'scratch82'),(115,1153248,1800,'scratch115')]
    for job in jobs:rack(*job)
    rack(55,553243,3500,'transfer55',['--external',*seeds,'scratch55/best-assigned.json'])
    run('sweep.py',0,1,'--count',24)
    lp(55,553284,1400,'chart55',[*seeds,'scratch55/best-assigned.json','pilot55/best-assigned.json'])
    for k in [53,82,92,115,137]:
        lp(k,int(f'400{k}'),400,f'chart{k}',[*seeds,f'scratch{k}/best-assigned.json'])
    env['PACK18_REPLAY']=str(source)
    run('prepare_leaf.py')
    run('leaf_run.py','--count',1400,'--rng',550753,'--out','leaf55-search')
    run('aggregate.py')
    run('verify_results.py','--run',work)
if __name__=='__main__':main()
