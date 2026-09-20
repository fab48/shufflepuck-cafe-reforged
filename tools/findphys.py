#!/usr/bin/env python3
"""Cherche la signature de la reponse a la collision :
   neg + asr (division par 2 signee) + plafonnement a +/-24."""
import sys, struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
b=open(sys.argv[1],'rb').read()
m=Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000); m.detail=False
LO,HI=0x008C00,0x018400
ins=list(m.disasm(b[LO:HI], LO))
print(f"{len(ins)} instructions desassemblees\n")

idx={i.address:n for n,i in enumerate(ins)}
def win(n,k=14): return ins[max(0,n-k):n+k]

print("=== fenetres contenant NEG et ASR rapproches ===")
seen=set()
for n,i in enumerate(ins):
    if not i.mnemonic.startswith('neg'): continue
    w=win(n,10)
    if any(j.mnemonic.startswith('asr') for j in w):
        a=w[0].address
        if any(abs(a-s)<0x60 for s in seen): continue
        seen.add(a)
        print(f"\n  --- autour de 0x{i.address:06x} ---")
        for j in w:
            mark=' <<<' if j.mnemonic.startswith(('neg','asr')) else ''
            print(f"    {j.address:06x}: {j.mnemonic:<9}{j.op_str}{mark}")
        if len(seen)>=4: break

print("\n\n=== comparaisons aux constantes +/-24 (0x18 / 0xffe8) ===")
cnt=0
for n,i in enumerate(ins):
    s=i.op_str.lower()
    if i.mnemonic.startswith(('cmp','cmpi')) and ('#$18' in s or '#$ffe8' in s or '#-$18' in s):
        print(f"  0x{i.address:06x}: {i.mnemonic:<9}{i.op_str}")
        cnt+=1
        if cnt>=25: break
