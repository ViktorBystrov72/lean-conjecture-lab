"""Record search counts from the individual logs and check their consistency."""
import csv
import json
from pathlib import Path
from collections import Counter

ROOT=Path.cwd()
def readcsv(path):
    with path.open() as f:return list(csv.DictReader(f))

def main():
    base=ROOT
    dirs=sorted([*base.glob('scratch*'),base/'pilot55',base/'transfer55',*(base/'all-orbits').glob('orbit-*')])
    rack=[];m=Counter();startstyles=Counter()
    for folder in dirs:
        stats=json.loads((folder/'summary.json').read_text())
        records=readcsv(folder/'rounds.csv')
        assert len(records)==stats['attempted'] and stats['attempted']>0
        rack+=records;m[int(stats['assigned_orbit'])]+=stats['attempted']
        startstyles.update(r['start'] for r in records)
    assert len(m)==187
    dirs=sorted(base.glob('chart*'));lp=[]
    for f in dirs:
        if f.is_dir():
            s=json.loads((f/'summary.json').read_text())
            assert len(readcsv(f/'rounds.csv'))==2*s['feasible_charts']
            lp.append(s)
    leaf=json.loads((base/'leaf55-search/summary.json').read_text())
    leaf_rows=readcsv(base/'leaf55-search/rounds.csv')
    assert len(leaf_rows)==leaf['leaf_starts']
    result=dict(rack_attempts=len(rack),rack_classes=len(m),rack_counts=dict(sorted(m.items())),
        rack_start_styles=dict(startstyles),matched_normalized_orbits=sum(int(r['assigned']==r['tag_before_release']) for r in rack),
        matched_orbit55=sum(int(r['assigned']=='55' and r['tag_before_release']=='55') for r in rack),
        orbit55_best_matching_repaired=min(float(r['repaired_before_release']) for r in rack if r['assigned']=='55' and r['tag_before_release']=='55'),
        lp_charts_attempted=sum(s['chart_attempts'] for s in lp),lp_feasible=sum(s['feasible_charts'] for s in lp),
        classes_in_lp=sorted(s['orbit'] for s in lp),leaf55_starts=len(leaf_rows),leaf55_counts=dict(Counter(r['leaf'] for r in leaf_rows)),
        leaf55_matching_repaired_min=min(float(r['assigned_L']) for r in leaf_rows if r['assigned_orbit']=='55'),
        total_distinct_rack_and_leaf_starts=len(rack)+len(leaf_rows))
    (ROOT/'run-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k!='rack_counts'})
if __name__=='__main__':main()
