import sqlite3
import os
import shutil

DB_PATH = "violations.db"
VIOLATIONS_DIR = "ihlal_kayitlari"

def clean_system():
    print("=== Sistem Temizliği Başlatılıyor ===")
    
    # 1. Veritabanını Sıfırla
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM violations")
            conn.commit()
            conn.close()
            print("[OK] Veritabanı (violations) temizlendi.")
        except Exception as e:
            print(f"[HATA] Veritabanı temizlenemedi: {e}")
    
    # 2. İhlal Kayıtlarını (Resim/Video) Sil
    if os.path.exists(VIOLATIONS_DIR):
        try:
            # Klasörün içindeki her şeyi sil ama klasörü tut
            for filename in os.listdir(VIOLATIONS_DIR):
                file_path = os.path.join(VIOLATIONS_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
            print(f"[OK] {VIOLATIONS_DIR} klasörü boşaltıldı.")
        except Exception as e:
            print(f"[HATA] Klasör temizlenemedi: {e}")

if __name__ == "__main__":
    clean_system()
