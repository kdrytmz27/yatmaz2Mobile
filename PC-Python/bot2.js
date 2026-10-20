var lastFd=-1,baseTik=0,baseTime=0,lastPkt3=null,pa3=null,found=false,lastSendTime=0,curX=0,curY=0,hedefX=0,hedefY=0,atkVID=0;
var sendFn2=new NativeFunction(Module.findExportByName("libc.so","send"),'int',['int','pointer','int','int']);

// Send hook - koordinat bul + bot paketi gönder
Interceptor.attach(Module.findExportByName("libc.so","send"),{
  onEnter:function(args){
    if(args[2].toInt32()!==16)return;
    var b=new Uint8Array(Memory.readByteArray(args[1],16));
    if(b[0]!==7)return;
    lastFd=args[0].toInt32();
    baseTik=b[12]|(b[13]<<8)|(b[14]<<16)|(b[15]<<24);
    baseTime=Date.now();
    lastPkt3=Array.from(b);
    if(b[1]===1){
      lastSendTime=Date.now();
      if(hedefX>0){
        args[1].add(4).writeS32(curX);
        args[1].add(8).writeS32(curY);
      }
    }
    if(b[1]!==0||found||Date.now()-lastSendTime>=500)return;
    var cx=b[4]|(b[5]<<8)|(b[6]<<16)|(b[7]<<24);
    var cy=b[8]|(b[9]<<8)|(b[10]<<16)|(b[11]<<24);
    curX=cx;curY=cy;
    var pat=cx.toString(16).padStart(8,"0").match(/../g).reverse().join(" ");
    var res=[];
    Process.enumerateRanges("rw-").forEach(function(r){
      if(r.size<50000000)try{Memory.scanSync(r.base,r.size,pat).forEach(function(m){res.push(m.address);});}catch(e){}
    });
    if(res.length>=2){pa3=res[1];found=true;console.log("PA3="+pa3+" curX="+curX+" curY="+curY);}
  }
});

// Memmove hook - istemci konumu güncelle
Interceptor.attach(Module.findExportByName("libc.so","memmove"),{
  onEnter:function(args){
    if(!pa3||hedefX===0)return;
    var dst=args[0];
    if(dst.compare(pa3.sub(16))>0&&dst.compare(pa3.add(16))<0){
      var x=Memory.readS32(args[1].add(4));
      if(x>800000&&x<1100000){
        var dx=hedefX-curX,dy=hedefY-curY;
        if(Math.abs(dx)>50)curX+=dx>0?50:-50;else curX=hedefX;
        if(Math.abs(dy)>50)curY+=dy>0?50:-50;else curY=hedefY;
        this.ok=true;this.dst=dst;
      }else this.ok=false;
    }else this.ok=false;
  },
  onLeave:function(){
    if(this.ok){try{this.dst.add(4).writeS32(curX);this.dst.add(8).writeS32(curY);}catch(e){}}
  }
});

// Saldırı fonksiyonu
function saldir(vid,x,y){
  if(lastFd<0)return;
  var p1=[0x3d,vid&0xFF,(vid>>8)&0xFF,(vid>>16)&0xFF,(vid>>24)&0xFF];
  var pkt1=Memory.alloc(5);pkt1.writeByteArray(p1);sendFn2(lastFd,pkt1,5,0);
  var p2=[0x02,0x00,vid&0xFF,(vid>>8)&0xFF,(vid>>16)&0xFF,(vid>>24)&0xFF,0x08,0x0f,0x00,vid&0xFF,(vid>>8)&0xFF,(vid>>16)&0xFF,(vid>>24)&0xFF,x&0xFF,(x>>8)&0xFF,(x>>16)&0xFF,(x>>24)&0xFF,y&0xFF,(y>>8)&0xFF,(y>>16)&0xFF,(y>>24)&0xFF];
  var pkt2=Memory.alloc(21);pkt2.writeByteArray(p2);sendFn2(lastFd,pkt2,21,0);
  console.log("[ATK] VID="+vid.toString(16));
}

// Bot hareket fonksiyonu
var rota=[];var rotaIdx=0;var botIv=null;
function botBaslat(r){
  rota=r;rotaIdx=0;
  hedefX=rota[0].x;hedefY=rota[0].y;
  if(botIv)clearInterval(botIv);
  botIv=setInterval(function(){
    if(!lastPkt3||lastFd<0)return;
    var dx=hedefX-curX,dy=hedefY-curY;
    if(Math.abs(dx)<300&&Math.abs(dy)<300){
      rotaIdx=(rotaIdx+1)%rota.length;
      hedefX=rota[rotaIdx].x;hedefY=rota[rotaIdx].y;
      console.log("Hedef #"+rotaIdx+": "+hedefX+","+hedefY);
    }
    var a=70;
    if(Math.abs(dx)>a)curX+=dx>0?a:-a;else curX=hedefX;
    if(Math.abs(dy)>a)curY+=dy>0?a:-a;else curY=hedefY;
    var p=lastPkt3.slice();p[1]=1;
    p[4]=curX&0xFF;p[5]=(curX>>8)&0xFF;p[6]=(curX>>16)&0xFF;p[7]=(curX>>24)&0xFF;
    p[8]=curY&0xFF;p[9]=(curY>>8)&0xFF;p[10]=(curY>>16)&0xFF;p[11]=(curY>>24)&0xFF;
    var tik=(baseTik+(Date.now()-baseTime))>>>0;
    p[12]=tik&0xFF;p[13]=(tik>>8)&0xFF;p[14]=(tik>>16)&0xFF;p[15]=(tik>>24)&0xFF;
    var pkt=Memory.alloc(16);pkt.writeByteArray(p);sendFn2(lastFd,pkt,16,0);
  },150);
  console.log("Bot başladı!");
}

function botDur(){clearInterval(botIv);hedefX=0;console.log("Bot durduruldu");}

console.log("Bot hazır! Komutlar: botBaslat(rota), botDur(), saldir(vid,x,y)");
console.log("Önce yürü ve dur — PA3 bulunacak");