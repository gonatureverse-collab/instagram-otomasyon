import os
import json
import requests
import html
import re
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# AYARLAR
# ============================================================

load_dotenv()

# Instagram
ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]

# GitHub
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

# Azure TTS
AZURE_TTS_KEY = os.environ["AZURE_TTS_KEY"]
AZURE_TTS_ENDPOINT = os.environ["AZURE_TTS_ENDPOINT"]
AZURE_TTS_REGION = os.environ["AZURE_TTS_REGION"]

# Türkçe Ses
AZURE_TTS_VOICE = "tr-TR-AhmetNeural"

# Instagram API
API_SURUM = "v21.0"
API_TEMEL = f"https://graph.instagram.com/{API_SURUM}"

# Klasörler
CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")
REEL_KLASOR = Path("reels")

# Video ayarları
SLAYT_SURESI = 2.0
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
# REEL SESLENDİRME METNİNİ HAZIRLA
# ============================================================

def emoji_temizle(metin):
    """
    Azure TTS'e gönderilmeden önce emoji ve görsel sembolleri temizler.

    ÖNEMLİ:
    - Instagram/Reels üzerindeki orijinal metin değişmez.
    - Sadece seslendirme için kullanılan metin temizlenir.
    - Türkçe harfler, rakamlar ve normal noktalama işaretleri korunur.
    """

    emoji_pattern = re.compile(
        "["
        "\U0001F1E0-\U0001F1FF"  # Bayraklar
        "\U0001F300-\U0001F5FF"  # Semboller ve piktogramlar
        "\U0001F600-\U0001F64F"  # Suratlar
        "\U0001F680-\U0001F6FF"  # Taşıtlar
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"  # Ek emoji
        "\U0001FA00-\U0001FAFF"  # Yeni emoji
        "\U0001FAD0-\U0001FAFF"  # Ek semboller
        "\u2600-\u26FF"          # Çeşitli semboller
        "\u2700-\u27BF"          # Dingbat sembolleri
        "\u2300-\u23FF"          # Teknik semboller
        "\u2B00-\u2BFF"          # Oklar ve semboller
        "\uFE0E-\uFE0F"          # Variation selector
        "\u200D"                 # Zero-width joiner
        "\u20E3"                 # Keycap combining
        "]+",
        flags=re.UNICODE
    )

    temiz = emoji_pattern.sub("", str(metin))

    # Emoji temizlendikten sonra oluşabilecek fazla boşlukları düzelt
    temiz = re.sub(r"\s+", " ", temiz).strip()

    return temiz


def reel_ses_metni_olustur(icerik):

    reel = icerik.get("reel")

    if not reel:

        raise ValueError(
            "İçerik JSON dosyasında 'reel' bölümü bulunamadı."
        )

    sahneler = reel.get(
        "sahneler",
        []
    )

    if not sahneler:

        raise ValueError(
            "Reel içerisinde 'sahneler' bulunamadı."
        )

    parcalar = []

    # Sahne metinleri
    for sahne in sahneler:

        if sahne and str(sahne).strip():

            parcalar.append(
                str(sahne).strip()
            )

    # CTA
    cta = reel.get(
        "cta",
        ""
    )

    if cta and str(cta).strip():

        parcalar.append(
            str(cta).strip()
        )

    metin = " ".join(
        parcalar
    )

    if not metin.strip():

        raise ValueError(
            "Seslendirme için kullanılabilecek metin bulunamadı."
        )

    # ========================================================
    # TTS İÇİN EMOJİLERİ / GÖRSEL SİMGELERİ TEMİZLE
    # ========================================================
    # Bu işlem sadece Azure'a gönderilecek ses metnine uygulanır.
    # Instagram'daki görsel/metin içeriği değişmez.
    tts_metin = emoji_temizle(metin)

    if not tts_metin.strip():

        raise ValueError(
            "Emoji temizlendikten sonra seslendirme metni boş kaldı."
        )

    print(
        f"TTS metni (emoji temizlenmiş): {tts_metin[:150]}..."
    )

    return tts_metin


