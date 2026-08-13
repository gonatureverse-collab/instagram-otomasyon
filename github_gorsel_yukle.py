import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GORSEL_KLASOR = Path("gorseller")


def githuba_gonder():

    print()
    print("=" * 60)
    print("GÖRSELLER GITHUB'A GÖNDERİLİYOR")
    print("=" * 60)

    # Git durumunu kontrol et
    subprocess.run(
        ["git", "status"],
        check=True
    )

    # Gorselleri ekle
    print()
    print("Görseller Git'e ekleniyor...")

    subprocess.run(
        ["git", "add", "gorseller/"],
        check=True
    )

    # Commit
    print()
    print("Commit oluşturuluyor...")

    sonuc = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "otomasyon: yeni carousel gorselleri"
        ],
        capture_output=True,
        text=True
    )

    # Değişiklik yoksa hata verme
    if sonuc.returncode != 0:

        if "nothing to commit" in sonuc.stdout.lower() or \
           "nothing to commit" in sonuc.stderr.lower():

            print()
            print("ℹ Yeni görsel commit edilecek değişiklik yok.")

        else:

            print(sonuc.stdout)
            print(sonuc.stderr)

            raise RuntimeError(
                "Git commit işlemi başarısız."
            )

    else:

        print()
        print("✓ Commit oluşturuldu.")


    # GitHub'a gönder
    print()
    print("GitHub'a gönderiliyor...")

    subprocess.run(
        ["git", "push", "origin", "main"],
        check=True
    )

    print()
    print("=" * 60)
    print("✓ GÖRSELLER GITHUB'A GÖNDERİLDİ")
    print("=" * 60)


if __name__ == "__main__":

    githuba_gonder()