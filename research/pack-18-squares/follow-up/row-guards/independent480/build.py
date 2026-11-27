"""Build a centred-wall variant of the independent terminal-crosscheck solver."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'terminal-crosscheck'/'exact.cpp'
BASE_SHA='7dceb12030d3cfbdf9ccb6049049fa9e0a404fbdd4b793d3603538cfc626ed7f'

PARSE=r'''
I number(const char *s,int base){
    std::string a(s);
    I val;
    auto parsed=std::from_chars(a.data(),a.data()+a.size(),val,base);
    if(a.empty()||parsed.ec!=std::errc{}||parsed.ptr!=a.data()+a.size())
        throw std::runtime_error("bad integer argument");
    return val;
}
int run(int argc,char **argv) {
    if(argc<7 || (argc-7)%3) throw std::runtime_error("mask bands rounds verify certificate sideNano [owner opcode value]...");
    I raw=number(argv[1],16), bandCount=number(argv[2],10), roundCount=number(argv[3],10);
    if(raw<=0||raw >= (1u<<21) || __builtin_popcount(unsigned(raw))!=18 ||
            bandCount<4||bandCount>768||roundCount<1||roundCount>1000) return 2;
    unsigned mask=unsigned(raw);
    int B=int(bandCount), rounds=int(roundCount);
    I sideNano=number(argv[6],10);
    if(sideNano<1000000000LL||sideNano>2*U||sideNano%4) return 2;
    I inset=(2*U-sideNano)/4; // Grid coordinates are in units of two nanounits.
    TRACE_INIT
'''

CUTS=r'''
    // Coordinate cut thresholds use millionths in the fixed rack frame.
    // An angular cut drops only bands disjoint from the closed physical
    // half-interval. A band touching the threshold is always retained.
    for(int pos=7;pos<argc;pos+=3){
        I owner=number(argv[pos],10), kind=number(argv[pos+1],10), v=number(argv[pos+2],10);
        if(owner<0||owner>=21||!(mask&(1u<<owner))||kind<0||kind>5) return 2;
        int j=__builtin_popcount(mask&((1u<<owner)-1));
        if(kind<4){
            if(v<0||v>4822876) return 2;
            I sign=kind%2?1:-1,limit=v*(D/1000000);
            H h{kind<2?sign:0, kind<2?0:sign, sign*limit};
            for(auto &p : state[j]) half(p,h);
        }else{
            if(v<1||v>=128) return 2;
            for(int k=0;k<B;++k){
                if((kind==4 && I(k)*128>I(B)*v) || (kind==5 && I(k+1)*128<I(B)*v))
                    state[j][k].clear();
            }
        }
    }
'''


def only(text,old,new):
    if text.count(old)!=1:raise ValueError("Unexpected pinned-source anchor")
    return text.replace(old,new)


def build(output,proposer=False,sanitize=False,export_boxes=False,extended_bands=False):
    original=BASE.read_bytes()
    if hashlib.sha256(original).hexdigest()!=BASE_SHA:raise ValueError("Base verifier digest has changed")
    text='#include <charconv>\n'+original.decode()
    lo=text.index('int run(int argc, char **argv)')
    hi=text.index('    int digits[21][2]',lo)
    init=('if(std::string(argv[4])!="verify") return 2;\n    CoreTrace trace(argv[5]);')
    prefix=''
    if proposer:
        prefix=(HERE/'point_suggestions.inc').read_text()
        init='CandidateTrace trace(argv[4],argv[5]);'
    parser_code=only(PARSE,'bandCount>768','bandCount>1280') if extended_bands else PARSE
    text=text[:lo]+prefix+'\n'+parser_code.replace('TRACE_INIT',init)+text[hi:]
    if proposer:text='#include <cmath>\n#include <memory>\n'+text
    text=only(text,'if (i != drop[0] && i != drop[1] && i != drop[2])','if (mask & (1u << i))')
    text=only(text,'p = {{w, w}, {U - w, w}, {U - w, U - w}, {w, U - w}};',
              'w += inset;\n            p = {{w, w}, {U - w, w}, {U - w, U - w}, {w, U - w}};')
    text=only(text,'    std::vector<Poly> cores;',CUTS+'\n    std::vector<Poly> cores;')
    if text.count('"EXCLUDED case " << cas')!=2:raise ValueError("Unexpected result markers")
    text=text.replace('"EXCLUDED case " << cas','"EXCLUDED mask " << mask')
    if export_boxes:
        anchor='    std::cout << "UNDECIDED\\n";'
        dump=r'''
    if(const char* output=std::getenv("PACK18_OUTER_BOXES")){
        std::ofstream out(output);
        if(!out) throw std::runtime_error("cannot write outer boxes");
        int idx=0;
        for(int owner=0; owner<21; ++owner) if(mask & (1u << owner)){
            for(int k=0; k<B; ++k){
                const auto& pol=state[idx][k];
                if(pol.empty()) continue;
                I x=pol[0].x,X=x,y=pol[0].y,Y=y;
                for(auto p: pol){
                    x=std::min(x,p.x); X=std::max(X,p.x);
                    y=std::min(y,p.y); Y=std::max(Y,p.y);
                }
                out<<owner<<" "<<k<<" "<<B<<" "<<x<<" "<<X<<" "<<y<<" "<<Y<<"\n";
            }
            ++idx;
        }
        if(!out) throw std::runtime_error("failed while writing outer boxes");
    }
'''
        text=only(text,anchor,dump+'\n'+anchor)
    with tempfile.TemporaryDirectory() as tmp:
        src=Path(tmp)/'inset.cpp';src.write_text(text)
        flags=['-fsanitize=undefined','-fno-sanitize-recover=all'] if sanitize else []
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O3','-ftrapv',*flags,src,'-o',output],check=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path)
    ap.add_argument('--proposer',action='store_true',help='also compile an optional floating heuristic for proposing exactly checked core points')
    ap.add_argument('--sanitize',action='store_true')
    ap.add_argument('--export-boxes',action='store_true',help='after an undecided run optionally export outer rectangles to PACK18_OUTER_BOXES')
    ap.add_argument('--extended-bands',action='store_true',help='allow up to 1,280 uniform angle bands')
    a=ap.parse_args();build(a.output.resolve(),a.proposer,a.sanitize,a.export_boxes,a.extended_bands)