# ============================================================
# AZURE TTS TÜRKÇE SES OLUŞTUR
# ============================================================

def ses_uret(icerik, tarih):

    ses_klasoru = (
        REEL_KLASOR / "sesler"
    )

    ses_klasoru.mkdir(
        parents=True,
        exist_ok=True
    )

    ses_yolu = (
        ses_klasoru
        / f"ses_{tarih}.mp3"
    )

    # Daha önce varsa tekrar üretme
    if ses_yolu.exists() and ses_yolu.stat().st_size > 0:

        print(
            f"✓ Ses dosyası zaten mevcut: {ses_yolu}"
        )

        return ses_yolu

    metin = reel_ses_metni_olustur(
        icerik
    )

    print()
    print(
        "Azure TTS ile Türkçe seslendirme oluşturuluyor..."
    )

    print(
        f"Ses: {AZURE_TTS_VOICE}"
    )

    print(
        f"Metin: {metin[:100]}..."
    )

    # ========================================================
    # Azure TTS API
    # ========================================================

    # Azure endpoint'i güvenli şekilde oluştur
    # .env içinde endpoint'in sonunda / olsa da olmasa da çalışır.
    azure_endpoint = AZURE_TTS_ENDPOINT.rstrip("/")

    if azure_endpoint.endswith("/cognitiveservices/v1"):
        url = azure_endpoint
    else:
        url = f"{azure_endpoint}/cognitiveservices/v1"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Type": "application/ssml+xml; charset=utf-8",
        "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
        "User-Agent": "AlmanyadaNasilYapilir-Reel-Automation",
    }

    # SSML içine giren metni XML açısından güvenli hale getir.
    # Örn. &, <, > karakterleri Azure'da 400 hatasına yol açabilir.
    guvenli_metin = html.escape(
        metin,
        quote=False
    )

    # SSML (Speech Synthesis Markup Language)
    ssml = f"""<?xml version="1.0" encoding="UTF-8"?>
<speak version="1.0"
       xmlns="http://www.w3.org/2001/10/synthesis"
       xml:lang="tr-TR">
    <voice name="{AZURE_TTS_VOICE}">
        {guvenli_metin}
    </voice>
</speak>"""

    print(
        f"Azure TTS endpoint: {url}"
    )
    print(
        f"Azure TTS voice: {AZURE_TTS_VOICE}"
    )
    print(
        "SSML hazır, Azure'a gönderiliyor..."
    )

    try:

        yanit = requests.post(
            url,
            headers=headers,
            data=ssml.encode("utf-8"),
            timeout=180
        )

    except requests.RequestException as hata:

        raise RuntimeError(
            f"Azure TTS bağlantı hatası: {hata}"
        )

    print(
        f"Azure HTTP durumu: {yanit.status_code}"
    )

    if not yanit.ok:

        print()
        print(
            "❌ AZURE TTS HATASI"
        )

        print(
            "Azure cevap gövdesi:"
        )
        print(
            yanit.text
        )

        print(
            "Azure response headers:"
        )
        print(
            dict(yanit.headers)
        )

        print(
            "Kullanılan TTS endpoint:"
        )
        print(
            url
        )

        print(
            "Kullanılan ses:"
        )
        print(
            AZURE_TTS_VOICE
        )

        yanit.raise_for_status()

    if not yanit.content:

        raise RuntimeError(
            "Azure başarılı cevap verdi ancak ses verisi boş."
        )

    # MP3 kaydet
    with open(
        ses_yolu,
        "wb"
    ) as dosya:

        dosya.write(
            yanit.content
        )

    # Kontrol
    if not ses_yolu.exists():

        raise FileNotFoundError(
            f"Ses dosyası oluşturulamadı: {ses_yolu}"
        )

    dosya_boyutu = (
        ses_yolu.stat().st_size
    )

    if dosya_boyutu == 0:

        raise RuntimeError(
            "Azure ses dosyası 0 byte oluştu."
        )

    print(
        f"✓ Türkçe ses oluşturuldu: {ses_yolu}"
    )

    print(
        f"✓ Ses boyutu: {dosya_boyutu} byte"
    )

    return ses_yolu


