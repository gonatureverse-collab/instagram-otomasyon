import os
import json
import time
import subprocess
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPO = os.environ["GITHUB_REPO"]

API_SURUM = "v21.0"
API_TEMEL = f"https://graph.instagram.com/{API_SURUM}"

CIKTI_KLASOR = Path("cikti")
GORSEL_KLASOR = Path("gorseller")


def son_icerik_dosyasi():
    dosyalar = sorted(CIKTI_KLASOR.glob("icerik_*.json"))
    if not dosyalar:
        raise FileNotFoundError("cikti/ klasöründe içerik dosyası bulunamadı.")
    return dosyalar[-1]


def gorselleri_githuba_gonder(tarih):
    print("Görseller GitHub'a gönderiliyor...")
    subprocess.run(["git", "add", f"gorseller/{tarih}"], check=True)

    # Değişiklik yoksa (görseller zaten push edilmişse) commit'i atla
    durum = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], capture_output=True
    )
    if durum.returncode == 0:
        print("Görseller zaten GitHub'da, yeni commit gerekmiyor.")
        return

    subprocess.run(["git", "commit", "-m", f"gorseller: {tarih}"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("Görseller GitHub'a gönderildi.")


def raw_url(tarih, dosya_adi):
    return (
        f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/"
        f"main/gorseller/{tarih}/{dosya_adi}"
    )


def container_olustur(image_url):
    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media",
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": ACCESS_TOKEN,
        },
    )
    if not yanit.ok:
        print("HATA DETAYI:", yanit.text)
    yanit.raise_for_status()
    return yanit.json()["id"]


def carousel_container_olustur(cocuk_id_listesi, caption):
    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(cocuk_id_listesi),
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },
    )
    yanit.raise_for_status()
    return yanit.json()["id"]


def container_durumu_bekle(container_id, zaman_asimi=60):
    baslangic = time.time()
    while time.time() - baslangic < zaman_asimi:
        yanit = requests.get(
            f"{API_TEMEL}/{container_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN},
        )
        yanit.raise_for_status()
        durum = yanit.json().get("status_code")
        if durum == "FINISHED":
            return True
        if durum == "ERROR":
            raise RuntimeError(f"Container hata verdi: {container_id}")
        time.sleep(3)
    raise TimeoutError(f"Container zaman aşımına uğradı: {container_id}")


def yayinla(container_id):
    yanit = requests.post(
        f"{API_TEMEL}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN},
    )
    yanit.raise_for_status()
    return yanit.json()


def main():
    icerik_dosyasi = son_icerik_dosyasi()
    icerik = json.loads(icerik_dosyasi.read_text(encoding="utf-8"))
    tarih = icerik["tarih"]

    hedef_klasor = GORSEL_KLASOR / tarih
    if not hedef_klasor.exists():
        raise FileNotFoundError(f"{hedef_klasor} bulunamadı. Önce gorsel_uret.py çalıştır.")

    gorselleri_githuba_gonder(tarih)

    # GitHub CDN'in dosyayı yayına almasını bekle
    print("GitHub CDN güncellemesi için 15 saniye bekleniyor...")
    time.sleep(15)

    dosyalar = sorted(hedef_klasor.glob("*.png"))
    print(f"{len(dosyalar)} görsel için container oluşturuluyor...")

    cocuk_id_listesi = []
    for dosya in dosyalar:
        url = raw_url(tarih, dosya.name)
        container_id = container_olustur(url)
        cocuk_id_listesi.append(container_id)
        print(f"  {dosya.name} -> container oluşturuldu")

    caption = icerik["caption"] + "\n\n" + " ".join(icerik["hashtagler"])

    print("Carousel container oluşturuluyor...")
    carousel_id = carousel_container_olustur(cocuk_id_listesi, caption)

    print("Container hazırlanması bekleniyor...")
    container_durumu_bekle(carousel_id)

    print("Yayınlanıyor...")
    sonuc = yayinla(carousel_id)

    print("Yayınlandı! Post ID:", sonuc.get("id"))


if __name__ == "__main__":
    main()