import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { 
  ShieldAlert, Camera, Trash2, Monitor, LayoutGrid, CheckCircle2, 
  ArrowRightLeft, Zap, User, Search, RefreshCcw, Maximize2, Minimize2,
  Calendar, Clock, Filter, Eye, X, Download, AlertTriangle, Trash, CheckSquare, Square,
  ChevronLeft, ChevronRight, Settings, Sun, Moon
} from 'lucide-react';

const API_BASE = "http://localhost:5000";

function App() {
  const [stats, setStats] = useState({ total: 0, history: [] });
  const [config, setConfig] = useState({ cameras: {} });
  const [auth, setAuth] = useState({ logged_in: false, role: null, user: null });
  const [isLight, setIsLight] = useState(localStorage.getItem('theme') === 'light');
  
  // Theme Management
  useEffect(() => {
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
  }, [isLight]);
  const [newAlert, setNewAlert] = useState(null);
  
  // Selection
  const [selectedIds, setSelectedIds] = useState([]);

  // Slider States
  const [camStartIndex, setCamStartIndex] = useState(0);
  const [chartStartIndex, setChartStartIndex] = useState(0);
  const VISIBLE_COUNT = 3;

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
      console.error("İstatistik hatası:", err);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/config`);
      setConfig(res.data);
    } catch (err) {
      console.error("Config hatası:", err);
    }
  };

  const fetchAuth = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/auth/status`);
      setAuth(res.data);
    } catch (err) {
      console.error("Auth hatası:", err);
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
    fetchConfig();
    fetchAuth();
    const eventSource = new EventSource(`${API_BASE}/stream`);
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setNewAlert(data);
      fetchStats();
      setTimeout(() => setNewAlert(null), 8000);
    };
    return () => eventSource.close();
  }, []);

  const camerasList = useMemo(() => {
    return Object.keys(config.cameras).map(id => ({
      id,
      ...config.cameras[id]
    }));
  }, [config.cameras]);

  const filteredHistory = useMemo(() => {
    return stats.history.filter(item => {
      // Camera Filter
      if (activeCam !== "all") {
        const cam = config.cameras[activeCam];
        if (cam && !item.cam_name.includes(cam.name)) return false;
      }
      
      // Type Filter
      if (activeType !== "all") {
        const typeMap = {
          'yaya': 'yaya',
          'hiz': 'hız',
          'ters': 'ters'
        };
        if (!item.type.toLowerCase().includes(typeMap[activeType])) return false;
      }
      
      // Date Filter
      if (filterDate && item.time.split(' ')[0] !== filterDate) return false;
      
      // Time Filter (Start/End)
      if (startTime || endTime) {
        const itemTime = item.time.split(' ')[1]; // "HH:MM:SS"
        if (startTime && itemTime < startTime) return false;
        if (endTime && itemTime > endTime) return false;
      }
      
      // Search Term
      if (searchTerm) {
        const s = searchTerm.toLowerCase();
        const matches = 
          item.vehicle_id.toString().includes(s) || 
          item.type.toLowerCase().includes(s) ||
          item.cam_name.toLowerCase().includes(s);
        if (!matches) return false;
      }
      
      return true;
    });
  }, [stats.history, activeCam, activeType, searchTerm, filterDate, startTime, endTime, config.cameras]);

  // Statistics
  const camStats = useMemo(() => {
    const counts = {};
    camerasList.forEach(cam => {
      counts[cam.id] = stats.history.filter(item => item.cam_name.includes(cam.name)).length;
    });
    return counts;
  }, [stats.history, camerasList]);

  const typeStats = useMemo(() => {
    const counts = { 'yaya': 0, 'hiz': 0, 'ters': 0 };
    stats.history.forEach(item => {
      const t = item.type.toLowerCase();
      if (t.includes("yaya")) counts['yaya']++;
      if (t.includes("hız")) counts['hiz']++;
      if (t.includes("ters")) counts['ters']++;
    });
    return counts;
  }, [stats.history]);

  // Slider Nav Logic
  const slide = (direction, type) => {
    const isCam = type === 'cam';
    const current = isCam ? camStartIndex : chartStartIndex;
    const setter = isCam ? setCamStartIndex : setChartStartIndex;
    const list = isCam ? camerasList : camerasList; // both based on cameras

    if (direction === 'next') {
      const nextIndex = Math.min(current + 2, list.length - VISIBLE_COUNT);
      setter(nextIndex);
    } else {
      const prevIndex = Math.max(current - 2, 0);
      setter(prevIndex);
    }
  };

  return (
    <div className={`min-h-screen bg-[#020203] text-white font-inter flex flex-col overflow-x-hidden selection:bg-red-500/30 transition-colors duration-500 ${isLight ? 'light-mode bg-slate-50 text-slate-900' : ''}`}>
      
      {/* Toast Alert */}
      {newAlert && (
        <div className="fixed top-10 right-10 z-[300] animate-in fade-in slide-in-from-right duration-500">
          <div className="glass border-red-500/50 p-6 rounded-3xl flex items-center gap-6 shadow-[0_0_80px_rgba(239,68,68,0.4)] bg-black/90 backdrop-blur-3xl border-2">
            <div className="w-16 h-16 bg-red-600 rounded-2xl flex items-center justify-center animate-pulse shadow-xl shadow-red-600/50">
              <ShieldAlert size={32} className="text-white" />
            </div>
            <div>
              <h4 className="font-outfit font-black text-red-500 text-2xl italic tracking-tighter">YENİ İHLAL!</h4>
              <p className="text-xl text-white font-black uppercase tracking-tight">{newAlert.type}</p>
              <p className="text-[10px] text-gray-500 font-bold uppercase mt-1 tracking-widest">{newAlert.cam_name}</p>
            </div>
          </div>
        </div>
      )}

      {/* Modern Top Header / Filter Hub */}
      <header className="w-full bg-[#0a0a0c] border-b border-white/5 p-8 lg:p-12 space-y-12 z-50 shadow-2xl relative overflow-hidden transition-all duration-500 header-glass">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-red-600/5 blur-[150px] rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
        
        <div className="max-w-[1800px] mx-auto flex flex-col lg:flex-row justify-between items-center gap-10">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-red-600 rounded-[30px] flex items-center justify-center shadow-2xl shadow-red-600/40 rotate-6 group hover:rotate-0 transition-transform">
              <ShieldAlert size={48} className="text-white" />
            </div>
            <div>
              <h1 className="text-5xl font-outfit font-black tracking-tighter italic leading-none text-white transition-colors">SafetySense <span className="text-red-600 text-3xl">AI</span></h1>
              <p className="text-xs text-gray-600 font-black tracking-[0.4em] mt-3 uppercase opacity-60">Visual Intelligence & Safety Control Center</p>
            </div>
          </div>

          <div className="flex flex-wrap justify-center lg:justify-end gap-6 w-full lg:w-auto">
            <StatPill label="TOPLAM İHLAL" value={stats.total} icon={<AlertTriangle size={20} className="text-red-500" />} />
            <StatPill label="BUGÜN AKTİF" value={stats.history.length} icon={<Zap size={20} className="text-orange-500" />} />
            <StatPill label="CANLI KAMERA" value={camerasList.length} icon={<Camera size={20} className="text-blue-500" />} />
            
            <div className="flex items-center gap-4">
              <button onClick={() => setIsLight(!isLight)} className="w-16 h-16 glass rounded-3xl flex items-center justify-center hover:scale-110 transition-all text-red-500 group">
                {isLight ? <Moon size={24} className="group-hover:rotate-12 transition-transform" /> : <Sun size={24} className="group-hover:rotate-45 transition-transform" />}
              </button>
              
              {auth.role === 'admin' && (
                <a href="/settings" className="glass px-8 py-4 rounded-3xl flex items-center gap-6 border-white/5 hover:border-red-600/50 hover:bg-red-600/10 transition-all group">
                  <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center group-hover:rotate-90 transition-transform duration-500">
                      <Settings size={20} className="text-gray-400 group-hover:text-red-500" />
                  </div>
                  <div className="text-left hidden md:block">
                      <p className="text-xl font-outfit font-black tracking-tight">AYARLAR</p>
                      <p className="text-[10px] text-gray-600 font-bold uppercase tracking-widest">SİSTEM PANELİ</p>
                  </div>
                </a>
              )}

              <a href="/logout" className="glass px-6 py-4 rounded-3xl flex items-center gap-4 border-white/5 hover:border-red-600/50 hover:bg-red-600/10 transition-all group">
                <div className="text-right hidden md:block">
                    <p className="text-sm font-outfit font-black tracking-tight">{auth.user}</p>
                    <p className="text-[9px] text-gray-600 font-bold uppercase tracking-widest">ÇIKIŞ YAP</p>
                </div>
                <User size={20} className="text-gray-400 group-hover:text-red-500" />
              </a>
            </div>
          </div>
        </div>

        {/* INTERACTIVE VISUAL FILTERS */}
        <div className="max-w-[1800px] mx-auto grid grid-cols-1 xl:grid-cols-12 gap-8 relative z-10">
          
          {/* 1. Camera Distribution Chart with Slider */}
          <div className="xl:col-span-5 bg-white/[0.02] border border-white/5 p-8 rounded-[45px] space-y-6 relative group">
            <div className="flex justify-between items-center px-2">
               <h3 className="text-[11px] font-black text-gray-500 uppercase tracking-[0.2em] flex items-center gap-3"><Camera size={16} className="text-red-500"/> KAMERA DAĞILIMI</h3>
               <div className="flex items-center gap-4">
                 {activeCam !== 'all' && <button onClick={() => setActiveCam('all')} className="text-[10px] font-black text-red-500 hover:underline z-20 relative mr-2">Sıfırla</button>}
                 {camerasList.length > VISIBLE_COUNT && (
                    <div className="flex gap-2">
                       <SliderBtn onClick={() => slide('prev', 'chart')} disabled={chartStartIndex === 0} icon={<ChevronLeft size={14}/>} />
                       <SliderBtn onClick={() => slide('next', 'chart')} disabled={chartStartIndex >= camerasList.length - VISIBLE_COUNT} icon={<ChevronRight size={14}/>} />
                    </div>
                 )}
               </div>
            </div>
            <div className="flex items-end justify-between h-40 gap-4 px-4 pt-4 relative z-10 overflow-hidden">
               {camerasList.slice(chartStartIndex, chartStartIndex + VISIBLE_COUNT).map(cam => (
                 <BarChartItem 
                   key={cam.id}
                   label={cam.name.toUpperCase()} 
                   count={camStats[cam.id] || 0} 
                   active={activeCam === cam.id} 
                   onClick={() => setActiveCam(cam.id)} 
                   total={stats.total} 
                 />
               ))}
            </div>
          </div>

          {/* 2. Violation Categories (Interactive Cards) */}
          <div className="xl:col-span-4 bg-white/[0.02] border border-white/5 p-8 rounded-[45px] space-y-6">
             <h3 className="text-[11px] font-black text-gray-500 uppercase tracking-[0.2em] px-2 flex items-center gap-3"><Filter size={16} className="text-red-500"/> İHLAL KATEGORİLERİ</h3>
             <div className="grid grid-cols-2 gap-4">
                <MiniCategory active={activeType === 'all'} onClick={() => setActiveType('all')} label="TÜMÜ" count={stats.history.length} />
                <MiniCategory active={activeType === 'yaya'} onClick={() => setActiveType('yaya')} label="YAYA" count={typeStats['yaya']} />
                <MiniCategory active={activeType === 'hiz'} onClick={() => setActiveType('hiz')} label="HIZ" count={typeStats['hiz']} />
                <MiniCategory active={activeType === 'ters'} onClick={() => setActiveType('ters')} label="TERS YÖN" count={typeStats['ters']} />
             </div>
          </div>

          {/* 3. Advanced Engine Filters */}
          <div className="xl:col-span-3 bg-white/[0.02] border border-white/5 p-8 rounded-[45px] flex flex-col justify-between space-y-6">
             <div className="space-y-4">
                <div className="relative group">
                   <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within:text-red-500 transition-colors" size={16} />
                   <input type="date" className="w-full bg-black/40 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm text-gray-300 focus:border-red-500/50 outline-none transition-all" value={filterDate} onChange={(e) => setFilterDate(e.target.value)} />
                </div>
                <div className="relative group">
                   <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within:text-red-500 transition-colors" size={16} />
                   <input type="text" placeholder="Hızlı ara..." className="w-full bg-black/40 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm focus:border-red-500/50 outline-none transition-all" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
                </div>
             </div>
             <button onClick={() => {setFilterDate(""); setSearchTerm(""); setActiveType("all"); setActiveCam("all"); setStartTime(""); setEndTime("");}} className="w-full py-4 text-[10px] font-black text-gray-600 hover:text-red-500 flex items-center justify-center gap-2 transition-all hover:bg-red-500/10 rounded-2xl border border-dashed border-white/10 hover:border-red-500/20">
               <RefreshCcw size={14}/> FİLTRELERİ TEMİZLE
             </button>
          </div>

        </div>
      </header>

      {/* Main Content Hub */}
      <main className="flex-1 max-w-[1800px] mx-auto w-full p-8 lg:p-12 space-y-16 animate-fade-in">
        
        {/* ACTIVE FILTERS BADGES */}
        <div className="flex flex-wrap items-center gap-4">
           <p className="text-[10px] font-black text-gray-700 uppercase tracking-widest mr-2">AKTİF FİLTRELER:</p>
           {activeCam !== 'all' && <FilterBadge label={config.cameras[activeCam]?.name || 'Kamera'} onClear={() => setActiveCam('all')} />}
           {activeType !== 'all' && <FilterBadge label={activeType.toUpperCase()} onClear={() => setActiveType('all')} />}
           {filterDate && <FilterBadge label={filterDate} onClear={() => setFilterDate('')} />}
           {searchTerm && <FilterBadge label={`Arama: ${searchTerm}`} onClear={() => setSearchTerm('')} />}
           {activeCam === 'all' && activeType === 'all' && !filterDate && !searchTerm && <span className="text-[10px] font-bold text-gray-600">FİLTRE YOK</span>}
        </div>

        {/* Video Walls with Slider */}
        <section className="space-y-10">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-5">
               <div className="h-10 w-1.5 bg-red-600 rounded-full"></div>
               <h2 className="text-3xl font-outfit font-black italic uppercase tracking-tighter">CANLI GÖZETİM ÜNİTESİ</h2>
            </div>
            {activeCam === "all" && camerasList.length > VISIBLE_COUNT && (
              <div className="flex gap-4">
                <SliderBtnLarge onClick={() => slide('prev', 'cam')} disabled={camStartIndex === 0} icon={<ChevronLeft size={24}/>} />
                <SliderBtnLarge onClick={() => slide('next', 'cam')} disabled={camStartIndex >= camerasList.length - VISIBLE_COUNT} icon={<ChevronRight size={24}/>} />
              </div>
            )}
          </div>

          {activeCam === "all" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-10">
              {camerasList.slice(camStartIndex, camStartIndex + VISIBLE_COUNT).map((cam) => {
                return (
                  <CamCard 
                    key={cam.id}
                    id={cam.id} 
                    title={cam.name} 
                    endpoint={`video_feed/${cam.id}`} 
                    camIdReal={cam.id}
                  />
                );
              })}
            </div>
          ) : (
            <BigCamView 
              id={activeCam} 
              title={config.cameras[activeCam]?.name.toUpperCase() || "KAMERA"} 
              endpoint={`video_feed/${activeCam}`} 
            />
          )}
        </section>

        {/* Violation Records */}
        <section className="space-y-12 border-t border-white/5 pt-16 pb-40">
           <div className="flex flex-col md:flex-row justify-between items-center gap-8">
              <div className="flex items-center gap-5">
                 <div className="w-16 h-16 bg-red-600/10 rounded-[25px] flex items-center justify-center text-red-500">
                    <LayoutGrid size={28} />
                 </div>
                 <div>
                    <h3 className="text-3xl font-outfit font-black italic uppercase tracking-tighter">İHLAL ANALİZ RAPORLARI</h3>
                    <p className="text-[10px] text-gray-700 font-bold uppercase tracking-widest mt-1">Bulunan Kayıt: {filteredHistory.length}</p>
                 </div>
              </div>
              
              <div className="flex gap-4">
                 <button onClick={() => setSelectedIds(filteredHistory.map(x => x.id))} className="px-6 py-3 rounded-2xl bg-white/5 hover:bg-white/10 text-[10px] font-black uppercase tracking-widest transition-all">TÜMÜNÜ SEÇ</button>
                 <button onClick={handleClearAll} className="px-6 py-3 rounded-2xl bg-red-600/10 hover:bg-red-600 text-red-500 hover:text-white text-[10px] font-black uppercase tracking-widest transition-all border border-red-500/20">ARŞİVİ BOŞALT</button>
              </div>
           </div>

          <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-12">
            {filteredHistory.map((item) => {
              const isSelected = selectedIds.includes(item.id);
              const isCritical = item.type.toLowerCase().includes("yaya") || item.type.toLowerCase().includes("ters");
              
              return (
                <div 
                  key={item.id} 
                  className={`group relative bg-[#0a0a0c] rounded-[50px] p-1 border transition-all duration-500 hover:scale-[1.02] cursor-pointer ${isSelected ? 'ring-4 ring-red-600/30' : ''}`}
                  onClick={() => toggleSelect(item.id)}
                >
                  <div className={`w-full h-full bg-[#0a0a0c] rounded-[48px] p-8 border ${isSelected ? 'border-red-600' : 'border-white/5 group-hover:border-white/20'}`}>
                    <div className="flex justify-between items-start mb-8">
                      <div className="flex gap-4">
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${isCritical ? 'bg-red-600/20 text-red-500' : 'bg-orange-500/20 text-orange-500'}`}>
                          {isCritical ? <AlertTriangle size={24} /> : <Zap size={24} />}
                        </div>
                        <div>
                          <h4 className="text-2xl font-outfit font-black text-white uppercase tracking-tight leading-tight">{item.type}</h4>
                          <p className="text-[10px] text-gray-500 font-black mt-1 uppercase tracking-widest">{item.cam_name}</p>
                        </div>
                      </div>
                      <div className={`px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest border ${isSelected ? 'bg-red-600 border-red-600 text-white' : 'bg-white/5 border-white/10 text-gray-700 group-hover:text-gray-400'}`}>
                        {isSelected ? 'SEÇİLDİ' : `#${item.id}`}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-5 mb-8" onClick={e => e.stopPropagation()}>
                      <div className="space-y-3">
                        <p className="text-[9px] font-black text-gray-700 uppercase tracking-widest ml-2 italic">OLAY ANI</p>
                        <div className="aspect-[4/3] bg-black rounded-[30px] overflow-hidden border border-white/5 cursor-zoom-in group/img" onClick={() => setSelectedImage(`${API_BASE}/screenshots/${item.img}`)}>
                           <img src={`${API_BASE}/screenshots/${item.img}`} className="w-full h-full object-cover transition-transform duration-700 group-hover/img:scale-110" />
                        </div>
                      </div>
                      <div className="space-y-3">
                        <p className="text-[9px] font-black text-gray-700 uppercase tracking-widest ml-2 italic">DETAY (CROP)</p>
                        <div className="aspect-[4/3] bg-black rounded-[30px] overflow-hidden border border-white/5 cursor-zoom-in group/img" onClick={() => setSelectedImage(`${API_BASE}/screenshots/crop_${item.img}`)}>
                           <img src={`${API_BASE}/screenshots/crop_${item.img}`} className="w-full h-full object-cover transition-transform duration-700 group-hover/img:scale-110" />
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-6 border-t border-white/5">
                      <div className="flex items-center gap-3">
                        <Clock size={14} className="text-gray-700" />
                        <span className="text-[11px] font-black text-gray-500 uppercase tracking-widest">{item.time}</span>
                      </div>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }} 
                        className="w-12 h-12 rounded-2xl bg-white/5 hover:bg-red-600 text-gray-700 hover:text-white flex items-center justify-center transition-all border border-white/5 hover:border-red-600"
                      >
                        <Trash size={18} />
                      </button>
                    </div>
                  </div>
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
        <div className="fixed inset-0 z-[400] bg-black/98 backdrop-blur-3xl flex flex-col p-4 md:p-8 animate-in fade-in duration-300" onClick={() => setSelectedImage(null)}>
           <div className="flex justify-between items-center text-white mb-6">
              <div className="flex items-center gap-4">
                <ShieldAlert className="text-red-600" size={32} />
                <h3 className="text-2xl font-outfit font-black italic uppercase tracking-widest">DETAYLI GÖRÜNTÜ ANALİZİ</h3>
              </div>
              <button onClick={() => setSelectedImage(null)} className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center hover:bg-red-500 transition-all shadow-2xl"><X size={36} /></button>
           </div>
           <div className="flex-1 w-full relative flex items-center justify-center overflow-hidden rounded-[60px] border border-white/10 bg-[#020203] shadow-[0_0_100px_rgba(255,255,255,0.02)]" onClick={e => e.stopPropagation()}>
              <img src={selectedImage} className="max-w-full max-h-full object-contain" />
           </div>
        </div>
      )}
    </div>
  );
}

