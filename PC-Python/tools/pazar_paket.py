# -*- coding: utf-8 -*-
"""
PAZAR paket çözümü — 0x26 GC_SHOP (oyuncu dükkânı içeriği).

20 Eyl 2026 kaydından (log/pazar_20260920_233729.pcap) çözüldü ve dört farklı
dükkânda doğrulandı.

    26 | boy u16 LE | alt u8 | sahip_vid u32 | bayrak u8 | 80 × slot(43 bayt)

    alt = 0 : dükkân içeriği (boy hep 3449)
    alt = 1 : dükkân kapandı (boy 4, gövde yok)

    slot (43 bayt) — 21 Eyl'de 313 paket / 2884 slot üzerinde doğrulandı:
        +0   u32     vnum      (0 = boş slot)
        +4   u32     fiyat     (yang)
        +8   u16     adet
        +10  3×u32   soket
        +22  7×(u8 tür + i16 değer)  EFSUN
        toplam 4+4+2+12+21 = 43 TAM

    Yerleşim iki adayla sınandı; "adet 1 bayt, efsun +21" varsayımı 1031
    efsunun 265'inde saçma değer veriyordu (tür 255, değer ±12000). Doğru
    yerleşimde 976 efsunun HİÇBİRİ saçma değil: tür 1-72, değer -26..2000,
    ortanca 7.

Ölçü doğrulaması: (3449 - 9) / 43 = 80 tam bölünüyor — standart 80 slotluk
özel dükkân. Sahip vid'i, tıklanan dükkânın vid'iyle birebir uyuştu
(1343620 / 16047 / 16390).

Dükkânları bulmak: /api/varliklar içinde tip=1 (NPC), vnum=30000 ve adı
"... Marketi" olan varlıklar oyuncu dükkânıdır.
"""

import argparse
import os
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
_KOK = os.path.dirname(_BURASI)
sys.path.insert(0, _BURASI)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                   # noqa: BLE001
        pass

BASLIK = 0x26
ALT_ICERIK = 0x00
ALT_KAPANDI = 0x01
GOVDE_BAS = 9          # 26 + boy(2) + alt(1) + sahip_vid(4) + bayrak(1)
SLOT_BOY = 43
SLOT_ADET = 80
ICERIK_BOY = GOVDE_BAS + SLOT_BOY * SLOT_ADET      # 3449

SOKET_OFS = 10          # 3 × u32
EFSUN_OFS = 22          # 7 × (u8 tür + i16 değer)
EFSUN_ADET = 7

# Standart Metin2 APPLY_* numaraları. Gözlenen türler (1,5,17,18,22,35,71,72)
# bu tabloya birebir oturuyor. Bilinmeyen tür "efsun N" diye gösterilir.
EFSUN_ADLARI = {
    1: "Maks. Can", 2: "Maks. Mana", 3: "Dayanıklılık", 4: "Zeka",
    5: "Güç", 6: "Çeviklik", 7: "Saldırı hızı", 8: "Hareket hızı",
    9: "Büyü hızı", 10: "Can dolumu", 11: "Mana dolumu",
    12: "Zehirlenme %", 13: "Sersemletme %", 14: "Yavaşlatma %",
    15: "Kritik %", 16: "Delici %", 17: "İnsana karşı",
    18: "Hayvana karşı", 19: "Orka karşı", 20: "Mistiğe karşı",
    21: "Ölümsüze karşı", 22: "Şeytana karşı", 23: "Can emme",
    24: "Mana emme", 25: "Mana yakma %", 26: "Hasarda mana",
    27: "Blok", 28: "Sekme", 29: "Kılıca dayanıklılık",
    30: "İki ele dayanıklılık", 31: "Hançere dayanıklılık",
    32: "Çıngırağa dayanıklılık", 33: "Yelpazeye dayanıklılık",
    34: "Oka dayanıklılık", 35: "Ateşe dayanıklılık",
    36: "Yıldırıma dayanıklılık", 37: "Büyüye dayanıklılık",
    38: "Rüzgâra dayanıklılık", 39: "Yakın hasar yansıtma",
    40: "Lanet yansıtma", 41: "Zehir azaltma", 42: "Öldürünce mana",
    43: "Tecrübe bonusu", 44: "Yang bonusu", 45: "Eşya düşme bonusu",
    46: "İksir bonusu", 47: "Öldürünce can", 48: "Sersemletme bağışıklığı",
    49: "Yavaşlatma bağışıklığı", 50: "Düşme bağışıklığı", 51: "Beceri",
    52: "Ok menzili", 53: "Saldırı değeri", 54: "Savunma değeri",
    55: "Büyü saldırısı", 56: "Büyü savunması", 57: "Lanet %",
    58: "Maks. dayanıklılık", 59: "Savaşçıya karşı", 60: "Suikastçıya karşı",
    61: "Suraya karşı", 62: "Şamana karşı", 63: "Savaşçıya dayanıklılık",
    64: "Suikastçıya dayanıklılık", 65: "Suraya dayanıklılık",
    66: "Şamana dayanıklılık", 67: "Enerji", 68: "Savunma",
    69: "Kostüm efsunu", 70: "Büyü hasarı %", 71: "Ortalama hasar %",
    72: "Buza dayanıklılık", 73: "Toprağa dayanıklılık",
    74: "Karanlığa dayanıklılık", 75: "Kritik direnci %",
    76: "Delici direnci %",
}


