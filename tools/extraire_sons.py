#!/usr/bin/env python3
"""Extrait les echantillons sonores d'un dump RAM vers des WAV.

Structure trouvee dans $14EEC / $14F4E :
    $1AFEA : nombre d'echantillons charges
    $1AFEE : table de pointeurs 32 bits, un par echantillon
    chaque echantillon : 8 octets d'en-tete puis les donnees
"""
import sys, struct, os

NB   = 0x1AFEA
TBL  = 0x1AFEE

def wav(path, data, rate=12000):
    n=len(data)
    h = b'RIFF'+struct.pack('<I',36+n)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,1,rate,rate,1,8)
    h += b'data'+struct.pack('<I',n)
    open(path,'wb').write(h+bytes(data))

def main(ram_path, outdir):
    R=open(ram_path,'rb').read()
    u32=lambda o: struct.unpack_from('>I',R,o)[0]
    u16=lambda o: struct.unpack_from('>H',R,o)[0]
    n=u16(NB)
    print(f"nombre d'echantillons charges : {n}")
    if not (0 < n < 256):
        print("valeur implausible, abandon"); return
    os.makedirs(outdir, exist_ok=True)
    ptrs=[u32(TBL+i*4) for i in range(n)]
    ok=0
    for i,p in enumerate(ptrs):
        if not (0x1000 <= p < len(R)-16):
            print(f"  {i:>3} pointeur hors zone 0x{p:08x}"); continue
        hdr = R[p:p+8]
        ln  = struct.unpack_from('>I',R,p+4)[0]
        if not (0 < ln < 200000) or p+8+ln > len(R):
            print(f"  {i:>3} @0x{p:06x} longueur implausible {ln}"); continue
        d = R[p+8:p+8+ln]
        # controle : un signal sonore varie doucement
        mad = sum(abs(d[k+1]-d[k]) for k in range(0,len(d)-1,7))/max(1,len(d)//7)
        wav(os.path.join(outdir,f"son_{i:02d}.wav"), d)
        print(f"  {i:>3} @0x{p:06x}  {ln:>7} o  ecart moyen {mad:5.1f}  "
              f"{'-> profil sonore' if mad<40 else '-> douteux'}")
        ok+=1
    print(f"\n{ok}/{n} extraits dans {outdir}")

if __name__=='__main__':
    main(sys.argv[1], sys.argv[2])
