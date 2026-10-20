import sys, time, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pazar_canli as pc
o = pc.CanliOkuyucu(lambda d: print("  DUKKAN vid=%s %d esya" % (d["sahip_vid"], len(d["esyalar"]))), print)
if o.basla():
    for i in range(8):
        time.sleep(1); print("\r  %d sn  paket %d" % (i+1, o.paket_say), end="")
    print()
    o.dur()
    print("toplam paket:", o.paket_say)