def efsun_adi(tur):
    return EFSUN_ADLARI.get(tur, "efsun %d" % tur)


# Oyuncu dükkânı: NPC tipinde, bu vnum'la ve "... Marketi" adıyla görünür.
DUKKAN_VNUM = 30000
DUKKAN_SONEK = "marketi"


def dukkan_mi(v):
    """Varlık listesindeki bir kayıt oyuncu dükkânı mı?"""
    try:
        if int(v.get("vnum", 0) or 0) == DUKKAN_VNUM:
            return True
    except (TypeError, ValueError):
        pass
    ad = (v.get("ad") or v.get("isim") or "").strip().lower()
    return ad.endswith(DUKKAN_SONEK)


def _u32(b, i):
    return int.from_bytes(b[i:i + 4], "little")


def cerceveleri_ayikla(b):
    """Bir TCP segmentindeki 0x26 çerçevelerini ayıklar.

    Üst sınır ÖNEMLİ: gevşek bırakılırsa rastgele bir 0x26 baytı kilobaytlarca
    veriyi tek paket sanıp yutuyor (bkz. docs/PROTOKOL_OFSET.md)."""
    out = []
    i = 0
    n = len(b)
    while i + 4 <= n:
        if b[i] == BASLIK:
            boy = int.from_bytes(b[i + 1:i + 3], "little")
            # SIKI FİLTRE: gözlenen tek iki boy var — içerik 3449, kapanış 4.
            # Gevşek aralık (4..4096) rastgele bir 0x26 baytını paket sanıp
            # çöp üretiyordu: vnum 4294901764, fiyat 2.147.483.647, efsun
            # +26981 gibi. Boyu tam eşleştirmek bunları tamamen eliyor.
            if boy in (ICERIK_BOY, 4) and i + boy <= n:
                out.append(bytes(b[i:i + boy]))
                i += boy
                continue
        i += 1
    return out


def coz(cerceve):
    """Bir 0x26 çerçevesini çözer.

    Döner: {"alt": 0/1, "sahip_vid": int, "esyalar": [{vnum, fiyat, adet, slot}]}
    İçerik paketi değilse esyalar boş döner.
    """
    b = cerceve
    if len(b) < 4 or b[0] != BASLIK:
        return None
    alt = b[3]
    sonuc = {"alt": alt, "sahip_vid": None, "esyalar": [], "boy": len(b)}
    if alt != ALT_ICERIK or len(b) < GOVDE_BAS:
        return sonuc                                   # kapanış ya da gövdesiz
    sonuc["sahip_vid"] = _u32(b, 4)
    for s in range(SLOT_ADET):
        i = GOVDE_BAS + s * SLOT_BOY
        if i + 12 > len(b):
            break
        vnum = _u32(b, i)
        if not vnum:
            continue                                   # boş slot
        soketler = [_u32(b, i + SOKET_OFS + 4 * k) for k in range(3)]
        efsunlar = []
        for k in range(EFSUN_ADET):
            p = i + EFSUN_OFS + 3 * k
            if p + 3 > len(b):
                break
            tur = b[p]
            deg = int.from_bytes(b[p + 1:p + 3], "little", signed=True)
            if tur and deg:                    # boş yuva: tür 0 / değer 0
                efsunlar.append({"tur": tur, "ad": efsun_adi(tur), "deger": deg})
        sonuc["esyalar"].append({
            "slot": s,
            "vnum": vnum,
            "fiyat": _u32(b, i + 4),
            "adet": int.from_bytes(b[i + 8:i + 10], "little"),
            "soketler": [x for x in soketler if x],
            "efsunlar": efsunlar,
        })
    return sonuc


