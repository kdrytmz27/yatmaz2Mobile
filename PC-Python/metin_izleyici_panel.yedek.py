# -*- coding: utf-8 -*-
"""
METİN İZLEYİCİ PANELİ — görüntüsüz izleyiciyi masaüstünden yönet.

    python metin_izleyici_panel.py

Hesaplar metin_izleyici.json'da tutulur (komut satırı sürümü
tools/metin_izleyici.py ile aynı dosya). Her hesap ya tek kanalda bekler ya
da kanalları sırayla tarar. Kanallar tablosu her kanalda metin olup
olmadığını canlı gösterir; bir kanalda metin belirince bildirim sesi çalar.

Şifre ve PIN pencerede gizli yazılır, günlüğe hiç yazılmaz. Aynı hesabı
emülatörde açarsan izleyici düşer: bir hesap aynı anda tek yerde olabilir.
"""

import collections
import http.server
import importlib.util
import io
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
import urllib.parse
from tkinter import messagebox, ttk

import sys
# EXE (PyInstaller) modunda kod _MEIPASS'ta paketlenir; tools da oraya konur.
KOK = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "metin_izleyici", os.path.join(KOK, "tools", "metin_izleyici.py"))
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)
_spec_tb = importlib.util.spec_from_file_location(
    "telegram_bildirim", os.path.join(KOK, "tools", "telegram_bildirim.py"))
tb = importlib.util.module_from_spec(_spec_tb)
_spec_tb.loader.exec_module(tb)

KOYU = "#0f1117"
PANEL = "#171922"
CIZGI = "#262a36"
METIN = "#e6e8ef"
SOLUK = "#9aa0b4"
VURGU = "#33aaff"
OK = "#37d67a"
UYARI = "#ffb020"
HATA = "#ff5a5a"
METIN_MAVI = "#3c8cff"     # web'deki metin rengi
OYUNCU_MOR = "#aa3cff"     # web'deki oyuncu rengi
YAZI = ("Segoe UI", 9)
KALIN = ("Segoe UI", 9, "bold")
SABIT = ("Consolas", 9)

# Günlüğe yazılmayanlar: paket dökümü ve taramanın her ziyarette tekrarlayan
# VAR/yok satırları (kanal kutuları bunu zaten gösteriyor; durum DEĞİŞİNCE
# ayrıca bir satır yazılır).
GIZLI_SEVIYELER = ("paket", "tarama_var", "tarama_yok")

# Telegram'a gidebilecek olaylar: (anahtar, kutudaki ad); varsayılan açık/kapalı
TG_OLAYLAR = (("metin_var", "Metin var"), ("kesiliyor", "Kesiliyor"), ("kesildi", "Kesildi"),
              ("yaninda", "Yanında oyuncu"), ("dusman", "Düşman"), ("hata", "Hata"),
              ("tur_ozeti", "Tur özeti"), ("her_ziyaret", "Her ziyaret"))
TG_VARSAYILAN = {"metin_var": True, "kesiliyor": True, "kesildi": True, "dusman": True,
                 "yaninda": False, "hata": True, "tur_ozeti": False, "her_ziyaret": False}


WEB_HTML = u"""<!doctype html><html lang="tr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Metin İzleyici</title>
<style>
*{box-sizing:border-box} body{margin:0;background:#0f1117;color:#e6e8ef;
 font:14px -apple-system,Segoe UI,Roboto,sans-serif}
#ust{position:sticky;top:0;z-index:5;background:#171922;padding:10px;display:flex;gap:8px;
 align-items:center;flex-wrap:wrap;border-bottom:1px solid #262a36}
h1{font-size:16px;margin:0 8px 0 0} button{background:#262a36;color:#e6e8ef;border:0;
 border-radius:6px;padding:9px 12px;font-size:14px;cursor:pointer} button:active{background:#33aaff}
.yesil{background:#37d67a;color:#0f1117} .kirmizi{background:#ff5a5a;color:#0f1117}
.sv{background:#33aaff;color:#0f1117}
#kanallar{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;padding:10px}
.k{background:#171922;border:2px solid #262a36;border-radius:8px;padding:8px;min-height:96px}
.k .b{font-weight:bold;font-size:15px} .d{font-weight:bold;margin:2px 0}
.ay{color:#9aa0b4;font-size:12px;white-space:pre-wrap} .oy{color:#aa3cff;font-size:12px}
.dsm{color:#ff5a5a;font-weight:bold} .metin{color:#3c8cff}
#bilgi{color:#9aa0b4;font-size:12px;padding:0 10px} #buffbilgi{color:#9aa0b4;font-size:12px;padding:2px 10px}
input,select{background:#0f1117;color:#e6e8ef;border:1px solid #262a36;border-radius:6px;
 padding:7px;font-size:14px} input[type=checkbox]{width:18px;height:18px}
details{background:#171922;border:1px solid #262a36;border-radius:8px;margin:8px 10px}
summary{padding:11px;font-weight:bold;cursor:pointer;color:#33aaff}
.f{display:flex;gap:8px;align-items:center;margin:7px 10px} .f label{flex:1;color:#9aa0b4;font-size:13px}
.f input.num{width:90px} .f input.txt{flex:1;min-width:0}
.hs{display:flex;gap:6px;align-items:center;margin:7px 10px;flex-wrap:wrap}
.hs .ad{flex:1;min-width:80px;font-weight:bold} .hs input.mk{width:66px} .hs button{padding:7px 9px}
.blk{margin:8px 10px} .blk button{width:100%}
#log{background:#0f1117;color:#9aa0b4;font:11px ui-monospace,monospace;white-space:pre-wrap;
 padding:8px;margin:0 10px 10px;max-height:240px;overflow:auto;border-radius:6px}
.not{color:#9aa0b4;font-size:11px;margin:2px 10px 8px}
</style></head><body>
<div id="ust"><h1>Metin İzleyici</h1>
 <button class="yesil" onclick="komut({komut:'baslat'})">▶ Hepsini başlat</button>
 <button class="kirmizi" onclick="komut({komut:'durdur'})">■ Hepsini durdur</button>
 <button onclick="ekran()">📷 Ekran</button>
 <span id="saat"></span></div>
<div id="kanallar"></div>
<div id="bilgi"></div>
<img id="ss" style="max-width:100%;display:none;padding:10px">

<details open><summary>Hesaplar</summary>
 <div id="hesaplar"></div>
 <div class="not">Her hesabın modunu (tek kanal / tara / buff) ve kanalını değiştir, kaydet;
  ▶/■ ile tek tek başlat-durdur.</div></details>

<details><summary>Ayarlar</summary>
 <div class="f"><label>Taramada kanal başına bakış (sn)</label><input class="num" id="ay_bakis"></div>
 <div class="f"><label>Aranan metin vnum'ları (virgülle)</label><input class="txt" id="ay_vnum"></div>
 <div class="f"><label>Bütün metinler (vnum'a bakma)</label><input type="checkbox" id="ay_tum"></div>
 <div class="f"><label>⚠ Ölünce yerinde canlan (/restart_here)</label><input type="checkbox" id="ay_canlan"></div>
 <div class="f"><label>⚠ Ölünce ch'den çıkıp tekrar gir (canlanır)</label><input type="checkbox" id="ay_yeniden"></div>
 <div class="f"><label>↳ tekrar girme süresi (sn)</label><input class="num" id="ay_yeniden_gecikme"></div>
 <div class="f"><label>⚠ Kısa mesafede park yerine dön (paket)</label><input type="checkbox" id="ay_don"></div>
 <div class="blk"><button class="sv" onclick="kaydetAyar()">Ayarları kaydet</button></div></details>

<details><summary>Düşman isimleri</summary>
 <div class="f"><input class="txt" id="dz_ad" placeholder="Adları virgülle yaz"></div>
 <div class="f"><label>Düşman görülünce ses çal (bilgisayarda)</label><input type="checkbox" id="dz_ses"></div>
 <div class="blk"><button class="kirmizi" onclick="kaydetDusman()">Düşmanları kaydet</button></div></details>

<details><summary>Buff'çı</summary>
 <div class="f"><label>⚠ Buff'çıyı çalıştır (oyuna paket)</label><input type="checkbox" id="bf_acik"></div>
 <div class="f"><label>Yaklaşınca buff'lanacak oyuncu</label><input class="txt" id="bf_hedef"></div>
 <div class="f"><label>Ejderha Yardımı vnum</label><input class="num" id="bf_yardim"></div>
 <div class="f"><label>Ejderha Gücü vnum</label><input class="num" id="bf_guc"></div>
 <div class="f"><label>İki yetenek arası (sn)</label><input class="num" id="bf_gecikme"></div>
 <div class="f"><label>Menzil (m)</label><input class="num" id="bf_menzil"></div>
 <div class="f"><label>Aynı kişiye tekrar (sn)</label><input class="num" id="bf_aralik"></div>
 <div class="blk"><button class="sv" onclick="kaydetBuff()">Buff ayarlarını kaydet</button></div>
 <div id="buffbilgi"></div>
 <div class="f"><label>Buff'çıyı kanala çek</label>
  <select id="buffk"></select><button onclick="buffCek()">Çek</button></div></details>

<details><summary>Telegram</summary>
 <div class="f"><label>Olayları Telegram'a gönder</label><input type="checkbox" id="tg_acik"></div>
 <div class="f"><label>Sohbet kimliği</label><input class="num" id="tg_sohbet"></div>
 <div id="tg_olaylar" class="blk"></div>
 <div class="blk"><button class="sv" onclick="kaydetTg()">Telegram'ı kaydet</button></div>
 <div class="not" id="tg_kurulu"></div>
 <div class="not">Bot token'ı güvenlik için web'e gösterilmez/değiştirilmez — masaüstünden girilir.</div></details>

<details><summary>Olaylar</summary><pre id="log"></pre></details>

<script>
var k=new URLSearchParams(location.search).get('k')||'';
function api(y){return y+(y.indexOf('?')<0?'?':'&')+'k='+encodeURIComponent(k)}
function q(id){return document.getElementById(id)}
async function komut(o){try{await fetch(api('api/komut'),{method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify(o)});setTimeout(durum,250)}catch(e){}}
function ekran(){var i=q('ss');i.style.display='block';i.src=api('api/ekran')+'&t='+Date.now()}
(function(){var s=q('buffk');for(var i=1;i<=8;i++){var o=document.createElement('option');
 o.value=i;o.textContent='ch'+i;s.appendChild(o)}})();

function kaydetAyar(){komut({komut:'ayarlar',bakis:q('ay_bakis').value,vnumlar:q('ay_vnum').value,
 tum:q('ay_tum').checked,canlan:q('ay_canlan').checked,yeniden:q('ay_yeniden').checked,
 yeniden_gecikme:q('ay_yeniden_gecikme').value,don:q('ay_don').checked})}
function kaydetDusman(){komut({komut:'dusman',metin:q('dz_ad').value,ses:q('dz_ses').checked})}
function kaydetBuff(){komut({komut:'buff',acik:q('bf_acik').checked,hedef:q('bf_hedef').value,
 yardim:+q('bf_yardim').value,guc:+q('bf_guc').value,gecikme:+q('bf_gecikme').value,
 menzil:+q('bf_menzil').value,aralik:+q('bf_aralik').value})}
function kaydetTg(){var ol={};document.querySelectorAll('[id^=tgo_]').forEach(function(e){
 ol[e.id.slice(4)]=e.checked});komut({komut:'telegram',acik:q('tg_acik').checked,
 sohbet:q('tg_sohbet').value,olaylar:ol})}
function buffCek(){komut({komut:'buff_cek',kanal:+q('buffk').value})}
function modKaydet(idx){var v=q('mk'+idx).value;
 komut({komut:'mod',idx:idx,mod:q('md'+idx).value,kanal:v,tarama:v})}

var dolduruldu=false;
function formDoldur(d){
 if(dolduruldu)return;dolduruldu=true;
 var a=d.ayarlar||{};q('ay_bakis').value=a.bakis;q('ay_vnum').value=a.vnumlar;
 q('ay_tum').checked=a.tum;q('ay_canlan').checked=a.canlan;
 q('ay_yeniden').checked=a.yeniden;q('ay_yeniden_gecikme').value=a.yeniden_gecikme;
 q('ay_don').checked=a.don;
 var dz=d.dusman||{};q('dz_ad').value=dz.adlar;q('dz_ses').checked=dz.ses;
 var b=d.buff||{};q('bf_acik').checked=b.acik;q('bf_hedef').value=b.hedef||'';
 q('bf_yardim').value=b.yardim;q('bf_guc').value=b.guc;q('bf_gecikme').value=b.gecikme;
 q('bf_menzil').value=b.menzil;q('bf_aralik').value=b.aralik;
 var t=d.telegram||{};q('tg_acik').checked=t.acik;q('tg_sohbet').value=t.sohbet||'';
 q('tg_kurulu').textContent=t.kurulu?'token kurulu ✓':'token yok — masaüstünden gir';
 var to=q('tg_olaylar');to.innerHTML='';
 (t.olaylar||[]).forEach(function(o){var w=document.createElement('label');
  w.className='f';w.innerHTML='<label>'+o.ad+'</label>';
  var c=document.createElement('input');c.type='checkbox';c.id='tgo_'+o.anahtar;c.checked=o.secili;
  w.appendChild(c);to.appendChild(w)});
}

var hesapImza='';
function hesaplariCiz(hs){
 var imza=hs.map(function(h){return h.idx+':'+h.ad+':'+h.mod}).join('|');
 var g=q('hesaplar');
 if(imza!==hesapImza){hesapImza=imza;g.innerHTML='';
  hs.forEach(function(h){var d=document.createElement('div');d.className='hs';
   d.innerHTML='<span class="ad">'+h.ad+'</span>'+
    '<select id="md'+h.idx+'"><option value="sabit">tek kanal</option>'+
    '<option value="tarama">tara</option><option value="buff">buff</option></select>'+
    '<input class="mk" id="mk'+h.idx+'">'+
    '<button class="sv" onclick="modKaydet('+h.idx+')">kaydet</button>'+
    '<button id="bs'+h.idx+'"></button>';
   g.appendChild(d);
   q('md'+h.idx).value=h.rol==='buff'?'buff':(h.tarama?'tarama':'sabit');
   q('mk'+h.idx).value=h.tarama?h.tarama_metin:h.kanal;});}
 hs.forEach(function(h){var b=q('bs'+h.idx);if(!b)return;
  b.textContent=h.calisiyor?'■':'▶';b.className=h.calisiyor?'kirmizi':'yesil';
  b.onclick=function(){komut({komut:h.calisiyor?'durdur_hesap':'baslat_hesap',idx:h.idx})}});
}

function oyunEt(o){var s=(o.ad||'oyuncu')+(o.mesafe_m!=null?' '+Math.round(o.mesafe_m)+'m':'');
 return o.dusman?'<span class="dsm">🔴 '+s+'</span>':s}
function kanallariCiz(d){q('saat').textContent=new Date().toLocaleTimeString();
 var g=q('kanallar');g.innerHTML='';
 var ks=d.kanallar||{};Object.keys(ks).sort(function(a,b){return a-b}).forEach(function(kn){
  var o=ks[kn],el=document.createElement('div');el.className='k';
  var mt=o.metinler||[],oy=o.oyuncular||[],dsm=oy.filter(function(p){return p.dusman});
  var kenar='#262a36',drenk='#9aa0b4',dyazi='izlenmiyor';
  var izlen=o.tarama?o.simdi_burada:o.oyunda;
  if(o.tarama&&o.son_bakis==null&&!izlen){drenk='#9aa0b4';dyazi='? bakılmadı'}
  else if(!izlen&&!o.tarama){dyazi=(o.durum||'')}
  else if(dsm.length){kenar='#ff5a5a';drenk='#ff5a5a';dyazi='🔴 DÜŞMAN: '+dsm.map(function(p){return p.ad}).join(', ')}
  else if(mt.some(function(m){return m.kesiliyor})){kenar='#ffb020';drenk='#ffb020';dyazi='⚔ kesiliyor 👤'}
  else if(mt.length){var op=mt.some(function(m){return m.oyuncu});
   kenar=op?'#ffb020':'#37d67a';drenk=kenar;dyazi='● '+mt.length+' metin'+(op?'  👤 oyuncu var':'')}
  else if(izlen){dyazi='○ yok'}
  if(o.buff&&kenar==='#262a36')kenar='#33aaff';
  if(o.oldu){kenar='#ff5a5a';drenk='#ff5a5a';
   dyazi='💀 ÖLDÜ'+(o.canlan_acik?' → canlanıyor':' (canlanma kapalı)')}
  el.style.borderColor=kenar;
  var h='<div class="b">ch'+kn+(o.buff?' 🛡':'')+'</div>'+
   '<div class="d" style="color:'+drenk+'">'+dyazi+'</div>'+
   (o.buff?'<div class="oy" style="color:#33aaff">🛡 buffçı burada</div>':'');
  mt.slice(0,3).forEach(function(m){h+='<div class="metin">'+(m.ad||'?')+
   (m.mesafe_m!=null?' '+Math.round(m.mesafe_m)+'m':'')+
   (m.oyuncu?' <span style="color:#ffb020">👤'+m.oyuncu+
    (m.oyuncu_mesafe_m!=null?' '+Math.round(m.oyuncu_mesafe_m)+'m':'')+'</span>':'')+'</div>'});
  if(oy.length)h+='<div class="oy">👥 '+oy.slice(0,6).map(oyunEt).join(', ')+'</div>';
  if(o.tarama&&o.son_bakis)h+='<div class="ay">son bakış '+o.son_bakis+'</div>';
  el.innerHTML=h;g.appendChild(el)});
 q('bilgi').textContent=(d.calisan||0)+'/'+(d.hesap||0)+' hesap çalışıyor';
 var b=d.buff||{},bt=b.calisan?('🛡 buffçı ch'+b.kanal+(b.acik?' — '+(b.hedef||'?')+' bekleniyor':' (kapalı)')):'buffçı çalışmıyor';
 q('buffbilgi').textContent=bt;
 if(b.calisan&&b.kanal&&document.activeElement.id!=='buffk')q('buffk').value=b.kanal;}

function logCiz(satirlar){var el=q('log');
 var yak=el.scrollHeight-el.scrollTop-el.clientHeight<40;
 el.textContent=(satirlar||[]).join(String.fromCharCode(10));if(yak)el.scrollTop=el.scrollHeight;}

async function durum(){try{var r=await fetch(api('api/durum'));if(r.status==403){
 q('bilgi').textContent='parola hatalı (URL sonundaki ?k=... doğru mu?)';return}
 var d=await r.json();kanallariCiz(d);formDoldur(d);hesaplariCiz(d.hesaplar||[]);logCiz(d.log);
}catch(e){q('bilgi').textContent='bağlantı yok'}}
setInterval(durum,500);durum();
</script></body></html>"""


