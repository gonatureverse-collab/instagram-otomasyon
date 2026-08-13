import os
import json
import requests
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# AYARLAR
# ============================================================

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]

API_SURUM = "v21.0"
API_TEMEL = f"https://graph.instagram.com/{API_SURUM}"

CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")
REEL_KLASOR = Path("reels")

# Video ayarları
SLAYT_SURESI = 1.5
FPS = 24

# Instagram video işleme ayarları
ILK_BEKLEME = 5          # Container oluşturulduktan sonra ilk bekleme
KONTROL_ARALIGI = 5      # Her status kontrolü arasındaki süre
MAKSIMUM_BEKLEME = 180   # Maksimum 3 dakika


# ============================================================
# DOSYA BULMA
# ============================================================

def son_icerik_dosyasi():
    dosyalar = sorted(CIKTI_KLASOR.glob("icerik_*.json"))

    if not dosyalar:
        raise FileNotFoundError(
            "cikti/ klasöründe içerik dosyası bulunamadı."
        )

    return dosyalar[-1]


def son_gorsel_klasoru():
    klasorler = sorted(
        [x for x in GORSEL_KLASOR.glob("*") if x.is_dir()],
        key=lambda x: x.name
    )

    if not klasorler:
        raise FileNotFoundError(
            "gorseller/ klasöründe görsel klasörü bulunamadı."
        )

    return klasorler[-1]


# ============================================================
# VIDEO OLUŞTUR
# ============================================================

def video_uret(gorsel_klasoru, icerik_dosyasi):

    icerik = json.loads(
        icerik_dosyasi.read_text(encoding="utf-8")
    )

    tarih = icerik["tarih"]

    REEL_KLASOR.mkdir(exist_ok=True)

    # PNG dosyalarını sırayla al
    png_dosyalari = sorted(
        gorsel_klasoru.glob("*.png")
    )

    if not png_dosyalari:
        raise FileNotFoundError(
            f"{gorsel_klasoru} klasöründe PNG bulunamadı."
        )

    print(
        f"{len(png_dosyalari)} PNG dosyası bulundu, "
        f"video oluşturuluyor..."
    )

    reel_yolu = REEL_KLASOR / f"reel_{tarih}.mp4"

    # FFmpeg concat dosyası
    files_txt = REEL_KLASOR / "files.txt"

    with open(files_txt, "w", encoding="utf-8") as f:

        for png_yolu in png_dosyalari:

            f.write(
                f"file '{png_yolu.absolute()}'\n"
            )

            f.write(
                f"duration {SLAYT_SURESI}\n"
            )

        # FFmpeg concat için son resmi tekrar eklemek
        # süre hesaplamasının düzgün olması için faydalıdır
        son_png = png_dosyalari[-1]

        f.write(
            f"file '{son_png.absolute()}'\n"
        )

    # FFmpeg komutu
    ffmpeg_komut = [
        "ffmpeg",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(files_txt),

        "-vf",
        (
            "scale=1080:1350:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1350:(ow-iw)/2:(oh-ih)/2"
        ),

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        "-y",

        str(reel_yolu),
    ]

    print("FFmpeg ile video oluşturuluyor...")

    subprocess.run(
        ffmpeg_komut,
        check=True
    )

    print(
        f"Video hazır: {reel_yolu}"
    )

    return reel_yolu


# ============================================================
# GITHUB'A GÖNDER
# ============================================================

def reel_github_ye_gonder(video_yolu):

    """
    Video'yu GitHub'a gönderir ve
    Instagram'ın erişebileceği raw URL'i döndürür.
    """

    print(
        "Video GitHub'a gönderiliyor..."
    )

    try:

        # GitHub'dan güncel durumu al
        subprocess.run(
            ["git", "fetch", "origin"],
            check=True
        )

        # Reels klasörünü ekle
        subprocess.run(
            ["git", "add", "reels/"],
            check=True
        )

        # Commit
        commit_sonucu = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "reel: video yayını"
            ],
            capture_output=True,
            text=True
        )

        # Commit yapılacak değişiklik yoksa hata kabul etmiyoruz
        if commit_sonucu.returncode != 0:

            if "nothing to commit" in (
                commit_sonucu.stdout.lower()
                + commit_sonucu.stderr.lower()
            ):

                print(
                    "GitHub'a gönderilecek yeni değişiklik yok."
                )

            else:

                print(
                    "Git commit uyarısı:"
                )

                print(
                    commit_sonucu.stdout
                )

                print(
                    commit_sonucu.stderr
                )

        # Push
        subprocess.run(
            ["git", "push"],
            check=True
        )

        print(
            "Video GitHub'a başarıyla gönderildi."
        )

    except Exception as e:

        print(
            f"Git işleminde uyarı: {e}"
        )

        print(
            "Raw URL yine oluşturulacak."
        )

    # GitHub bilgileri
    GITHUB_USERNAME = os.environ[
        "GITHUB_USERNAME"
    ]

    GITHUB_REPO = os.environ[
        "GITHUB_REPO"
    ]

    # Dosyanın sadece adı
    dosya_adi = video_yolu.name

    # Instagram için raw URL
    raw_url = (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"main/reels/"
        f"{dosya_adi}"
    )

    print(
        f"Instagram video URL: {raw_url}"
    )

    return raw_url