# ============================================================
# SES SÜRESİNİ ÖLÇ
# ============================================================

def ses_suresini_bul(ses_yolu):

    try:

        sonuc = subprocess.run(

            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(ses_yolu),
            ],

            capture_output=True,
            text=True,

            check=True
        )

    except FileNotFoundError:

        raise RuntimeError(
            "ffprobe bulunamadı. "
            "FFmpeg kurulumu kontrol edilmeli."
        )

    try:

        sure = float(
            sonuc.stdout.strip()
        )

    except ValueError:

        raise RuntimeError(
            f"Ses süresi okunamadı: "
            f"{sonuc.stdout}"
        )

    if sure <= 0:

        raise RuntimeError(
            "Ses süresi 0 veya geçersiz."
        )

    print(
        f"✓ Ses süresi: {sure:.2f} saniye"
    )

    return sure


# ============================================================
# VIDEO ÜRET
# ============================================================

def video_uret(
    gorsel_klasoru,
    icerik_dosyasi,
    ses_yolu
):

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
    # PNG dosyaları
    # --------------------------------------------------------

    png_dosyalari = sorted(
        gorsel_klasoru.glob("*.png")
    )

    if not png_dosyalari:

        raise FileNotFoundError(
            f"{gorsel_klasoru} klasöründe PNG bulunamadı."
        )

    print(
        f"{len(png_dosyalari)} PNG dosyası bulundu."
    )

    # --------------------------------------------------------
    # Ses süresi
    # --------------------------------------------------------

    ses_suresi = (
        ses_suresini_bul(
            ses_yolu
        )
    )

    # --------------------------------------------------------
    # Her görsel için süre
    # --------------------------------------------------------

    minimum_video_suresi = (
        len(png_dosyalari)
        * SLAYT_SURESI
    )

    video_suresi = max(
        ses_suresi,
        minimum_video_suresi
    )

    slayt_suresi = (
        video_suresi
        / len(png_dosyalari)
    )

    print(
        f"Video hedef süresi: {video_suresi:.2f} saniye"
    )

    print(
        f"Slayt başına süre: {slayt_suresi:.2f} saniye"
    )

    # --------------------------------------------------------
    # Video yolu
    # --------------------------------------------------------

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

            dosya = (
                png_yolu.resolve()
            )

            f.write(
                f"file '{dosya}'\n"
            )

            f.write(
                f"duration {slayt_suresi}\n"
            )

        # Son görseli tekrar ekle
        son_png = (
            png_dosyalari[-1].resolve()
        )

        f.write(
            f"file '{son_png}'\n"
        )

    # --------------------------------------------------------
    # FFmpeg kontrol
    # --------------------------------------------------------

    try:

        ffmpeg_kontrol = subprocess.run(

            [
                "ffmpeg",
                "-version"
            ],

            capture_output=True,
            text=True
        )

    except FileNotFoundError:

        raise RuntimeError(
            "FFmpeg bulunamadı."
        )

    if ffmpeg_kontrol.returncode != 0:

        raise RuntimeError(
            "FFmpeg çalıştırılamadı."
        )

    # --------------------------------------------------------
    # Video oluştur
    # --------------------------------------------------------

    print()
    print(
        "FFmpeg ile sesli Reel oluşturuluyor..."
    )

    ffmpeg_komut = [

        "ffmpeg",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(files_txt),

        "-i",
        str(ses_yolu),

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

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-af",
        "apad",

        "-shortest",

        "-movflags",
        "+faststart",

        "-y",

        str(reel_yolu)
    ]

    subprocess.run(
        ffmpeg_komut,
        check=True
    )

    # --------------------------------------------------------
    # Son kontrol
    # --------------------------------------------------------

    if not reel_yolu.exists():

        raise FileNotFoundError(
            f"FFmpeg video oluşturamadı: "
            f"{reel_yolu}"
        )

    video_boyutu = (
        reel_yolu.stat().st_size
    )

    if video_boyutu == 0:

        raise RuntimeError(
            "Video dosyası 0 byte oluştu."
        )

    print(
        f"✓ Sesli Reel hazır: {reel_yolu}"
    )

    print(
        f"✓ Video boyutu: {video_boyutu} byte"
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

        subprocess.run(
            [
                "git",
                "fetch",
                "origin"
            ],
            check=True
        )

        subprocess.run(
            [
                "git",
                "add",
                "reels/"
            ],
            check=True
        )

        commit_sonucu = subprocess.run(

            [
                "git",
                "commit",
                "-m",
                "reel: sesli video yayını"
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
            "✓ Sesli Reel GitHub'a gönderildi."
        )

    except subprocess.CalledProcessError as hata:

        raise RuntimeError(
            f"GitHub Reel yükleme işlemi başarısız: "
            f"{hata}"
        )

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

    # Reel açıklaması
    icerik_dosyasi = (
        son_icerik_dosyasi()
    )

    try:

        icerik = json.loads(
            icerik_dosyasi.read_text(
                encoding="utf-8"
            )
        )

        reel = icerik.get(
            "reel",
            {}
        )

        caption = reel.get(
            "baslik",
            "Reels video yayını 🎬"
        )

        hashtagler = icerik.get(
            "hashtagler",
            []
        )

        if hashtagler:

            caption += (
                "\n\n"
                + " ".join(
                    hashtagler
                )
            )

    except Exception:

        caption = (
            "Reels video yayını 🎬"
        )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media",

        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
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
# CONTAINER DURUMU
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

        if gecen_sure > MAKSIMUM_BEKLEME:

            raise TimeoutError(
                "Instagram videosu "
                f"{MAKSIMUM_BEKLEME} saniye içinde "
                "hazır olmadı."
            )

        durum = (
            container_durumunu_kontrol_et(
                container_id
            )
        )

        if durum == "FINISHED":

            print(
                "✓ Instagram videosu hazır."
            )

            return True

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

        if durum == "ERROR":

            raise RuntimeError(
                "Instagram Reel container "
                "işlenirken ERROR oluştu."
            )

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
    # GitHub
    # --------------------------------------------------------

    video_url = (
        reel_github_ye_gonder(
            video_yolu
        )
    )

    # --------------------------------------------------------
    # Container
    # --------------------------------------------------------

    container_id = (
        reel_container_olustur(
            video_url
        )
    )

    # --------------------------------------------------------
    # Hazır olmasını bekle
    # --------------------------------------------------------

    container_hazir_olmasini_bekle(
        container_id
    )

    # --------------------------------------------------------
    # Yayınla
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
        "✓ SESLİ REELS BAŞARIYLA YAYINLANDI!"
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
        "Instagram Sesli Reels Otomasyonu Başlıyor"
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
    # 4. Aynı içeriğin görsel klasörü
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
    # 5. AZURE TTS ses üret
    # --------------------------------------------------------

    ses_yolu = (
        ses_uret(
            icerik,
            tarih
        )
    )

    # --------------------------------------------------------
    # 6. Video üret
    # --------------------------------------------------------

    video_yolu = (
        video_uret(
            gorsel_klasoru,
            icerik_dosyasi,
            ses_yolu
        )
    )

    # --------------------------------------------------------
    # 7. Reel yayınla
    # --------------------------------------------------------

    reel_yayinla(
        video_yolu
    )

    print(
        "\n✓ Türkçe sesli Reel başarıyla yayınlandı!"
    )


# ============================================================
# PROGRAMI ÇALIŞTIR
# ============================================================

if __name__ == "__main__":
    main()
