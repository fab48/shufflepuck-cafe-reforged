import struct, sys, os
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]
u32=lambda b,o: struct.unpack_from('<I',b,o)[0]

def build(b, skip_image):
    img=bytearray(); ok=bad=0; off=16
    for _ in range(b[10]):
        rsize,fz=u32(b,off),u32(b,off+4)
        nsec,flags=u16(b,off+8),u16(b,off+10)
        tnum=b[off+14]; trk=tnum&0x7f
        p=off+16; descs=[]
        if flags & 0x01:
            for i in range(nsec):
                descs.append((u32(b,p), b[p+10], b[p+11])); p+=16
        p+=fz
        if not (trk>79 or nsec==0):
            q=p
            if skip_image and (flags & 0x40):
                if flags & 0x80: q+=2
                q+=2+u16(b,q)
            sect={}
            for doff,sec,size in descs:
                if (size&3)==2 and 1<=sec<=9:
                    s=b[q+doff:q+doff+512]
                    if len(s)==512: sect.setdefault(sec,s)
            for n in range(1,10):
                if n in sect: img+=sect[n]; ok+=1
                else:         img+=bytes(512); bad+=1
        off+=rsize
    return bytes(img), ok, bad

def bpb(img):
    if len(img)<512: return None
    bps,spc,res,nfat,root,tot,spf=u16(img,11),img[13],u16(img,14),img[16],u16(img,17),u16(img,19),u16(img,22)
    if bps!=512 or nfat!=2 or spc not in (1,2) or not (100<=root<=256): return None
    return dict(res=res,nfat=nfat,spf=spf,root=root,spc=spc,tot=tot)

def safe(s): return ''.join(c if 32<=ord(c)<127 else f'<{ord(c):02X}>' for c in s)

for path in sys.argv[2:]:
    b=open(path,'rb').read(); tag=path.split('(')[-1][:11].replace(' ','')
    for skip in (False,True):
        img,ok,bad=build(b,skip); g=bpb(img)
        if g: break
    out=os.path.join(sys.argv[1], tag+'.st'); open(out,'wb').write(img)
    print(f"=== {tag}: {ok} secteurs OK, {bad} manquants -> {len(img)} o  [{out}]")
    start=(g['res']+g['nfat']*g['spf'])*512; tot=0; n=0
    for i in range(g['root']):
        e=img[start+i*32:start+i*32+32]
        if not e or e[0]==0: break
        if e[0]==0xE5 or (e[11] & 0x08): continue
        nm=e[0:8].decode('latin1').rstrip(); ex=e[8:11].decode('latin1').rstrip()
        sz=u32(e,28); tot+=sz; n+=1
        print(f"   {safe(nm+('.'+ex if ex else '')):<20}{sz:>9}  {'DIR' if e[11]&0x10 else ''}")
    print(f"   {n} entrees, {tot} octets\n")
