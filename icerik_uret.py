import os
import json
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

KONULAR_DOSYA = Path("konular.json")
KULLANILAN_DOSYA = Path("kullanilan_konular.json")
CIKTI_KLASOR = Path("cikti")


def konu_sec():
    konular = json.loads(KONULAR_DOSYA.read_text(encoding="utf-8"))

    if KULLANILAN_DOSYA.exists():
        kullanilan = json.loads(KULLANILAN_DOSYA.read_text(encoding="utf-8"))
    else:
        kullanilan = []

    kalan = [k for k in konular if k not in kullanilan]

    if not kalan:
        print("Tüm konular kullanıldı, listeye yeni konu eklemen gerekiyor.")
        kalan = konular
        kullanilan = []

    secilen = random.choice(kalan)
    kullanilan.append(secilen)
    KULLANILAN_DOSYA.write_text(
        json.dumps(kullanilan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return secilen


def icerik_uret(konu):
    prompt = f"""Sen Almanya'da yaşam konusunda "nasıl yapılır" tarzı bir Instagram
hesabı için içerik üreten bir asistansın. Konu: "{konu}"

Bir Instagram carousel postu için içerik üret. Şu kurallara uy:
- Sade, anlaşılır, samimi bir dil kullan
- Her slayt kısa olsun (maksimum 2 cümle)
- Pratik ve doğru bilgi ver

Her slayt için o slaytın konusunu temsil eden TEK bir emoji seç (örn. ev konusu için 🏠, evrak için 📄, para için 💶).

Sadece aşağıdaki JSON formatında cevap ver, başka hiçbir şey yazma:

{{
  "baslik": "carousel'in kapak başlığı, kısa ve dikkat çekici",
  "kapak_emoji": "başlığı temsil eden tek emoji",
  "slaytlar": [
    "slayt 1 metni",
    "slayt 2 metni",
    "slayt 3 metni",
    "slayt 4 metni",
    "slayt 5 metni"
  ],
  "emojiler": ["slayt 1 emoji", "slayt 2 emoji", "slayt 3 emoji", "slayt 4 emoji", "slayt 5 emoji"],
  "caption": "Instagram açıklama metni, 2-3 cümle, samimi ton",
  "hashtagler": ["#almanya", "#almanyadayasam", "..."]
}}"""

    yanit = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    metin = yanit.content[0].text.strip()

    # Model bazen kod bloğu içine sarabilir, temizleyelim
    if metin.startswith("```"):
        metin = metin.split("```")[1]
        if metin.startswith("json"):
            metin = metin[4:]

    return json.loads(metin.strip())


def main():
    CIKTI_KLASOR.mkdir(exist_ok=True)

    konu = konu_sec()
    print(f"Seçilen konu: {konu}")

    icerik = icerik_uret(konu)
    icerik["konu"] = konu
    icerik["tarih"] = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    dosya_adi = CIKTI_KLASOR / f"icerik_{icerik['tarih']}.json"
    dosya_adi.write_text(
        json.dumps(icerik, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"İçerik üretildi: {dosya_adi}")
    print(json.dumps(icerik, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()