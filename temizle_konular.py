import re
import json
from pathlib import Path

HAM_DOSYA = Path("ham_konular.txt")
CIKTI_DOSYA = Path("konular.json")


def main():
    metin = HAM_DOSYA.read_text(encoding="utf-8")

    # Çift tırnak içindeki her metni yakala (satır sonundaki virgül olsun olmasın)
    konular = re.findall(r'"([^"]+)"', metin)

    # Tekrarlananları temizle, sırayı koru
    gorulen = set()
    temiz_konular = []
    for k in konular:
        k = k.strip()
        if k and k not in gorulen:
            gorulen.add(k)
            temiz_konular.append(k)

    CIKTI_DOSYA.write_text(
        json.dumps(temiz_konular, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Toplam {len(temiz_konular)} benzersiz konu bulundu.")
    print(f"Kaydedildi: {CIKTI_DOSYA}")


if __name__ == "__main__":
    main()