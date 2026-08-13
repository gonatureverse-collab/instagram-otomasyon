import os
import json
import random
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic


# ============================================================
# AYARLAR
# ============================================================

load_dotenv()

client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"]
)

KONULAR_DOSYA = Path("konular.json")
KULLANILAN_DOSYA = Path("kullanilan_konular.json")
CIKTI_KLASOR = Path("cikti")


# ============================================================
# KONU SEÇ
# ============================================================

def konu_sec():

    konular = json.loads(
        KONULAR_DOSYA.read_text(
            encoding="utf-8"
        )
    )

    if KULLANILAN_DOSYA.exists():

        kullanilan = json.loads(
            KULLANILAN_DOSYA.read_text(
                encoding="utf-8"
            )
        )

    else:

        kullanilan = []

    kalan = [
        konu for konu in konular
        if konu not in kullanilan
    ]

    if not kalan:

        print(
            "Tüm konular kullanıldı. "
            "Konu listesi yeniden başlatılıyor."
        )

        kalan = konular
        kullanilan = []

    secilen = random.choice(kalan)

    kullanilan.append(secilen)

    KULLANILAN_DOSYA.write_text(
        json.dumps(
            kullanilan,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return secilen


# ============================================================
# AI İÇERİK ÜRET
# ============================================================

def icerik_uret(konu):

    prompt = f"""
Sen "Almanya'da Nasıl Yapılır" adlı Instagram hesabı için
Türkçe içerik üreten profesyonel bir içerik asistanısın.

KONU:
"{konu}"

Bu konu hakkında aynı anda:

1. Instagram Carousel
2. Instagram Reel
3. Instagram Story
4. Instagram caption
5. Hashtagler

oluştur.

Amaç:
Almanya'da yaşayan veya Almanya'ya yeni gelen
Türkçe konuşan insanların işine yarayan,
sade, pratik ve güvenilir içerikler hazırlamak.

============================================================
ÇOK ÖNEMLİ: BİLGİ DOĞRULUĞU
============================================================

- Bilmediğin bilgiyi kesin gerçek olarak yazma.
- Rakam uydurma.
- Para miktarı uydurma.
- Başvuru ücreti uydurma.
- Tarih veya son başvuru tarihi uydurma.
- Yasal şartları uydurma.
- Mahkeme, oturum, vatandaşlık, vergi, sosyal yardım,
  burs veya resmi başvurular hakkında emin olmadığın
  bilgileri kesin ifadelerle verme.
- Bir bilgi değişebilir nitelikteyse bunu açıkça belirt.
- "Güncel bilgiyi ilgili resmi kurumdan kontrol edin"
  şeklinde uyarı ekleyebilirsin.
- Farklı resmi kurumları veya başvuru sistemlerini birbirine
  karıştırma.
- Resmi bir internet sitesi veya başvuru sistemi hakkında
  emin değilsen URL veya sistem adı uydurma.
- "Kesinlikle", "garanti", "herkes alabilir" gibi ifadeler
  kullanma.
- İçerik faydalı fakat temkinli olmalı.

============================================================
CAROUSEL
============================================================

1 kapak + 5 içerik slaytı oluştur.

Kurallar:

- Kapak başlığı kısa ve dikkat çekici olsun.
- Her içerik slaytı maksimum 2 kısa cümle olsun.
- Sade Türkçe kullan.
- Pratik bilgi ver.
- Her slayt için TEK emoji seç.

============================================================
REEL
============================================================

15-20 saniyelik Reel için içerik oluştur.

- 5-6 kısa sahne.
- İlk sahne güçlü bir dikkat çekici giriş olsun.
- Carousel'in aynısını kelimesi kelimesine tekrar etme.
- Reel daha hızlı ve konuşma diline yakın olsun.
- Sonunda kısa CTA olsun.
- Her sahne kısa olsun.

============================================================
STORY
============================================================

Tek bir Story oluştur.

- Kısa ve etkileşimli olsun.
- Soru içersin.
- 2 anket seçeneği olsun.

============================================================
CAPTION
============================================================

- 2-4 kısa cümle.
- Samimi ve bilgilendirici.
- Sonunda kısa CTA.
- Kullanıcıyı kaydetmeye, paylaşmaya veya yorum yapmaya teşvik et.

============================================================
HASHTAG
============================================================

Maksimum 10 tane alakalı hashtag üret.

============================================================
JSON
============================================================

SADECE aşağıdaki JSON formatında cevap ver.

JSON dışında hiçbir açıklama yazma.

{{
  "baslik": "Carousel kapak başlığı",

  "kapak_emoji": "🇩🇪",

  "slaytlar": [
    "Slayt 1 metni",
    "Slayt 2 metni",
    "Slayt 3 metni",
    "Slayt 4 metni",
    "Slayt 5 metni"
  ],

  "emojiler": [
    "📄",
    "🏠",
    "📅",
    "💶",
    "✅"
  ],

  "reel": {{
    "baslik": "Reel başlığı",
    "sahneler": [
      "Sahne 1",
      "Sahne 2",
      "Sahne 3",
      "Sahne 4",
      "Sahne 5",
      "Sahne 6"
    ],
    "cta": "Reel CTA metni"
  }},

  "story": {{
    "baslik": "Story başlığı",
    "metin": "Story soru metni",
    "anket": [
      "Seçenek 1",
      "Seçenek 2"
    ]
  }},

  "caption": "Instagram açıklama metni",

  "hashtagler": [
    "#almanya",
    "#almanyadayasam",
    "#almanyadanasilyapilir"
  ]
}}
"""

    print(
        "Claude ile Carousel + Reel + Story içeriği oluşturuluyor..."
    )

    yanit = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2500,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    metin = yanit.content[0].text.strip()

    # ========================================================
    # MARKDOWN JSON TEMİZLE
    # ========================================================

    if metin.startswith("```"):

        parcalar = metin.split("```")

        if len(parcalar) >= 2:
            metin = parcalar[1]

            if metin.startswith("json"):
                metin = metin[4:]

    metin = metin.strip()

    # ========================================================
    # JSON OKU
    # ========================================================

    try:

        icerik = json.loads(metin)

    except json.JSONDecodeError as hata:

        print("AI JSON üretmedi veya JSON bozuk.")

        print()
        print("AI CEVABI:")
        print(metin)

        raise hata

    # ========================================================
    # ALAN KONTROLÜ
    # ========================================================

    gerekli_alanlar = [
        "baslik",
        "kapak_emoji",
        "slaytlar",
        "emojiler",
        "reel",
        "story",
        "caption",
        "hashtagler"
    ]

    for alan in gerekli_alanlar:

        if alan not in icerik:

            raise ValueError(
                f"AI çıktısında '{alan}' alanı bulunamadı."
            )

    # Reel kontrol
    if "sahneler" not in icerik["reel"]:
        raise ValueError(
            "Reel içeriğinde 'sahneler' bulunamadı."
        )

    # Story kontrol
    if "anket" not in icerik["story"]:
        raise ValueError(
            "Story içeriğinde 'anket' bulunamadı."
        )

    if len(icerik["story"]["anket"]) < 2:
        raise ValueError(
            "Story anketinde en az 2 seçenek gerekli."
        )

    return icerik


# ============================================================
# ANA PROGRAM
# ============================================================

def main():

    CIKTI_KLASOR.mkdir(
        exist_ok=True
    )

    print()
    print("=" * 60)
    print("ALMANYA'DA NASIL YAPILIR?")
    print("GÜNLÜK İÇERİK ÜRETİMİ")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Konu seç
    # --------------------------------------------------------

    konu = konu_sec()

    print(
        f"Seçilen konu: {konu}"
    )

    # --------------------------------------------------------
    # İçerik üret
    # --------------------------------------------------------

    icerik = icerik_uret(
        konu
    )

    # --------------------------------------------------------
    # Meta bilgiler
    # --------------------------------------------------------

    icerik["konu"] = konu

    icerik["tarih"] = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    # --------------------------------------------------------
    # JSON kaydet
    # --------------------------------------------------------

    dosya_adi = (
        CIKTI_KLASOR
        / f"icerik_{icerik['tarih']}.json"
    )

    dosya_adi.write_text(
        json.dumps(
            icerik,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # Sonuç
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("✓ İÇERİK BAŞARIYLA ÜRETİLDİ")
    print("=" * 60)
    print()

    print(
        f"JSON: {dosya_adi}"
    )

    print()
    print("Üretilen içerikler:")
    print("✓ 1 Carousel")
    print("✓ 1 Reel")
    print("✓ 1 Story")

    print()
    print(
        json.dumps(
            icerik,
            ensure_ascii=False,
            indent=2
        )
    )


# ============================================================
# ÇALIŞTIR
# ============================================================

if __name__ == "__main__":
    main()