# ============================================================
# CONTAINER DURUMUNU KONTROL ET
# ============================================================

def container_durumunu_kontrol_et(container_id):

    """
    Instagram Reels container durumunu kontrol eder.
    """

    try:

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

            return None

        veri = yanit.json()

        status_code = veri.get(
            "status_code"
        )

        status = veri.get(
            "status"
        )

        print(
            f"Instagram container durumu: "
            f"{status_code or status}"
        )

        return status_code or status

    except requests.RequestException as e:

        print(
            f"Durum kontrolünde bağlantı hatası: {e}"
        )

        return None


# ============================================================
# CONTAINER HAZIR OLANA KADAR BEKLE
# ============================================================

def container_hazir_olmasini_bekle(container_id):

    """
    Instagram video işleme tamamlanana kadar bekler.

    FINISHED  -> devam
    IN_PROGRESS -> bekle
    ERROR -> hata
    """

    print(
        "Instagram videoyu işliyor..."
    )

    print(
        f"İlk {ILK_BEKLEME} saniye bekleniyor..."
    )

    time.sleep(
        ILK_BEKLEME
    )

    baslangic_zamani = time.time()

    while True:

        gecen_sure = (
            time.time()
            - baslangic_zamani
        )

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                "Instagram videosu "
                f"{MAKSIMUM_BEKLEME} saniye içinde "
                "hazır olmadı."
            )

        durum = container_durumunu_kontrol_et(
            container_id
        )

        # ----------------------------------------------------
        # Video hazır
        # ----------------------------------------------------

        if durum == "FINISHED":

            print(
                "✓ Instagram videosu hazır."
            )

            return True

        # ----------------------------------------------------
        # Video hâlâ işleniyor
        # ----------------------------------------------------

        if durum in (
            "IN_PROGRESS",
            "PROCESSING"
        ):

            print(
                f"Video hâlâ işleniyor... "
                f"{int(gecen_sure)} saniye geçti."
            )

            time.sleep(
                KONTROL_ARALIGI
            )

            continue

        # ----------------------------------------------------
        # Instagram hata verdi
        # ----------------------------------------------------

        if durum == "ERROR":

            raise RuntimeError(
                "Instagram video container "
                "işlenirken ERROR oluştu."
            )

        # ----------------------------------------------------
        # Bilinmeyen durum
        # ----------------------------------------------------

        print(
            f"Beklenmeyen container durumu: {durum}"
        )

        time.sleep(
            KONTROL_ARALIGI
        )


# ============================================================
# REELS YAYINLA
# ============================================================

def reel_yayinla(video_yolu):

    """
    Instagram Reels API ile yayınlar.

    1. Video GitHub'a gönderilir.
    2. Raw URL alınır.
    3. Instagram media container oluşturulur.
    4. Container durumu kontrol edilir.
    5. FINISHED olduğunda yayınlanır.
    """

    # --------------------------------------------------------
    # 1. GitHub
    # --------------------------------------------------------

    video_url = reel_github_ye_gonder(
        video_yolu
    )

    # --------------------------------------------------------
    # 2. Instagram container oluştur
    # --------------------------------------------------------

    print(
        "Instagram Reels container oluşturuluyor..."
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media",

        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": "Reels video yayını 🎬",
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print(
            "HATA - Container oluşturulamadı:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = yanit.json()["id"]

    print(
        f"✓ Reels container oluşturuldu: "
        f"{container_id}"
    )

    # --------------------------------------------------------
    # 3. Video hazır olana kadar bekle
    # --------------------------------------------------------

    container_hazir_olmasini_bekle(
        container_id
    )

    # --------------------------------------------------------
    # 4. FINISHED -> yayınla
    # --------------------------------------------------------

    print(
        "Instagram Reels yayınlanıyor..."
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media_publish",

        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    # --------------------------------------------------------
    # Yayınlama hatası
    # --------------------------------------------------------

    if not yanit.ok:

        print(
            "HATA - Reel yayınlanamadı:"
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

    print(
        "===================================="
    )

    print(
        "✓ REELS BAŞARIYLA YAYINLANDI!"
    )

    print(
        f"Post ID: {post_id}"
    )

    print(
        "===================================="
    )

    return post_id


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "===================================="
    )

    print(
        "Instagram Reels Otomasyonu Başlıyor"
    )

    print(
        "===================================="
    )

    # İçerik dosyasını bul
    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    # Görsel klasörünü bul
    gorsel_klasoru = (
        son_gorsel_klasoru()
    )

    print(
        f"İçerik: {icerik_dosyasi.name}"
    )

    print(
        f"Görseller: {gorsel_klasoru.name}"
    )

    # Video oluştur
    video_yolu = video_uret(
        gorsel_klasoru,
        icerik_dosyasi
    )

    # Instagram'a gönder
    reel_yayinla(
        video_yolu
    )

    print(
        "\n✓ Reels video başarıyla yayınlandı!"
    )


# ============================================================
# PROGRAMI ÇALIŞTIR
# ============================================================

if __name__ == "__main__":
    main()