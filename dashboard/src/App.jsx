import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Camera, Clock, BarChart3, RefreshCcw, Search, ChevronRight } from 'lucide-react';

const API_BASE = "http://localhost:5000";

function App() {
  const [stats, setStats] = useState({ total: 0, history: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [newAlert, setNewAlert] = useState(null);
  const [selectedDate, setSelectedDate] = useState(""); // Tarih filtresi için state
  const [activeTab, setActiveTab] = useState("ters_yon"); // Sekme yönetimi
  const [selectedIds, setSelectedIds] = useState([]); // Çoklu silme için
  
  // Modal detayları için state
  const [selectedItem, setSelectedItem] = useState(null);
  const [showSS, setShowSS] = useState(false);
  const [fullImage, setFullImage] = useState(null); // Full screen resim için

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/stats`);
      setStats(res.data);
      setError(false);
    } catch (err) {
      console.error("Veri çekilemedi:", err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Bu ihlali onaylayıp listeden silmek istediğinize emin misiniz?")) return;
    try {
      await axios.delete(`${API_BASE}/delete_violation/${id}`);
      setSelectedItem(null);
      fetchStats(); // Listeyi yenile
    } catch (err) {
      console.error("İhlal silinemedi:", err);
      alert("Silme işlemi sırasında bir hata oluştu.");
    }
  };

  const handleBulkDelete = async () => {
    if (!window.confirm(`${selectedIds.length} adet ihlali silmek istediğinize emin misiniz?`)) return;
    try {
      await axios.post(`${API_BASE}/delete_multiple`, { ids: selectedIds });
      setSelectedIds([]);
      fetchStats();
    } catch (err) {
      alert("Toplu silme hatası.");
    }
  };

  useEffect(() => {
    fetchStats();
    
    // Server-Sent Events (SSE) Dinleyicisi
    const eventSource = new EventSource(`${API_BASE}/stream`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("Yeni İhlal Bildirimi Geldi!", data);
      
      // Ekranda popup (toast) göstermek için state'i güncelle
      setNewAlert(data);
      
      // Veritabanından en güncel veriyi tekrar çek
      fetchStats();
      
      // Uyarıyı 5 saniye sonra gizle
      setTimeout(() => setNewAlert(null), 5000);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0f1115] text-white p-4 md:p-8 font-sans">
      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4 border-b border-white/10 pb-6">
        <div className="flex items-center gap-4">
          <div className="bg-red-500 p-3 rounded-xl shadow-[0_0_20px_rgba(239,68,68,0.3)]">
            <ShieldAlert size={32} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">FABRİKA GÜVENLİK SİSTEMİ</h1>
            <p className="text-gray-400 text-sm flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              Canlı Takip Aktif
            </p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="bg-[#1a1d23] border border-white/5 px-6 py-3 rounded-2xl flex items-center gap-4">
            <BarChart3 className="text-red-400" />
            <div>
              <p className="text-xs text-gray-500 font-medium">TOPLAM İHLAL</p>
              <p className="text-2xl font-bold text-red-500">{stats.total}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Canlı Uyarı (Toast Notification) */}
      {newAlert && (
        <div className="fixed top-8 right-8 z-50 bg-red-600 border-l-4 border-white text-white p-4 rounded-lg shadow-2xl animate-bounce">
          <div className="flex items-center gap-3">
            <ShieldAlert size={28} />
            <div>
              <h4 className="font-bold text-lg">YENİ İHLAL TESPİTİ!</h4>
              <p className="text-sm opacity-90">{newAlert.cam_name} bölgesinde {newAlert.type} (Araç #{newAlert.id})</p>
            </div>
          </div>
        </div>
      )}


      {/* Ana İçerik */}
      {error ? (
        <div className="bg-red-500/10 border border-red-500/20 p-8 rounded-3xl text-center">
          <RefreshCcw className="mx-auto mb-4 animate-spin text-red-500" />
          <p className="text-lg font-medium">Backend Sunucusuna Bağlanılamıyor...</p>
          <p className="text-gray-500 text-sm">server.py'ın çalıştığından emin olun.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {/* Sekme Menüsü (Tabs) */}
          <div className="flex gap-4 mb-2 border-b border-white/10 pb-4">
            <button 
              onClick={() => setActiveTab('ters_yon')} 
              className={`px-6 py-2 rounded-xl font-bold transition-all flex items-center gap-2 ${activeTab === 'ters_yon' ? 'bg-red-600 text-white shadow-lg shadow-red-600/20' : 'bg-[#1a1d23] text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
              🚗 Ters Yön Takibi
            </button>
            <button 
              onClick={() => setActiveTab('yaya')} 
              className={`px-6 py-2 rounded-xl font-bold transition-all flex items-center gap-2 ${activeTab === 'yaya' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'bg-[#1a1d23] text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
              🚶 Yaya İhlal Takibi
            </button>
            <button 
              onClick={() => setActiveTab('hiz')} 
              className={`px-6 py-2 rounded-xl font-bold transition-all flex items-center gap-2 ${activeTab === 'hiz' ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'bg-[#1a1d23] text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
              ⚡ Hız İhlal Takibi
            </button>
          </div>

          {/* Canlı Kamera Akışları */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-4">
            <div className="bg-[#1a1d23] border border-white/5 rounded-3xl overflow-hidden p-5 shadow-lg">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                {activeTab === 'ters_yon' ? 'Ana Koridor (Ters Yön) Canlı' : 
                 activeTab === 'yaya' ? 'Güvensiz Bölge (Yaya) Canlı' : 'Hız Koridoru Canlı'}
              </h2>
              <div className="relative aspect-video bg-black rounded-2xl overflow-hidden border border-white/5">
                {activeTab === 'ters_yon' && (
                  <img src={`${API_BASE}/vehicle_stream`} className="w-full h-full object-contain" alt="Ters Yön Canlı" />
                )}
                {activeTab === 'yaya' && (
                  <img src={`${API_BASE}/pedestrian_stream`} className="w-full h-full object-contain" alt="Yaya Tespiti Canlı" />
                )}
                {activeTab === 'hiz' && (
                  <img src={`${API_BASE}/speed_stream`} className="w-full h-full object-contain" alt="Hız Takibi Canlı" />
                )}
              </div>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center px-2 gap-4">
            <div className="flex items-center gap-6">
              <h2 className="text-xl font-bold flex items-center gap-3">
                <Camera size={24} className={activeTab === 'ters_yon' ? 'text-red-400' : 'text-orange-400'} />
                {activeTab === 'ters_yon' ? 'Ters Yön' : 'Yaya'} İhlal Listesi
              </h2>
              {selectedIds.length > 0 && (
                <button 
                  onClick={handleBulkDelete}
                  className="bg-red-600/90 hover:bg-red-600 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 animate-pulse"
                >
                  <ShieldAlert size={14} />
                  Seçilenleri Sil ({selectedIds.length})
                </button>
              )}
            </div>
            
            <div className="flex items-center gap-4">
              {/* Tarih Filtresi */}
              <div className="flex items-center gap-2 bg-[#1a1d23] border border-white/10 px-4 py-2 rounded-xl">
                <span className="text-sm text-gray-400">Tarih:</span>
                <input 
                  type="date" 
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="bg-transparent border-none outline-none text-sm text-white cursor-pointer"
                />
              </div>
            </div>
          </div>

          {stats.history.length === 0 ? (
            <div className="bg-[#1a1d23] border border-white/5 p-12 rounded-3xl text-center text-gray-500">
              <p>Şu ana kadar herhangi bir ihlal tespit edilmedi.</p>
            </div>
          ) : (() => {
            // Sekme filtrelemesi
            let tabFiltered = stats.history;
            if (activeTab === 'ters_yon') {
              tabFiltered = stats.history.filter(item => item.type.includes("Ters Yön"));
            } else if (activeTab === 'yaya') {
              tabFiltered = stats.history.filter(item => item.type.includes("Yaya"));
            } else {
              tabFiltered = stats.history.filter(item => item.type.includes("Hız"));
            }

            // Tarih filtrelemesi
            const finalFiltered = selectedDate 
              ? tabFiltered.filter(item => item.time.startsWith(selectedDate))
              : tabFiltered;

            if (finalFiltered.length === 0) {
              return (
                <div className="bg-[#1a1d23] border border-white/5 p-12 rounded-3xl text-center text-gray-500">
                  <p>Bu sekmeye veya seçilen tarihe ait ihlal kaydı bulunmamaktadır.</p>
                </div>
              );
            }

            return (
              <div className="flex flex-col gap-3">
                {/* Liste Başlıkları */}
                <div className="grid grid-cols-[50px_1fr_1fr_1fr_1fr_80px] px-6 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">
                  <div className="flex items-center">
                    <input 
                      type="checkbox" 
                      onChange={(e) => {
                        if (e.target.checked) setSelectedIds(finalFiltered.map(i => i.id));
                        else setSelectedIds([]);
                      }}
                      className="w-4 h-4 rounded border-gray-600 bg-gray-700"
                    />
                  </div>
                  <div>Zaman</div>
                  <div>İhlal Türü</div>
                  <div>ID</div>
                  <div>Kamera</div>
                  <div className="text-right">Detay</div>
                </div>

                {finalFiltered.map((item, idx) => (
                  <div 
                    key={idx}
                    className={`grid grid-cols-[50px_1fr_1fr_1fr_1fr_80px] px-6 py-4 bg-[#1a1d23] border border-white/5 rounded-2xl hover:bg-white/5 transition-all items-center group cursor-pointer ${selectedIds.includes(item.id) ? 'border-red-500/50 bg-red-500/5' : ''}`}
                    onClick={() => { setSelectedItem(item); setShowSS(false); }}
                  >
                    <div>
                      <input 
                        type="checkbox" 
                        checked={selectedIds.includes(item.id)}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => {
                          if (selectedIds.includes(item.id)) setSelectedIds(selectedIds.filter(i => i !== item.id));
                          else setSelectedIds([...selectedIds, item.id]);
                        }}
                        className="w-4 h-4 rounded border-gray-600 bg-gray-700"
                      />
                    </div>
                    <div className="text-sm font-medium text-gray-300">{item.time.split(' ')[1]} <span className="text-[10px] opacity-40 ml-1">{item.time.split(' ')[0]}</span></div>
                    <div>
                      <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase ${item.type.includes("Yaya") ? "bg-orange-500/20 text-orange-400" : "bg-red-500/20 text-red-400"}`}>
                        {item.type}
                      </span>
                    </div>
                    <div className="font-mono text-xs text-gray-400">#{item.vehicle_id}</div>
                    <div className="text-xs text-gray-500">{item.cam_name}</div>
                    <div className="text-right">
                      <ChevronRight className="inline-block text-gray-600 group-hover:text-white transition-colors" size={20} />
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      )}

      {/* Modal / Büyütülmüş İnceleme Görünümü */}
      {selectedItem && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/90 backdrop-blur-md" 
          onClick={() => setSelectedItem(null)}
        >
          <div 
            className="bg-[#1a1d23] border border-white/10 rounded-3xl overflow-hidden max-w-5xl w-full shadow-[0_0_50px_rgba(239,68,68,0.15)]" 
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex justify-between items-center p-5 border-b border-white/5">
              <h3 className="font-bold text-xl flex items-center gap-2">
                <Camera className="text-red-500" />
                {selectedItem.cam_name} - Detaylı İnceleme
              </h3>
              <button 
                onClick={() => setSelectedItem(null)} 
                className="text-gray-500 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center transition-colors"
              >
                &times;
              </button>
            </div>
            
            {/* Modal Body */}
            <div className="p-5">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Sol Taraf: Kanıt (Video veya SS) */}
                <div className="lg:col-span-2 bg-black rounded-2xl overflow-hidden aspect-video relative group border border-white/10">
                  {!showSS && selectedItem.video ? (
                    <video 
                      key={selectedItem.video}
                      controls 
                      autoPlay 
                      className="w-full h-full object-contain"
                    >
                      <source src={`${API_BASE}/videos/${selectedItem.video}`} type="video/mp4" />
                      Tarayıcınız video oynatmayı desteklemiyor.
                    </video>
                  ) : (
                    <img 
                      src={`${API_BASE}/screenshots/${selectedItem.img}`} 
                      className="w-full h-full object-contain cursor-zoom-in" 
                      alt="İhlal Kanıtı" 
                      onClick={() => setFullImage(`${API_BASE}/screenshots/${selectedItem.img}`)}
                    />
                  )}
                </div>
                
                {/* Sağ Taraf: Detaylar ve ZOOM (CROP) */}
                <div className="flex flex-col gap-6">
                  <div className="bg-white/5 p-4 rounded-2xl border border-white/5">
                    <h4 className="text-xs font-bold text-gray-500 uppercase mb-3 flex items-center gap-2">
                      <Search size={14} /> Yakınlaştırılmış Görüntü
                    </h4>
                    <div className="aspect-square bg-black rounded-xl overflow-hidden border border-white/10 shadow-inner group relative">
                      <img 
                        src={`${API_BASE}/screenshots/crop_${selectedItem.img}`} 
                        className="w-full h-full object-cover cursor-zoom-in group-hover:scale-105 transition-transform" 
                        alt="Zoom"
                        onClick={() => setFullImage(`${API_BASE}/screenshots/crop_${selectedItem.img}`)}
                        onError={(e) => { e.target.src = `${API_BASE}/screenshots/${selectedItem.img}`; }}
                      />
                    </div>
                    <p className="text-[10px] text-gray-500 mt-2 text-center">Otomatik nesne odaklı yakınlaştırma</p>
                  </div>

                  <div className="bg-white/5 p-6 rounded-2xl border border-white/5 flex-1">
                    <p className="text-gray-500 text-[10px] uppercase font-bold mb-4 tracking-widest">İhlal Detayları</p>
                    <div className="space-y-4">
                      <div>
                        <p className="text-gray-400 text-xs mb-1">Kamera / Bölge</p>
                        <p className="font-bold text-lg">{selectedItem.cam_name}</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-xs mb-1">Tarih & Zaman</p>
                        <p className="font-medium">{selectedItem.time}</p>
                      </div>
                      <div>
                        <p className="text-gray-400 text-xs mb-1">Takip ID</p>
                        <p className="text-2xl font-mono font-black text-red-500">#{selectedItem.vehicle_id}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
                
              <div className="flex flex-col sm:flex-row justify-end items-center gap-4 mt-6">
                <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
                  {selectedItem.video && (
                    <button 
                      onClick={() => setShowSS(!showSS)}
                      className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all flex items-center gap-2 justify-center border border-white/10"
                    >
                      <Camera size={18} />
                      {showSS ? "Videoya Dön" : "Net SS Gör"}
                    </button>
                  )}
                  <button 
                    onClick={() => handleDelete(selectedItem.id)}
                    className="bg-green-600 hover:bg-green-500 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all transform hover:scale-105 shadow-[0_0_15px_rgba(34,197,94,0.3)] flex items-center gap-2 justify-center"
                  >
                    <ShieldAlert size={18} />
                    Onayla ve Listeden Sil
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-12 text-center text-gray-600 text-xs py-8 border-t border-white/5">
        &copy; 2026 Fabrika Güvenlik ve İSG İzleme Sistemi v1.0.0
      </footer>
      {/* Full Screen Image Overlay */}
      {fullImage && (
        <div 
          className="fixed inset-0 z-[200] bg-black/95 flex items-center justify-center p-4 md:p-10 cursor-zoom-out"
          onClick={() => setFullImage(null)}
        >
          <img src={fullImage} className="max-w-full max-h-full object-contain shadow-2xl" alt="Full" />
          <button className="absolute top-10 right-10 text-white bg-white/10 p-4 rounded-full hover:bg-white/20 transition-all">&times;</button>
        </div>
      )}
    </div>
  );
}

export default App;
