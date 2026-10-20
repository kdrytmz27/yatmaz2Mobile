# -*- coding: utf-8 -*-
"""IN cerceve tablosunu buyuterek %100'e yaklas. Kalan opcode'lar icin
en iyi sabit uzunlugu ardisik cerceveleme kapsamina gore secer."""
import struct, sys, os, collections
if hasattr(sys.stdout,'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    except Exception: pass
OYUN_IP='185.128.114.87'
def pcap_oku(yol):
    f=open(yol,'rb').read()
    le=f[:4] in (b'\xd4\xc3\xb2\xa1',b'\x4d\x3c\xb2\xa1'); end='<' if le else '>'
    link=struct.unpack_from(end+'I',f,20)[0]; lh=16 if link==113 else 14; o=24
    g,d=bytearray(),bytearray()
    while o+16<=len(f):
        _,_,cap,_=struct.unpack_from(end+'IIII',f,o); o+=16
        pkt=f[o:o+cap]; o+=cap
        if len(pkt)<lh+40: continue
        ip=lh
        if (pkt[ip]>>4)!=4 or pkt[ip+9]!=6: continue
        tcp=ip+(pkt[ip]&0xF)*4
        yuk=pkt[tcp+(((pkt[tcp+12]>>4)&0xF)*4):cap]
        if not yuk: continue
        src='.'.join(str(b) for b in pkt[ip+12:ip+16])
        (g if src==OYUN_IP else d).__iadd__(yuk)
    return bytes(g),bytes(d)
def frame(d,sabit,dinamik):
    o=0; msgs=[]; bosbyte=0
    while o<len(d):
        op=d[o]; boy=None
        if op in sabit: boy=sabit[op]
        elif op in dinamik and o+3<=len(d): boy=struct.unpack_from('<H',d,o+1)[0]
        if boy is None or boy<2 or o+boy>len(d):
            o+=1; bosbyte+=1; continue
        msgs.append((o,op,boy)); o+=boy
    return msgs,bosbyte
def kapsam(d,sabit,dinamik):
    m,bos=frame(d,sabit,dinamik); return sum(x[2] for x in m),bos
def main():
    yol=sys.argv[1] if len(sys.argv)>1 else 'log/r2_20260823_012800.pcap'
    if not os.path.isabs(yol): yol=os.path.join(os.path.dirname(__file__),'..',yol)
    g,d=pcap_oku(yol)
    sabit={0x01:38,0x02:5,0x03:24,0x11:14}; dinamik={0x04}
    # greedy: her turda en cok bayt kazandiran (opcode,uzunluk)'u ekle
    for tur in range(8):
        coz,bos=kapsam(g,sabit,dinamik)
        # su an cozulemeyen ilk baytlar hangi opcode?
        m,_=frame(g,sabit,dinamik)
        tuketilen=set()
        o=0
        while o<len(g):
            op=g[o]; boy=sabit.get(op)
            if op in dinamik and o+3<=len(g): boy=struct.unpack_from('<H',g,o+1)[0]
            if boy is None or boy<2 or o+boy>len(g): o+=1; continue
            o+=boy
        # kalan opcode adaylari
        kalan=collections.Counter()
        o=0
        while o<len(g):
            op=g[o]; boy=sabit.get(op)
            if op in dinamik and o+3<=len(g): boy=struct.unpack_from('<H',g,o+1)[0]
            if boy is None or boy<2 or o+boy>len(g):
                kalan[op]+=1; o+=1; continue
            o+=boy
        if not kalan: break
        aday=kalan.most_common(1)[0][0]
        en_iyi=(coz,None)
        for L in range(2,60):
            t=dict(sabit); t[aday]=L
            c,_=kapsam(g,t,dinamik)
            if c>en_iyi[0]: en_iyi=(c,L)
        if en_iyi[1] is None:
            print('  0x%02X icin kazancli uzunluk yok (kalan %d)'%(aday,kalan[aday])); break
        sabit[aday]=en_iyi[1]
        print('  + 0x%02X = %d bayt  -> kapsam %.1f%%'%(aday,en_iyi[1],100*en_iyi[0]/len(g)))
    coz,bos=kapsam(g,sabit,dinamik)
    print('\nSON TABLO sabit=%s dinamik=%s'%({('0x%02X'%k):v for k,v in sabit.items()},dinamik))
    print('IN kapsam %.1f%%  (kalan %d bayt)'%(100*coz/len(g),bos))
    # son tabloyla 0x3F,0x3E ornekleri
    m,_=frame(g,sabit,dinamik)
    for hedef in (0x3F,0x3E,0x0D,0x70,0x2C):
        ornek=[x for x in m if x[1]==hedef][:4]
        for o,op,boy in ornek:
            print('  0x%02X [%d]: %s'%(op,boy,' '.join('%02X'%x for x in g[o:o+boy])))
if __name__=='__main__': main()
