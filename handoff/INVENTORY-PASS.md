# Envanter tasarım adımı — build 6

Referans: https://romia2.com/assets/romia2/assets/pres/baslangic_0.jpeg

Ortadaki geniş panel yerine sağda yan yana Ekipman ve Envanter bölümleri. Çanta 5 sütun / 9 satır; 32 piksel hücre aralığı oyun içindeki çok hücreli eşya ölçüleriyle aynı. İki çalışan sayfa korunur; sunucuda olmayan 3/4. sayfa düğmeleri eklenmez. İki başlığın kapatma düğmesi envanter penceresini kapatır. Kemer çekmecesi ekipman panelinin yanına hizalanır.

Tema değişikliği yalnızca modernInventory işaretli panele uygulanır. Başlıklar Türkçe; genel oyun dili ve diğer ekranların metinleri bu adımda değiştirilmedi. Mevcut Türkçe seçeneği uilocaleselector.py içinde tr koduyla bulunuyor.

MuMu kontrolü: envanter açılışı, 1 -> 2 -> 1 sayfa geçişi, sağ başlıktan kapatıp yeniden açma, dolu yuvalar ve eşya açıklaması. syserr boş. Eşya taşıma/kullanma ve fiziksel Android cihaz testi yapılmadı.
