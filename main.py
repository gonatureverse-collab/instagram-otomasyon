import subprocess
import sys


def calistir(script_adi):

    print()
    print("=" * 60)
    print(f"ÇALIŞTIRILIYOR: {script_adi}")
    print("=" * 60)
    print()

    sonuc = subprocess.run(
        [sys.executable, script_adi]
    )

    if sonuc.returncode != 0:

        print()
        print("=" * 60)
        print(f"HATA: {script_adi} başarısız oldu!")
        print("=" * 60)
        print()

        sys.exit(1)

    print()
    print(f"✓ {script_adi} başarıyla tamamlandı.")


def main():

    print()
    print("=" * 60)
    print("ALMANYA'DA NASIL YAPILIR?")
    print("GÜNLÜK INSTAGRAM OTOMASYONU")
    print("=" * 60)
    print()

    # ========================================================
    # 1. YENİ İÇERİK ÜRET
    # ========================================================

    calistir("icerik_uret.py")


    # ========================================================
    # 2. CAROUSEL GÖRSELLERİNİ ÜRET
    # ========================================================

    calistir("gorsel_uret.py")


    # ========================================================
    # 3. CAROUSEL GÖRSELLERİNİ GITHUB'A GÖNDER
    # ========================================================

    calistir("github_gorsel_yukle.py")


    # ========================================================
    # 4. REEL ÜRET VE INSTAGRAM'A YAYINLA
    # ========================================================

    calistir("reel_uret.py")


    # ========================================================
    # 5. STORY GÖRSELİNİ ÜRET
    # ========================================================

    calistir("story_uret.py")


    # ========================================================
    # 6. STORY'Yİ INSTAGRAM'A YAYINLA
    # ========================================================

    calistir("story_yayinla.py")


    # ========================================================
    # 7. CAROUSEL'İ INSTAGRAM'A YAYINLA
    # ========================================================

    calistir("carousel_yayinla.py")


    # ========================================================
    # TAMAMLANDI
    # ========================================================

    print()
    print("=" * 60)
    print("✓✓✓ TÜM INSTAGRAM İÇERİKLERİ BAŞARIYLA YAYINLANDI ✓✓✓")
    print("=" * 60)
    print()

    print("✓ 1 Carousel")
    print("✓ 1 Reel")
    print("✓ 1 Story")
    print()

    print("Günlük otomasyon tamamlandı.")
    print()


if __name__ == "__main__":
    main()