def ad_fold(s):
    """Ad karşılaştırması için sadeleştir: Türkçe harfleri düzle + küçük harf."""
    s = (s or "").strip()
    for a, b in (("İ", "i"), ("I", "i"), ("ı", "i"), ("Ş", "s"), ("ş", "s"),
                 ("Ğ", "g"), ("ğ", "g"), ("Ü", "u"), ("ü", "u"),
                 ("Ö", "o"), ("ö", "o"), ("Ç", "c"), ("ç", "c")):
        s = s.replace(a, b)
    # İ'nin küçük hali birleşik nokta (U+0307) bırakabilir; onu da at.
    return s.lower().replace("̇", "")
TG_YARDIM = ("Kurulum: @BotFather → /newbot → token'ı yapıştır → botunda Başlat → Bul → Kaydet."
             "  Komutlar: /durum  /oyuncular  /ekran  /durdur  /baslat")
RENKLI_ETIKETLER = {"VAR": OK, "ÇIKTI": OK, "GİTTİ": UYARI, "HATA": HATA,
                    "UYARI": UYARI, "bilgi": SOLUK, "KESİLİYOR": UYARI,
                    "KESİLDİ": HATA, "BIRAKTI": SOLUK, "YANINDA": UYARI}


def bildirim_sesi():
    """İki kez 'di-dıt'. TAMBOT_SESSIZ varsa çalmaz (testler)."""
    if os.environ.get("TAMBOT_SESSIZ"):
        return False

    def cal():
        try:
            import winsound
            for _ in range(2):
                winsound.Beep(1000, 140)
                winsound.Beep(1500, 220)
                time.sleep(0.08)
        except Exception:                               # noqa: BLE001
            pass

    threading.Thread(target=cal, daemon=True).start()
    return True


def mod_metni(h):
    if (h.get("rol") or "").lower() == "buff":
        try:
            return "buff ch%d" % int(h.get("kanal", 0))
        except (TypeError, ValueError):
            return "buff"
    tarama = h.get("tarama") or []
    if tarama:
        k = [int(x) for x in tarama]
        if len(k) > 2 and k == list(range(k[0], k[0] + len(k))):
            return "tarama %d-%d" % (k[0], k[-1])
        return "tarama " + ",".join(map(str, k))
    try:
        return "ch%d" % int(h.get("kanal", 0))
    except (TypeError, ValueError):
        return "?"


# Harita: ±HARITA_YARICAP_HAM ham (100 ham = 1 m) görünür. Görüş ~50 m.
HARITA_YARICAP_HAM = 6000
RENK_METIN = "#3c8cff"
RENK_OYUNCU = "#aa3cff"
RENK_CANAVAR = "#ff3232"
RENK_NPC = "#00b050"
RENK_BEN = "#37d67a"


def harita_px(konum, x, y, orta, olcek):
    """Ham (x, y) -> canvas pikseli. Karakter (konum) merkezde; +y aşağı."""
    cx, cy = konum
    return orta + (x - cx) * olcek, orta + (y - cy) * olcek


def oyuncu_etiket(oy, dusmanlar=None):
    """Haritadaki oyuncu: 'Ad 12m'. Düşmansa başına 🔴."""
    ad = oy.get("ad") or "oyuncu"
    s = "%s %.0fm" % (ad, oy["mesafe_m"]) if oy.get("mesafe_m") is not None else ad
    if dusmanlar and ad_fold(ad) in dusmanlar:
        return "🔴 " + s
    return s


def oyuncu_notu(m):
    """Metnin yanındaki oyuncu: kesen (vuran) öncelikli, yoksa yakındaki oyuncu."""
    if m.get("kesiliyor") and m.get("vuran"):
        d = "  %.0f m" % m["vuran_mesafe_m"] if m.get("vuran_mesafe_m") is not None else ""
        return "⚔ %s%s" % (m["vuran"], d)
    if m.get("oyuncu"):
        d = "  %.0f m" % m["oyuncu_mesafe_m"] if m.get("oyuncu_mesafe_m") is not None else ""
        return "👤 %s%s" % (m["oyuncu"], d)
    return ""


def metin_satiri(m):
    """Kanal kutusundaki metin satırı: ad + mesafe + (varsa) yanındaki oyuncu — TEK satırda."""
    s = m.get("ad", "?")
    if m.get("mesafe_m") is not None:
        s += "  %.0f m" % m["mesafe_m"]
    not_ = oyuncu_notu(m)
    if not_:
        s += "\n  " + not_
    return s


def gecen(sn):
    if sn is None:
        return ""
    sn = int(sn)
    if sn < 60:
        return "%d sn önce" % sn
    return "%d dk %02d sn önce" % divmod(sn, 60)


