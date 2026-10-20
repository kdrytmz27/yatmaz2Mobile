'use strict';

var sendFn = new NativeFunction(
    Module.findExportByName("libc.so", "send"),
    'int', ['int', 'pointer', 'int', 'int']
);

var lastPkt  = null;
var baseTik  = 0;
var baseTime = 0;
var lastFd   = -1;
var botAktif = false;
var hedefX   = 0;
var hedefY   = 0;
var interval = null;

/* Oyunun send() çağrısından tik ve fd yakala */
Interceptor.attach(Module.findExportByName("libc.so", "send"), {
    onEnter: function(args) {
        var len = args[2].toInt32();
        if (len !== 16) return;
        var b = new Uint8Array(Memory.readByteArray(args[1], 16));
        if (b[0] !== 7) return;

        lastFd   = args[0].toInt32();
        baseTik  = (b[12]) | (b[13] << 8) | (b[14] << 16) | (b[15] << 24);
        baseTime = Date.now();
        lastPkt  = Array.from(b);

        var curX = (b[4]) | (b[5] << 8) | (b[6] << 16) | (b[7] << 24);
        var curY = (b[8]) | (b[9] << 8) | (b[10] << 16) | (b[11] << 24);
        send({ type: 'konum', x: curX, y: curY, hedefX: hedefX, hedefY: hedefY, dist: 0 });
    }
});

function paketGonder() {
    if (!botAktif || !lastPkt || lastFd < 0) return;

    var b    = lastPkt;
    var curX = (b[4]) | (b[5] << 8) | (b[6] << 16) | (b[7] << 24);
    var curY = (b[8]) | (b[9] << 8) | (b[10] << 16) | (b[11] << 24);
    var dx   = hedefX - curX;
    var dy   = hedefY - curY;
    var dist2 = dx * dx + dy * dy;

    if (dist2 < 2500) {
        botAktif = false;
        send({ type: 'durum', mesaj: 'Hedefe ulasildi: ' + curX + ',' + curY });
        return;
    }

    var adim = 70;
    var nx, ny;
    if (dist2 <= adim * adim) {
        nx = hedefX; ny = hedefY;
    } else {
        nx = (curX + ((dx * adim * adim) / dist2) | 0);
        ny = (curY + ((dy * adim * adim) / dist2) | 0);
    }

    var p  = lastPkt.slice();
    p[1]   = 1;
    nx     = nx >>> 0; ny = ny >>> 0;
    p[4]   = nx & 0xFF;         p[5]  = (nx >> 8) & 0xFF;
    p[6]   = (nx >> 16) & 0xFF; p[7]  = (nx >> 24) & 0xFF;
    p[8]   = ny & 0xFF;         p[9]  = (ny >> 8) & 0xFF;
    p[10]  = (ny >> 16) & 0xFF; p[11] = (ny >> 24) & 0xFF;
    var tik = (baseTik + (Date.now() - baseTime)) >>> 0;
    p[12]  = tik & 0xFF;         p[13] = (tik >> 8) & 0xFF;
    p[14]  = (tik >> 16) & 0xFF; p[15] = (tik >> 24) & 0xFF;

    var pkt = Memory.alloc(16);
    pkt.writeByteArray(p);
    var r = sendFn(lastFd, pkt, 16, 0);

    /* lastPkt'i güncelle — sonraki tik için */
    lastPkt = p;
    baseTik = tik;
    baseTime = Date.now();

    send({ type: 'konum', x: nx, y: ny, hedefX: hedefX, hedefY: hedefY,
           dist: (Math.sqrt(dist2) | 0) });
}

/* 150ms'de bir paket gönder */
interval = setInterval(paketGonder, 150);

function bekleHareket() {
    recv('hareket', function(msg) {
        hedefX   = msg.x;
        hedefY   = msg.y;
        botAktif = true;
        send({ type: 'durum', mesaj: 'Hareket basladi -> ' + msg.x + ',' + msg.y });
        bekleHareket();
    });
}

function bekleDur() {
    recv('dur', function(msg) {
        botAktif = false;
        send({ type: 'durum', mesaj: 'Bot durduruldu' });
        bekleDur();
    });
}

bekleHareket();
bekleDur();
send({ type: 'durum', mesaj: 'Bot hazir' });