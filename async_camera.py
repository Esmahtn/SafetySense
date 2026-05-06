import cv2
import threading
import time

class SmartCamera:
    """
    Kamera kaynağına göre akıllı davranan VideoCapture okuyucusu.
    Eğer kaynak RTSP (IP Kamera) ise asenkron (Thread) okuma yapar ve lag/gecikmeyi önler.
    Eğer kaynak yerel bir video dosyası (.mp4, .avi) ise normal senkron okuma yapar.
    """
    def __init__(self, source, simulate_live=False):
        self.source = str(source)
        # Eğer simulate_live True ise .avi ve .mp4'leri de canlı gibi (RTSP gibi) simüle et
        self.is_live = self.source.startswith("rtsp://") or self.source.startswith("http://") or self.source.isdigit()
        
        if simulate_live:
            self.is_live = True
            
        self.cap = cv2.VideoCapture(source)
        
        self.ret = False
        self.frame = None
        self.running = False
        
        # Orijinal videonun FPS'ini alarak canlı yayın hızı belirle
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not self.fps or self.fps <= 0:
            self.fps = 25.0

    def start(self):
        """Threadi başlatır. set() işlemlerinden sonra çağrılmalıdır."""
        if self.is_live and self.cap.isOpened() and not self.running:
            self.ret, self.frame = self.cap.read()
            self.running = True
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
        return self

    def _update(self):
        """Thread içinde sürekli kare okur."""
        last_frame_time = time.time()
        
        while self.running:
            if not self.cap.isOpened():
                self.cap.open(self.source)
                time.sleep(2)
                continue

            ret, frame = self.cap.read()
            
            if not ret:
                # Bağlantı koptu veya video bitti
                self.ret = False
                # Video dosyasıysa başa sar (RTSP değilse)
                if not (self.source.startswith("rtsp://") or self.source.startswith("http://") or self.source.isdigit()):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.1)
                else:
                    # Canlı yayında kopma varsa release yap ve bekle
                    self.cap.release()
                    time.sleep(2)
                continue

            # Kare başarıyla okundu
            self.ret = True
            self.frame = frame
            last_frame_time = time.time()
            
            # ⭐ Watchdog: Eğer canlı yayınsa ve okuma çok hızlıysa 
            # (RTSP zaten kendi hızında gönderir, sleep'e gerek yok)
            # Ancak CPU'yu %100 bitirmemek için çok küçük bir bekleme:
            if self.source.startswith("rtsp://") or self.source.startswith("http://"):
                time.sleep(0.001) 
            else:
                # Video dosyası simülasyonu ise FPS'i koru
                delay = 1.0 / self.fps
                time.sleep(delay)

            # ⭐ Bağlantı Sağlık Kontrolü: 5 saniye boyunca yeni kare gelmezse
            if time.time() - last_frame_time > 5.0:
                print(f"[!] Kamera Zaman Aşımı: {self.source}")
                self.ret = False
                self.cap.release()

    def read(self):
        if self.is_live:
            # Canlı yayınsa, her zaman en son anlık kareyi (lag olmadan) döndür
            return self.ret, self.frame
        else:
            # Video dosyasıysa, bittiğinde otomatik başa sar
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            return ret, frame

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.running = False
        if self.is_live and hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        self.cap.release()

    def get(self, propId):
        return self.cap.get(propId)

    def set(self, propId, value):
        return self.cap.set(propId, value)
