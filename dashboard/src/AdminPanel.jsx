import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { ArrowLeft, Camera, ListChecks, Plus, Mail, Server, AtSign, Lock, Send, CheckCircle, Loader } from 'lucide-react';
import UserManagement from './UserManagement';

const API_BASE = 'http://localhost:5000';

function AdminPanel({ onBack, isLight }) {
  const [activeSection, setActiveSection] = useState('cameras');
  const [config, setConfig] = useState({ cameras: {} });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [newCam, setNewCam] = useState({ id: '', name: '', ip: '', port: '554', username: 'admin', password: 'admin', path: 'live.sdp' });
  const [newTask, setNewTask] = useState({ cameraId: '', type: 'wrong_way', roiPoints: [], middleLinePoints: [] });
  const [drawingMode, setDrawingMode] = useState('roi'); // 'roi' veya 'middleLine'
  const [emailCfg, setEmailCfg] = useState({ enabled: false, smtp_host: 'smtp.gmail.com', smtp_port: 587, sender_email: '', recipient_email: '', has_password: false });
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [testing, setTesting] = useState(false);
  const [emailLoading, setEmailLoading] = useState(true);
  const imageRef = useRef(null);
  const canvasRef = useRef(null);
  const [imageLoaded, setImageLoaded] = useState(false);

  const selectedCamera = newTask.cameraId ? config.cameras[newTask.cameraId] : null;

  const generateRtsp = () => {
    const ip = newCam.ip.trim();
    if (!ip) return '';
    const username = newCam.username.trim() || 'admin';
    const passwordValue = newCam.password.trim() || 'admin';
    const port = newCam.port.trim() || '554';
    const path = newCam.path.trim().replace(/^\/+/, '') || 'live.sdp';
    return `rtsp://${encodeURIComponent(username)}:${encodeURIComponent(passwordValue)}@${ip}:${port}/${path}`;
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    window.setTimeout(() => setMessage(null), 5000);
  };

  const fetchConfig = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/config`);
      setConfig(res.data);
    } catch (err) {
      showMessage('error', 'Kamera ayarları yüklenemedi.');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmailSettings = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/email_settings`);
      setEmailCfg(res.data);
    } catch (err) {
      showMessage('error', 'SMTP ayarları yüklenemedi.');
    } finally {
      setEmailLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
    fetchEmailSettings();
  }, []);

  const saveConfig = async (updatedConfig) => {
    setSaving(true);
    try {
      await axios.post(`${API_BASE}/api/config`, updatedConfig);
      setConfig(updatedConfig);
      showMessage('success', 'Kayıtlar kaydedildi.');
    } catch (err) {
      showMessage('error', 'Kayıtlar kaydedilemedi.');
    } finally {
      setSaving(false);
    }
  };

  const saveEmailSettings = async () => {
    setSaving(true);
    try {
      const payload = {
        enabled: emailCfg.enabled,
        smtp_host: emailCfg.smtp_host,
        smtp_port: emailCfg.smtp_port,
        sender_email: emailCfg.sender_email,
        recipient_email: emailCfg.recipient_email,
      };
      if (password) payload.sender_password = password;
      await axios.post(`${API_BASE}/api/email_settings`, payload);
      setEmailCfg(prev => ({ ...prev, has_password: true }));
      setPassword('');
      showMessage('success', 'SMTP ayarları kaydedildi.');
    } catch (err) {
      showMessage('error', 'SMTP ayarları kaydedilemedi.');
    } finally {
      setSaving(false);
    }
  };

  const testEmailSettings = async () => {
    setTesting(true);
    try {
      const payload = {};
      if (password) payload.sender_password = password;
      const res = await axios.post(`${API_BASE}/api/test_email`, payload);
      showMessage('success', res.data.message || 'Test e-postası gönderildi!');
    } catch (err) {
      showMessage('error', err?.response?.data?.message || 'Test e-postası gönderilemedi.');
    } finally {
      setTesting(false);
    }
  };

  const drawRoi = () => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img || !imageLoaded) return;
    const rect = canvas.getBoundingClientRect();
    // Canvas boyutunu sadece bir kez ayarla
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!newTask.roiPoints.length || !img.naturalWidth || !img.naturalHeight) return;
    const scaleX = canvas.width / img.naturalWidth;
    const scaleY = canvas.height / img.naturalHeight;
    ctx.strokeStyle = '#ff4d4f';
    ctx.lineWidth = 3;
    ctx.fillStyle = 'rgba(255,77,79,0.25)';
    ctx.beginPath();
    newTask.roiPoints.forEach((point, index) => {
      const x = point[0] * scaleX;
      const y = point[1] * scaleY;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    if (newTask.roiPoints.length > 1) ctx.closePath();
    ctx.fill();
    ctx.stroke();
    newTask.roiPoints.forEach((point) => {
      const x = point[0] * scaleX;
      const y = point[1] * scaleY;
      ctx.beginPath();
      ctx.arc(x, y, 6, 0, Math.PI * 2);
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.strokeStyle = '#ff4d4f';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
    
    // Orta çizgi çiz (ters yön için) - sarı renkte
    if (newTask.type === 'wrong_way' && newTask.middleLinePoints.length >= 1) {
      ctx.strokeStyle = '#ffff00';
      ctx.lineWidth = 3;
      ctx.beginPath();
      newTask.middleLinePoints.forEach((point, index) => {
        const x = point[0] * scaleX;
        const y = point[1] * scaleY;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      if (newTask.middleLinePoints.length >= 2) ctx.stroke();
      newTask.middleLinePoints.forEach((point, index) => {
        const x = point[0] * scaleX;
        const y = point[1] * scaleY;
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.fillStyle = index === 0 ? '#00ff00' : '#ffff00'; // İlk nokta yeşil = başlangıç/doğru yön
        ctx.fill();
        ctx.strokeStyle = '#ffff00';
        ctx.lineWidth = 2;
        ctx.stroke();
        // Nokta etiketini göster
        ctx.fillStyle = index === 0 ? '#00ff00' : '#ffff00';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText(index === 0 ? '▶ DOĞRU YÖN BAŞLANGICI' : '■ BİTİŞ', x + 8, y - 6);
      });
      // İki nokta varsa ok çiz
      if (newTask.middleLinePoints.length >= 2) {
        const p1 = newTask.middleLinePoints[0];
        const p2 = newTask.middleLinePoints[1];
        const x1 = p1[0] * scaleX, y1 = p1[1] * scaleY;
        const x2 = p2[0] * scaleX, y2 = p2[1] * scaleY;
        const angle = Math.atan2(y2 - y1, x2 - x1);
        const arrowSize = 14;
        ctx.strokeStyle = '#ffff00';
        ctx.fillStyle = '#ffff00';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - arrowSize * Math.cos(angle - Math.PI/6), y2 - arrowSize * Math.sin(angle - Math.PI/6));
        ctx.lineTo(x2 - arrowSize * Math.cos(angle + Math.PI/6), y2 - arrowSize * Math.sin(angle + Math.PI/6));
        ctx.closePath();
        ctx.fill();
      }
    }
  };

  useEffect(() => {
    drawRoi();
  }, [newTask.roiPoints, newTask.middleLinePoints, selectedCamera, imageLoaded]);

  const handlePreviewClick = (event) => {
    if (!imageRef.current || !canvasRef.current || !imageLoaded) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const scaleX = imageRef.current.naturalWidth / rect.width;
    const scaleY = imageRef.current.naturalHeight / rect.height;
    const point = [Math.round(x * scaleX), Math.round(y * scaleY)];
    
    if (drawingMode === 'roi') {
      setNewTask(prev => ({ ...prev, roiPoints: [...prev.roiPoints, point] }));
    } else if (drawingMode === 'middleLine') {
      setNewTask(prev => ({ ...prev, middleLinePoints: [...prev.middleLinePoints, point] }));
    }
  };

  const clearCurrentRoi = () => {
    setNewTask(prev => ({ ...prev, roiPoints: [], middleLinePoints: [] }));
  };

  const clearMiddleLine = () => {
    setNewTask(prev => ({ ...prev, middleLinePoints: [] }));
  };

  useEffect(() => {
    if (!selectedCamera) {
      setNewTask(prev => ({ ...prev, roiPoints: [], middleLinePoints: [] }));
      setImageLoaded(false);
    }
  }, [selectedCamera]);

  const addCamera = async () => {
    const id = newCam.id.trim();
    if (!id || !newCam.name.trim()) {
      showMessage('error', 'Kamera ID ve isim zorunludur.');
      return;
    }
    if (config.cameras[id]) {
      showMessage('error', 'Bu ID zaten mevcut.');
      return;
    }
    const source = generateRtsp();
    if (!source) {
      showMessage('error', 'Geçerli bir IP ve kimlik bilgisi girin.');
      return;
    }
    const updated = {
      ...config,
      cameras: {
        ...config.cameras,
        [id]: { name: newCam.name.trim(), source, tasks: [] }
      }
    };
    setConfig(updated);
    setNewCam({ id: '', name: '', ip: '', port: '554', username: 'admin', password: 'admin', path: 'live.sdp' });
    await saveConfig(updated);
    // Kamera motorunu sunucuda başlat
    try {
      await axios.post(`${API_BASE}/api/start_camera`, { camera_id: id });
      showMessage('success', 'Kamera eklendi ve motor başlatıldı.');
    } catch (err) {
      showMessage('error', 'Kamera eklendi ama motor başlatılamadı.');
    }
  };

  const addTask = () => {
    const cameraId = newTask.cameraId;
    if (!cameraId || !config.cameras[cameraId]) {
      showMessage('error', 'Lütfen görev eklemek için bir kamera seçin.');
      return;
    }
    if (newTask.roiPoints.length < 2) {
      showMessage('error', 'ROI en az 2 noktadan oluşmalıdır.');
      return;
    }
    const taskData = { type: newTask.type, roi: newTask.roiPoints };
    if (newTask.type === 'wrong_way' && newTask.middleLinePoints.length >= 2) {
      taskData.middleLine = newTask.middleLinePoints;
    }
    const updatedCamera = {
      ...config.cameras[cameraId],
      tasks: [
        ...config.cameras[cameraId].tasks,
        taskData
      ]
    };
    const updated = {
      ...config,
      cameras: {
        ...config.cameras,
        [cameraId]: updatedCamera
      }
    };
    setConfig(updated);
    // cameraId'yi koruyarak sadece nokta verilerini sıfırla (kamera seçili kalsın)
    setNewTask(prev => ({ ...prev, roiPoints: [], middleLinePoints: [] }));
    setDrawingMode('roi');
    saveConfig(updated);
  };

  const removeCamera = (cameraId) => {
    const updated = {
      ...config,
      cameras: Object.fromEntries(Object.entries(config.cameras).filter(([key]) => key !== cameraId))
    };
    setConfig(updated);
    saveConfig(updated);
  };

  const removeTask = (cameraId, taskIndex) => {
    const camera = config.cameras[cameraId];
    const updatedCamera = {
      ...camera,
      tasks: camera.tasks.filter((_, idx) => idx !== taskIndex)
    };
    const updated = {
      ...config,
      cameras: {
        ...config.cameras,
        [cameraId]: updatedCamera
      }
    };
    setConfig(updated);
    saveConfig(updated);
  };

  return (
    <div className={`min-h-screen p-6 md:p-12 ${isLight ? 'bg-slate-100 text-slate-900' : 'bg-[#020203] text-white'}`}>
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center justify-between gap-4">
          <button onClick={onBack} className="flex items-center gap-2 px-4 py-3 rounded-3xl border border-white/10 bg-white/5 hover:bg-white/10 transition-all">
            <ArrowLeft size={18} /> Geri Dön
          </button>
          <div>
            <h1 className="text-3xl font-black">Yönetim Paneli</h1>
            <p className="text-sm text-gray-400">Kamera, görev, kullanıcı ve SMTP ayarlarını tek panelde yönetin.</p>
          </div>
        </div>

        {message && (
          <div className={`p-4 rounded-3xl ${message.type === 'success' ? 'bg-emerald-600/15 border border-emerald-500/20 text-emerald-300' : 'bg-red-600/15 border border-red-500/20 text-red-300'}`}>
            {message.text}
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { key: 'cameras', label: 'KAMERA AYARLARI' },
            { key: 'tasks', label: 'GÖREV AYARLARI' },
            { key: 'users', label: 'KULLANICI YÖNETİMİ' },
            { key: 'smtp', label: 'SMTP AYARLARI' }
          ].map((section) => (
            <button
              key={section.key}
              onClick={() => setActiveSection(section.key)}
              className={`rounded-3xl border p-4 text-left transition-all ${activeSection === section.key ? 'bg-red-600 text-white border-red-600 shadow-lg shadow-red-600/20' : 'bg-white/5 border-white/10 hover:bg-white/10 text-gray-300'}`}
            >
              <p className="text-[10px] font-black uppercase tracking-[0.35em] mb-2 text-gray-400">{section.label}</p>
              <p className="text-sm leading-6">
                {section.key === 'cameras' && 'Kamera ekle, düzenle ve sil.'}
                {section.key === 'tasks' && 'Görevleri ROI ile tanımla.'}
                {section.key === 'users' && 'Kullanıcıları ve rollerini yönet.'}
                {section.key === 'smtp' && 'E-posta bildirim ayarları.'}
              </p>
            </button>
          ))}
        </div>

        <div className={`rounded-[40px] border p-8 ${isLight ? 'bg-white border-slate-200' : 'bg-white/[0.03] border-white/10'}`}>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-3xl bg-red-600/10 flex items-center justify-center text-red-500">
              <Camera size={22} />
            </div>
            <div>
              <h2 className="text-2xl font-black uppercase tracking-tight">
                {activeSection === 'cameras' ? 'Kamera Ayarları' : activeSection === 'tasks' ? 'Görev Ayarları' : activeSection === 'users' ? 'Kullanıcı Yönetimi' : 'SMTP Ayarları'}
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                {activeSection === 'cameras' && 'Yeni kamera ekleyin, mevcut kameraları görüntüleyin ve yönetin.'}
                {activeSection === 'tasks' && 'Kameralar için ROI tabanlı görevler oluşturun.'}
                {activeSection === 'users' && 'Admin ve kullanıcı rolleri buradan düzenlenir.'}
                {activeSection === 'smtp' && 'SMTP bağlantısını ve e-posta bildirimlerini yapılandırın.'}
              </p>
            </div>
          </div>

          {activeSection === 'cameras' && (
            <div className="space-y-8">
              <div className="grid gap-4 sm:grid-cols-3">
                <label className="space-y-2 text-sm">
                  ID
                  <input value={newCam.id} onChange={(e) => setNewCam(prev => ({ ...prev, id: e.target.value }))} placeholder="Örn: 4" className="w-full rounded-2xl border px-4 py-3 outline-none text-sm" />
                </label>
                <label className="space-y-2 text-sm sm:col-span-2">
                  Kamera Adı
                  <input value={newCam.name} onChange={(e) => setNewCam(prev => ({ ...prev, name: e.target.value }))} placeholder="Örn: 4. Koridor" className="w-full rounded-2xl border px-4 py-3 outline-none text-sm" />
                </label>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm">
                  IP Adresi
                  <input value={newCam.ip} onChange={(e) => setNewCam(prev => ({ ...prev, ip: e.target.value }))} placeholder="Örn: 192.168.1.10" className="w-full rounded-2xl border px-4 py-3 outline-none text-sm" />
                </label>
                <label className="space-y-2 text-sm">
                  Port
                  <input value={newCam.port} onChange={(e) => setNewCam(prev => ({ ...prev, port: e.target.value }))} placeholder="554" className="w-full rounded-2xl border px-4 py-3 outline-none text-sm" />
                </label>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm">
                  Kullanıcı Adı
                  <input value={newCam.username} onChange={(e) => setNewCam(prev => ({ ...prev, username: e.target.value }))} placeholder="admin" className="w-full rounded-2xl border px-4 py-3 outline-none text-sm" />
                </label>
                <label className="space-y-2 text-sm">
                  Şifre
                  <input type="password" value={newCam.password} onChange={(e) => setNewCam(prev => ({ ...prev, password: e.target.value }))} placeholder="admin" className="w-full rounded-2xl border px-4 py-3 outline-none text-sm" />
                </label>
              </div>
              <label className="space-y-2 text-sm">
                RTSP Path
                <input value={newCam.path} onChange={(e) => setNewCam(prev => ({ ...prev, path: e.target.value }))} placeholder="live.sdp" className="w-full rounded-2xl border px-4 py-3 outline-none text-sm" />
              </label>
              <p className="text-[11px] text-gray-500 break-words">Otomatik oluşturulan RTSP URL: <span className="font-bold text-white">{generateRtsp() || 'IP bilgisi girin'}</span></p>
              <button onClick={addCamera} disabled={saving} className="inline-flex items-center gap-2 rounded-3xl bg-red-600 px-6 py-3 text-sm font-black uppercase tracking-[0.2em] text-white hover:bg-red-700 transition-all disabled:opacity-60">
                <Plus size={16} /> Kamera Ekle
              </button>

              <div className="mt-10 space-y-4">
                <h3 className="text-lg font-black">Mevcut Kameralar</h3>
                {loading ? (
                  <p className="text-gray-400">Yükleniyor...</p>
                ) : Object.keys(config.cameras).length === 0 ? (
                  <p className="text-gray-400">Kayıtlı kamera yok.</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(config.cameras).map(([id, cam]) => (
                      <div key={id} className="rounded-3xl border border-white/10 p-4 bg-black/10 flex items-start justify-between gap-4">
                        <div>
                          <p className="text-sm text-gray-300 font-bold">ID: {id}</p>
                          <p className="text-lg font-black">{cam.name}</p>
                          <p className="text-xs text-gray-500 break-all">{cam.source}</p>
                          <p className="mt-2 text-[11px] text-gray-400">Görev sayısı: {cam.tasks?.length || 0}</p>
                        </div>
                        <button onClick={() => removeCamera(id)} className="text-red-500 hover:text-white text-sm font-black">Kaldır</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeSection === 'tasks' && (
            <div className="space-y-8">
              <label className="space-y-2 text-sm">
                Kamera Seçin
                <select value={newTask.cameraId} onChange={(e) => setNewTask(prev => ({ ...prev, cameraId: e.target.value }))} className="w-full rounded-2xl border px-4 py-3 text-sm outline-none">
                  <option value="">Kamera seçin</option>
                  {Object.entries(config.cameras).map(([id, cam]) => (
                    <option key={id} value={id}>{id} - {cam.name}</option>
                  ))}
                </select>
              </label>

              <div className="grid grid-cols-2 gap-4">
                <label className="space-y-2 text-sm">
                  Görev Türü
                  <select value={newTask.type} onChange={(e) => setNewTask(prev => ({ ...prev, type: e.target.value }))} className="w-full rounded-2xl border px-4 py-3 text-sm outline-none">
                    <option value="wrong_way">Ters Yön</option>
                    <option value="pedestrian">Yaya</option>
                    <option value="speed">Hız</option>
                  </select>
                </label>
              </div>

              <div className="space-y-3">
                <p className="text-sm font-black">ROI Çizimi</p>
                {selectedCamera ? (
                  <div className="relative rounded-[30px] overflow-hidden border border-white/10 bg-black">
                    <img
                      ref={imageRef}
                      src={`${API_BASE}/video_feed/${newTask.cameraId}`}
                      alt="Kamera ön izleme"
                      className="w-full h-auto object-contain"
                      onLoad={() => setImageLoaded(true)}
                    />
                    <canvas
                      ref={canvasRef}
                      onClick={handlePreviewClick}
                      className="absolute inset-0 w-full h-full cursor-crosshair"
                      style={{ position: 'absolute', top: 0, left: 0 }}
                    />
                  </div>
                ) : (
                  <div className="rounded-3xl border border-white/10 p-6 text-gray-400">Önce bir kamera seçin, ardından görüntü üzerinde ROI çizebilirsiniz.</div>
                )}
                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={clearCurrentRoi} className="rounded-3xl bg-white/5 px-5 py-3 text-sm font-black uppercase tracking-[0.18em] border border-white/10 hover:bg-white/10 transition-all">ROI Temizle</button>
                  {newTask.type === 'wrong_way' && (
                    <>
                      <button type="button" onClick={() => setDrawingMode('roi')} className={`rounded-3xl px-5 py-3 text-sm font-black uppercase tracking-[0.18em] border transition-all ${drawingMode === 'roi' ? 'bg-red-600 text-white border-red-600' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}>ROI Çiz</button>
                      <button type="button" onClick={() => setDrawingMode('middleLine')} className={`rounded-3xl px-5 py-3 text-sm font-black uppercase tracking-[0.18em] border transition-all ${drawingMode === 'middleLine' ? 'bg-yellow-600 text-white border-yellow-600' : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-300 hover:bg-yellow-500/20'}`}>Orta Çizgi Çiz</button>
                      <button type="button" onClick={clearMiddleLine} className="rounded-3xl bg-white/5 px-5 py-3 text-sm font-black uppercase tracking-[0.18em] border border-white/10 hover:bg-white/10 transition-all">Orta Çizgi Temizle</button>
                    </>
                  )}
                  <span className="text-[11px] text-gray-400 self-center">Tıklayarak nokta ekleyin, iki veya daha fazla nokta ekledikten sonra görevi kaydedin.</span>
                </div>
                {newTask.type === 'wrong_way' && drawingMode === 'middleLine' && (
                  <div className="rounded-2xl border border-yellow-500/30 bg-yellow-500/5 p-4 text-[11px] text-yellow-300">
                    <p className="font-bold mb-1">⚠️ Sarı Orta Çizgi — Doğru Yön Çizgisi</p>
                    <p>1. Tıklama: <span className="text-green-400 font-bold">Doğru yönün başlangıç noktası ▶</span></p>
                    <p>2. Tıklama: Çizginin bitiş noktası</p>
                    <p className="mt-1 opacity-70">Araç bu çizginin <strong>başlangıcından bitişine</strong> doğru gidiyorsa normal, tersi ters yön sayılır.</p>
                  </div>
                )}
                <div className="rounded-3xl border border-white/10 bg-black/10 p-4 text-[11px] text-gray-300">
                  <p className="font-bold mb-2">Mevcut ROI Noktaları:</p>
                  {newTask.roiPoints.length === 0 ? (
                    <p>Henüz nokta yok.</p>
                  ) : (
                    <ol className="list-decimal ml-5 space-y-1">
                      {newTask.roiPoints.map((point, idx) => (
                        <li key={idx}>[{point[0]}, {point[1]}]</li>
                      ))}
                    </ol>
                  )}
                </div>
              </div>
              <button onClick={addTask} disabled={saving} className="inline-flex items-center gap-2 rounded-3xl bg-red-600 px-6 py-3 text-sm font-black uppercase tracking-[0.2em] text-white hover:bg-red-700 transition-all disabled:opacity-60">
                <Plus size={16} /> Görev Ekle
              </button>

              <div className="mt-10 space-y-4">
                <h3 className="text-lg font-black">Mevcut Görevler</h3>
                {Object.entries(config.cameras).filter(([, cam]) => cam.tasks?.length).length === 0 ? (
                  <p className="text-gray-400">Hiç görev bulunmuyor.</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(config.cameras).map(([id, cam]) => cam.tasks?.map((task, idx) => (
                      <div key={`${id}-${idx}`} className="rounded-3xl border border-white/10 p-4 bg-black/10 flex items-start justify-between gap-4">
                        <div>
                          <p className="text-xs text-gray-400">Kamera {id} · {cam.name}</p>
                          <p className="font-black">{task.type.replace('_', ' ').toUpperCase()}</p>
                          <p className="text-[11px] text-gray-400 mt-2">ROI noktaları: {task.roi.length}</p>
                        </div>
                        <button onClick={() => removeTask(id, idx)} className="text-red-500 hover:text-white text-sm font-black">Sil</button>
                      </div>
                    ))) }
                  </div>
                )}
              </div>
            </div>
          )}

          {activeSection === 'users' && (
            <div className="mt-4">
              <UserManagement embedded={true} isLight={isLight} />
            </div>
          )}

          {activeSection === 'smtp' && (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2 space-y-2">
                  <label className="text-xs font-black uppercase tracking-widest text-gray-500 flex items-center gap-2">
                    <Server size={12} /> SMTP Sunucu
                  </label>
                  <input
                    type="text"
                    value={emailCfg.smtp_host}
                    onChange={e => setEmailCfg(prev => ({ ...prev, smtp_host: e.target.value }))}
                    placeholder="smtp.gmail.com"
                    className="w-full rounded-2xl border bg-black/10 border-white/10 px-4 py-3 text-sm outline-none"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-black uppercase tracking-widest text-gray-500 flex items-center gap-2">
                    Port
                  </label>
                  <input
                    type="number"
                    value={emailCfg.smtp_port}
                    onChange={e => setEmailCfg(prev => ({ ...prev, smtp_port: e.target.value }))}
                    placeholder="587"
                    className="w-full rounded-2xl border bg-black/10 border-white/10 px-4 py-3 text-sm outline-none"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-black uppercase tracking-widest text-gray-500 flex items-center gap-2">
                  <AtSign size={12} /> Gönderici E-posta
                </label>
                <input
                  type="email"
                  value={emailCfg.sender_email}
                  onChange={e => setEmailCfg(prev => ({ ...prev, sender_email: e.target.value }))}
                  placeholder="gonderici@gmail.com"
                  className="w-full rounded-2xl border bg-black/10 border-white/10 px-4 py-3 text-sm outline-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-black uppercase tracking-widest text-gray-500 flex items-center gap-2">
                  <Lock size={12} /> Uygulama Şifresi
                </label>
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder={emailCfg.has_password ? '(değiştirmek için girin)' : 'Gmail Uygulama Şifresi'}
                  className="w-full rounded-2xl border bg-black/10 border-white/10 px-4 py-3 text-sm outline-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-black uppercase tracking-widest text-gray-500 flex items-center gap-2">
                  <Mail size={12} /> Alıcı E-posta
                </label>
                <input
                  type="email"
                  value={emailCfg.recipient_email}
                  onChange={e => setEmailCfg(prev => ({ ...prev, recipient_email: e.target.value }))}
                  placeholder="guvenlik@sirket.com"
                  className="w-full rounded-2xl border bg-black/10 border-white/10 px-4 py-3 text-sm outline-none"
                />
              </div>

              <div className={`flex items-center gap-3 p-4 rounded-2xl border ${emailCfg.enabled ? 'border-green-500/30 bg-green-500/5' : 'border-white/10 bg-white/5'}`}>
                <div className={`w-2.5 h-2.5 rounded-full ${emailCfg.enabled ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                <span className="text-sm font-bold text-gray-300">
                  {emailCfg.enabled ? 'Bildirimler AKTİF — ihlal e-postaları gönderilecek.' : 'Bildirimler PASİF — e-posta bildirimi kapalı.'}
                </span>
              </div>

              <div className="flex flex-wrap gap-4">
                <button
                  onClick={saveEmailSettings}
                  disabled={saving}
                  className="inline-flex items-center gap-3 rounded-3xl bg-red-600 px-6 py-3 text-sm font-black uppercase tracking-[0.2em] text-white hover:bg-red-700 transition-all disabled:opacity-60"
                >
                  {saving ? <Loader size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                  {saving ? 'Kaydediliyor...' : 'SMTP Ayarlarını Kaydet'}
                </button>
                <button
                  onClick={testEmailSettings}
                  disabled={testing || !emailCfg.enabled || !emailCfg.sender_email || !emailCfg.recipient_email}
                  className="inline-flex items-center gap-3 rounded-3xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-black uppercase tracking-[0.2em] text-white hover:bg-white/10 transition-all disabled:opacity-60"
                >
                  {testing ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
                  {testing ? 'Test Gönderiliyor...' : 'Test E-postası Gönder'}
                </button>
              </div>
            </div>
          )}

          {(activeSection === 'cameras' || activeSection === 'tasks') && (
            <div className="flex justify-end mt-8">
              <button onClick={() => saveConfig(config)} disabled={saving} className="rounded-3xl bg-white/10 px-6 py-3 text-sm font-black uppercase tracking-[0.2em] text-white transition-all hover:bg-white/20 disabled:opacity-60">
                {saving ? 'Kaydediliyor...' : 'Değişiklikleri Kaydet'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminPanel;
