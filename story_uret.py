import json
from pathlib import Path
from playwright.sync_api import sync_playwright


# ============================================================
# KLASÖRLER
# ============================================================

CIKTI_KLASOR = Path("cikti")
STORY_KLASOR = Path("stories")

# Instagram Story ölçüsü
GENISLIK = 1080
YUKSEKLIK = 1920


# ============================================================
# STORY HTML TASARIMI
# ============================================================

STORY_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&display=swap');

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    width: {genislik}px;
    height: {yukseklik}px;

    font-family: 'Montserrat', sans-serif;

    background:
        radial-gradient(
            circle at 50% 20%,
            #292929 0%,
            #111111 45%,
            #050505 100%
        );

    color: white;

    position: relative;

    overflow: hidden;
}}


/* ========================================================
   ÜST ALMAN BAYRAĞI ŞERİDİ
   ======================================================== */

.ust-serit {{
    position: absolute;

    top: 0;
    left: 0;

    width: 100%;
    height: 30px;

    display: flex;
}}

.ust-serit .siyah {{
    flex: 1;
    background: #111111;
}}

.ust-serit .kirmizi {{
    flex: 1;
    background: #DD0000;
}}

.ust-serit .sari {{
    flex: 1;
    background: #FFCE00;
}}


/* ========================================================
   ALT ALMAN BAYRAĞI ŞERİDİ
   ======================================================== */

.alt-serit {{
    position: absolute;

    bottom: 0;
    left: 0;

    width: 100%;
    height: 30px;

    display: flex;
}}

.alt-serit .siyah {{
    flex: 1;
    background: #111111;
}}

.alt-serit .kirmizi {{
    flex: 1;
    background: #DD0000;
}}

.alt-serit .sari {{
    flex: 1;
    background: #FFCE00;
}}


/* ========================================================
   ÜST BAŞLIK
   ======================================================== */

.logo {{
    position: absolute;

    top: 100px;
    left: 70px;
    right: 70px;

    text-align: center;

    color: #FFCE00;

    font-size: 32px;

    font-weight: 800;

    letter-spacing: 3px;
}}


/* ========================================================
   STORY İKONU
   ======================================================== */

.ikon {{
    position: absolute;

    top: 250px;

    left: 0;
    right: 0;

    text-align: center;

    font-size: 150px;
}}


/* ========================================================
   BAŞLIK
   ======================================================== */

.baslik {{
    position: absolute;

    top: 480px;

    left: 70px;
    right: 70px;

    text-align: center;

    color: white;

    font-size: 58px;

    line-height: 1.2;

    font-weight: 900;
}}


/* ========================================================
   SORU KUTUSU
   ======================================================== */

.soru-kutusu {{
    position: absolute;

    top: 760px;

    left: 70px;
    right: 70px;

    padding: 60px 45px;

    background: white;

    border-radius: 35px;

    box-shadow:
        0 15px 50px rgba(0,0,0,0.45);

    text-align: center;
}}

.soru {{
    color: #111111;

    font-size: 46px;

    line-height: 1.3;

    font-weight: 800;
}}


/* ========================================================
   ANKET
   ======================================================== */

.anket {{
    position: absolute;

    top: 1190px;

    left: 70px;
    right: 70px;

    display: flex;

    gap: 30px;
}}

.secenek {{
    flex: 1;

    min-height: 220px;

    background: #ffffff;

    border-radius: 35px;

    display: flex;

    align-items: center;

    justify-content: center;

    text-align: center;

    padding: 35px;

    color: #111111;

    font-size: 34px;

    font-weight: 800;

    box-shadow:
        0 15px 40px rgba(0,0,0,0.35);
}}

.secenek:first-child {{
    border-top: 15px solid #DD0000;
}}

.secenek:last-child {{
    border-top: 15px solid #FFCE00;
}}


/* ========================================================
   CTA
   ======================================================== */

.cta {{
    position: absolute;

    bottom: 140px;

    left: 70px;
    right: 70px;

    text-align: center;

    color: #ffffff;

    font-size: 30px;

    font-weight: 600;

    line-height: 1.4;
}}

.cta span {{
    color: #FFCE00;

    font-weight: 900;
}}

</style>

</head>


<body>


<!-- ÜST ŞERİT -->

<div class="ust-serit">

    <div class="siyah"></div>

    <div class="kirmizi"></div>

    <div class="sari"></div>

</div>


<!-- ALT ŞERİT -->

<div class="alt-serit">

    <div class="siyah"></div>

    <div class="kirmizi"></div>

    <div class="sari"></div>

</div>


<!-- HESAP ADI -->

