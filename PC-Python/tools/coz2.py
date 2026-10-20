# -*- coding: utf-8 -*-
"""0x01 spawn(38B) tam alan cozumu + OUT yeni opcode cerceveleme + 0x04/0x3E/0x6F."""
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

def main():
    yol=sys.argv[1] if len(sys.argv)>1 else 'log/r2_20260823_012800.pcap'
    if not os.path.isabs(yol): yol=os.path.join(os.path.dirname(__file__),'..',yol)
    g,d=pcap_oku(yol)
    IN_S={0x01:38,0x02:5,0x03:24,0x11:14}; IN_D={0x04}

    # ---- 0x01 spawn 38B tam alan cozumu ----
    print('=== 0x01 CHARACTER_ADD (38 bayt) alan cozumu ===')
    m,_=frame(g,IN_S,IN_D); c=0
    for o,op,boy in m:
        if op!=0x01: continue
        v=g[o:o+38]
        vid=struct.unpack_from('<I',v,1)[0]
        ang=struct.unpack_from('<f',v,5)[0]
        x=struct.unpack_from('<i',v,9)[0]; y=struct.unpack_from('<i',v,13)[0]
        z=struct.unpack_from('<i',v,17)[0]
        bType=v[21]
        vnum=struct.unpack_from('<H',v,22)[0]
        vnum32=struct.unpack_from('<I',v,22)[0]
        # kalan: 24..37
        kalan=' '.join('%02X'%x for x in v[24:38])
        print('  vid=%-10d ang=%6.1f x=%d y=%d z=%d bType=%d vnum16=%d vnum32=%d | +24: %s'%(
            vid,ang,x,y,z,bType,vnum,vnum32,kalan))
        c+=1
        if c>=8: break

    # ---- 0x04 CHAT ----
    print('\n=== 0x04 (len-prefixed) icerik ===')
    c=0
    for o,op,boy in m:
        if op!=0x04: continue
        v=g[o:o+boy]
        txt=''.join(chr(b) if 32<=b<127 else '.' for b in v[3:])
        print('  @%-5d boy=%-3d altbas=%02X  "%s"'%(o,boy,v[3] if boy>3 else 0,txt[:60]))
        c+=1
        if c>=8: break

    # ---- kalan IN bosluklar: 0x3E, 0x6F ----
    print('\n=== IN kalan opcode kesifi (0x3E/0x6F vs) ===')
    _,bos=frame(g,IN_S,IN_D)
    ilk={}
    for o,ln in bos:
        op=g[o]
        if op not in ilk: ilk[op]=(o,ln,g[o:o+min(ln,20)])
    for op,(o,ln,raw) in sorted(ilk.items()):
        print('  0x%02X  @%-5d %3d bayt: %s'%(op,o,ln,' '.join('%02X'%x for x in raw)))

    # ---- OUT yeni opcode cerceveleme ----
    print('\n=== OUT genisletilmis cerceve ===')
    OUT_S={0x07:16,0x02:6,0x3D:5,0x34:9,0x08:7}; OUT_D=set()
    mo,bo=frame(d,OUT_S,OUT_D)
    coz=sum(x[2] for x in mo)
    say=collections.Counter(op for _,op,_ in mo)
    print('  %d mesaj, %d/%d bayt (%.1f%%)  opcode:%s'%(len(mo),coz,len(d),100*coz/len(d),
          {('0x%02X'%k):v for k,v in say.most_common()}))
    if bo:
        print('  kalan bosluklar:')
        ilk={}
        for o,ln in bo:
            op=d[o]
            if op not in ilk: ilk[op]=(o,ln,d[o:o+min(ln,16)])
        for op,(o,ln,raw) in sorted(ilk.items()):
            print('    0x%02X @%-5d %3d: %s'%(op,o,ln,' '.join('%02X'%x for x in raw)))
    # OUT ornek mesajlar
    print('  --- OUT ornek (opcode bazli) ---')
    gor=set()
    for o,op,boy in mo:
        if op in gor: continue
        gor.add(op)
        print('    0x%02X [%d]: %s'%(op,boy,' '.join('%02X'%x for x in d[o:o+boy])))

if __name__=='__main__': main()