// Visual Dashboard Components
function StatPill({ label, value, icon }) {
  return (
    <div className="glass px-8 py-4 rounded-3xl flex items-center gap-6 border-white/5 hover:border-white/10 transition-colors">
       <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center">{icon}</div>
       <div className="text-left">
          <p className="text-3xl font-outfit font-black tracking-tight">{value}</p>
          <p className="text-[10px] text-gray-600 font-bold uppercase tracking-widest">{label}</p>
       </div>
    </div>
  );
}

function BarChartItem({ label, count, active, onClick, total }) {
  const percentage = total > 0 ? Math.max(10, (count / total) * 100) : 10;
  return (
    <div className="flex-1 flex flex-col items-center gap-4 group cursor-pointer animate-in fade-in slide-in-from-right duration-500" onClick={onClick}>
       <div className="w-full flex-1 relative flex items-end justify-center px-4">
          <div 
            style={{ height: `${percentage}%` }}
            className={`w-full max-w-[40px] rounded-t-xl transition-all duration-700 relative ${active ? 'bg-red-600 shadow-[0_0_30px_rgba(239,68,68,0.5)]' : 'bg-white/5 group-hover:bg-white/10'}`}
          >
             {active && <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-red-600 text-white text-[10px] font-black px-2 py-1 rounded-md animate-bounce">{count}</div>}
          </div>
       </div>
       <p className={`text-[9px] font-black uppercase tracking-tight text-center leading-tight ${active ? 'text-red-500' : 'text-gray-600'}`}>{label}</p>
    </div>
  );
}

function MiniCategory({ active, onClick, label, count }) {
  return (
    <button onClick={onClick} className={`relative p-5 rounded-[28px] border transition-all text-left overflow-hidden group ${active ? 'bg-red-600 border-red-600 shadow-xl' : 'bg-black/40 border-white/5 hover:border-white/10'}`}>
       <p className={`text-[10px] font-black uppercase tracking-widest ${active ? 'text-white' : 'text-gray-600'}`}>{label}</p>
       <p className={`text-2xl font-outfit font-black mt-1 ${active ? 'text-white' : 'text-white'}`}>{count}</p>
       {active && <div className="absolute top-2 right-2 w-2 h-2 bg-white rounded-full"></div>}
    </button>
  );
}

function FilterBadge({ label, onClear }) {
  return (
    <div className="bg-red-600/10 border border-red-600/20 px-4 py-2 rounded-xl flex items-center gap-3 animate-in zoom-in duration-300">
       <span className="text-[10px] font-black text-red-500 uppercase">{label}</span>
       <button onClick={onClear} className="text-red-500 hover:text-white transition-colors"><X size={12} /></button>
    </div>
  );
}

function SliderBtn({ onClick, disabled, icon }) {
  return (
    <button 
      onClick={onClick} 
      disabled={disabled}
      className={`w-8 h-8 rounded-full flex items-center justify-center transition-all border ${disabled ? 'opacity-20 cursor-not-allowed border-white/5' : 'bg-white/5 hover:bg-red-600 border-white/10 hover:border-red-600 text-gray-500 hover:text-white'}`}
    >
      {icon}
    </button>
  );
}

function SliderBtnLarge({ onClick, disabled, icon }) {
  return (
    <button 
      onClick={onClick} 
      disabled={disabled}
      className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all border shadow-xl ${disabled ? 'opacity-20 cursor-not-allowed border-white/5' : 'bg-white/5 hover:bg-red-600 border-white/10 hover:border-red-600 text-gray-500 hover:text-white'}`}
    >
      {icon}
    </button>
  );
}

function CamCard({ id, title, endpoint, camIdReal }) {
  return (
    <div className="bg-[#0a0a0c] rounded-[55px] overflow-hidden border border-white/5 shadow-2xl hover:border-red-600/30 transition-all group animate-in fade-in slide-in-from-right duration-700">
      <div className="p-8 border-b border-white/5 bg-white/[0.01] flex justify-between items-center">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-red-600/10 rounded-2xl flex items-center justify-center group-hover:bg-red-600 transition-colors">
            <Camera size={18} className="text-red-500 group-hover:text-white transition-colors" />
          </div>
          <div>
            <h4 className="text-sm font-black flex items-center gap-3 italic tracking-tight uppercase">{title}</h4>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse shadow-lg shadow-red-600/50"></span>
              <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">LIVE STREAM</span>
            </div>
          </div>
        </div>
        <div className="px-4 py-2 bg-white/5 rounded-2xl text-[9px] font-black text-gray-500 uppercase tracking-widest border border-white/5">CAM-0{camIdReal}</div>
      </div>
      <div className="aspect-video bg-black relative group-hover:scale-[1.02] transition-transform duration-500">
        <img src={`${API_BASE}/video_feed/${camIdReal}`} className="w-full h-full object-contain" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
      </div>
    </div>
  );
}

function BigCamView({ id, title, endpoint }) {
  return (
    <div className="bg-[#0a0a0c] rounded-[70px] overflow-hidden border-2 border-red-600/20 shadow-[0_0_80px_rgba(239,68,68,0.1)] animate-in zoom-in duration-500">
      <div className="p-10 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
        <div className="flex items-center gap-6">
           <div className="w-16 h-16 bg-red-600 rounded-[25px] flex items-center justify-center shadow-2xl shadow-red-600/40">
              <Maximize2 size={32} className="text-white" />
           </div>
           <h4 className="text-5xl font-outfit font-black tracking-tighter italic uppercase">{title}</h4>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-red-500 font-black uppercase tracking-[0.3em]">FOCUSED CAMERA VIEW</p>
          <p className="text-gray-600 font-black text-sm uppercase">CAM-0{id}</p>
        </div>
      </div>
      <div className="aspect-video bg-black p-4"><img src={`${API_BASE}/video_feed/${id}`} className="w-full h-full object-contain rounded-[40px] shadow-2xl" /></div>
    </div>
  );
}

export default App;
