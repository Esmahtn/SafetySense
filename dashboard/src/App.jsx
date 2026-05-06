import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { 
  ShieldAlert, Camera, Trash2, Monitor, LayoutGrid, CheckCircle2, 
  ArrowRightLeft, Zap, User, Search, RefreshCcw, Maximize2, Minimize2,
  Calendar, Clock, Filter, Eye, X, Download, AlertTriangle, Trash, CheckSquare, Square
} from 'lucide-react';

const API_BASE = "http://localhost:5000";

function App() {
  const [stats, setStats] = useState({ total: 0, history: [] });
  const [newAlert, setNewAlert] = useState(null);
  
  // Selection
  const [selectedIds, setSelectedIds] = useState([]);

  // Filters
  const [activeCam, setActiveCam] = useState("all"); 
  const [activeType, setActiveType] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterDate, setFilterDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  const [selectedImage, setSelectedImage] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/stats`);
      setStats(res.data);
    } catch (err) {
      console.error("Veri hatası:", err);
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!window.confirm(`${selectedIds.length} ADET KAYDI SİLMEK İSTEDİĞİNİZE EMİN MİSİNİZ?`)) return;
    try {
      await axios.post(`${API_BASE}/delete_multiple`, { ids: selectedIds });
      setSelectedIds([]);
      fetchStats();
    } catch (err) {
      alert("Toplu silme hatası.");
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API_BASE}/delete_violation/${id}`);
      fetchStats();
    } catch (err) {
      alert("Silme hatası.");
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("TÜM İHLAL KAYITLARINI SİLMEK İSTEDİĞİNİZE EMİN MİSİNİZ?")) return;
    try {
      await axios.delete(`${API_BASE}/clear_all_violations`);
      fetchStats();
    } catch (err) {
      alert("Toplu silme hatası.");
    }
  };

  useEffect(() => {
    fetchStats();
    const eventSource = new EventSource(`${API_BASE}/stream`);
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setNewAlert(data);
      fetchStats();
      setTimeout(() => setNewAlert(null), 8000);
    };
    return () => eventSource.close();
  }, []);

  const filteredHistory = useMemo(() => {
    return stats.history.filter(item => {
      if (activeCam !== "all") {
        const camId = activeCam === "1" ? "Ana Koridor" : activeCam === "2" ? "Güvensiz Bölge" : "Hız Koridoru";
        if (!item.cam_name.includes(camId)) return false;
      }
      if (activeType !== "all") {
        const typeSearch = activeType === 'yaya' ? 'yaya' : activeType === 'hız' ? 'hız' : 'ters';
        if (!item.type.toLowerCase().includes(typeSearch)) return false;
      }
      if (filterDate && item.time.split(' ')[0] !== filterDate) return false;
      if (searchTerm && !item.vehicle_id.toString().includes(searchTerm) && !item.type.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });
  }, [stats.history, activeCam, activeType, searchTerm, filterDate]);

  return (
    <div className="min-h-screen bg-[#050507] text-white font-inter flex flex-col lg:flex-row overflow-hidden selection:bg-red-500/30">
      
      {/* Toast Alert */}
      {newAlert && (
        <div className="fixed top-10 right-10 z-[200] animate-in fade-in slide-in-from-right duration-500">
          <div className="glass border-red-500/50 p-8 rounded-[40px] flex items-center gap-6 glow-red shadow-[0_0_80px_rgba(239,68,68,0.5)] bg-black/80 backdrop-blur-3xl min-w-[400px]">
            <div className="w-20 h-20 bg-red-600 rounded-full flex items-center justify-center animate-pulse shadow-2xl shadow-red-600/50">
              <ShieldAlert size={40} className="text-white" />
            </div>
            <div>
              <h4 className="font-outfit font-black text-red-500 text-3xl mb-1 italic tracking-tighter">YENİ İHLAL!</h4>
              <p className="text-2xl text-white font-black uppercase tracking-tight">{newAlert.type}</p>
              <p className="text-[11px] text-gray-400 font-bold uppercase mt-1 opacity-60 tracking-widest">{newAlert.cam_name}</p>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar */}
      <aside className="w-full lg:w-[380px] bg-[#0a0a0c] border-r border-white/5 p-8 flex flex-col space-y-6 z-30 overflow-y-auto custom-scrollbar">
        <div className="flex items-center gap-4 mb-4">
          <ShieldAlert size={32} className="text-red-600" />
          <h1 className="text-2xl font-outfit font-black tracking-tighter italic">SafetySense</h1>
        </div>

        <nav className="space-y-1.5">
          <p className="text-[10px] font-black text-gray-700 uppercase tracking-widest mb-2 ml-2">KAMERA SEÇİMİ</p>
          <SidebarBtn active={activeCam === 'all'} onClick={() => setActiveCam('all')} icon={<LayoutGrid size={16}/>} label="TÜM KAMERALAR" />
          <SidebarBtn active={activeCam === '1'} onClick={() => setActiveCam('1')} icon={<ArrowRightLeft size={16}/>} label="ANA KORİDOR" />
          <SidebarBtn active={activeCam === '2'} onClick={() => setActiveCam('2')} icon={<User size={16}/>} label="GÜVENSİZ BÖLGE" />
          <SidebarBtn active={activeCam === '3'} onClick={() => setActiveCam('3')} icon={<Zap size={16}/>} label="HIZ KORİDORU" />
        </nav>

        <div className="space-y-1.5 pt-4 border-t border-white/5">
          <p className="text-[10px] font-black text-gray-700 uppercase tracking-widest mb-2 ml-2">İHLAL TÜRÜ</p>
          <div className="grid grid-cols-2 gap-2">
            <TypeBtn active={activeType === 'all'} onClick={() => setActiveType('all')} label="TÜMÜ" />
            <TypeBtn active={activeType === 'yaya'} onClick={() => setActiveType('yaya')} label="YAYA" />
            <TypeBtn active={activeType === 'hız'} onClick={() => setActiveType('hız')} label="HIZ" />
            <TypeBtn active={activeType === 'ters'} onClick={() => setActiveType('ters')} label="TERS YÖN" />
          </div>
        </div>

        <div className="space-y-4 pt-4 border-t border-white/5">
          <p className="text-[10px] font-black text-gray-700 uppercase tracking-widest ml-2">GELİŞMİŞ FİLTRE</p>
          <input type="date" className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-sm text-gray-400" value={filterDate} onChange={(e) => setFilterDate(e.target.value)} />
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" size={14} />
            <input type="text" placeholder="Ara..." className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-10 pr-4 text-sm focus:border-red-500/50" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
          <button onClick={() => {setFilterDate(""); setSearchTerm(""); setActiveType("all"); setActiveCam("all"); setSelectedIds([]);}} className="w-full py-2 text-[10px] font-black text-gray-600 hover:text-red-500 flex items-center justify-center gap-2 transition-all"><RefreshCcw size={12}/> SIFIRLA</button>
        </div>

        <div className="mt-auto pt-4 border-t border-white/5">
           <div className="bg-red-600/10 p-5 rounded-3xl border border-red-600/20 text-center">
              <p className="text-3xl font-outfit font-black text-white">{stats.total}</p>
              <p className="text-[9px] text-red-500 font-bold uppercase tracking-widest">GÜNLÜK TOPLAM</p>
           </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto custom-scrollbar p-6 lg:p-12 space-y-12 bg-[#050507]">
        <section className="space-y-8 animate-fade-in">
          <div className="flex justify-between items-center">
            <h2 className="text-4xl font-outfit font-black flex items-center gap-5 italic uppercase tracking-tighter">
              <Monitor className="text-red-600" size={36} />
              {activeCam === "all" ? "CANLI GÖZETİM DUVARI" : "ODAKLANMIŞ AKIŞ"}
            </h2>
          </div>

          {activeCam === "all" ? (
            <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-8">
              <CamCard id={1} title="Ana Koridor" endpoint="vehicle_stream" />
              <CamCard id={2} title="Güvensiz Bölge" endpoint="pedestrian_stream" />
              <CamCard id={3} title="Hız Koridoru" endpoint="speed_stream" />
            </div>
          ) : (
            <BigCamView id={activeCam} title={activeCam === "1" ? "ANA KORİDOR" : activeCam === "2" ? "GÜVENSİZ BÖLGE" : "HIZ KORİDORU"} endpoint={activeCam === "1" ? "vehicle_stream" : activeCam === "2" ? "pedestrian_stream" : "speed_stream"} />
          )}
        </section>

        <section className="space-y-10 pt-12 border-t border-white/5 pb-40">
          <div className="flex justify-between items-end">
             <h3 className="text-3xl font-outfit font-black text-red-500 flex items-center gap-4 italic uppercase tracking-tighter"><AlertTriangle size={32} /> İHLAL KAYITLARI</h3>
             <div className="flex gap-4">
                <button onClick={() => setSelectedIds(filteredHistory.map(x => x.id))} className="text-[10px] font-black text-white/50 hover:text-white uppercase tracking-widest">TÜMÜNÜ SEÇ</button>
                <button onClick={handleClearAll} className="text-[10px] font-black text-red-500/50 hover:text-red-500 uppercase tracking-widest">ARŞİVİ BOŞALT</button>
             </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-10">
            {filteredHistory.map((item) => {
              const isSelected = selectedIds.includes(item.id);
              return (
                <div 
                  key={item.id} 
                  className={`bg-[#0a0a0c] rounded-[45px] p-8 border transition-all shadow-2xl relative group cursor-pointer ${isSelected ? 'border-red-600 ring-2 ring-red-600/50' : 'border-white/5 hover:border-red-600/40'}`}
                  onClick={() => toggleSelect(item.id)}
                >
                  <div className="absolute top-6 right-6">
                    {isSelected ? <CheckSquare className="text-red-600" size={24} /> : <Square className="text-white/10" size={24} />}
                  </div>

                  <div className="flex justify-between items-start mb-6 pr-10">
                    <div>
                      <h4 className="text-2xl font-outfit font-black text-white uppercase tracking-tight leading-tight">{item.type}</h4>
                      <p className="text-[10px] text-gray-500 font-black mt-1 uppercase tracking-widest">{item.cam_name}</p>
                      <p className="text-[10px] text-gray-700 font-black mt-0.5 uppercase tracking-widest">{item.time}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4" onClick={e => e.stopPropagation()}>
                    <div className="space-y-2">
                      <p className="text-[9px] font-black text-gray-700 uppercase tracking-widest ml-2 italic">GENEL</p>
                      <div className="aspect-video bg-black rounded-3xl overflow-hidden border border-white/5 cursor-zoom-in" onClick={() => setSelectedImage(`${API_BASE}/screenshots/${item.img}`)}>
                         <img src={`${API_BASE}/screenshots/${item.img}`} className="w-full h-full object-cover" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <p className="text-[9px] font-black text-gray-700 uppercase tracking-widest ml-2 italic">ZOOM</p>
                      <div className="aspect-video bg-black rounded-3xl overflow-hidden border border-white/5 cursor-zoom-in" onClick={() => setSelectedImage(`${API_BASE}/screenshots/crop_${item.img}`)}>
                         <img src={`${API_BASE}/screenshots/crop_${item.img}`} className="w-full h-full object-cover" />
                      </div>
                    </div>
                  </div>

                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }} 
                    className="w-full mt-6 bg-green-600/10 hover:bg-red-600 hover:text-white py-3.5 rounded-3xl font-black text-xs border border-green-600/20 uppercase tracking-widest transition-all"
                  >
                    KAYDI SİL
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      </main>

      {/* BULK ACTION BAR */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-10 left-1/2 -translate-x-1/2 z-[100] animate-in slide-in-from-bottom duration-500">
           <div className="glass border-red-600/50 p-6 rounded-[35px] flex items-center gap-10 shadow-[0_0_100px_rgba(239,68,68,0.3)] bg-black/90 backdrop-blur-3xl border-2">
              <div className="flex items-center gap-4">
                 <div className="w-12 h-12 bg-red-600 rounded-full flex items-center justify-center font-black text-xl shadow-lg shadow-red-600/40">
                   {selectedIds.length}
                 </div>
                 <div>
                    <p className="font-black text-sm uppercase tracking-tighter">KAYIT SEÇİLDİ</p>
                    <p className="text-[10px] text-gray-500 font-bold uppercase">TOPLU İŞLEM MERKEZİ</p>
                 </div>
              </div>
              <div className="flex gap-4">
                 <button onClick={() => setSelectedIds([])} className="px-8 py-3.5 rounded-2xl bg-white/5 hover:bg-white/10 font-black text-xs transition-all uppercase">VAZGEÇ</button>
                 <button onClick={handleBulkDelete} className="px-10 py-3.5 rounded-2xl bg-red-600 hover:bg-red-700 text-white font-black text-xs shadow-xl transition-all flex items-center gap-3 uppercase">
                   <Trash2 size={16} /> SEÇİLENLERİ SİL
                 </button>
              </div>
           </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedImage && (
        <div className="fixed inset-0 z-[200] bg-black/98 backdrop-blur-3xl flex flex-col p-4 md:p-8 animate-in fade-in duration-300" onClick={() => setSelectedImage(null)}>
           <div className="flex justify-between items-center text-white mb-6">
              <div className="flex items-center gap-4">
                <ShieldAlert className="text-red-600" size={32} />
                <h3 className="text-2xl font-outfit font-black italic uppercase tracking-widest">DETAYLI GÖRÜNTÜ</h3>
              </div>
              <button onClick={() => setSelectedImage(null)} className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center hover:bg-red-500 transition-all"><X size={36} /></button>
           </div>
           <div className="flex-1 w-full relative flex items-center justify-center overflow-hidden rounded-[50px] border border-white/10 bg-[#020203]" onClick={e => e.stopPropagation()}>
              <img src={selectedImage} className="max-w-full max-h-full object-contain" />
           </div>
        </div>
      )}
    </div>
  );
}

// Sub-components
function SidebarBtn({ active, onClick, icon, label }) {
  return (
    <button onClick={onClick} className={`w-full flex items-center gap-4 px-5 py-4 rounded-3xl transition-all font-black text-xs ${active ? 'bg-red-600 text-white shadow-xl shadow-red-600/30 translate-x-2' : 'text-gray-600 hover:bg-white/5 hover:text-white'}`}>
      {icon} {label}
    </button>
  );
}

function TypeBtn({ active, onClick, label }) {
  return (
    <button onClick={onClick} className={`py-2.5 rounded-2xl text-[10px] font-black transition-all border ${active ? 'bg-red-600 border-red-600 text-white shadow-lg shadow-red-600/20' : 'bg-white/5 border-white/10 text-gray-500 hover:text-white hover:border-white/20'}`}>
      {label}
    </button>
  );
}

function CamCard({ id, title, endpoint }) {
  return (
    <div className="bg-[#0a0a0c] rounded-[45px] overflow-hidden border border-white/5 shadow-2xl hover:border-red-600/30 transition-all">
      <div className="p-6 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
        <h4 className="text-xs font-black flex items-center gap-3 italic"><span className="w-2 h-2 bg-red-600 rounded-full animate-pulse shadow-lg shadow-red-600/50"></span>{title.toUpperCase()}</h4>
        <span className="text-[10px] font-black text-gray-700 tracking-widest">CAM-0{id}</span>
      </div>
      <div className="aspect-video bg-black"><img src={`${API_BASE}/${endpoint}`} className="w-full h-full object-contain" /></div>
    </div>
  );
}

function BigCamView({ id, title, endpoint }) {
  return (
    <div className="bg-[#0a0a0c] rounded-[60px] overflow-hidden border border-white/5 shadow-2xl">
      <div className="p-10 border-b border-white/5 bg-white/[0.02] flex justify-between items-center"><h4 className="text-4xl font-outfit font-black tracking-tighter italic uppercase">{title}</h4></div>
      <div className="aspect-video bg-black"><img src={`${API_BASE}/${endpoint}`} className="w-full h-full object-contain" /></div>
    </div>
  );
}

export default App;