def _yang(n):
    """Fiyatı okunur yaz: 1.250.000 gibi."""
    return "{:,}".format(int(n)).replace(",", ".")


# ── kayıttan doğrulama ───────────────────────────────────────────────────
def pcap_coz(yol, adlar=None):
    import kanal_bul as kb
    ALT, UST = 30000, 30100
    paketler = kb.pcap_tcp(yol)
    if not paketler:
        print("X paket okunamadı")
        return []
    t0 = paketler[0][0]
    dukkanlar = []
    for z, kip, kport, hip, hport, bayrak, yuk in paketler:
        if not yuk or not (ALT <= kport <= UST):        # yalnız sunucudan gelen
            continue
        for cer in cerceveleri_ayikla(bytes(yuk)):
            d = coz(cer)
            if d and d["alt"] == ALT_ICERIK:
                d["t"] = (z - t0) / 1e6
                dukkanlar.append(d)
    return dukkanlar


def main(argv=None):
    ap = argparse.ArgumentParser(description="0x26 GC_SHOP çözümü (doğrulama)")
    ap.add_argument("--dosya", required=True, help="pazar_*.pcap")
    a = ap.parse_args(argv)

    adlar = {}
    yan = os.path.splitext(a.dosya)[0] + "_varliklar.json"
    if os.path.exists(yan):
        import json
        try:
            with open(yan, encoding="utf-8") as f:
                for v in json.load(f):
                    if v.get("vid"):
                        adlar[int(v["vid"])] = v.get("ad") or v.get("isim") or ""
        except Exception:                               # noqa: BLE001
            pass

    dukkanlar = pcap_coz(a.dosya)
    print("=" * 74)
    print("ÇÖZÜLEN DÜKKÂNLAR: %d" % len(dukkanlar))
    print("=" * 74)
    for d in dukkanlar:
        ad = adlar.get(d["sahip_vid"], "?")
        print("\n+%.2f sn  vid=%-9s %s   (%d eşya, %d bayt)"
              % (d["t"], d["sahip_vid"], ad, len(d["esyalar"]), d["boy"]))
        for e in d["esyalar"][:25]:
            ek = ""
            if e.get("efsunlar"):
                ek = "  [" + ", ".join("%s %+d" % (x["ad"], x["deger"])
                                       for x in e["efsunlar"]) + "]"
            if e.get("soketler"):
                ek += "  soket:%s" % e["soketler"]
            print("    slot %-3d vnum %-7d adet %-5d fiyat %14s%s"
                  % (e["slot"], e["vnum"], e["adet"], _yang(e["fiyat"]), ek))
        if len(d["esyalar"]) > 25:
            print("    ... (%d eşya daha)" % (len(d["esyalar"]) - 25))
    # sağlama
    print("\n" + "-" * 74)
    print("SAĞLAMA")
    print("  içerik paketi boyu  : %s  (beklenen %d)"
          % (sorted({d["boy"] for d in dukkanlar}) or "-", ICERIK_BOY))
    print("  slot ölçüsü         : (%d - %d) / %d = %.2f"
          % (ICERIK_BOY, GOVDE_BAS, SLOT_BOY,
             (ICERIK_BOY - GOVDE_BAS) / float(SLOT_BOY)))
    kotu = [d for d in dukkanlar
            if any(e["fiyat"] > 10 ** 10 or e["adet"] > 10 ** 6
                   for e in d["esyalar"])]
    print("  saçma fiyat/adet    : %s" % ("YOK" if not kotu else "%d dükkânda VAR" % len(kotu)))


if __name__ == "__main__":
    main()
