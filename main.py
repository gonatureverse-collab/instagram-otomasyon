import subprocess
import sys


def calistir(script_adi):
    print(f"\n{'='*50}")
    print(f"ÇALIŞTIRILIYOR: {script_adi}")
    print(f"{'='*50}\n")
    sonuc = subprocess.run([sys.executable, script_adi])
    if sonuc.returncode != 0:
        print(f"\nHATA: {script_adi} başarısız oldu, işlem durduruldu.")
        sys.exit(1)


def main():
    calistir("icerik_uret.py")
    calistir("gorsel_uret.py")
    calistir("yayinla.py")
    print("\nTüm adımlar tamamlandı, post yayınlandı!")


if __name__ == "__main__":
    main()