import os
import json
import time
import requests

from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# AYARLAR
# ============================================================

load_dotenv()

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]

GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

API_SURUM = "v21.0"
API_TEMEL = f"https://graph.instagram.com/{API_SURUM}"

CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")

KONTROL_ARALIGI = 5
MAKSIMUM_BEKLEME = 180


# ============================================================
# SON İÇERİK DOSYASINI BUL
# ============================================================

def son_icerik_dosyasi():

    dosyalar = sorted(
        CIKTI_KLASOR.glob("icerik_*.json")
    )

    if not dosyalar:

        raise FileNotFoundError(
            "cikti/ klasöründe icerik_*.json bulunamadı."
        )

    return dosyalar[-1]


# ============================================================
# İÇERİĞE AİT GÖRSEL KLASÖRÜNÜ BUL
# ============================================================

def gorsel_klasoru_bul(tarih):

    hedef_klasor = (
        GORSEL_KLASOR / tarih
    )

    if not hedef_klasor.exists():

        raise FileNotFoundError(
            f"Bu içeriğe ait görsel klasörü bulunamadı: "
            f"{hedef_klasor}"
        )

    if not hedef_klasor.is_dir():

        raise NotADirectoryError(
            f"Görsel yolu klasör değil: "
            f"{hedef_klasor}"
        )

    return hedef_klasor


# ============================================================
# GITHUB RAW URL
# ============================================================

def github_raw_url(dosya_yolu):

    relative_path = dosya_yolu.as_posix()

    return (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"main/"
        f"{relative_path}"
    )


# ============================================================
# CONTAINER DURUMU
# ============================================================

def container_durumu(container_id):

    yanit = requests.get(

        f"{API_TEMEL}/{container_id}",

        params={
            "fields": "status_code,status",
            "access_token": ACCESS_TOKEN,
        },

        timeout=30
    )

    if not yanit.ok:

        print(
            "Container durum kontrolü başarısız:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    veri = yanit.json()

    return veri


# ============================================================
# CONTAINER HAZIR OLANA KADAR BEKLE
# ============================================================

def container_bekle(container_id):

    print()
    print(
        f"Container hazırlanıyor: {container_id}"
    )

    baslangic = time.time()

    while True:

        durum = container_durumu(
            container_id
        )

        status_code = durum.get(
            "status_code"
        )

        status = durum.get(
            "status"
        )

        print(
            f"Durum: {status_code or status}"
        )

        # ----------------------------------------------------
        # Hazır
        # ----------------------------------------------------

        if status_code == "FINISHED":

            print(
                "✓ Container hazır."
            )

            return True

        # ----------------------------------------------------
        # Hata
        # ----------------------------------------------------

        if status_code in [
            "ERROR",
            "EXPIRED"
        ]:

            raise RuntimeError(
                f"Instagram container hatası: {durum}"
            )

        # ----------------------------------------------------
        # Timeout
        # ----------------------------------------------------

        gecen_sure = (
            time.time()
            - baslangic
        )

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                f"Container {MAKSIMUM_BEKLEME} saniye "
                f"içinde hazır olmadı: {container_id}"
            )

        time.sleep(
            KONTROL_ARALIGI
        )


# ============================================================
# CHILD CONTAINER
# ============================================================

