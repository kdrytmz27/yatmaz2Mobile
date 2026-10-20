# -*- coding: utf-8 -*-
"""IN/OUT akisini GUNCEL cerceve tablosuyla yeniden coz ve kapsam olc."""
import struct, sys, os, collections
if hasattr(sys.stdout,'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    except Exception: pass
OYUN_IP='185.128.114.87'

# GUNCEL tablo (bu yakalamayla)
IN_SABIT  = {0x01:38, 0x02:5, 0x03:24, 0x11:14}
IN_DINAMIK= {0x04}                 # 04 | u16 toplamBoy | govde
OUT_SABIT = {0x07:16}
OUT_DINAMIK=set()

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
    o=0; msgs=[]; bos=[]
    while o<len(d):
        op=d[o]; boy=None
        if op in sabit: boy=sabit[op]
        elif op in dinamik and o+3<=len(d): boy=struct.unpack_from('<H',d,o+1)[0]
        if boy is None or boy<2 or o+boy>len(d):
            b=o; o+=1
            while o<len(d) and d[o] not in sabit and d[o] not in dinamik: o+=1
            bos.append((b,o-b)); continue
        msgs.append((o,op,boy)); o+=boy
    return msgs,bos

def rapor(ad,akis,sabit,dinamik):
    m,b=frame(akis,sabit,dinamik)
    coz=sum(x[2] for x in m); toplam=len(akis)
    say=collections.Counter(op for _,op,_ in m)
    print('\n=== %s ===  %d mesaj, %d/%d bayt (%.1f%%)'%(ad,len(m),coz,toplam,100*coz/toplam))
    print('  opcode:', {('0x%02X'%k):v for k,v in say.most_common()})
    if b:
        bt=sum(x[1] for x in b)
        print('  COZULEMEYEN %d bolge / %d bayt (%.1f%%)'%(len(b),bt,100*bt/toplam))
        for o,ln in b[:12]:
            print('    @%-5d %3d bayt: %s'%(o,ln,' '.join('%02X'%x for x in akis[o:o+min(ln,20)])))
    return m

def main():
    yol=sys.argv[1] if len(sys.argv)>1 else 'log/r2_20260823_012800.pcap'
    if not os.path.isabs(yol): yol=os.path.join(os.path.dirname(__file__),'..',yol)
    g,d=pcap_oku(yol)
    rapor('IN',g,IN_SABIT,IN_DINAMIK)
    rapor('OUT',d,OUT_SABIT,OUT_DINAMIK)

    # 0x11 icerik incele (14 bayt)
    print('\n--- 0x11 ornekleri (14 bayt: hdr|vid?|...) ---')
    m,_=frame(g,IN_SABIT,IN_DINAMIK); c=0
    for o,op,boy in m:
        if op==0x11:
            v=g[o:o+14]
            vid=struct.unpack_from('<I',v,1)[0]
            a=struct.unpack_from('<i',v,5)[0]; b2=struct.unpack_from('<i',v,9)[0]
            print('  @%-5d vid=%-10d  +5=%-8d +9=%-8d  raw=%s'%(o,vid,a,b2,' '.join('%02X'%x for x in v)))
            c+=1
            if c>=10: break
if __name__=='__main__': main()
