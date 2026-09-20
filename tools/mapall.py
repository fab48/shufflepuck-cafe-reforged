#!/usr/bin/env python3
"""Cartographie complete : fonctions, appels, references aux donnees."""
import sys, struct, re, collections
sys.path.insert(0,'tools')
from sweep import sweep

CODE_LO, CODE_HI = 0x008C00, 0x018400
DATA_LO, DATA_HI = 0x018400, 0x01B700

def build(b):
    ins = sweep(b)
    by = {i.address: i for i in ins}
    # bornes de fonctions : prologue -> rts/jmp final
    starts = sorted({i.address for i in ins
                     if i.mnemonic in ('link.w','link.l')
                     or (i.mnemonic=='movem.l' and '-(a7)' in i.op_str)})
    funcs = []
    for n,s in enumerate(starts):
        e = starts[n+1] if n+1 < len(starts) else CODE_HI
        funcs.append((s,e))
    return ins, by, funcs

def analyse(b):
    ins, by, funcs = build(b)
    fstart = [s for s,_ in funcs]
    def owner(a):
        lo=0; hi=len(fstart)-1; r=None
        while lo<=hi:
            m=(lo+hi)//2
            if fstart[m]<=a: r=fstart[m]; lo=m+1
            else: hi=m-1
        return r
    calls = collections.defaultdict(set)      # appelant -> appeles
    callers = collections.defaultdict(set)    # appele -> appelants
    datarefs = collections.defaultdict(set)   # fonction -> adresses donnees
    dataused = collections.defaultdict(set)   # adresse -> fonctions
    for i in ins:
        o = owner(i.address)
        if o is None: continue
        if i.mnemonic in ('jsr','bsr'):
            m = re.search(r'\$([0-9a-f]+)', i.op_str)
            if m:
                t = int(m.group(1),16)
                if i.mnemonic=='bsr' or '(pc)' in i.op_str:
                    pass
                if CODE_LO <= t < CODE_HI:
                    calls[o].add(t); callers[t].add(o)
        for m in re.finditer(r'\$([0-9a-f]{4,6})\.l', i.op_str):
            a = int(m.group(1),16)
            if DATA_LO <= a < DATA_HI:
                datarefs[o].add(a); dataused[a].add(o)
    return ins, funcs, calls, callers, datarefs, dataused

if __name__ == '__main__':
    b = open(sys.argv[1],'rb').read()
    ins, funcs, calls, callers, datarefs, dataused = analyse(b)
    print(f"instructions : {len(ins)}")
    print(f"fonctions    : {len(funcs)}")
    print(f"aretes appel : {sum(len(v) for v in calls.values())}")
    print(f"adresses de donnees referencees : {len(dataused)}")
    orphelines = [s for s,_ in funcs if s not in callers]
    print(f"fonctions sans appelant connu : {len(orphelines)}")
