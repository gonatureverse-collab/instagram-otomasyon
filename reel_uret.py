import os
import json
import requests
import subprocess
import time

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
REEL_KLASOR = Path("reels")

# Video ayarları
SLAYT_SURESI = 1.5
FPS = 24

# Instagram video işleme
ILK_BEKLEME = 5
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
            "cikti/ klasöründe içerik dosyası bulunamadı."
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
            f"İçerik için görsel klasörü bulunamadı: "
            f"{hedef_klasor}"
        )

    if not hedef_klasor.is_dir():

        raise NotADirectoryError(
            f"Görsel yolu klasör değil: "
            f"{hedef_klasor}"
        )

    return hedef_klasor


# ============================================================
# VIDEO ÜRET
# ============================================================

def video_uret(gorsel_klasoru, icerik_dosyasi):

    icerik = json.loads(
        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    tarih = icerik["tarih"]

    REEL_KLASOR.mkdir(
        exist_ok=True
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

    print(
        f"{len(png_dosyalari)} PNG dosyası bulundu, "
        f"video oluşturuluyor..."
    )

    reel_yolu = (
        REEL_KLASOR
        / f"reel_{tarih}.mp4"
    )

    # --------------------------------------------------------
    # FFmpeg concat dosyası
    # --------------------------------------------------------

    files_txt = (
        REEL_KLASOR
        / f"files_{tarih}.txt"
    )

    with open(
        files_txt,
        "w",
        encoding="utf-8"
    ) as f:

        for png_yolu in png_dosyalari:

            # Windows ve Linux uyumlu path
            dosya = png_yolu.resolve()

            f.write(
                f"file '{dosya}'\n"
            )

            f.write(
                f"duration {SLAYT_SURESI}\n"
            )

        # Son görseli tekrar ekle
        # FFmpeg concat davranışını düzgün tutmak için
        son_png = png_dosyalari[-1].resolve()

        f.write(
            f"file '{son_png}'\n"
        )

    # --------------------------------------------------------
    # FFmpeg
    # --------------------------------------------------------

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

        str(reel_yolu)
    ]

    print(
        "FFmpeg ile video oluşturuluyor..."
    )

    # FFmpeg gerçekten var mı?
    try:

        ffmpeg_kontrol = subprocess.run(
            [
                "ffmpeg",
                "-version"
            ],
            capture_output=True,
            text=True
        )

        if ffmpeg_kontrol.returncode != 0:

            raise RuntimeError(
                "FFmpeg çalıştırılamadı."
            )

    except FileNotFoundError:

        raise RuntimeError(
            "FFmpeg bulunamadı. "
            "GitHub Actions ortamında FFmpeg kurulmalı."
        )

    # --------------------------------------------------------
    # Video oluştur
    # --------------------------------------------------------

    subprocess.run(
        ffmpeg_komut,
        check=True
    )

    # --------------------------------------------------------
    # Kontrol
    # --------------------------------------------------------

    if not reel_yolu.exists():

        raise FileNotFoundError(
            f"FFmpeg video oluşturamadı: "
            f"{reel_yolu}"
        )

    print(
        f"Video hazır: {reel_yolu}"
    )

    return reel_yolu


# ============================================================
# GITHUB'A REEL GÖNDER
# ============================================================

def reel_github_ye_gonder(video_yolu):

    print(
        "\nVideo GitHub'a gönderiliyor..."
    )

    try:

        # Güncel remote bilgisi
        subprocess.run(
            [
                "git",
                "fetch",
                "origin"
            ],
            check=True
        )

        # Reel dosyasını ekle
        subprocess.run(
            [
                "git",
                "add",
                "reels/"
            ],
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

        if commit_sonucu.returncode != 0:

            cikti = (
                commit_sonucu.stdout
                + commit_sonucu.stderr
            ).lower()

            if "nothing to commit" in cikti:

                print(
                    "Yeni Reel commit edilecek "
                    "değişiklik bulunamadı."
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

        else:

            print(
                "✓ Reel commit edildi."
            )

        # ----------------------------------------------------
        # Push
        # ----------------------------------------------------

        subprocess.run(
            [
                "git",
                "push",
                "origin",
                "main"
            ],
            check=True
        )

        print(
            "✓ Video GitHub'a başarıyla gönderildi."
        )

    except subprocess.CalledProcessError as hata:

        raise RuntimeError(
            f"GitHub Reel yükleme işlemi başarısız: {hata}"
        )

    # --------------------------------------------------------
    # Raw URL
    # --------------------------------------------------------

    raw_url = (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"main/reels/"
        f"{video_yolu.name}"
    )

    print(
        f"Instagram video URL:\n{raw_url}"
    )

    return raw_url


# ============================================================
# REEL CONTAINER OLUŞTUR
# ============================================================

def reel_container_olustur(video_url):

    print(
        "\nInstagram Reels container oluşturuluyor..."
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
            "HATA - Reel container oluşturulamadı:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = (
        yanit.json()["id"]
    )

    print(
        f"✓ Reels container oluşturuldu: "
        f"{container_id}"
    )

    return container_id


# ============================================================
# CONTAINER DURUMUNU KONTROL ET
# ============================================================

def container_durumunu_kontrol_et(container_id):

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

    except requests.RequestException as hata:

        print(
            f"Durum kontrolünde bağlantı hatası: {hata}"
        )

        return None


# ============================================================
# REEL HAZIR OLANA KADAR BEKLE
# ============================================================

def container_hazir_olmasini_bekle(container_id):

    print(
        "\nInstagram videoyu işliyor..."
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

        # ----------------------------------------------------
        # Timeout
        # ----------------------------------------------------

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                "Instagram videosu "
                f"{MAKSIMUM_BEKLEME} saniye içinde "
                "hazır olmadı."
            )

        # ----------------------------------------------------
        # Durum
        # ----------------------------------------------------

        durum = (
            container_durumunu_kontrol_et(
                container_id
            )
        )

        # ----------------------------------------------------
        # Hazır
        # ----------------------------------------------------

        if durum == "FINISHED":

            print(
                "✓ Instagram videosu hazır."
            )

            return True

        # ----------------------------------------------------
        # İşleniyor
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
        # Hata
        # ----------------------------------------------------

        if durum == "ERROR":

            raise RuntimeError(
                "Instagram Reel container "
                "işlenirken ERROR oluştu."
            )

        # ----------------------------------------------------
        # Bilinmeyen
        # ----------------------------------------------------

        print(
            f"Beklenmeyen container durumu: {durum}"
        )

        time.sleep(
            KONTROL_ARALIGI
        )


# ============================================================
# REEL YAYINLA
# ============================================================

def reel_yayinla(video_yolu):

    # --------------------------------------------------------
    # 1. GitHub
    # --------------------------------------------------------

    video_url = (
        reel_github_ye_gonder(
            video_yolu
        )
    )

    # --------------------------------------------------------
    # 2. Container
    # --------------------------------------------------------

    container_id = (
        reel_container_olustur(
            video_url
        )
    )

    # --------------------------------------------------------
    # 3. Hazır olmasını bekle
    # --------------------------------------------------------

    container_hazir_olmasini_bekle(
        container_id
    )

    # --------------------------------------------------------
    # 4. Yayınla
    # --------------------------------------------------------

    print(
        "\nInstagram Reels yayınlanıyor..."
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media_publish",

        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print(
            "HATA - Reel yayınlanamadı:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    post_id = (
        yanit.json().get("id")
    )

    print(
        "\n========================================"
    )

    print(
        "✓ REELS BAŞARIYLA YAYINLANDI!"
    )

    print(
        f"Post ID: {post_id}"
    )

    print(
        "========================================"
    )

    return post_id


# ============================================================
# ANA PROGRAM
# ============================================================

def main():

    print(
        "========================================"
    )

    print(
        "Instagram Reels Otomasyonu Başlıyor"
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # 1. İçerik dosyasını bul
    # --------------------------------------------------------

    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    # --------------------------------------------------------
    # 2. İçeriği oku
    # --------------------------------------------------------

    icerik = json.loads(
        icerik_dosyasi.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------------
    # 3. Tarih
    # --------------------------------------------------------

    tarih = icerik.get(
        "tarih"
    )

    if not tarih:

        raise ValueError(
            "İçerik JSON dosyasında 'tarih' bulunamadı."
        )

    # --------------------------------------------------------
    # 4. AYNI İÇERİĞE AİT GÖRSEL KLASÖRÜ
    # --------------------------------------------------------

    gorsel_klasoru = (
        gorsel_klasoru_bul(
            tarih
        )
    )

    print(
        f"\nİçerik: {icerik_dosyasi.name}"
    )

    print(
        f"Görseller: {gorsel_klasoru}"
    )

    # --------------------------------------------------------
    # 5. Video üret
    # --------------------------------------------------------

    video_yolu = (
        video_uret(
            gorsel_klasoru,
            icerik_dosyasi
        )
    )

    # --------------------------------------------------------
    # 6. Reel yayınla
    # --------------------------------------------------------

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
