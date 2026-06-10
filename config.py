# =========================================================
# SİSTEM YAPILANDIRMA AYARLARI
# =========================================================

# ÇALIŞMA MODU: "DEMO" (Video dosyaları) veya "LIVE" (Canlı Kamera)
MODE = "LIVE" 

# KAMERA KAYNAKLARI (DAHUA / HIKVISION RTSP ŞABLONU)
# ---------------------------------------------------------
# Dahua: "rtsp://admin:sifre123@IP_ADRESI:554/cam/realmonitor?channel=1&subtype=0"
# Hikvision: "rtsp://admin:sifre123@IP_ADRESI:554/Streaming/Channels/101"

SOURCES = {
    "ANA_KORIDOR": {
        "LIVE": "rtsp://admin:admin1234@192.168.12.129:554/cam/realmonitor?channel=1&subtype=0",
        "DEMO": r"c:\Users\bplas\Desktop\video\192.168.12.5_ch49_20260422112301_20260422113058_ters_yön.avi"
    },
    "GUVENSIZ_BOLGE": {
        "LIVE": "rtsp://admin:admin1234@192.168.12.125:554/cam/realmonitor?channel=1&subtype=0",
        "DEMO": r"c:\Users\bplas\Desktop\video\192.168.12.5_ch45_20260422112303_20260422113058_güvensiz.avi"
    },
    "HIZ_KORIDORU": {
        "LIVE": "rtsp://admin:admin1234@192.168.12.130:554/cam/realmonitor?channel=1&subtype=0",
        "DEMO": r"c:\Users\bplas\Desktop\video\192.168.12.5_ch50_20260422112304_20260422113058_hız.avi"
    }
}

def get_source(cam_key):
    """Mevcut moda göre kamera kaynağını döndürür."""
    if cam_key in SOURCES:
        return SOURCES[cam_key][MODE]
    return None
