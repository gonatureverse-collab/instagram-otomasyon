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

API_SURUM = "v21.0"
API_TEMEL = f"https://graph.instagram.com/{API_SURUM}"

CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")

# Container'ın hazır olması için maksimum bekleme
MAKSIMUM_BEKLEME = 180

# Her kontrol arasındaki süre
KONTROL_ARALIGI = 5


# ============================================================
# SON İÇERİK DOSYASINI BUL
# ============================================================

def son_icerik_dosyasi():

    dosyalar = sorted(
        CIKTI_KLASOR.glob("icerik_*.json")
    )

    if not dosyalar:
        raise FileNotFoundError(
            "cikti klasöründe icerik_*.json bulunamadı."
        )

    return dosyalar[-1]


# ============================================================
# SON GÖRSEL KLASÖRÜNÜ BUL
# ============================================================

def son_gorsel_klasoru():

    klasorler = [
        x for x in GORSEL_KLASOR.glob("*")
        if x.is_dir()
    ]

    if not klasorler:
        raise FileNotFoundError(
            "gorseller klasöründe görsel klasörü bulunamadı."
        )

    return sorted(
        klasorler,
        key=lambda x: x.name
    )[-1]


# ============================================================
# GITHUB RAW URL OLUŞTUR
# ============================================================

def github_raw_url(dosya_yolu):

    username = os.environ["GITHUB_USERNAME"]
    repo = os.environ["GITHUB_REPO"]

    # gorseller/tarih/dosya.png
    relative_path = dosya_yolu.as_posix()

    return (
        f"https://raw.githubusercontent.com/"
        f"{username}/{repo}/main/"
        f"{relative_path}"
    )


# ============================================================
# CONTAINER DURUMUNU KONTROL ET
# ============================================================

def container_durumu(container_id):

    yanit = requests.get(
        f"{API_TEMEL}/{container_id}",
        params={
            "fields": "status_code,status",
            "access_token": ACCESS_TOKEN,
        },
        timeout=30,
    )

    if not yanit.ok:
        print(
            "Container durum kontrolü başarısız:"
        )
        print(yanit.text)

        yanit.raise_for_status()

    return yanit.json()


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

        durum = container_durumu(container_id)

        status_code = durum.get("status_code")
        status = durum.get("status")

        print(
            f"Durum: {status_code or status}"
        )

        # Hazır
        if status_code == "FINISHED":

            print(
                "✓ Container hazır."
            )

            return True

        # Hata
        if status_code == "ERROR":

            raise RuntimeError(
                f"Instagram container hatası: {durum}"
            )

        # Timeout
        gecen_sure = time.time() - baslangic

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                f"Container {MAKSIMUM_BEKLEME} saniye "
                f"içinde hazır olmadı: {container_id}"
            )

        time.sleep(KONTROL_ARALIGI)


# ============================================================
# CHILD CONTAINER OLUŞTUR
# ============================================================

def child_container_olustur(gorsel_url):

    print()
    print(
        "Child container oluşturuluyor:"
    )

    print(gorsel_url)

    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media",
        data={
            "image_url": gorsel_url,
            "is_carousel_item": "true",
            "access_token": ACCESS_TOKEN,
        },
        timeout=60,
    )

    if not yanit.ok:

        print()
        print(
            "❌ Child container oluşturulamadı."
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = yanit.json()["id"]

    print(
        f"✓ Child container: {container_id}"
    )

    return container_id


# ============================================================
# CAROUSEL CONTAINER OLUŞTUR
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
        timeout=60,
    )

    if not yanit.ok:

        print()
        print(
            "❌ Carousel container oluşturulamadı."
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = yanit.json()["id"]

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
    # İçerik
    # --------------------------------------------------------

    icerik_dosyasi = son_icerik_dosyasi()

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
    # Görseller
    # --------------------------------------------------------

    gorsel_klasoru = son_gorsel_klasoru()

    print(
        f"Görseller: {gorsel_klasoru}"
    )


    # --------------------------------------------------------
    # PNG dosyalarını sırala
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
    # Child container'lar
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

        # GitHub yolu
        github_yolu = png_dosyasi.as_posix()

        # Public URL
        gorsel_url = github_raw_url(
            Path(github_yolu)
        )

        print(
            f"URL: {gorsel_url}"
        )

        # Child oluştur
        child_id = child_container_olustur(
            gorsel_url
        )

        # Hazır olmasını bekle
        container_bekle(
            child_id
        )

        child_ids.append(
            child_id
        )


    # --------------------------------------------------------
    # Caption
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
    # Carousel container
    # --------------------------------------------------------

    carousel_id = carousel_container_olustur(
        child_ids,
        caption
    )


    # --------------------------------------------------------
    # Carousel hazır olana kadar bekle
    # --------------------------------------------------------

    container_bekle(
        carousel_id
    )


    # --------------------------------------------------------
    # YAYINLA
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
        timeout=60,
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
    # Başarılı
    # --------------------------------------------------------

    post_id = yanit.json().get(
        "id"
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
        print(hata)

        raise