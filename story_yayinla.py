import os
import subprocess
import time
from pathlib import Path

import requests
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

STORY_KLASOR = Path("stories")


# ============================================================
# EN SON STORY DOSYASINI BUL
# ============================================================

def son_story_dosyasi():

    story_dosyalari = sorted(
        STORY_KLASOR.glob("*/story.png")
    )

    if not story_dosyalari:

        raise FileNotFoundError(
            "stories/ klasöründe story.png bulunamadı. "
            "Önce story_uret.py çalıştır."
        )

    return story_dosyalari[-1]


# ============================================================
# STORY'Yİ GITHUB'A GÖNDER
# ============================================================

def story_githuba_gonder(story_yolu):

    print("\nStory GitHub'a gönderiliyor...")

    try:

        # Güncel GitHub bilgilerini al
        subprocess.run(
            ["git", "fetch", "origin"],
            check=True
        )

        # Story dosyasını ekle
        subprocess.run(
            ["git", "add", str(story_yolu)],
            check=True
        )

        # Commit
        commit = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "story: otomatik story yayini"
            ],
            capture_output=True,
            text=True
        )

        # Commit yapılacak değişiklik yoksa sorun değil
        if commit.returncode != 0:

            print(
                "Yeni commit oluşturulmadı. "
                "Dosya zaten commit edilmiş olabilir."
            )

        else:

            print(
                "✓ Story commit edildi."
            )

        # GitHub'a gönder
        subprocess.run(
            ["git", "push"],
            check=True
        )

        print(
            "✓ Story GitHub'a başarıyla gönderildi."
        )

    except subprocess.CalledProcessError as e:

        raise RuntimeError(
            f"GitHub işlemi başarısız oldu: {e}"
        )

    # --------------------------------------------------------
    # Raw GitHub URL
    # --------------------------------------------------------

    # Windows Path -> /
    relative_path = story_yolu.as_posix()

    raw_url = (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USERNAME}/"
        f"{GITHUB_REPO}/"
        f"main/"
        f"{relative_path}"
    )

    print(
        f"\nStory Raw URL:\n{raw_url}"
    )

    return raw_url


# ============================================================
# STORY CONTAINER OLUŞTUR
# ============================================================

def story_container_olustur(image_url):

    print(
        "\nInstagram Story container oluşturuluyor..."
    )

    yanit = requests.post(

        f"{API_TEMEL}/{IG_USER_ID}/media",

        data={
            "media_type": "STORIES",
            "image_url": image_url,
            "access_token": ACCESS_TOKEN,
        },

        timeout=60
    )

    if not yanit.ok:

        print(
            "HATA DETAYI:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    container_id = yanit.json()["id"]

    print(
        f"✓ Story container oluşturuldu: "
        f"{container_id}"
    )

    return container_id


# ============================================================
# CONTAINER DURUMUNU KONTROL ET
# ============================================================

def container_durumunu_kontrol_et(container_id):

    print(
        "\nStory'nin hazırlanması bekleniyor..."
    )

    maksimum_deneme = 24

    for deneme in range(1, maksimum_deneme + 1):

        yanit = requests.get(

            f"{API_TEMEL}/{container_id}",

            params={
                "fields": "status_code,status",
                "access_token": ACCESS_TOKEN,
            },

            timeout=60
        )

        if not yanit.ok:

            print(
                "STATUS HATASI:"
            )

            print(
                yanit.text
            )

            yanit.raise_for_status()

        veri = yanit.json()

        status_code = veri.get(
            "status_code"
        )

        status = veri.get(
            "status"
        )

        print(
            f"Deneme {deneme}/{maksimum_deneme} "
            f"→ status_code={status_code}, "
            f"status={status}"
        )

        # Hazır
        if status_code == "FINISHED":

            print(
                "✓ Story yayınlanmaya hazır."
            )

            return True

        # Hata
        if status_code in [
            "ERROR",
            "EXPIRED"
        ]:

            raise RuntimeError(
                f"Instagram Story container hatası: "
                f"{veri}"
            )

        # Henüz hazırlanıyor
        time.sleep(5)

    raise TimeoutError(
        "Story container zamanında hazır olmadı."
    )


# ============================================================
# STORY'Yİ YAYINLA
# ============================================================

def story_yayinla(container_id):

    print(
        "\nInstagram Story yayınlanıyor..."
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
            "YAYINLAMA HATASI:"
        )

        print(
            yanit.text
        )

        yanit.raise_for_status()

    veri = yanit.json()

    print(
        "\n========================================"
    )

    print(
        "✓ INSTAGRAM STORY YAYINLANDI!"
    )

    print(
        "========================================"
    )

    print(
        f"Post ID: {veri.get('id')}"
    )

    return veri


# ============================================================
# ANA İŞLEM
# ============================================================

def main():

    print(
        "========================================"
    )

    print(
        "INSTAGRAM STORY YAYINLAMA"
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # 1. Story dosyasını bul
    # --------------------------------------------------------

    story_yolu = son_story_dosyasi()

    print(
        f"\nStory dosyası:"
    )

    print(
        story_yolu
    )

    # --------------------------------------------------------
    # 2. GitHub'a gönder
    # --------------------------------------------------------

    image_url = story_githuba_gonder(
        story_yolu
    )

    # --------------------------------------------------------
    # 3. Instagram container
    # --------------------------------------------------------

    container_id = story_container_olustur(
        image_url
    )

    # --------------------------------------------------------
    # 4. Hazır olmasını bekle
    # --------------------------------------------------------

    container_durumunu_kontrol_et(
        container_id
    )

    # --------------------------------------------------------
    # 5. Yayınla
    # --------------------------------------------------------

    story_yayinla(
        container_id
    )

    print(
        "\n✓ Story işlemi tamamlandı."
    )


# ============================================================
# ÇALIŞTIR
# ============================================================

if __name__ == "__main__":

    main()