<div class="logo">

    ALMANYA'DA NASIL YAPILIR?

</div>


<!-- İKON -->

<div class="ikon">

    📊

</div>


<!-- STORY BAŞLIĞI -->

<div class="baslik">

    {baslik}

</div>


<!-- SORU -->

<div class="soru-kutusu">

    <div class="soru">

        {metin}

    </div>

</div>


<!-- ANKET -->

<div class="anket">

    <div class="secenek">

        {secenek1}

    </div>

    <div class="secenek">

        {secenek2}

    </div>

</div>


<!-- CTA -->

<div class="cta">

    <span>Oyunu kullan 👆</span><br>

    Senin cevabın hangisi?

</div>


</body>

</html>
"""


# ============================================================
# EN SON İÇERİK DOSYASINI BUL
# ============================================================

def son_icerik_dosyasi():

    dosyalar = sorted(
        CIKTI_KLASOR.glob("icerik_*.json")
    )

    if not dosyalar:

        raise FileNotFoundError(
            "cikti/ klasöründe içerik dosyası bulunamadı. "
            "Önce icerik_uret.py çalıştır."
        )

    return dosyalar[-1]


# ============================================================
# STORY ÜRET
# ============================================================

def story_uret(icerik_dosyasi: Path):

    # --------------------------------------------------------
    # JSON oku
    # --------------------------------------------------------

    icerik = json.loads(
        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------------
    # Story kontrolü
    # --------------------------------------------------------

    if "story" not in icerik:

        raise ValueError(
            "JSON içerisinde 'story' bölümü bulunamadı."
        )

    story = icerik["story"]

    # --------------------------------------------------------
    # Tarih
    # --------------------------------------------------------

    tarih = icerik.get(
        "tarih",
        "story"
    )

    # --------------------------------------------------------
    # Story klasörü
    # --------------------------------------------------------

    hedef_klasor = (
        STORY_KLASOR
        / tarih
    )

    hedef_klasor.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Story bilgileri
    # --------------------------------------------------------

    baslik = story.get(
        "baslik",
        "Sen ne düşünüyorsun?"
    )

    metin = story.get(
        "metin",
        "Bu konu hakkında ne düşünüyorsun?"
    )

    anket = story.get(
        "anket",
        []
    )

    # --------------------------------------------------------
    # Anket kontrolü
    # --------------------------------------------------------

    if len(anket) < 2:

        anket = [
            "Evet 👍",
            "Hayır 👎"
        ]

    secenek1 = anket[0]
    secenek2 = anket[1]

    # --------------------------------------------------------
    # HTML oluştur
    # --------------------------------------------------------

    html = STORY_HTML.format(

        genislik=GENISLIK,

        yukseklik=YUKSEKLIK,

        baslik=baslik,

        metin=metin,

        secenek1=secenek1,

        secenek2=secenek2
    )

    # --------------------------------------------------------
    # Playwright
    # --------------------------------------------------------

    print(
        "\nInstagram Story oluşturuluyor..."
    )

    with sync_playwright() as p:

        tarayici = p.chromium.launch()

        sayfa = tarayici.new_page(

            viewport={
                "width": GENISLIK,
                "height": YUKSEKLIK
            },

            device_scale_factor=1
        )

        # HTML yükle
        sayfa.set_content(
            html,
            wait_until="networkidle"
        )

        # Fontların yüklenmesi için bekle
        sayfa.wait_for_timeout(
            1000
        )

        # ----------------------------------------------------
        # PNG
        # ----------------------------------------------------

        story_yolu = (
            hedef_klasor
            / "story.png"
        )

        sayfa.screenshot(

            path=str(story_yolu),

            full_page=True
        )

        tarayici.close()

    # --------------------------------------------------------
    # Sonuç
    # --------------------------------------------------------

    print(
        f"✓ Story oluşturuldu: {story_yolu}"
    )

    return story_yolu


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "========================================"
    )

    print(
        "INSTAGRAM STORY ÜRETİCİ"
    )

    print(
        "========================================"
    )

    # Son JSON
    icerik_dosyasi = son_icerik_dosyasi()

    print(
        f"\nKullanılan içerik:"
        f"\n{icerik_dosyasi}"
    )

    # Story üret
    story_yolu = story_uret(
        icerik_dosyasi
    )

    print(
        "\n========================================"
    )

    print(
        "✓ STORY BAŞARIYLA OLUŞTURULDU"
    )

    print(
        "========================================"
    )

    print(
        f"\nDosya:"
        f"\n{story_yolu}"
    )


# ============================================================
# ÇALIŞTIR
# ============================================================

if __name__ == "__main__":

    main()