def child_container_olustur(gorsel_url):

    print()
    print(
        "Child container oluşturuluyor:"
    )

    print(
        gorsel_url
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media",

        data={
            "image_url": gorsel_url,
            "is_carousel_item": "true",
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print()
        print(
            "❌ Child container oluşturulamadı:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = (
        yanit.json()["id"]
    )

    print(
        f"✓ Child container: {container_id}"
    )

    return container_id


# ============================================================
# CAROUSEL CONTAINER
# ============================================================

def carousel_container_olustur(
    child_ids,
    caption
):

    print()
    print(
        "Carousel container oluşturuluyor..."
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media",

        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print()
        print(
            "❌ Carousel container oluşturulamadı:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = (
        yanit.json()["id"]
    )

    print(
        f"✓ Carousel container: {container_id}"
    )

    return container_id


# ============================================================
# CAROUSEL YAYINLA
# ============================================================

def carousel_yayinla():

    print()
    print("=" * 60)
    print("INSTAGRAM CAROUSEL YAYINI")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. İçerik JSON
    # --------------------------------------------------------

    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    print()
    print(
        f"İçerik: {icerik_dosyasi}"
    )

    icerik = json.loads(

        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------------
    # 2. İçeriğin tarihini al
    # --------------------------------------------------------

    tarih = icerik.get(
        "tarih"
    )

    if not tarih:

        raise ValueError(
            "İçerik JSON dosyasında 'tarih' bulunamadı."
        )

    # --------------------------------------------------------
    # 3. AYNI İÇERİĞE AİT GÖRSEL KLASÖRÜ
    # --------------------------------------------------------

    gorsel_klasoru = (
        gorsel_klasoru_bul(
            tarih
        )
    )

    print(
        f"Görseller: {gorsel_klasoru}"
    )

    # --------------------------------------------------------
    # 4. PNG dosyaları
    # --------------------------------------------------------

    png_dosyalari = sorted(
        gorsel_klasoru.glob("*.png")
    )

    if not png_dosyalari:

        raise FileNotFoundError(
            f"{gorsel_klasoru} klasöründe PNG bulunamadı."
        )

    print()
    print(
        f"{len(png_dosyalari)} görsel bulundu."
    )

    # --------------------------------------------------------
    # 5. Instagram child container'ları
    # --------------------------------------------------------

    child_ids = []

    for sira, png_dosyasi in enumerate(
        png_dosyalari,
        start=1
    ):

        print()
        print(
            f"[{sira}/{len(png_dosyalari)}]"
        )

        # Dosya yolu
        gorsel_yolu = png_dosyasi.as_posix()

        # GitHub Raw URL
        gorsel_url = github_raw_url(
            Path(gorsel_yolu)
        )

        print(
            f"URL: {gorsel_url}"
        )

        # Child container oluştur
        child_id = (
            child_container_olustur(
                gorsel_url
            )
        )

        # Hazır olmasını bekle
        container_bekle(
            child_id
        )

        child_ids.append(
            child_id
        )

    # --------------------------------------------------------
    # 6. Caption
    # --------------------------------------------------------

    caption = icerik.get(
        "caption",
        ""
    )

    hashtagler = icerik.get(
        "hashtagler",
        []
    )

    if hashtagler:

        caption = (
            caption
            + "\n\n"
            + " ".join(hashtagler)
        )

    # --------------------------------------------------------
    # 7. Ana Carousel container
    # --------------------------------------------------------

    carousel_id = (
        carousel_container_olustur(
            child_ids,
            caption
        )
    )

    # --------------------------------------------------------
    # 8. Ana container hazır mı?
    # --------------------------------------------------------

    container_bekle(
        carousel_id
    )

    # --------------------------------------------------------
    # 9. Yayınla
    # --------------------------------------------------------

    print()
    print(
        "Carousel Instagram'a yayınlanıyor..."
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media_publish",

        data={
            "creation_id": carousel_id,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print()
        print(
            "❌ CAROUSEL YAYINLANAMADI"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    # --------------------------------------------------------
    # 10. Başarılı
    # --------------------------------------------------------

    post_id = (
        yanit.json().get("id")
    )

    print()
    print("=" * 60)
    print("✓ CAROUSEL BAŞARIYLA YAYINLANDI")
    print("=" * 60)

    print()
    print(
        f"Instagram Post ID: {post_id}"
    )

    print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        carousel_yayinla()

    except Exception as hata:

        print()
        print("=" * 60)
        print("❌ CAROUSEL HATASI")
        print("=" * 60)

        print()
        print(
            hata
        )

        raise
