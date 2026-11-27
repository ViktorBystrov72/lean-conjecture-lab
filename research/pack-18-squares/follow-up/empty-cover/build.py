"""Build the verified centre-domain solver with closed angle cuts enabled."""
import argparse
import hashlib
from pathlib import Path
import os
import subprocess
import tempfile

PARENT=Path(__file__).resolve().parent.parent/'terminal-audit'/'case_audit.cpp'
PIN='055d0ff0c503d66e24e3905e08f480f2db64d342e5f4d64e57ae3b0c9928c6a7'

ANGLES=r'''
  // The calling proof tree puts all angular cuts before coordinate cuts.
  // --angle owner le|ge numerator denominator. t = tan(theta/2).
  std::vector<std::array<I,4>> angular;
  while(argc>1 && string(argv[1])=="--angle"){
    I owner,n,d;
    if(argc<6 || !parse(argv[2],10,owner) || owner<0 || owner>=21 ||
       !parse(argv[4],10,n) || !parse(argv[5],10,d) ||
       d<1 || d>1024 || n<0 || n>d) return 2;
    std::string sense(argv[3]);
    if(sense!="le" && sense!="ge")return 2;
    angular.push_back({owner,sense=="le"?0:1,n,d});
    argc-=5;argv+=5;
  }
'''
PRUNE=r'''
  // Remove a closed band only if it misses the required closed half-interval.
  // In particular a band touching a split threshold survives.
  for(auto cut:angular){
    auto [owner,sense,n,d]=cut;
    if(!(mask>>owner&1u))return 2;
    for(I k=0;k<B;++k) {
      if((sense==0 && k*d>B*n) || (sense==1 && (k+1)*d<B*n))
        c[owner][k].clear();
    }
  }
'''

def build(output, endpoints=False):
    source=PARENT.read_bytes()
    if hashlib.sha256(source).hexdigest()!=PIN:raise ValueError('Base kernel differs from its audited revision')
    text=source.decode('utf-8')
    for anchor,addition in [('  std::vector<std::pair<int, HP>> cuts;',ANGLES),
                            ('  W inf = (W)1 << 100;',PRUNE)]:
        if text.count(anchor)!=1:raise ValueError('Unexpected base-kernel structure')
        text=text.replace(anchor,addition+'\n'+anchor)
    if endpoints:
        extension=Path(__file__).with_name('endpoint_supports.inc').read_text()
        edits=[
            ('bool parse(',extension+'\nbool parse('),
            ('  for (int r = 0; r < maxr; r++) {',
             '  EndpointSupports es(bins);\n  for (int r = 0; r < maxr; r++) {\n    auto endpoint=endpoint_forbidden(es,c,own);'),
            ('              p = minus_region(p, F[jj][k]);',
             '              p = minus_region(p, F[jj][k]);\n            if(!p.empty()) p = minus_region(p,endpoint[jj][k]);'),
        ]
        for original,replacement in edits:
            if text.count(original)!=1:raise ValueError('Unexpected support insertion point')
            text=text.replace(original,replacement)
    with tempfile.TemporaryDirectory() as tmp:
        src=Path(tmp)/'angular.cpp'
        src.write_text(text)
        subprocess.run([os.environ.get('CXX','c++'),'-O3','-std=c++17',str(src),'-o',str(output)],check=True)
    print('Built extended kernel',hashlib.sha256(text.encode()).hexdigest())

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--endpoint-supports',action='store_true',help='add direct rotational support constraints')
    args=parser.parse_args()
    build(args.output.resolve(),args.endpoint_supports)
