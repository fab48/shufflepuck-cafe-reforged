#!/usr/bin/env python3
"""Balayage lineaire resilient : reprend apres chaque octet invalide."""
import sys
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
LO,HI = 0x008C00, 0x018400

def sweep(b, lo=LO, hi=HI):
    m=Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000); m.detail=False
    out=[]; pc=lo
    while pc < hi:
        n=0
        for i in m.disasm(b[pc:hi], pc):
            out.append(i); pc=i.address+i.size; n+=1
        if n==0:
            pc+=2
    return out

if __name__=='__main__':
    b=open(sys.argv[1],'rb').read()
    ins=sweep(b)
    print(f"{len(ins)} instructions, de 0x{ins[0].address:06x} a 0x{ins[-1].address:06x}")
    cov=sum(i.size for i in ins)
    print(f"couverture : {cov} octets sur {HI-LO} ({100*cov//(HI-LO)}%)")
