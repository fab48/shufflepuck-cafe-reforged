import struct, sys, collections
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]
u32=lambda b,o: struct.unpack_from('<I',b,o)[0]

def main(path):
    b=open(path,'rb').read()
    ntrk=b[10]
    print(f"--- {path.split('(')[-1][:12]}  {len(b)} octets, {ntrk} pistes, rev={b[11]}")
    off=16; secdist=collections.Counter(); fuzzy_t=[]; odd=[]; mfm=[]
    for i in range(ntrk):
        rsize,fuzzy=u32(b,off),u32(b,off+4)
        nsec,flags=u16(b,off+8),u16(b,off+10)
        mfmlen=u16(b,off+12); tnum=b[off+14]
        trk,side=tnum&0x7f,(tnum>>7)&1
        secdist[nsec]+=1; mfm.append(mfmlen)
        if fuzzy: fuzzy_t.append((trk,side,fuzzy))
        # flags bit1 = piste image presente (timing/MFM brut) -> souvent protection
        if flags & 0x40 or mfmlen not in (0,6250) and mfmlen>6400: odd.append((trk,side,flags,mfmlen))
        off+=rsize
    print("  secteurs/piste :", dict(sorted(secdist.items())))
    print(f"  mfm_len min/max : {min(mfm)}/{max(mfm)}")
    print(f"  pistes avec fuzzy bytes : {len(fuzzy_t)}" + (f" -> {fuzzy_t[:6]}" if fuzzy_t else ""))
    print(f"  pistes MFM surdimensionnees : {len(odd)}" + (f" -> {[(t,s,hex(f),m) for t,s,f,m in odd[:6]]}" if odd else ""))
for p in sys.argv[1:]: main(p)
