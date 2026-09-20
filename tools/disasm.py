#!/usr/bin/env python3
"""Desassembleur 68000 pour les dumps RAM de Shufflepuck (capstone M68K).

Usage:
  disasm.py <ram> func <addr>        desassemble la fonction contenant <addr>
  disasm.py <ram> range <a> <b>      desassemble une plage
  disasm.py <ram> xref <addr>        fonctions qui referencent <addr>
  disasm.py <ram> funcs              liste les fonctions detectees
"""
import sys, struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

CODE_LO, CODE_HI = 0x008C00, 0x018400

def md():
    m = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    m.detail = True
    return m

def load(p): return open(p,'rb').read()

def find_funcs(b):
    """Prologues LINK A5/A6 et MOVEM.L -(SP) = debuts de fonction."""
    fs=[]
    for o in range(CODE_LO, CODE_HI-2, 2):
        w = struct.unpack_from('>H', b, o)[0]
        if w in (0x4e55, 0x4e56, 0x48e7):
            fs.append(o)
    return fs

def func_bounds(b, addr):
    fs = find_funcs(b)
    start = max([f for f in fs if f <= addr], default=CODE_LO)
    nxt   = min([f for f in fs if f >  addr], default=CODE_HI)
    return start, nxt

def show(b, lo, hi, mark=None):
    m = md()
    for i in m.disasm(b[lo:hi], lo):
        flag = ''
        if mark is not None and f"0x{mark:x}" in i.op_str.lower(): flag = '   <<<'
        print(f"  {i.address:06x}:  {i.mnemonic:<10}{i.op_str}{flag}")

def xrefs(b, target):
    out=[]
    for o in range(CODE_LO, CODE_HI-4, 2):
        if struct.unpack_from('>I', b, o)[0] == target:
            out.append(o)
    return out

if __name__ == '__main__':
    b = load(sys.argv[1]); cmd = sys.argv[2]
    if cmd == 'funcs':
        fs = find_funcs(b); print(f"{len(fs)} prologues"); 
        for f in fs[:200]: print(f"  0x{f:06x}")
    elif cmd == 'range':
        show(b, int(sys.argv[3],16), int(sys.argv[4],16))
    elif cmd == 'func':
        a=int(sys.argv[3],16); s,e=func_bounds(b,a)
        print(f"=== fonction 0x{s:06x} - 0x{e:06x} (contient 0x{a:06x}) ===")
        show(b,s,e,a)
    elif cmd == 'xref':
        t=int(sys.argv[3],16)
        for o in xrefs(b,t):
            s,e = func_bounds(b,o)
            print(f"  reference @0x{o:06x}  dans la fonction 0x{s:06x}")