class Panel(tk.Tk):
    def __init__(self, ayar_yolu=None):
        super().__init__()
        self.ayar_yolu = ayar_yolu or mi.AYAR_DOSYASI
        self.title("Metin İzleyici")
        self.geometry("1060x800")
        self.minsize(920, 700)
        self.configure(bg=KOYU)
        self.kuyruk = queue.Queue()
        self.izleyiciler = {}          # hesap indeksi -> Izleyici
        self._canli = []               # HTTP durum sunucusunun gördüğü liste
        self.adlar = mi.katalog_yukle()
        self.http = None
        self._onceki_var = {}
        self._onceki_kes = {}
        self._onceki_dusman = {}       # kanal -> uyarı verilen düşman adları
        self.harita_pencere = None     # açık HaritaPenceresi (tek pencere)
        self._web_kuyruk = queue.Queue()   # web panelinden gelen komutlar
        self._son_bbox = None          # panel penceresi konumu (ekran görüntüsü için)
        self._tunel_proc = None        # cloudflared alt süreci
        self._tunel_url = None         # yakalanan genel tünel adresi
        self._qr_img = None            # QR PhotoImage (çöp toplanmasın)
        self._web_log = collections.deque(maxlen=120)   # web için son olaylar
        self.tg = None                 # TelegramGonderici (ayar açıksa)
        self.tg_kumanda = None         # TelegramKumanda (komut dinleyici)
        self._tg_kuyruk = queue.Queue()
        self._tg_acici = None          # testler sahte HTTP verir
        self._onceki_tur = {}          # izleyici id -> son bildirilen tur
        self._onceki_bakis = {}        # kanal -> son ziyaretin saati
        self._kapaniyor = False
        self.veri = self._veri_oku()
        self._stil()
        self._arayuz()
        self._hesaplari_listele()
        self._ayarlari_goster()
        self._buff_goster()
        self.dusman_var.set(", ".join(self.veri.get("dusmanlar", []) or []))
        self.dusman_ses_var.set(bool(self.veri.get("dusman_ses", True)))
        self._tg_goster()
        self._web_goster()
        self._web_baslat()             # ayar açıksa mobil web panelini başlat
        # Tam bottaki (tambot) kanalı izleyen arka plan durumu
        self._tb_kanal = {"simdi": 0, "cekilen": 0, "hata": ""}
        self._tb_iplik = None
        self._tb_api = None
        self._tazele_ms = int(self.veri.get("tazele_ms", 200))   # ekran/komut tazeleme
        self.after(self._tazele_ms, self._tazele)
        self.protocol("WM_DELETE_WINDOW", self._kapat)

    # ── dosya ────────────────────────────────────────────────────
    def _veri_oku(self):
        if not os.path.exists(self.ayar_yolu):
            mi.ayar_yukle(self.ayar_yolu)          # boş örneği yazar
        with open(self.ayar_yolu, encoding="utf-8-sig") as f:
            return json.load(f)

    def _veri_yaz(self):
        gecici = self.ayar_yolu + ".yeni"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(self.veri, f, ensure_ascii=False, indent=2)
        os.replace(gecici, self.ayar_yolu)

    def _hesaplar(self):
        return self.veri.setdefault("hesaplar", [])

    @staticmethod
    def _dolu_mu(h):
        return bool((h.get("kullanici") or "").strip() and h.get("sifre"))

    # ── görünüm ──────────────────────────────────────────────────
    def _stil(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=METIN, rowheight=22, font=YAZI, borderwidth=0)
        s.map("Treeview", background=[("selected", VURGU)],
              foreground=[("selected", KOYU)])
        s.configure("Treeview.Heading", background=CIZGI, foreground=SOLUK,
                    font=KALIN, relief="flat")

    def _btn(self, ana, metin, komut, renk=CIZGI):
        return tk.Button(ana, text=metin, command=komut, bg=renk,
                         fg=KOYU if renk in (VURGU, OK, UYARI, HATA) else METIN,
                         activebackground=VURGU, activeforeground=KOYU,
                         relief="flat", bd=0, padx=10, pady=4, font=YAZI,
                         cursor="hand2")

    def _kutu(self, ana, baslik):
        dis = tk.Frame(ana, bg=PANEL, highlightbackground=CIZGI, highlightthickness=1)
        tk.Label(dis, text=baslik, bg=PANEL, fg=VURGU, font=KALIN,
                 anchor="w").pack(fill="x", padx=8, pady=(6, 2))
        return dis

    def _onay_kutusu(self, ana, metin, degisken, bg):
        return tk.Checkbutton(ana, text=metin, variable=degisken, bg=bg, fg=METIN,
                              selectcolor=KOYU if bg == PANEL else PANEL,
                              activebackground=bg, activeforeground=METIN, font=YAZI)

    def _arayuz(self):
        ust = tk.Frame(self, bg=KOYU)
        ust.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(ust, text="METİN İZLEYİCİ", bg=KOYU, fg=METIN,
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        self.http_etiket = tk.Label(ust, text="", bg=KOYU, fg=SOLUK, font=YAZI)
        self.http_etiket.pack(side="left", padx=14)
        self._btn(ust, "■ Hepsini durdur", self._hepsini_durdur, HATA).pack(
            side="right", padx=(6, 0))
        self._btn(ust, "▶ Hepsini başlat", self._hepsini_baslat, OK).pack(side="right")
        self.ses_var = tk.BooleanVar(value=True)
        self._onay_kutusu(ust, "Metin bulunca ses", self.ses_var, KOYU).pack(
            side="right", padx=12)

        govde = tk.Frame(self, bg=KOYU)
        govde.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        govde.columnconfigure(0, weight=2)
        govde.columnconfigure(1, weight=3)
        govde.rowconfigure(0, weight=1)

        # — sol: hesaplar + ayarlar (kaydırılabilir — çok kutu var) —
        sol_dis = tk.Frame(govde, bg=KOYU)
        sol_dis.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        sol_kanvas = tk.Canvas(sol_dis, bg=KOYU, highlightthickness=0, bd=0)
        sol_kaydir = ttk.Scrollbar(sol_dis, orient="vertical", command=sol_kanvas.yview)
        sol_kanvas.configure(yscrollcommand=sol_kaydir.set)
        sol_kaydir.pack(side="right", fill="y")
        sol_kanvas.pack(side="left", fill="both", expand=True)
        sol = tk.Frame(sol_kanvas, bg=KOYU)
        _sol_pencere = sol_kanvas.create_window((0, 0), window=sol, anchor="nw")
        sol.bind("<Configure>",
                 lambda e: sol_kanvas.configure(scrollregion=sol_kanvas.bbox("all")))
        sol_kanvas.bind("<Configure>",
                        lambda e: sol_kanvas.itemconfigure(_sol_pencere, width=e.width))

        def _sol_teker(e):
            # Yalnızca fare sol panelin üstündeyken sol sütunu kaydır.
            w = self.winfo_containing(e.x_root, e.y_root)
            while w is not None:
                if w is sol_kanvas or w is sol:
                    sol_kanvas.yview_scroll(int(-e.delta / 120), "units")
                    return
                w = getattr(w, "master", None)

        sol_kanvas.bind_all("<MouseWheel>", _sol_teker, add="+")
        kh = self._kutu(sol, "Hesaplar")
        kh.pack(fill="both", expand=True)
        self.agac = ttk.Treeview(kh, columns=("mod", "kullanici", "durum"),
                                 show="headings", height=4, selectmode="browse")
        for sutun, baslik, gen in (("mod", "Mod", 90), ("kullanici", "Hesap", 110),
                                   ("durum", "Durum", 230)):
            self.agac.heading(sutun, text=baslik)
            self.agac.column(sutun, width=gen, anchor="w")
        self.agac.pack(fill="both", expand=True, padx=8, pady=4)
        self.agac.bind("<Double-1>", lambda e: self._duzenle())
        self.agac.bind("<<TreeviewSelect>>", lambda e: self._mod_goster())
        bh = tk.Frame(kh, bg=PANEL)
        bh.pack(fill="x", padx=8, pady=(0, 8))
        for metin, komut, renk in (("Ekle", self._ekle, CIZGI),
                                   ("Düzenle", self._duzenle, CIZGI),
                                   ("Sil", self._sil, CIZGI),
                                   ("▶ Başlat", self._secileni_baslat, OK),
                                   ("■ Durdur", self._secileni_durdur, HATA)):
            self._btn(bh, metin, komut, renk).pack(side="left", padx=(0, 4))

        # — seçili hesabın modu: tek kanal / kanal değiştirerek tarama —
        km = tk.Frame(kh, bg=KOYU, highlightbackground=CIZGI, highlightthickness=1)
        km.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(km, text="Seçili hesap ne yapsın?", bg=KOYU, fg=VURGU, font=KALIN,
                 anchor="w").grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 2))
        self.mod_var = tk.StringVar(value="sabit")
        self.mod_kanal_var = tk.StringVar(value="1")
        self.mod_tarama_var = tk.StringVar(value="1-8")
        for r, (metin, deger) in enumerate((("Tek kanalda bekle", "sabit"),
                                            ("Kanalları tara", "tarama"),
                                            ("Buff'çı (YIKAR'a bas)", "buff")), 1):
            tk.Radiobutton(km, text=metin, variable=self.mod_var, value=deger, bg=KOYU, fg=METIN,
                           selectcolor=PANEL, activebackground=KOYU, activeforeground=METIN,
                           font=YAZI).grid(row=r, column=0, sticky="w", padx=4)
        tk.Spinbox(km, from_=1, to=8, textvariable=self.mod_kanal_var, width=4, bg=PANEL,
                   fg=METIN, buttonbackground=CIZGI, relief="flat", font=SABIT).grid(
            row=1, column=1, sticky="w", padx=4)
        tk.Entry(km, textvariable=self.mod_tarama_var, bg=PANEL, fg=METIN,
                 insertbackground=METIN, relief="flat", width=10, font=SABIT).grid(
            row=2, column=1, sticky="w", padx=4)
        self._btn(km, "Modu kaydet", self._mod_kaydet, VURGU).grid(
            row=1, column=2, rowspan=3, sticky="nsew", padx=6, pady=2)
        tk.Label(km, text="Tara = tek hesap kanal değiştirerek (ör. 1-8) sırayla gezer. "
                          "Buff'çı = tek kanalda durup YIKAR yaklaşınca yetenek basar "
                          "(ayarlar aşağıda \"Buff'çı\" kutusunda).",
                 bg=KOYU, fg=SOLUK, font=("Segoe UI", 8), anchor="w", justify="left",
                 wraplength=360).grid(row=4, column=0, columnspan=3, sticky="w", padx=6)
        self.mod_etiket = tk.Label(km, text="önce listeden bir hesap seç", bg=KOYU, fg=SOLUK,
                                   font=YAZI, anchor="w")
        self.mod_etiket.grid(row=5, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))
        km.columnconfigure(0, weight=1)

        ka = self._kutu(sol, "Ayarlar")
        ka.pack(fill="x", pady=(8, 0))
        g = tk.Frame(ka, bg=PANEL)
        g.pack(fill="x", padx=8, pady=(2, 8))
        self.bakis_var = tk.StringVar()
        self.vnum_var = tk.StringVar()
        self.tum_var = tk.BooleanVar()
        for i, (etiket, var) in enumerate((
                ("Taramada kanal başına bakış (sn)", self.bakis_var),
                ("Aranan metin vnum'ları (virgülle)", self.vnum_var))):
            tk.Label(g, text=etiket, bg=PANEL, fg=SOLUK, font=YAZI).grid(
                row=i, column=0, sticky="w", pady=2)
            tk.Entry(g, textvariable=var, bg=KOYU, fg=METIN, insertbackground=METIN,
                     relief="flat", width=14, font=SABIT).grid(
                row=i, column=1, sticky="e", pady=2)
        self._onay_kutusu(g, "Bütün metinler (vnum'a bakma)", self.tum_var, PANEL).grid(
            row=2, column=0, columnspan=2, sticky="w")
        # PAKET GÖNDEREN özellikler — ayrı, uyarılı bölüm.
        tk.Label(g, text="⚠ Aşağıdakiler oyuna paket gönderir (isteğe bağlı):",
                 bg=PANEL, fg=UYARI, font=("Segoe UI", 8)).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.canlan_var = tk.BooleanVar()
        self.yeniden_var = tk.BooleanVar()
        self.don_var = tk.BooleanVar()
        self._onay_kutusu(g, "Ölünce yerinde canlan (/restart_here)",
                          self.canlan_var, PANEL).grid(row=4, column=0, columnspan=2, sticky="w")
        self._onay_kutusu(g, "Ölünce kanaldan çıkıp tekrar gir (canlanır)",
                          self.yeniden_var, PANEL).grid(row=5, column=0, columnspan=2, sticky="w")
        tk.Label(g, text="↳ tekrar girme süresi (sn)", bg=PANEL, fg=SOLUK, font=YAZI).grid(
            row=6, column=0, sticky="w", pady=2)
        self.yeniden_gecikme_var = tk.StringVar()
        tk.Entry(g, textvariable=self.yeniden_gecikme_var, bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat", width=14, font=SABIT).grid(
            row=6, column=1, sticky="e", pady=2)
        self._onay_kutusu(g, "Kısa mesafede park noktasına dön",
                          self.don_var, PANEL).grid(row=7, column=0, columnspan=2, sticky="w")
        self._btn(g, "Ayarları kaydet", self._ayarlari_kaydet, VURGU).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        g.columnconfigure(0, weight=1)

        # — düşman listesi —
        kdz = self._kutu(sol, "Düşman isimleri")
        kdz.pack(fill="x", pady=(8, 0))
        gd = tk.Frame(kdz, bg=PANEL)
        gd.pack(fill="x", padx=8, pady=(2, 8))
        tk.Label(gd, text="Adları virgülle yaz — görülünce kanal KIRMIZI olur:",
                 bg=PANEL, fg=SOLUK, font=YAZI).pack(anchor="w")
        self.dusman_var = tk.StringVar()
        tk.Entry(gd, textvariable=self.dusman_var, bg=KOYU, fg=HATA, insertbackground=METIN,
                 relief="flat", font=SABIT).pack(fill="x", pady=2)
        self.dusman_ses_var = tk.BooleanVar(value=True)
        self._onay_kutusu(gd, "Düşman görülünce ses çal", self.dusman_ses_var, PANEL).pack(anchor="w")
        self._btn(gd, "Düşmanları kaydet", self._dusman_kaydet, HATA).pack(fill="x")
        tk.Label(gd, text="Hangi kanalda görünürse o kutu kırmızı, ses + Telegram uyarısı.",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8), justify="left",
                 wraplength=360).pack(anchor="w", pady=(2, 0))

        # — buff'çı —
        kb = self._kutu(sol, "Buff'çı")
        kb.pack(fill="x", pady=(8, 0))
        gb = tk.Frame(kb, bg=PANEL)
        gb.pack(fill="x", padx=8, pady=(2, 8))
        self.buff_acik_var = tk.BooleanVar(value=False)
        self.buff_hedef_var = tk.StringVar()
        self.buff_yardim_var = tk.StringVar()
        self.buff_guc_var = tk.StringVar()
        self.buff_menzil_var = tk.StringVar()
        self.buff_aralik_var = tk.StringVar()
        self.buff_gecikme_var = tk.StringVar()
        self.buff_cek_var = tk.StringVar(value="1")
        tk.Label(gb, text="⚠ Oyuna paket gönderir (hesap adı YIKAR'a yetenek basar). "
                          "Rolü \"Buff'çı\" olan hesapta çalışır.",
                 bg=PANEL, fg=UYARI, font=("Segoe UI", 8), justify="left",
                 wraplength=360).grid(row=0, column=0, columnspan=2, sticky="w")
        self._onay_kutusu(gb, "Buff'çıyı çalıştır", self.buff_acik_var, PANEL).grid(
            row=1, column=0, columnspan=2, sticky="w")
        for r, (etiket, var) in enumerate((
                ("Yaklaşınca buff'lanacak oyuncu", self.buff_hedef_var),
                ("Ejderha Yardımı — yetenek vnum", self.buff_yardim_var),
                ("Ejderha Gücü — yetenek vnum", self.buff_guc_var),
                ("İki yetenek arası (sn)", self.buff_gecikme_var),
                ("Menzil (m)", self.buff_menzil_var),
                ("Aynı kişiye tekrar (sn)", self.buff_aralik_var)), 2):
            tk.Label(gb, text=etiket, bg=PANEL, fg=SOLUK, font=YAZI).grid(
                row=r, column=0, sticky="w", pady=1)
            tk.Entry(gb, textvariable=var, bg=KOYU, fg=METIN, insertbackground=METIN,
                     relief="flat", width=12, font=SABIT).grid(row=r, column=1, sticky="e", pady=1)
        self._btn(gb, "Buff ayarlarını kaydet", self._buff_kaydet, VURGU).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        cf = tk.Frame(gb, bg=PANEL)
        cf.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        tk.Label(cf, text="Buff'çıyı kanala çek:", bg=PANEL, fg=SOLUK, font=YAZI).pack(side="left")
        tk.Spinbox(cf, from_=1, to=8, textvariable=self.buff_cek_var, width=4, bg=KOYU,
                   fg=METIN, buttonbackground=CIZGI, relief="flat", font=SABIT).pack(
            side="left", padx=4)
        self._btn(cf, "Çek", self._buff_cek, OK).pack(side="left")
        self.buff_takip_var = tk.BooleanVar(value=bool(self.veri.get("buff_takip")))
        self._onay_kutusu(gb, "Tam bottaki kanalı otomatik takip et",
                          self.buff_takip_var, PANEL).grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(4, 0))
        tk.Label(gb, text="Tam bot hangi kanala geçerse buff'çı da anında oraya "
                          "çekilir (kanal APK durumundaki porttan okunur).",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8), justify="left",
                 wraplength=360).grid(row=12, column=0, columnspan=2, sticky="w")
        tk.Label(gb, text="vnum'ları bulmak için oyunda yetenekleri bas, "
                          "python tools/yetenek_kaydet.py çalıştır — bastığın vnum'ları yazar.",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8), justify="left",
                 wraplength=360).grid(row=10, column=0, columnspan=2, sticky="w", pady=(4, 0))
        gb.columnconfigure(0, weight=1)

        # — Telegram bildirimi —
        kt = self._kutu(sol, "Telegram bildirimi")
        kt.pack(fill="x", pady=(8, 0))
        gt = tk.Frame(kt, bg=PANEL)
        gt.pack(fill="x", padx=8, pady=(2, 8))
        self.tg_acik_var = tk.BooleanVar(value=False)
        self.tg_token_var = tk.StringVar()
        self.tg_sohbet_var = tk.StringVar()
        self.tg_olay_vars = {k: tk.BooleanVar(value=v) for k, v in TG_VARSAYILAN.items()}
        self._onay_kutusu(gt, "Olayları Telegram'a gönder", self.tg_acik_var, PANEL).grid(
            row=0, column=0, columnspan=3, sticky="w")
        tk.Label(gt, text="Bot token", bg=PANEL, fg=SOLUK, font=YAZI).grid(
            row=1, column=0, sticky="w", pady=2)
        tk.Entry(gt, textvariable=self.tg_token_var, show="•", bg=KOYU, fg=METIN,
                 insertbackground=METIN, relief="flat", font=SABIT).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=2)
        tk.Label(gt, text="Sohbet kimliği", bg=PANEL, fg=SOLUK, font=YAZI).grid(
            row=2, column=0, sticky="w", pady=2)
        tk.Entry(gt, textvariable=self.tg_sohbet_var, bg=KOYU, fg=METIN, insertbackground=METIN,
                 relief="flat", font=SABIT, width=16).grid(row=2, column=1, sticky="ew", pady=2)
        self._btn(gt, "Bul", self._tg_bul).grid(row=2, column=2, sticky="ew", padx=(4, 0), pady=2)
        of = tk.Frame(gt, bg=PANEL)
        of.grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 0))
        for n, (anahtar, ad) in enumerate(TG_OLAYLAR):
            self._onay_kutusu(of, ad, self.tg_olay_vars[anahtar], PANEL).grid(
                row=n // 3, column=n % 3, sticky="w", padx=(0, 6))
        bf = tk.Frame(gt, bg=PANEL)
        bf.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self._btn(bf, "Kaydet", self._tg_kaydet, VURGU).pack(side="left", fill="x", expand=True,
                                                           padx=(0, 3))
        self._btn(bf, "Test mesajı", self._tg_test).pack(side="left", fill="x", expand=True,
                                                        padx=(3, 0))
        self.tg_etiket = tk.Label(gt, text=TG_YARDIM, bg=PANEL, fg=SOLUK, font=("Segoe UI", 8),
                                  justify="left", anchor="w", wraplength=380)
        self.tg_etiket.grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 0))
        gt.columnconfigure(1, weight=1)

        # — mobil web paneli —
        kw = self._kutu(sol, "Web paneli (telefon)")
        kw.pack(fill="x", pady=(8, 0))
        gw = tk.Frame(kw, bg=PANEL)
        gw.pack(fill="x", padx=8, pady=(2, 8))
        self.web_acik_var = tk.BooleanVar(value=False)
        self.web_port_var = tk.StringVar()
        self.web_parola_var = tk.StringVar()
        self._onay_kutusu(gw, "Web panelini aç (telefondan izle/yönet)",
                          self.web_acik_var, PANEL).grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(gw, text="Port", bg=PANEL, fg=SOLUK, font=YAZI).grid(
            row=1, column=0, sticky="w", pady=2)
        tk.Entry(gw, textvariable=self.web_port_var, bg=KOYU, fg=METIN, insertbackground=METIN,
                 relief="flat", font=SABIT, width=10).grid(row=1, column=1, sticky="w", pady=2)
        tk.Label(gw, text="Parola", bg=PANEL, fg=SOLUK, font=YAZI).grid(
            row=2, column=0, sticky="w", pady=2)
        tk.Entry(gw, textvariable=self.web_parola_var, bg=KOYU, fg=OK, insertbackground=METIN,
                 relief="flat", font=SABIT, state="readonly",
                 readonlybackground=KOYU).grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)
        self._btn(gw, "Kaydet & başlat", self._web_kaydet, VURGU).grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.web_url_etiket = tk.Label(gw, text="", bg=PANEL, fg=OK, font=SABIT,
                                       justify="left", anchor="w", wraplength=380)
        self.web_url_etiket.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))
        tk.Label(gw, text="Telefon aynı Wi-Fi'deyken yukarıdaki adres. Mobil veriyle "
                          "(her yerden) erişim için alttaki tüneli aç:",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8), justify="left",
                 wraplength=380).grid(row=5, column=0, columnspan=3, sticky="w", pady=(2, 0))
        # — uzaktan erişim tüneli (cloudflared) —
        tf = tk.Frame(gw, bg=PANEL)
        tf.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.tunel_btn = self._btn(tf, "Tünel aç (uzaktan)", self._tunel_ac_kapa, OK)
        self.tunel_btn.pack(side="left")
        self._btn(tf, "Kopyala", self._tunel_kopyala).pack(side="left", padx=4)
        self._btn(tf, "QR", self._tunel_qr).pack(side="left")
        self.tunel_url_var = tk.StringVar()
        tk.Entry(gw, textvariable=self.tunel_url_var, bg=KOYU, fg=OK, insertbackground=METIN,
                 relief="flat", font=SABIT, state="readonly",
                 readonlybackground=KOYU).grid(row=7, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.tunel_etiket = tk.Label(gw, text="tünel kapalı", bg=PANEL, fg=SOLUK,
                                     font=("Segoe UI", 8), justify="left", anchor="w",
                                     wraplength=380)
        self.tunel_etiket.grid(row=8, column=0, columnspan=3, sticky="w", pady=(2, 0))
        gw.columnconfigure(1, weight=1)

        # — sağ: kanallar + olaylar —
        sag = tk.Frame(govde, bg=KOYU)
        sag.grid(row=0, column=1, sticky="nsew")
        kk = self._kutu(sag, "Kanallar")
        kk.pack(fill="x")
        self.metin_ozet = tk.Label(kk, text="metin olan kanal yok", bg=PANEL, fg=SOLUK,
                                   font=("Segoe UI", 11, "bold"), anchor="w")
        self.metin_ozet.pack(fill="x", padx=8, pady=(0, 2))
        izgara = tk.Frame(kk, bg=PANEL)
        izgara.pack(fill="x", padx=8, pady=(2, 8))
        self.kanal_hucreleri = {}
        self.kanal_basliklari = {}
        for i in range(8):
            k = i + 1
            hucre = tk.Frame(izgara, bg=KOYU, highlightthickness=2, highlightbackground=CIZGI)
            hucre.grid(row=i // 4, column=i % 4, sticky="nsew", padx=3, pady=3)
            baslik = tk.Label(hucre, text="ch%d" % k, bg=KOYU, fg=METIN,
                              font=("Segoe UI", 11, "bold"), anchor="w")
            baslik.pack(fill="x", padx=6, pady=(4, 0))
            self.kanal_basliklari[k] = baslik
            durum = tk.Label(hucre, text="izlenmiyor", bg=KOYU, fg=SOLUK, font=KALIN,
                             anchor="w", justify="left")
            durum.pack(fill="x", padx=6)
            # Detay artık RENKLİ (web'deki gibi): metin mavi, oyuncu mor,
            # düşman kırmızı, buff/şimdi-burada mavi, ben yeşil — Text + etiket.
            ayrinti = tk.Text(hucre, bg=KOYU, fg=SOLUK, font=("Segoe UI", 8),
                              relief="flat", bd=0, highlightthickness=0, wrap="word",
                              height=6, width=1, cursor="hand2", state="disabled",
                              spacing1=0, spacing3=0)
            ayrinti.pack(fill="both", expand=True, padx=6, pady=(0, 4))
            for etk, renk in (("metin", METIN_MAVI), ("oyuncu", OYUNCU_MOR),
                              ("dusman", HATA), ("buff", VURGU), ("ben", OK),
                              ("sari", UYARI), ("soluk", SOLUK)):
                ayrinti.tag_configure(etk, foreground=renk)
            self.kanal_hucreleri[k] = (hucre, durum, ayrinti)
            # Kanala tıklayınca o kanalın haritası (R2 Panel'deki gibi radar).
            for w in (hucre, baslik, durum, ayrinti):
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda e, kk=k: self._harita_ac(kk))
        for c in range(4):
            izgara.columnconfigure(c, weight=1, uniform="kanal")

        ko = self._kutu(sag, "Olaylar")
        ko.pack(fill="both", expand=True, pady=(8, 0))
        self.log = tk.Text(ko, bg=KOYU, fg=METIN, relief="flat", font=SABIT, height=12,
                           wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        for etiket, renk in RENKLI_ETIKETLER.items():
            self.log.tag_configure(etiket, foreground=renk)

    def _log_yaz(self, metin, etiket="bilgi"):
        try:
            self._web_log.append(metin)
        except Exception:                              # noqa: BLE001
            pass
        self.log.configure(state="normal")
        self.log.insert("end", metin + "\n", etiket)
        if int(self.log.index("end-1c").split(".")[0]) > 600:
            self.log.delete("1.0", "150.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ── hesaplar ─────────────────────────────────────────────────
    def _hesaplari_listele(self):
        secili = self.agac.selection()
        self.agac.delete(*self.agac.get_children())
        for i, h in enumerate(self._hesaplar()):
            if not self._dolu_mu(h):
                continue
            self.agac.insert("", "end", iid=str(i),
                             values=(mod_metni(h), h.get("kullanici", ""), self._durum(i)))
        if secili and self.agac.exists(secili[0]):
            self.agac.selection_set(secili[0])
        elif self.agac.get_children():
            # Açılışta ilk hesap seçili gelsin: mod bölümü hemen dolu görünür.
            self.agac.selection_set(self.agac.get_children()[0])
        self._mod_goster()

    def _mod_goster(self):
        """Seçili hesabın modunu ana penceredeki mod bölümüne yükler."""
        if not hasattr(self, "mod_etiket"):
            return
        idx = self._secili()
        if idx is None:
            self.mod_etiket.configure(text="önce listeden bir hesap seç", fg=SOLUK)
            return
        h = self._hesaplar()[idx]
        if (h.get("rol") or "").lower() == "buff":
            self.mod_var.set("buff")
            self.mod_kanal_var.set(str(h.get("kanal", 1) or 1))
        elif h.get("tarama"):
            self.mod_var.set("tarama")
            self.mod_tarama_var.set(mod_metni(h)[len("tarama "):])
        else:
            self.mod_var.set("sabit")
            self.mod_kanal_var.set(str(h.get("kanal", 1) or 1))
        self.mod_etiket.configure(text="%s: %s" % (h.get("kullanici", ""), mod_metni(h)), fg=SOLUK)

    def _mod_kaydet(self):
        """Mod bölümündeki seçimi seçili hesaba yazar. Döner: kaydedildi mi."""
        idx = self._secili()
        if idx is None:
            self.mod_etiket.configure(text="önce listeden bir hesap seç", fg=UYARI)
            return False
        h = dict(self._hesaplar()[idx])
        try:
            if self.mod_var.get() == "tarama":
                h.pop("rol", None)
                h["tarama"] = mi.tarama_coz(self.mod_tarama_var.get())
                h["kanal"] = h["tarama"][0]
            else:
                k = int(self.mod_kanal_var.get())
                if not 1 <= k <= 8:
                    raise ValueError("kanal 1-8 arası olmalı")
                h.pop("tarama", None)
                h["kanal"] = k
                if self.mod_var.get() == "buff":
                    h["rol"] = "buff"
                else:
                    h.pop("rol", None)
        except ValueError as e:
            self.mod_etiket.configure(text="hatalı: %s" % e, fg=HATA)
            return False
        hatalar = self._hesap_kaydet(idx, h)
        if hatalar:
            self.mod_etiket.configure(text=hatalar[0], fg=HATA)
            return False
        self.agac.selection_set(str(idx))
        self.mod_etiket.configure(text="kaydedildi: %s — şimdi ▶ Başlat" % mod_metni(h), fg=OK)
        return True

    def _durum(self, i):
        z = self.izleyiciler.get(i)
        if z is None:
            return "durdu"
        if not z.is_alive():
            return "durdu"
        if getattr(z, "_oldu", False):
            return "💀 ÖLDÜ" + (" → canlanıyor" if getattr(z, "olunce_canlan", False)
                                else " (canlanma kapalı)")
        return z.durum

    def _calisiyor_mu(self, i):
        z = self.izleyiciler.get(i)
        return z is not None and z.is_alive()

    def _secili(self):
        sec = self.agac.selection()
        return int(sec[0]) if sec else None

    def _hesap_kaydet(self, idx, hesap):
        """Hesabı ekler/günceller. Döner: hata listesi (boşsa kaydedildi)."""
        if idx is not None and self._calisiyor_mu(idx):
            return ["Bu hesap çalışıyor — önce durdur."]
        if not self._dolu_mu(hesap):
            return ["Kullanıcı adı ve şifre gerekli."]
        hesaplar = list(self._hesaplar())
        if idx is None:
            hesaplar.append(hesap)
        else:
            hesaplar[idx] = hesap
        hatalar = mi.hesaplari_dogrula([h for h in hesaplar if self._dolu_mu(h)])
        if hatalar:
            return hatalar
        self.veri["hesaplar"] = hesaplar
        self._veri_yaz()
        self._hesaplari_listele()
        return []

    def _hesap_sil(self, idx):
        if self._calisiyor_mu(idx):
            return "Bu hesap çalışıyor — önce durdur."
        hesaplar = self._hesaplar()
        if not 0 <= idx < len(hesaplar):
            return "hesap yok"
        del hesaplar[idx]
        self.izleyiciler = {(i - 1 if i > idx else i): z
                            for i, z in self.izleyiciler.items() if i != idx}
        self._veri_yaz()
        self._hesaplari_listele()
        return None

    def _ekle(self):
        HesapPenceresi(self)

    def _duzenle(self):
        idx = self._secili()
        if idx is not None:
            HesapPenceresi(self, idx)

    def _sil(self):
        idx = self._secili()
        if idx is None:
            return
        ad = self._hesaplar()[idx].get("kullanici", "")
        if messagebox.askyesno("Hesabı sil", "%s silinsin mi?" % ad, parent=self):
            hata = self._hesap_sil(idx)
            if hata:
                self._log_yaz("HATA  " + hata, "HATA")

    # ── başlat / durdur ──────────────────────────────────────────
    def _bildir(self, kanal, seviye, metin):
        self.kuyruk.put((time.strftime("%H:%M:%S"), kanal, seviye, metin))

    def _baslat(self, idx):
        """Döner: None başlatıldı / hata metni."""
        if self._calisiyor_mu(idx):
            return None
        h = self._hesaplar()[idx]
        if not self._dolu_mu(h):
            return "hesap boş"
        hatalar = mi.hesaplari_dogrula([h])
        if hatalar:
            self._log_yaz("HATA  %s" % "; ".join(hatalar), "HATA")
            return hatalar[0]
        ad = h["kullanici"].strip().lower()
        for j in list(self.izleyiciler):
            if j != idx and self._calisiyor_mu(j) and \
                    (self._hesaplar()[j].get("kullanici") or "").strip().lower() == ad:
                return "aynı hesap zaten çalışıyor"
        ayar = mi.ayar_yukle(self.ayar_yolu)
        z = mi.Izleyici(h, ayar, self.adlar, self._bildir)
        eski = self.izleyiciler.get(idx)
        if eski in self._canli:
            self._canli.remove(eski)
        self.izleyiciler[idx] = z
        self._canli.append(z)
        z.start()
        self._http_baslat(ayar)
        self._log_yaz("%s  %s başlatıldı (%s)" % (time.strftime("%H:%M:%S"),
                                                  h.get("kullanici", ""), mod_metni(h)))
        self._agac_tazele()
        return None

    def _durdur(self, idx):
        z = self.izleyiciler.get(idx)
        if z is not None:
            z.durdur()

    def _secileni_baslat(self):
        idx = self._secili()
        if idx is not None:
            hata = self._baslat(idx)
            if hata:
                self._log_yaz("HATA  " + hata, "HATA")

    def _secileni_durdur(self):
        idx = self._secili()
        if idx is not None:
            self._durdur(idx)

    def _hepsini_baslat(self):
        sira = [i for i, h in enumerate(self._hesaplar())
                if self._dolu_mu(h) and not self._calisiyor_mu(i)]
        ara = float(self.veri.get("baslama_araligi_sn",
                                  mi.VARSAYILAN["baslama_araligi_sn"]))
        for n, i in enumerate(sira):
            self.after(int(n * ara * 1000), lambda i=i: self._baslat(i))
        return sira

    def _hepsini_durdur(self):
        for i in list(self.izleyiciler):
            self._durdur(i)

    def _http_baslat(self, ayar):
        self._web_baslat()

    # ── mobil web paneli ─────────────────────────────────────────
    def _web_port(self):
        return int(self.veri.get("web_portu",
                                 self.veri.get("http_portu", mi.VARSAYILAN["http_portu"])))

    def _web_parola(self):
        p = self.veri.get("web_parola")
        if not p:
            p = os.urandom(5).hex()          # 10 haneli parola
            self.veri["web_parola"] = p
            self._veri_yaz()
        return p

    def _web_durum(self):
        """Web/telefon için tam durum (JSON'lanabilir)."""
        try:
            kanallar = mi.durum_ozeti(list(self._canli))["kanallar"]
        except Exception:                              # noqa: BLE001
            kanallar = {}
        dk = self._dusman_kumesi()
        for o in kanallar.values():
            for oy in o.get("oyuncular") or []:
                oy["dusman"] = ad_fold(oy.get("ad")) in dk
        calisan = sum(1 for i in self.izleyiciler if self._calisiyor_mu(i))
        buffcular = self._buff_calisanlar()
        buff = {"calisan": bool(buffcular),
                "kanal": buffcular[0][1].kanal if buffcular else None,
                "acik": bool(self.veri.get("buff_acik")),
                "hedef": self.veri.get("buff_hedef", "") or "",
                "yardim": self.veri.get("buff_yardim_vnum", 0),
                "guc": self.veri.get("buff_guc_vnum", 0),
                "gecikme": self.veri.get("buff_skill_gecikme_sn", 5),
                "menzil": self.veri.get("buff_menzil_m", 4),
                "aralik": self.veri.get("buff_aralik_sn", 8)}
        # Hesap listesi — ŞİFRE/PIN ASLA gönderilmez.
        hesaplar = []
        for i, h in enumerate(self._hesaplar()):
            if not self._dolu_mu(h):
                continue
            tar = bool(h.get("tarama"))
            hesaplar.append({"idx": i, "ad": h.get("kullanici", ""), "mod": mod_metni(h),
                             "kanal": h.get("kanal", 1), "tarama": tar,
                             "tarama_metin": ",".join(str(x) for x in h.get("tarama") or []),
                             "rol": (h.get("rol") or "izleyici"),
                             "calisiyor": self._calisiyor_mu(i)})
        ayarlar = {"bakis": self.veri.get("tarama_bakis_sn", mi.VARSAYILAN["tarama_bakis_sn"]),
                   "vnumlar": ",".join(str(v) for v in self.veri.get("metin_vnumlari", []) or []),
                   "tum": bool(self.veri.get("tum_metinler")),
                   "canlan": bool(self.veri.get("olunce_canlan")),
                   "yeniden": bool(self.veri.get("olunce_yeniden_gir")),
                   "yeniden_gecikme": self.veri.get("yeniden_gir_gecikme_sn", 1.5),
                   "don": bool(self.veri.get("yerine_don"))}
        t = self.veri.get("telegram") or {}
        tg_olaylar = dict(TG_VARSAYILAN, **(t.get("olaylar") or {}))
        telegram = {"acik": bool(t.get("acik")), "sohbet": str(t.get("sohbet", "") or ""),
                    "kurulu": bool(t.get("token")),        # token YOK, sadece var mı bilgisi
                    "olaylar": [{"anahtar": a, "ad": ad, "secili": bool(tg_olaylar.get(a))}
                                for a, ad in TG_OLAYLAR]}
        return {"zaman": time.strftime("%H:%M:%S"), "kanallar": kanallar,
                "dusmanlar": self.veri.get("dusmanlar", []) or [],
                "hesap": sum(1 for h in self._hesaplar() if self._dolu_mu(h)),
                "calisan": calisan, "buff": buff, "hesaplar": hesaplar,
                "ayarlar": ayarlar,
                "dusman": {"adlar": ", ".join(self.veri.get("dusmanlar", []) or []),
                           "ses": bool(self.veri.get("dusman_ses", True))},
                "telegram": telegram, "log": list(self._web_log)}

    def _web_png(self):
        """Panel görüntüsü (web thread'inden; bbox ana thread'de saklanır)."""
        if not self._son_bbox:
            return None
        try:
            from PIL import ImageGrab
            tampon = io.BytesIO()
            ImageGrab.grab(bbox=self._son_bbox).save(tampon, "PNG")
            return tampon.getvalue()
        except Exception:                              # noqa: BLE001
            return None

    def _web_komut(self, o):
        """Web'den gelen komut (ana thread'de _tazele_bir işler)."""
        komut = (o.get("komut") or "").lower()
        if komut == "baslat":
            self._hepsini_baslat()
        elif komut == "durdur":
            self._hepsini_durdur()
        elif komut == "baslat_hesap":
            self._baslat(int(o.get("idx", -1)))
        elif komut == "durdur_hesap":
            self._durdur(int(o.get("idx", -1)))
        elif komut == "dusman":
            self.dusman_var.set(o.get("metin", ""))
            if "ses" in o:
                self.dusman_ses_var.set(bool(o.get("ses")))
            self._dusman_kaydet()
        elif komut == "buff_cek":
            self._buff_cek(o.get("kanal"))
        elif komut == "mod":
            idx = int(o.get("idx", -1))
            if 0 <= idx < len(self._hesaplar()) and self.agac.exists(str(idx)):
                self.agac.selection_set(str(idx))
                m = (o.get("mod") or "sabit").lower()
                self.mod_var.set(m)
                if m == "tarama":
                    self.mod_tarama_var.set(str(o.get("tarama") or o.get("kanal") or "1-8"))
                else:
                    self.mod_kanal_var.set(str(o.get("kanal") or "1"))
                self._mod_kaydet()
        elif komut == "ayarlar":
            self.bakis_var.set(str(o.get("bakis", "")))
            self.vnum_var.set(str(o.get("vnumlar", "")))
            self.tum_var.set(bool(o.get("tum")))
            self.canlan_var.set(bool(o.get("canlan")))
            self.yeniden_var.set(bool(o.get("yeniden")))
            if o.get("yeniden_gecikme") is not None:
                self.yeniden_gecikme_var.set(str(o.get("yeniden_gecikme")))
            self.don_var.set(bool(o.get("don")))
            self._ayarlari_kaydet()
        elif komut == "buff":
            self.buff_acik_var.set(bool(o.get("acik")))
            self.buff_hedef_var.set(str(o.get("hedef", "")))
            self.buff_yardim_var.set(str(o.get("yardim", 0)))
            self.buff_guc_var.set(str(o.get("guc", 0)))
            self.buff_gecikme_var.set(str(o.get("gecikme", 5)))
            self.buff_menzil_var.set(str(o.get("menzil", 4)))
            self.buff_aralik_var.set(str(o.get("aralik", 8)))
            self._buff_kaydet()
        elif komut == "telegram":
            self.tg_acik_var.set(bool(o.get("acik")))
            self.tg_sohbet_var.set(str(o.get("sohbet", "")))
            gelen = o.get("olaylar") or {}
            for k, v in self.tg_olay_vars.items():
                if k in gelen:
                    v.set(bool(gelen[k]))
            self._tg_kaydet()
        self._log_yaz("%s  web: %s" % (time.strftime("%H:%M:%S"), komut or "?"))

    def _web_baslat(self):
        if self.http is not None:
            return
        parola = self._web_parola()
        port = self._web_port()
        acik = bool(self.veri.get("web_acik"))
        # Açıkken tüm arayüzlere (telefon aynı Wi-Fi'de erişsin), kapalıyken
        # yalnız bu bilgisayara bağlan.
        adres = "" if acik else "127.0.0.1"
        panel = self

        class Isleyici(http.server.BaseHTTPRequestHandler):
            def _yetki(self, q):
                # Panel kapalıyken sunucu yalnız 127.0.0.1'e bağlı; açıkken
                # (LAN/tünel) parola şart. Tünel de localhost'tan bağlandığı
                # için istemci adresine GÜVENME — sadece parolaya bak.
                if not acik:
                    return True
                return q.get("k", [""])[0] == parola

            def _yolla(self, kod, govde, tur="application/json; charset=utf-8"):
                if isinstance(govde, str):
                    govde = govde.encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", tur)
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                try:
                    self.wfile.write(govde)
                except OSError:
                    pass

            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(u.query)
                if u.path in ("/", "/index.html"):
                    self._yolla(200, WEB_HTML, "text/html; charset=utf-8")
                elif not self._yetki(q):
                    self._yolla(403, '{"hata":"parola"}')
                elif u.path in ("/api/durum", "/durum"):
                    self._yolla(200, json.dumps(panel._web_durum(), ensure_ascii=False))
                elif u.path == "/api/ekran":
                    png = panel._web_png()
                    if png:
                        self._yolla(200, png, "image/png")
                    else:
                        self._yolla(503, '{"hata":"goruntu"}')
                else:
                    self._yolla(404, '{"hata":"yok"}')

            def do_POST(self):
                u = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(u.query)
                if u.path != "/api/komut" or not self._yetki(q):
                    self._yolla(403, '{"hata":"parola"}')
                    return
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                    o = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
                except Exception:                      # noqa: BLE001
                    o = {}
                panel._web_kuyruk.put(o)
                self._yolla(200, '{"ok":true}')

            def log_message(self, *a):
                pass

        try:
            self.http = http.server.ThreadingHTTPServer((adres, port), Isleyici)
        except OSError as e:
            self.http_etiket.configure(text="web paneli açılamadı (port %d meşgul?)" % port, fg=UYARI)
            self._log_yaz("web paneli açılamadı: %s" % e, "HATA")
            return
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        if not acik:
            self.http_etiket.configure(text="durum: :%d (yalnız bu bilgisayar)" % port, fg=SOLUK)
            if getattr(self, "web_url_etiket", None) is not None:
                self.web_url_etiket.configure(text="")
            return
        try:
            ip = __import__("socket").gethostbyname(__import__("socket").gethostname())
        except Exception:                              # noqa: BLE001
            ip = "BİLGİSAYAR-IP"
        url = "http://%s:%d/?k=%s" % (ip, port, parola)
        self.http_etiket.configure(text="web: :%d açık — durum: telefonda" % port, fg=OK)
        if getattr(self, "web_url_etiket", None) is not None:
            self.web_url_etiket.configure(text=url)
        self._log_yaz("web paneli açık → aynı Wi-Fi'de:  %s" % url, "bilgi")

    def _web_durdur(self):
        if self.http is not None:
            threading.Thread(target=self.http.shutdown, daemon=True).start()
            self.http = None

    # ── uzaktan erişim tüneli (cloudflared) ──────────────────────
    def _cloudflared_bul(self):
        ozel = (self.veri.get("cloudflared_yolu") or "").strip()
        if ozel and os.path.exists(ozel):
            return ozel
        yol = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
        if yol:
            return yol
        import glob
        adaylar = [
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"
                               r"\Cloudflare.cloudflared_*\cloudflared.exe"),
            os.path.expandvars(r"%ProgramData%\chocolatey\bin\cloudflared.exe"),
            r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
            r"C:\Program Files\cloudflared\cloudflared.exe",
        ]
        for a in adaylar:
            for m in glob.glob(a):
                if os.path.exists(m):
                    return m
        return None

    def _tunel_ac_kapa(self):
        if self._tunel_proc is None:
            self._tunel_baslat()
        else:
            self._tunel_durdur()
            self._log_yaz("%s  tünel kapatıldı" % time.strftime("%H:%M:%S"))

    def _tunel_baslat(self):
        if self._tunel_proc is not None:
            return
        if not self.veri.get("web_acik"):
            self.tunel_etiket.configure(text="önce web panelini AÇ + Kaydet & başlat", fg=UYARI)
            return
        exe = self._cloudflared_bul()
        if not exe:
            self.tunel_etiket.configure(
                text="cloudflared bulunamadı — kur, ya da tam yolunu "
                     "metin_izleyici.json içinde \"cloudflared_yolu\"na yaz", fg=HATA)
            self._log_yaz("cloudflared bulunamadı", "HATA")
            return
        port = self._web_port()
        try:
            self._tunel_proc = subprocess.Popen(
                [exe, "tunnel", "--url", "http://127.0.0.1:%d" % port],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self.tunel_etiket.configure(text="tünel açılamadı: %s" % e, fg=HATA)
            self._tunel_proc = None
            return
        self._tunel_url = None
        self.tunel_url_var.set("")
        self.tunel_etiket.configure(text="tünel açılıyor… adres birkaç dakikaya kadar sürebilir",
                                    fg=UYARI)
        self.tunel_btn.configure(text="Tüneli kapat")
        threading.Thread(target=self._tunel_oku, args=(self._tunel_proc,), daemon=True).start()

    def _tunel_oku(self, proc):
        kalip = re.compile(r"https://[a-z0-9.-]+\.trycloudflare\.com")
        try:
            for satir in iter(proc.stdout.readline, ""):
                if proc is not self._tunel_proc:
                    break
                m = kalip.search(satir)
                if m and not self._tunel_url:
                    self._tunel_url = m.group(0)
                    self.after(0, self._tunel_url_bulundu)
        except Exception:                              # noqa: BLE001
            pass
        finally:
            try:
                proc.stdout.close()
            except Exception:                          # noqa: BLE001
                pass
        if proc is self._tunel_proc:                   # kendiliğinden kapandı
            self.after(0, self._tunel_bitti)

    def _tunel_url_bulundu(self):
        if not self._tunel_url:
            return
        tam = "%s/?k=%s" % (self._tunel_url, self._web_parola())
        self.tunel_url_var.set(tam)
        self.tunel_etiket.configure(text="tünel açık — bu adresi telefonda aç (parola dahil), "
                                    "ya da QR'ı okut", fg=OK)
        self._log_yaz("%s  tünel açık: %s" % (time.strftime("%H:%M:%S"), tam), "bilgi")

    def _tunel_bitti(self):
        self._tunel_proc = None
        if getattr(self, "tunel_btn", None) is None:
            return
        self.tunel_btn.configure(text="Tünel aç (uzaktan)")
        self.tunel_etiket.configure(
            text="tünel kapandı" if self._tunel_url else "tünel kapandı (adres alınamadı)",
            fg=SOLUK)
        self._tunel_url = None
        self.tunel_url_var.set("")

    def _tunel_durdur(self):
        proc = self._tunel_proc
        self._tunel_proc = None
        self._tunel_url = None
        if proc is not None:
            try:
                proc.terminate()
            except Exception:                          # noqa: BLE001
                pass
        if getattr(self, "tunel_btn", None) is not None:
            self.tunel_btn.configure(text="Tünel aç (uzaktan)")
            self.tunel_url_var.set("")
            self.tunel_etiket.configure(text="tünel kapalı", fg=SOLUK)

    def _tunel_kopyala(self):
        url = self.tunel_url_var.get().strip()
        if not url:
            self.tunel_etiket.configure(text="önce tüneli aç", fg=UYARI)
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.tunel_etiket.configure(text="adres panoya kopyalandı", fg=OK)

    def _tunel_qr(self):
        url = self.tunel_url_var.get().strip()
        if not url:
            self.tunel_etiket.configure(text="önce tüneli aç (QR için adres gerekir)", fg=UYARI)
            return
        try:
            import qrcode
            from PIL import ImageTk
        except Exception:                              # noqa: BLE001
            self.tunel_etiket.configure(text="QR için bir kez:  pip install \"qrcode[pil]\"",
                                        fg=UYARI)
            return
        q = qrcode.QRCode(box_size=6, border=2)
        q.add_data(url)
        q.make()
        img = q.make_image(fill_color="black", back_color="white").convert("RGB")
        pen = tk.Toplevel(self)
        pen.title("Telefonla okut")
        pen.configure(bg=KOYU)
        self._qr_img = ImageTk.PhotoImage(img)
        tk.Label(pen, image=self._qr_img, bg="white").pack(padx=12, pady=12)
        tk.Label(pen, text=url, bg=KOYU, fg=OK, font=SABIT, wraplength=300,
                 justify="center").pack(padx=12, pady=(0, 12))

    def _web_goster(self):
        """Ayardaki web panel değerlerini kutuya doldur."""
        self.web_acik_var.set(bool(self.veri.get("web_acik", False)))
        self.web_port_var.set(str(self._web_port()))
        self.web_parola_var.set(self._web_parola())

    def _web_kaydet(self):
        try:
            port = int((self.web_port_var.get() or "").strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            self.http_etiket.configure(text="geçersiz port", fg=HATA)
            return
        self.veri["web_acik"] = bool(self.web_acik_var.get())
        self.veri["web_portu"] = port
        self._veri_yaz()
        self._web_durdur()
        self._web_baslat()             # kapalıyken de localhost durum sunucusu döner
        self._log_yaz("%s  web paneli %s"
                      % (time.strftime("%H:%M:%S"),
                         "açıldı" if self.veri["web_acik"] else "kapatıldı"))

    # ── ayarlar ──────────────────────────────────────────────────
    def _ayarlari_goster(self):
        self.bakis_var.set(str(self.veri.get("tarama_bakis_sn",
                                             mi.VARSAYILAN["tarama_bakis_sn"])))
        self.vnum_var.set(",".join(str(v) for v in self.veri.get(
            "metin_vnumlari", mi.VARSAYILAN["metin_vnumlari"])))
        self.tum_var.set(bool(self.veri.get("tum_metinler", False)))
        self.canlan_var.set(bool(self.veri.get("olunce_canlan", False)))
        self.yeniden_var.set(bool(self.veri.get("olunce_yeniden_gir", False)))
        self.yeniden_gecikme_var.set(str(self.veri.get("yeniden_gir_gecikme_sn", 1.5)))
        self.don_var.set(bool(self.veri.get("yerine_don", False)))
        self.dusman_var.set(", ".join(self.veri.get("dusmanlar", []) or []))

    def _dusman_kumesi(self):
        """Kayıtlı düşman adları (karşılaştırma için sadeleştirilmiş küme)."""
        return {ad_fold(a) for a in (self.veri.get("dusmanlar") or []) if ad_fold(a)}

    def _dusman_kaydet(self):
        adlar = [a.strip() for a in self.dusman_var.get().replace(";", ",").split(",")
                 if a.strip()]
        self.veri["dusmanlar"] = adlar
        self.veri["dusman_ses"] = bool(self.dusman_ses_var.get())
        self._veri_yaz()
        self._onceki_dusman.clear()
        self._log_yaz("düşman listesi kaydedildi: %s" % (", ".join(adlar) or "(boş)"),
                      "HATA" if adlar else "bilgi")
        return True

    # ── buff'çı ──────────────────────────────────────────────────
    def _buff_goster(self):
        self.buff_acik_var.set(bool(self.veri.get("buff_acik", False)))
        self.buff_hedef_var.set(self.veri.get("buff_hedef", "") or "")
        self.buff_yardim_var.set(str(self.veri.get("buff_yardim_vnum", 0) or 0))
        self.buff_guc_var.set(str(self.veri.get("buff_guc_vnum", 0) or 0))
        self.buff_menzil_var.set(str(self.veri.get("buff_menzil_m", 4)))
        self.buff_aralik_var.set(str(self.veri.get("buff_aralik_sn", 8)))
        self.buff_gecikme_var.set(str(self.veri.get("buff_skill_gecikme_sn", 5)))

    def _buff_kaydet(self):
        try:
            yardim = int((self.buff_yardim_var.get() or "0").strip())
            guc = int((self.buff_guc_var.get() or "0").strip())
            menzil = float(self.buff_menzil_var.get().replace(",", "."))
            aralik = float(self.buff_aralik_var.get().replace(",", "."))
            gecikme = float(self.buff_gecikme_var.get().replace(",", "."))
            if yardim < 0 or guc < 0 or menzil <= 0 or aralik < 0 or gecikme < 0:
                raise ValueError
        except ValueError:
            self._log_yaz("HATA  buff: vnum'lar sayı, menzil > 0, aralık/gecikme ≥ 0 olmalı", "HATA")
            return False
        acik = bool(self.buff_acik_var.get())
        hedef = self.buff_hedef_var.get().strip()
        self.veri["buff_takip"] = bool(self.buff_takip_var.get())
        self.veri.update({"buff_acik": acik, "buff_hedef": hedef,
                          "buff_yardim_vnum": yardim, "buff_guc_vnum": guc,
                          "buff_menzil_m": menzil, "buff_aralik_sn": aralik,
                          "buff_skill_gecikme_sn": gecikme})
        self._veri_yaz()
        # Çalışan buff'çılara canlı uygula (yeniden başlatmaya gerek kalmasın).
        vnumlar = [v for v in (yardim, guc) if v > 0]
        for z in self.izleyiciler.values():
            if getattr(z, "rol", "") == "buff":
                z.buff_acik = acik
                z.buff_hedef = ad_fold(hedef)
                z.buff_vnumlar = list(vnumlar)
                z.buff_menzil = menzil * 100.0
                z.buff_aralik = aralik
                z.buff_skill_gecikme = gecikme
        if acik and not vnumlar:
            self._log_yaz("⚠ buff açık ama yetenek vnum'u yok — önce vnum gir "
                          "(tools/yetenek_kaydet.py)", "UYARI")
        elif acik:
            self._log_yaz("buff'çı ayarları kaydedildi (%s → vnum %s) ⚠ paket gönderir"
                          % (hedef or "?", ", ".join(map(str, vnumlar))), "UYARI")
        else:
            self._log_yaz("buff'çı ayarları kaydedildi (kapalı)")
        return True

    def _buff_calisanlar(self):
        return [(i, z) for i, z in self.izleyiciler.items()
                if getattr(z, "rol", "") == "buff" and z.is_alive()]

    def _buff_cek(self, kanal=None):
        """Çalışan buff'çı(lar)ı istenen kanala çeker. Döner: çekilen sayısı."""
        try:
            k = int(kanal if kanal is not None else self.buff_cek_var.get())
        except (TypeError, ValueError):
            self._log_yaz("HATA  geçersiz kanal", "HATA")
            return 0
        calisanlar = self._buff_calisanlar()
        if not calisanlar:
            self._log_yaz("çekilecek çalışan buff'çı yok (önce rolü Buff'çı yap + başlat)", "UYARI")
            return 0
        for _, z in calisanlar:
            z.kanala_cek(k)
        self._log_yaz("buff'çı ch%d kanalına çekiliyor" % k, "bilgi")
        return len(calisanlar)

    def _ayarlari_kaydet(self):
        try:
            bakis = float(self.bakis_var.get().replace(",", "."))
            if not 1 <= bakis <= 120:
                raise ValueError
        except ValueError:
            self._log_yaz("HATA  bakış süresi 1-120 sn arası bir sayı olmalı", "HATA")
            return False
        try:
            vnumlar = [int(x) for x in self.vnum_var.get().replace(" ", "").split(",") if x]
        except ValueError:
            self._log_yaz("HATA  vnum'lar virgülle ayrılmış sayılar olmalı", "HATA")
            return False
        try:
            yg = float(self.yeniden_gecikme_var.get().replace(",", "."))
            if yg < 0:
                raise ValueError
        except ValueError:
            self._log_yaz("HATA  tekrar girme süresi 0 veya daha büyük bir sayı olmalı", "HATA")
            return False
        self.veri["tarama_bakis_sn"] = bakis
        self.veri["metin_vnumlari"] = vnumlar
        self.veri["tum_metinler"] = bool(self.tum_var.get())
        self.veri["olunce_canlan"] = bool(self.canlan_var.get())
        self.veri["olunce_yeniden_gir"] = bool(self.yeniden_var.get())
        self.veri["yeniden_gir_gecikme_sn"] = yg
        self.veri["yerine_don"] = bool(self.don_var.get())
        self._veri_yaz()
        # Çalışan izleyici/buff'çılara CANLI uygula (yeniden başlatmaya gerek yok).
        canlan = bool(self.canlan_var.get())
        yeniden = bool(self.yeniden_var.get())
        don = bool(self.don_var.get())
        n = 0
        for z in self.izleyiciler.values():
            if z.is_alive():
                z.olunce_canlan = canlan
                z.olunce_yeniden_gir = yeniden
                z.yeniden_gir_gecikme = yg
                z.yerine_don = don
                n += 1
        self._log_yaz("ayarlar kaydedildi%s"
                      % (" — %d çalışan hesaba uygulandı" % n if n else ""))
        if canlan or don or yeniden:
            self._log_yaz("⚠ paket gönderen özellik açık (canlanma/yerine dön) — "
                          "oyuna paket gider", "UYARI")
        return True

    # ── telegram ─────────────────────────────────────────────────
    def _tg_goster(self):
        t = self.veri.get("telegram") or {}
        self.tg_acik_var.set(bool(t.get("acik")))
        self.tg_token_var.set(t.get("token", "") or "")
        self.tg_sohbet_var.set(str(t.get("sohbet", "") or ""))
        olaylar = dict(TG_VARSAYILAN, **(t.get("olaylar") or {}))
        for k, v in self.tg_olay_vars.items():
            v.set(bool(olaylar.get(k)))
        self._tg_hazirla()

    def _tg_ayar(self):
        return {"acik": bool(self.tg_acik_var.get()), "token": self.tg_token_var.get().strip(),
                "sohbet": self.tg_sohbet_var.get().strip(),
                "olaylar": {k: bool(v.get()) for k, v in self.tg_olay_vars.items()}}

    def _tg_durum(self, metin, renk=SOLUK):
        self.tg_etiket.configure(text=metin, fg=renk)

    def _tg_kaydet(self):
        t = self._tg_ayar()
        if t["acik"] or t["token"]:
            if not tb.token_gecerli_mi(t["token"]):
                self._tg_durum("Token biçimi hatalı — BotFather'ın verdiği 123456789:AA... "
                               "metnini olduğu gibi yapıştır", HATA)
                return False
            if not t["sohbet"]:
                self._tg_durum("Sohbet kimliği boş — botunu Telegram'da açıp Başlat'a bas, "
                               "sonra Bul", HATA)
                return False
        self.veri["telegram"] = t
        self._veri_yaz()
        self._tg_hazirla()
        self._tg_durum("kaydedildi — Telegram bildirimi %s" % ("AÇIK" if self.tg else "kapalı"), OK)
        return True

    def _tg_hazirla(self):
        if self.tg is not None:
            self.tg.durdur()
            self.tg = None
        if self.tg_kumanda is not None:
            self.tg_kumanda.durdur()
            self.tg_kumanda = None
        t = self.veri.get("telegram") or {}
        if t.get("acik") and t.get("token") and t.get("sohbet"):
            self.tg = tb.TelegramGonderici(t["token"], t["sohbet"], acici=self._tg_acici,
                                           gunluk=lambda s: self._tg_kuyruk.put(("log", s)))
            # Telegram'dan durdur/başlat/durum: yalnızca kayıtlı sohbetten.
            self.tg_kumanda = tb.TelegramKumanda(
                t["token"], t["sohbet"],
                lambda metin, sohbet: self._tg_kuyruk.put(("komut", metin)),
                acici=self._tg_acici, gunluk=lambda s: self._tg_kuyruk.put(("log", s)))
            self.tg_kumanda.start()

    def _tg_yanit(self, metin):
        """Komut cevabı / özet gönder (aynı metin tekrarı engellenmez)."""
        if self.tg is not None:
            self.tg.gonder(metin, tekrar_sn=0)

    def _kanal_ozet_metni(self):
        """Bütün izlenen kanalların o anki durumu (tek metin blok)."""
        kanallar = mi.durum_ozeti(list(self._canli))["kanallar"]
        if not kanallar:
            return "izlenen kanal yok"
        dusman_kume = self._dusman_kumesi()
        satirlar = []
        for k in sorted(kanallar, key=int):
            o = kanallar[k]
            metinler = o.get("metinler") or []
            tarama = o.get("tarama") is True
            izleniyor = o.get("simdi_burada") if tarama else o.get("oyunda")
            if metinler:
                isaret = "⚔️" if any(m.get("kesiliyor") for m in metinler) else "🟢"
                parcalar = []
                for m in metinler[:3]:
                    p = m.get("ad", "?")
                    if m.get("mesafe_m") is not None:
                        p += " %.0f m" % m["mesafe_m"]
                    if m.get("kesiliyor") and m.get("vuran"):
                        p += " ⚔️%s" % m["vuran"]
                    elif m.get("oyuncu"):
                        p += " 👤%s" % m["oyuncu"]
                    parcalar.append(p)
                ic = ", ".join(parcalar)
                if any(m.get("oyuncu") or m.get("vuran") for m in metinler):
                    isaret += "👤"
            elif not tarama and not izleniyor:
                isaret, ic = "·", (o.get("durum") or "izlenmiyor")[:30]
            elif tarama and o.get("son_bakis") is None:
                isaret, ic = "·", "henüz bakılmadı"
            else:
                isaret, ic = "⚫", "yok"
            zaman = ""
            if tarama and o.get("yas_sn") is not None:
                zaman = "  (%s)" % gecen(o["yas_sn"])
            satirlar.append("ch%s %s %s%s" % (k, isaret, ic, zaman))
            # HARİTADAKİ OYUNCULAR — metnin yanındakinden ayrı, tam liste.
            oyuncular = o.get("oyuncular") or []
            if izleniyor and oyuncular:
                satirlar.append("     👥 %s" % ", ".join(
                    oyuncu_etiket(oy, dusman_kume) for oy in oyuncular[:6]))
        return "\n".join(satirlar)

    def _oyuncu_ozet_metni(self):
        """Her izlenen kanalda haritadaki oyuncular (Telegram /oyuncular için)."""
        kanallar = mi.durum_ozeti(list(self._canli))["kanallar"]
        satirlar = []
        for k in sorted(kanallar, key=int):
            o = kanallar[k]
            tarama = o.get("tarama") is True
            izleniyor = o.get("simdi_burada") if tarama else o.get("oyunda")
            if not izleniyor:
                continue
            oyuncular = o.get("oyuncular") or []
            if oyuncular:
                satirlar.append("ch%s: %s" % (k, ", ".join(
                    oyuncu_etiket(oy) for oy in oyuncular[:10])))
            else:
                satirlar.append("ch%s: — yok" % k)
        return "\n".join(satirlar) or "izlenen kanal yok"

    def _komut_isle(self, metin):
        """Telegram'dan gelen /komut. Yalnızca kayıtlı sohbetten geldi (dinleyici süzdü)."""
        komut = metin.split()[0].lstrip("/").split("@")[0].lower()
        if komut in ("durum", "status"):
            self._tg_yanit("📋 Kanallar (%s)\n%s" % (time.strftime("%H:%M:%S"),
                                                     self._kanal_ozet_metni()))
        elif komut in ("oyuncular", "players", "kim"):
            self._tg_yanit("👥 Haritadaki oyuncular (%s)\n%s" % (time.strftime("%H:%M:%S"),
                                                                self._oyuncu_ozet_metni()))
        elif komut in ("ekran", "screenshot", "ss"):
            self._ekran_gonder()
        elif komut in ("durdur", "stop", "dur"):
            self._hepsini_durdur()
            self._log_yaz("%s  Telegram: durdur komutu" % time.strftime("%H:%M:%S"), "UYARI")
            self._tg_yanit("⏹ İzleyici durduruldu (Telegram komutu).")
        elif komut in ("baslat", "start", "basla"):
            n = self._hepsini_baslat()
            self._log_yaz("%s  Telegram: başlat komutu (%d hesap)" % (time.strftime("%H:%M:%S"), len(n)),
                          "UYARI")
            self._tg_yanit("▶️ İzleyici başlatılıyor — %d hesap." % len(n)
                           if n else "▶️ Başlatılacak (durmuş) hesap yok.")
        else:
            self._tg_yanit("Komutlar: /durum  /oyuncular  /ekran  /durdur  /baslat")

    def _panel_png(self):
        """Panel penceresinin o anki görüntüsü (PNG baytları) ya da None."""
        try:
            from PIL import ImageGrab
        except Exception:                              # noqa: BLE001
            return None
        try:
            self.update_idletasks()
            x, y = self.winfo_rootx(), self.winfo_rooty()
            g, h = self.winfo_width(), self.winfo_height()
            resim = ImageGrab.grab(bbox=(x, y, x + g, y + h))
            import io
            tampon = io.BytesIO()
            resim.save(tampon, "PNG")
            return tampon.getvalue()
        except Exception:                              # noqa: BLE001
            return None

    def _ekran_gonder(self):
        """/ekran: panel görüntüsünü Telegram'a fotoğraf olarak yollar."""
        if self.tg is None:
            return
        png = self._panel_png()                        # pencere ana iş parçacığında
        t = self.veri.get("telegram") or {}
        token, sohbet = t.get("token"), t.get("sohbet")
        if not png:
            self._tg_yanit("ekran görüntüsü alınamadı (Pillow kurulu mu, pencere açık mı?)")
            return
        acici = self._tg_acici

        def is_():
            try:
                tb.foto_gonder(token, sohbet, png, "📷 Metin İzleyici — %s"
                               % time.strftime("%H:%M:%S"), acici=acici)
            except tb.TelegramHatasi as e:
                self._tg_kuyruk.put(("log", "Telegram ekran: %s" % e))

        threading.Thread(target=is_, daemon=True).start()

    def _tg_bul(self):
        token = self.tg_token_var.get().strip()
        if not tb.token_gecerli_mi(token):
            self._tg_durum("Önce BotFather'ın verdiği token'ı yapıştır", HATA)
            return
        self._tg_durum("sohbet aranıyor…")
        acici = self._tg_acici

        def is_():
            try:
                kimlik, ad = tb.sohbet_bul(token, acici=acici)
                self._tg_kuyruk.put(("sohbet", kimlik, ad))
            except tb.TelegramHatasi as e:
                self._tg_kuyruk.put(("durum", str(e), HATA))

        threading.Thread(target=is_, daemon=True).start()

    def _tg_test(self):
        t = self._tg_ayar()
        if not tb.token_gecerli_mi(t["token"]) or not t["sohbet"]:
            self._tg_durum("Token ve sohbet kimliği gerekli (sohbet için Bul'a bas)", HATA)
            return
        self._tg_durum("test mesajı gönderiliyor…")
        acici = self._tg_acici

        def is_():
            try:
                tb.mesaj_gonder(t["token"], t["sohbet"],
                                "✅ Metin İzleyici bağlandı — bildirimler bu sohbete gelecek.",
                                acici=acici)
                self._tg_kuyruk.put(("durum", "test mesajı gönderildi — Telegram'a bak", OK))
            except tb.TelegramHatasi as e:
                self._tg_kuyruk.put(("durum", str(e), HATA))

        threading.Thread(target=is_, daemon=True).start()

    def _bildirim(self, tur, metin, tekrar_sn=60):
        """Olay türü Telegram ayarında açıksa gönderir."""
        if self.tg is None:
            return False
        olaylar = dict(TG_VARSAYILAN, **((self.veri.get("telegram") or {}).get("olaylar") or {}))
        if not olaylar.get(tur):
            return False
        return self.tg.gonder(metin, tekrar_sn=tekrar_sn)

    # ── canlı tazeleme ───────────────────────────────────────────
    def _ses(self):
        bildirim_sesi()

    def _tazele(self):
        if self._kapaniyor:
            return
        try:
            self._tazele_bir()
        finally:
            if not self._kapaniyor:
                self.after(self._tazele_ms, self._tazele)

    def _tb_kanal_dongu(self):
        """ARKA PLAN: tam botun kanalını APK durumundan sürekli oku.

        Kanal, /api/durum -> proxy.port'tan tambot.port_kanali() ile çözülür;
        proxy.kanal eski port düzenini varsaydığı için artık hep 0 geliyor."""
        try:
            import importlib.util as _iu
            _sp = _iu.spec_from_file_location(
                "tambot", os.path.join(KOK, "tambot.py"))
            _tb = _iu.module_from_spec(_sp)
            _sp.loader.exec_module(_tb)
            self._tb_api = _tb.Api()
        except Exception as e:                      # noqa: BLE001
            self._tb_kanal["hata"] = "tambot yüklenemedi: %s" % type(e).__name__
            return
        while not self._kapaniyor:
            try:
                d = self._tb_api.get("/api/durum")
                if isinstance(d, dict):
                    proxy = d.get("proxy") or {}
                    try:
                        k = int(proxy.get("kanal", 0) or 0)
                    except (TypeError, ValueError):
                        k = 0
                    if not k:
                        try:
                            port = int(proxy.get("port", 0) or 0)
                        except (TypeError, ValueError):
                            port = 0
                        k = _tb.port_kanali(port) if port else 0
                    self._tb_kanal["hata"] = ""
                    if k:
                        self._tb_kanal["simdi"] = k
                else:
                    self._tb_kanal["hata"] = "APK'ye ulaşılamıyor"
            except Exception as e:                  # noqa: BLE001
                self._tb_kanal["hata"] = type(e).__name__
            time.sleep(1.0)

    def _buff_takip_isle(self):
        """ANA THREAD: tam bot kanal değiştiyse buff'çıyı oraya çek."""
        try:
            acik = bool(self.buff_takip_var.get())
        except Exception:                           # noqa: BLE001
            return
        if not acik:
            return
        if self._tb_iplik is None or not self._tb_iplik.is_alive():
            self._tb_iplik = threading.Thread(target=self._tb_kanal_dongu,
                                              daemon=True)
            self._tb_iplik.start()
        k = self._tb_kanal.get("simdi", 0)
        if not k or k == self._tb_kanal.get("cekilen", 0):
            return
        if not self._buff_calisanlar():
            return                                  # çalışan buff'çı yok
        self._tb_kanal["cekilen"] = k
        self._log_yaz("tam bot ch%d'e geçti — buff'çı takip ediyor" % k, "bilgi")
        self._buff_cek(k)

    def _tazele_bir(self):
        self._buff_takip_isle()
        # Ekran görüntüsü için pencere konumunu ANA thread'de sakla (web thread okur).
        try:
            if self.winfo_viewable():
                self._son_bbox = (self.winfo_rootx(), self.winfo_rooty(),
                                  self.winfo_rootx() + self.winfo_width(),
                                  self.winfo_rooty() + self.winfo_height())
        except Exception:                              # noqa: BLE001
            pass
        # Web panelinden gelen komutlar (ana thread'de işle — tkinter güvenli).
        while True:
            try:
                o = self._web_kuyruk.get_nowait()
            except queue.Empty:
                break
            try:
                self._web_komut(o)
            except Exception as e:                     # noqa: BLE001
                self._log_yaz("web komut hatası: %s" % e, "HATA")
        while True:
            try:
                is_ = self._tg_kuyruk.get_nowait()
            except queue.Empty:
                break
            if is_[0] == "sohbet":
                self.tg_sohbet_var.set(is_[1])
                self._tg_durum("sohbet bulundu: %s — şimdi Kaydet" % (is_[2] or is_[1]), OK)
            elif is_[0] == "durum":
                self._tg_durum(is_[1], is_[2])
            elif is_[0] == "log":
                self._log_yaz("%s  %s" % (time.strftime("%H:%M:%S"), is_[1]), "UYARI")
            elif is_[0] == "komut":
                self._komut_isle(is_[1])
        while True:
            try:
                saat, kanal, seviye, metin = self.kuyruk.get_nowait()
            except queue.Empty:
                break
            # Metin var / kesiliyor / (taramada) metin kalmadı kanal kutusundaki
            # DURUM DEĞİŞİMİNDEN gönderilir; burada yalnızca izleyicinin kendi
            # olayları: kesildi, yanında oyuncu, hata.
            if seviye == "kesildi":
                self._bildirim("kesildi", "💥 ch%d KESİLDİ — %s" % (kanal, metin))
            elif seviye == "yaninda":
                self._bildirim("yaninda", "👤 ch%d oyuncu metnin yanında — %s" % (kanal, metin))
            elif seviye in ("hata", "uyari"):
                self._bildirim("hata", "⚠️ ch%d %s" % (kanal, metin), tekrar_sn=600)
            if seviye in GIZLI_SEVIYELER:
                continue
            etiket = mi.ETIKETLER.get(seviye, seviye)
            self._log_yaz("%s  ch%d  %-6s %s" % (saat, kanal, etiket, metin),
                          etiket if etiket in RENKLI_ETIKETLER else "bilgi")
        for z in list(self._canli):
            if not z.is_alive():
                self._canli.remove(z)
        self._agac_tazele()
        self._kanallari_ciz()

    def _agac_tazele(self):
        for i in range(len(self._hesaplar())):
            iid = str(i)
            if self.agac.exists(iid):
                self.agac.set(iid, "durum", self._durum(i))

    def _ayrinti_yaz(self, w, satirlar):
        """Kanal kartının renkli detay kutusunu yazar: [(metin, etiket), ...]."""
        try:
            w.configure(state="normal")
            w.delete("1.0", "end")
            for n, (metin, etk) in enumerate(satirlar):
                w.insert("end", ("\n" if n else "") + metin, etk)
            w.configure(state="disabled")
        except tk.TclError:
            pass

    def _kanallari_ciz(self):
        kanallar = mi.durum_ozeti(list(self._canli))["kanallar"]
        metin_kanallari = []            # metin GÖRÜLEN kanallar (üst özet)
        for k, (hucre, durum, ayrinti) in self.kanal_hucreleri.items():
            o = kanallar.get(str(k))
            if o is None:
                durum.configure(text="izlenmiyor", fg=SOLUK)
                self._ayrinti_yaz(ayrinti, [])
                hucre.configure(highlightbackground=CIZGI)
                self.kanal_basliklari[k].configure(fg=METIN)
                self._onceki_var.pop(k, None)
                self._onceki_kes.pop(k, None)
                self._onceki_dusman.pop(k, None)
                continue
            metinler = o.get("metinler") or []
            kenar = CIZGI
            bakildi = False
            dusman_kume = self._dusman_kumesi()
            if o.get("tarama") is True:
                bakildi = o.get("son_bakis") is not None
                if not bakildi:
                    durum.configure(text="? henüz bakılmadı", fg=SOLUK)
                if o.get("simdi_burada"):
                    kenar = VURGU
            else:
                bakildi = bool(o.get("oyunda"))
                if bakildi:
                    kenar = VURGU
                else:
                    durum.configure(text=(o.get("durum") or "")[:34], fg=UYARI)
            oyuncular = o.get("oyuncular") or [] if bakildi else []
            var = bakildi and bool(metinler)
            kesilen = [m for m in metinler if m.get("kesiliyor")] if bakildi else []
            oyunculu = bool(var and any(m.get("oyuncu") for m in metinler))
            if bakildi:
                if kesilen:
                    durum.configure(text="⚔ kesiliyor 👤", fg=UYARI)
                    kenar = UYARI
                elif var:
                    durum.configure(text="● %d metin%s" % (len(metinler), "  👤 oyuncu var"
                                    if oyunculu else ""), fg=UYARI if oyunculu else OK)
                    kenar = UYARI if oyunculu else OK
                else:
                    durum.configure(text="○ yok", fg=METIN)
            dusmanlar = [oy for oy in oyuncular if ad_fold(oy.get("ad")) in dusman_kume]
            if dusmanlar:                          # DÜŞMAN: kanalı kırmızıya boya
                kenar = HATA
                durum.configure(text="🔴 DÜŞMAN: %s" % ", ".join(
                    oy.get("ad", "?") for oy in dusmanlar[:3]), fg=HATA)
            if o.get("buff") and kenar == CIZGI:
                kenar = VURGU
            if o.get("buff") and not (metinler or oyuncular or dusmanlar):
                durum.configure(text="🛡 buff'çı burada", fg=VURGU)
            if o.get("oldu"):                      # bu kanaldaki hesap öldü
                kenar = HATA
                durum.configure(text="💀 ÖLDÜ%s" % (" → canlanıyor" if o.get("canlan_acik")
                                                    else " (canlanma KAPALI)"), fg=HATA)
            # — RENKLİ DETAY (web'deki gibi), üstten alta —
            satirlar = []
            if o.get("donuyor") and not o.get("oldu"):
                satirlar.append(("↩ yerine dönüyor (%.0f m)" % o["sapma_m"], "sari"))
            if o.get("buff"):
                satirlar.append(("🛡 buff'çı burada", "buff"))
            if oyuncular:
                satirlar.append(("👥 %s" % ", ".join(oyuncu_etiket(oy, dusman_kume)
                                                     for oy in oyuncular[:5]),
                                 "dusman" if dusmanlar else "oyuncu"))
            if var:
                for m in metinler[:3]:
                    satirlar.append((metin_satiri(m), "metin"))
            if o.get("tarama") is True and o.get("simdi_burada"):
                satirlar.append(("▶ şimdi burada", "buff"))
            elif not o.get("tarama") and bakildi:
                satirlar.append(("sürekli izleniyor", "soluk"))
            if o.get("tarama") is True and o.get("son_bakis"):
                satirlar.append(("son bakış %s  %s" % (o["son_bakis"], gecen(o.get("yas_sn"))),
                                 "soluk"))
            self._ayrinti_yaz(ayrinti, satirlar)
            hucre.configure(highlightbackground=kenar)
            # Başlık (ch4) YALNIZCA metin varsa yeşil; yoksa normal beyaz.
            self.kanal_basliklari[k].configure(fg=OK if var else METIN)
            if var:
                metin_kanallari.append(k)
            # DÜŞMAN uyarısı: yeni görülen düşman için ses + günlük + Telegram.
            simdiki_dusman = {oy.get("ad") for oy in dusmanlar}
            yeni_dusman = simdiki_dusman - self._onceki_dusman.get(k, set())
            if yeni_dusman:
                ad_liste = ", ".join(oyuncu_etiket(oy) for oy in dusmanlar
                                     if oy.get("ad") in yeni_dusman)
                self._log_yaz("%s  ch%d  🔴 DÜŞMAN GÖRÜLDÜ: %s" % (
                    time.strftime("%H:%M:%S"), k, ad_liste), "HATA")
                self._bildirim("dusman", "🔴 ch%d DÜŞMAN: %s" % (k, ad_liste), tekrar_sn=30)
                if self.dusman_ses_var.get():      # metin sesinden AYRI kapatılabilir
                    self._ses()
            if bakildi:
                self._onceki_dusman[k] = simdiki_dusman
            else:
                self._onceki_dusman.pop(k, None)
            if kesilen and not self._onceki_kes.get(k):
                m = kesilen[0]
                self._log_yaz("%s  ch%d  METİN KESİLİYOR: %s%s" % (
                    time.strftime("%H:%M:%S"), k, m.get("ad", "?"),
                    ("  — vuran: %s" % m["vuran"]) if m.get("vuran") else ""), "KESİLİYOR")
                self._bildirim("kesiliyor", "⚔️ ch%d KESİLİYOR — %s%s" % (
                    k, m.get("ad", "?"),
                    ("  vuran: %s%s" % (m["vuran"], " (%.0f m)" % m["vuran_mesafe_m"]
                                        if m.get("vuran_mesafe_m") is not None else ""))
                    if m.get("vuran") else ""))
                if self.ses_var.get():
                    self._ses()
            if bakildi:
                self._onceki_kes[k] = bool(kesilen)
            onceki = self._onceki_var.get(k)
            if var and not onceki:
                # Kırıldıktan sonra yeniden doğma süresi (kanalda sürekli bakan
                # hesap için ~1 sn hassas). son_kirilma yoksa (girişte hazır
                # bulunan metin) süre gösterilmez.
                son_k = o.get("son_kirilma")
                dogma = "  ⏱ %.1f dk sonra" % ((time.time() - son_k) / 60.0) if son_k else ""
                self._log_yaz("%s  ch%d  METİN ÇIKTI%s: %s" % (
                    time.strftime("%H:%M:%S"), k, dogma,
                    ", ".join(m.get("ad", "?") for m in metinler)), "VAR")
                oyuncular = o.get("oyuncular") or []
                oyuncu_ek = ("\n👥 %s" % ", ".join(oyuncu_etiket(oy) for oy in oyuncular[:6])
                             ) if oyuncular else ""
                self._bildirim("metin_var", "🟢 ch%d METİN ÇIKTI%s — %s%s" % (k, dogma, ", ".join(
                    "%s%s%s" % (m.get("ad", "?"), " (%.0f m)" % m["mesafe_m"]
                                if m.get("mesafe_m") is not None else "",
                                "  👤%s" % m["oyuncu"] if m.get("oyuncu") else "")
                    for m in metinler[:4]), oyuncu_ek))
                if self.ses_var.get():
                    self._ses()
            elif onceki and bakildi and not var:
                self._log_yaz("%s  ch%d  metin kalmadı" % (time.strftime("%H:%M:%S"), k),
                              "GİTTİ")
                if o.get("tarama") is True:
                    # Sabit kanalda izleyici KESİLDİ olayını zaten yollar.
                    self._bildirim("kesildi", "⚫ ch%d metin kalmadı (iki bakış arasında kesilmiş)" % k)
            if bakildi:
                self._onceki_var[k] = var
            # HER ZİYARET: taramada son bakış saati değişince o kanalın güncel durumu
            if o.get("tarama") is True and o.get("son_bakis") \
                    and self._onceki_bakis.get(k) != o["son_bakis"]:
                self._onceki_bakis[k] = o["son_bakis"]
                if metinler:
                    ic = ", ".join("%s%s" % (m.get("ad", "?"), " %.0f m" % m["mesafe_m"]
                                   if m.get("mesafe_m") is not None else "") for m in metinler[:3])
                    if any(m.get("kesiliyor") for m in metinler):
                        ic = "⚔️ " + ic
                else:
                    ic = "yok"
                self._bildirim("her_ziyaret", "🔎 ch%d — %s" % (k, ic), tekrar_sn=0)
        # Üst özet: metin GÖRÜLEN kanallar (kullanıcı buradan bakacak).
        if metin_kanallari:
            self.metin_ozet.configure(
                text="🟢 METİN VAR: " + ", ".join("ch%d" % k for k in metin_kanallari),
                fg=OK)
        else:
            self.metin_ozet.configure(text="metin olan kanal yok", fg=SOLUK)
        self._tur_kontrol()

    def _tur_kontrol(self):
        """Bir tarama turu bitince (ch listesi başa sarınca) bütün kanalların özetini yolla."""
        canli_id = set()
        for z in list(self._canli):
            if len(getattr(z, "tarama", []) or []) <= 1:
                continue
            canli_id.add(id(z))
            tur = getattr(z, "tur_sayisi", 0)
            onceki = self._onceki_tur.get(id(z))
            self._onceki_tur[id(z)] = tur
            if onceki is not None and tur > onceki:
                self._bildirim("tur_ozeti", "📋 Tur %d bitti (%s)\n%s" % (
                    tur, time.strftime("%H:%M:%S"), self._kanal_ozet_metni()), tekrar_sn=0)
        for anahtar in [a for a in self._onceki_tur if a not in canli_id]:
            self._onceki_tur.pop(anahtar, None)

    def _kanal_izleyici(self, k):
        """O an k kanalında canlı izleyici (tarama başka kanaldaysa None)."""
        for z in self._canli:
            if z.is_alive() and z.kanal == k and getattr(z, "harita_verisi", None):
                return z
        return None

    def _harita_ac(self, k):
        if self.harita_pencere is not None and self.harita_pencere.winfo_exists():
            self.harita_pencere.kanal_sec(k)
            self.harita_pencere.lift()
        else:
            self.harita_pencere = HaritaPenceresi(self, k)

    def _kapat(self):
        self._kapaniyor = True
        self._hepsini_durdur()
        if self.tg is not None:
            self.tg.durdur()
        if self.tg_kumanda is not None:
            self.tg_kumanda.durdur()
        if self.http is not None:
            threading.Thread(target=self.http.shutdown, daemon=True).start()
        self._tunel_durdur()
        self.destroy()


class HesapPenceresi(tk.Toplevel):
    """Hesap ekle / düzenle."""

    def __init__(self, panel, idx=None):
        super().__init__(panel)
        self.panel = panel
        self.idx = idx
        h = panel._hesaplar()[idx] if idx is not None else {}
        self.title("Hesabı düzenle" if idx is not None else "Hesap ekle")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(panel)

        self.kullanici = tk.StringVar(value=h.get("kullanici", ""))
        self.sifre = tk.StringVar(value=h.get("sifre", ""))
        self.pin = tk.StringVar(value=str(h.get("pin", "") or ""))
        self.yuva = tk.StringVar(value=str(h.get("karakter_yuvasi", 0) or 0))
        self.mod = tk.StringVar(value="tarama" if h.get("tarama") else "sabit")
        self.kanal = tk.StringVar(value=str(h.get("kanal", 1) or 1))
        self.tarama = tk.StringVar(value=mod_metni(h)[len("tarama "):]
                                   if h.get("tarama") else "1-8")

        g = tk.Frame(self, bg=PANEL)
        g.pack(padx=14, pady=12)

        def giris(var, gizli=False):
            return tk.Entry(g, textvariable=var, show="•" if gizli else "", bg=KOYU,
                            fg=METIN, insertbackground=METIN, relief="flat", width=22,
                            font=SABIT)

        def sayi(var, en_az, en_cok):
            return tk.Spinbox(g, from_=en_az, to=en_cok, textvariable=var, width=5,
                              bg=KOYU, fg=METIN, buttonbackground=CIZGI, relief="flat",
                              font=SABIT)

        def radyo(metin, deger):
            return tk.Radiobutton(g, text=metin, variable=self.mod, value=deger, bg=PANEL,
                                  fg=METIN, selectcolor=KOYU, activebackground=PANEL,
                                  activeforeground=METIN, font=YAZI)

        for r, (etiket, w) in enumerate((("Kullanıcı adı", giris(self.kullanici)),
                                         ("Şifre", giris(self.sifre, True)),
                                         ("PIN", giris(self.pin, True)),
                                         ("Karakter yuvası (0 = ilk)", sayi(self.yuva, 0, 3)))):
            tk.Label(g, text=etiket, bg=PANEL, fg=SOLUK, font=YAZI).grid(
                row=r, column=0, sticky="w", pady=3, padx=(0, 10))
            w.grid(row=r, column=1, sticky="ew" if r < 3 else "w", pady=3)
        radyo("Tek kanalda bekle", "sabit").grid(row=4, column=0, sticky="w", pady=(8, 0))
        sayi(self.kanal, 1, 8).grid(row=4, column=1, sticky="w", pady=(8, 0))
        radyo("Kanalları tara", "tarama").grid(row=5, column=0, sticky="w")
        giris(self.tarama).grid(row=5, column=1, sticky="ew")
        tk.Label(g, text="ör. 1-8  ya da  1,3,5", bg=PANEL, fg=SOLUK,
                 font=("Segoe UI", 8)).grid(row=6, column=1, sticky="w")
        tk.Label(g, text="Karakteri önce oyunda metin alanının ortasına bırakıp\n"
                         "oyundan çık; izleyici o noktadan bakar.",
                 bg=PANEL, fg=SOLUK, font=("Segoe UI", 8), justify="left").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.hata = tk.Label(g, text="", bg=PANEL, fg=HATA, font=YAZI, wraplength=300,
                             justify="left")
        self.hata.grid(row=8, column=0, columnspan=2, sticky="w")
        b = tk.Frame(g, bg=PANEL)
        b.grid(row=9, column=0, columnspan=2, sticky="e", pady=(8, 0))
        panel._btn(b, "İptal", self.destroy).pack(side="right", padx=(6, 0))
        panel._btn(b, "Kaydet", self._kaydet, VURGU).pack(side="right")

    def hesap(self):
        """Pencere alanlarından hesap sözlüğü. Kanal listesi hatalıysa ValueError."""
        h = dict(self.panel._hesaplar()[self.idx]) if self.idx is not None else {}
        h.update({"kullanici": self.kullanici.get().strip(), "sifre": self.sifre.get(),
                  "pin": self.pin.get().strip()})
        try:
            h["karakter_yuvasi"] = int(self.yuva.get())
        except ValueError:
            h["karakter_yuvasi"] = 0
        if self.mod.get() == "tarama":
            h["tarama"] = mi.tarama_coz(self.tarama.get())
            h["kanal"] = h["tarama"][0]
        else:
            h.pop("tarama", None)
            h["kanal"] = int(self.kanal.get())
        return h

    def _kaydet(self):
        try:
            h = self.hesap()
        except ValueError as e:
            self.hata.configure(text="Kanal hatalı: %s" % e)
            return
        hatalar = self.panel._hesap_kaydet(self.idx, h)
        if hatalar:
            self.hata.configure(text="\n".join(hatalar))
            return
        self.destroy()


class HaritaPenceresi(tk.Toplevel):
    """Bir kanalın etrafını gösteren radar: karakter merkez, canlı yenilenir."""

    BOYUT = 480

    def __init__(self, panel, k):
        super().__init__(panel)
        self.panel = panel
        self.kanal = k
        self.configure(bg=KOYU)
        self.resizable(False, False)
        self.orta = self.BOYUT // 2
        self.olcek = (self.orta - 12) / float(HARITA_YARICAP_HAM)
        ust = tk.Frame(self, bg=KOYU)
        ust.pack(fill="x", padx=8, pady=(8, 2))
        self.baslik = tk.Label(ust, text="", bg=KOYU, fg=METIN, font=KALIN)
        self.baslik.pack(side="left")
        efs = tk.Frame(self, bg=KOYU)
        efs.pack(anchor="w", padx=8)
        for metin, renk in (("● metin", RENK_METIN), ("● oyuncu", RENK_OYUNCU),
                            ("● canavar", RENK_CANAVAR), ("● sen", RENK_BEN),
                            ("halka: 4 / 20 / 40 m", SOLUK)):
            tk.Label(efs, text=metin, bg=KOYU, fg=renk, font=("Segoe UI", 8)).pack(
                side="left", padx=(0, 8))
        self.tuval = tk.Canvas(self, width=self.BOYUT, height=self.BOYUT, bg="#0b0d13",
                               highlightthickness=1, highlightbackground=CIZGI)
        self.tuval.pack(padx=8, pady=6)
        self.bilgi = tk.Label(self, text="", bg=KOYU, fg=SOLUK, font=("Segoe UI", 8),
                              anchor="w", justify="left")
        self.bilgi.pack(fill="x", padx=8, pady=(0, 8))
        self.kanal_sec(k)
        self._ciz()

    def kanal_sec(self, k):
        self.kanal = k
        self.title("ch%d haritası" % k)

    def _daire(self, x, y, r, **kw):
        self.tuval.create_oval(x - r, y - r, x + r, y + r, **kw)

    def _ciz(self):
        if self._kapali():
            return
        t = self.tuval
        t.delete("all")
        o = self.orta
        z = self.panel._kanal_izleyici(self.kanal)
        veri = z.harita_verisi() if z is not None else None
        self.baslik.configure(text="ch%d" % self.kanal)
        # menzil halkaları
        for m_metre, renk in ((4, "#3a2020"), (20, "#20303a"), (40, "#1b2430")):
            r = m_metre * 100 * self.olcek
            self._daire(o, o, r, outline=renk)
        if veri is None or not veri.get("konum"):
            t.create_text(o, o, text="şu an bu kanalda izleyici yok\n(tarama başka kanalda ya da durmuş)",
                          fill=SOLUK, font=("Segoe UI", 9), justify="center")
            self.bilgi.configure(text="")
        else:
            konum = veri["konum"]
            for c in veri["canavarlar"]:
                px, py = harita_px(konum, c["x"], c["y"], o, self.olcek)
                self._daire(px, py, 2, fill=RENK_CANAVAR, outline="")
            for n in veri["npcler"]:
                px, py = harita_px(konum, n["x"], n["y"], o, self.olcek)
                self._daire(px, py, 2, fill=RENK_NPC, outline="")
            for oy in veri["oyuncular"]:
                px, py = harita_px(konum, oy["x"], oy["y"], o, self.olcek)
                self._daire(px, py, 4, fill=RENK_OYUNCU, outline="#ffffff")
                if oy.get("ad"):
                    t.create_text(px + 6, py, text=oy["ad"], fill=RENK_OYUNCU,
                                  font=("Segoe UI", 7), anchor="w")
            for m in veri["metinler"]:
                px, py = harita_px(konum, m["x"], m["y"], o, self.olcek)
                kenar = UYARI if m.get("kesiliyor") else "#ffffff"
                t.create_rectangle(px - 5, py - 5, px + 5, py + 5, fill=RENK_METIN, outline=kenar,
                                   width=2 if m.get("kesiliyor") else 1)
                etiket = m.get("ad", "metin")
                if m.get("mesafe_m") is not None:
                    etiket += "  %.0f m" % m["mesafe_m"]
                if m.get("kesiliyor"):
                    etiket += "  ⚔"
                elif m.get("oyuncu"):
                    etiket += "  👤"
                t.create_text(px + 8, py, text=etiket, fill=RENK_METIN,
                              font=("Segoe UI", 8, "bold"), anchor="w")
            # karakter (merkez)
            self._daire(o, o, 4, fill=RENK_BEN, outline="#ffffff")
            self.bilgi.configure(text="%d metin · %d oyuncu · %d canavar   (konum %d, %d)" % (
                len(veri["metinler"]), len(veri["oyuncular"]), len(veri["canavarlar"]),
                konum[0], konum[1]))
        self.after(500, self._ciz)

    def _kapali(self):
        try:
            return not self.winfo_exists()
        except tk.TclError:
            return True


if __name__ == "__main__":
    Panel().mainloop()
