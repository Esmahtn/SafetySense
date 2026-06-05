import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Sun, Moon, ArrowLeft, Mail, MailCheck, MailX,
  Shield, Send, Eye, EyeOff, CheckCircle, XCircle,
  Loader, Server, AtSign, Lock, ChevronRight
} from 'lucide-react';

const API_BASE = 'http://localhost:5000';

function SettingsPage({ isLight, setIsLight, onBack }) {
  const [emailCfg, setEmailCfg] = useState({
    enabled: false,
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    sender_email: '',
    recipient_email: '',
    has_password: false,
  });
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [toast, setToast] = useState(null); // { type: 'success'|'error', msg: '' }
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_BASE}/api/email_settings`, { withCredentials: true })
      .then(res => { setEmailCfg(res.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const showToast = (type, msg) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 4000);
  };

  const handleSave = async () => {
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
      await axios.post(`${API_BASE}/api/email_settings`, payload, { withCredentials: true });
      showToast('success', 'Ayarlar başarıyla kaydedildi.');
      if (password) { setEmailCfg(p => ({ ...p, has_password: true })); setPassword(''); }
    } catch {
      showToast('error', 'Kaydetme başarısız oldu.');
    }
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const payload = {};
      if (password) payload.sender_password = password;
      const res = await axios.post(`${API_BASE}/api/test_email`, payload, { withCredentials: true });
      showToast('success', res.data.message || 'Test e-postası gönderildi!');
    } catch (err) {
      showToast('error', err?.response?.data?.message || 'Test gönderilemedi.');
    }
    setTesting(false);
  };

  const base = isLight
    ? 'min-h-screen bg-slate-50 text-slate-900'
    : 'min-h-screen bg-[#020203] text-white';

  const card = isLight
    ? 'bg-white border border-slate-200 shadow-sm'
    : 'bg-white/[0.03] border border-white/8';

  const input = isLight
    ? 'bg-white border border-slate-200 text-slate-800 focus:border-red-400'
    : 'bg-black/40 border border-white/10 text-white focus:border-red-500/60';

  return (
    <div className={`${base} p-6 md:p-12`}>
      {/* Toast */}
      {toast && (
        <div className={`fixed top-8 right-8 z-[500] flex items-center gap-4 px-6 py-4 rounded-2xl shadow-2xl backdrop-blur-xl border transition-all animate-in fade-in slide-in-from-right duration-300 ${toast.type === 'success' ? 'bg-green-600/90 border-green-500 text-white' : 'bg-red-600/90 border-red-500 text-white'}`}>
          {toast.type === 'success' ? <CheckCircle size={20} /> : <XCircle size={20} />}
          <span className="font-bold text-sm">{toast.msg}</span>
        </div>
      )}

      <div className="max-w-3xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-5">
          <button
            onClick={onBack}
            className={`w-12 h-12 rounded-2xl flex items-center justify-center border transition-all hover:scale-105 ${isLight ? 'bg-slate-100 border-slate-200 hover:bg-slate-200' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-3xl font-outfit font-black tracking-tight">Sistem Ayarları</h1>
            <p className={`text-sm font-bold mt-1 ${isLight ? 'text-slate-500' : 'text-gray-500'}`}>SafetySense AI · Yönetim Paneli</p>
          </div>
        </div>

        {/* Theme Card */}
        <div className={`${card} rounded-3xl p-8 space-y-6`}>
          <div className="flex items-center gap-4 mb-2">
            <div className="w-12 h-12 bg-violet-600/10 rounded-2xl flex items-center justify-center">
              {isLight ? <Sun size={22} className="text-yellow-500" /> : <Moon size={22} className="text-violet-400" />}
            </div>
            <div>
              <h2 className="text-xl font-outfit font-black">Arayüz Teması</h2>
              <p className={`text-xs font-bold uppercase tracking-widest ${isLight ? 'text-slate-400' : 'text-gray-600'}`}>Görsel tercih</p>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-bold">Şu anki tema: <span className={`${isLight ? 'text-yellow-600' : 'text-violet-400'}`}>{isLight ? 'Açık Mod' : 'Koyu Mod'}</span></p>
              <p className={`text-sm mt-1 ${isLight ? 'text-slate-500' : 'text-gray-600'}`}>Tema seçimi tarayıcıya kaydedilir.</p>
            </div>
            <button
              onClick={() => setIsLight(!isLight)}
              className={`relative w-16 h-8 rounded-full transition-colors duration-300 ${isLight ? 'bg-yellow-400' : 'bg-violet-600'}`}
            >
              <span className={`absolute top-1 w-6 h-6 rounded-full bg-white shadow-lg transition-all duration-300 ${isLight ? 'left-1' : 'left-9'}`}></span>
            </button>
          </div>
        </div>

        {/* Email Notification Card */}
        <div className={`${card} rounded-3xl p-8 space-y-7`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${emailCfg.enabled ? 'bg-green-600/15' : 'bg-red-600/10'}`}>
                {emailCfg.enabled ? <MailCheck size={22} className="text-green-500" /> : <MailX size={22} className="text-red-500" />}
              </div>
              <div>
                <h2 className="text-xl font-outfit font-black">E-posta Bildirimleri</h2>
                <p className={`text-xs font-bold uppercase tracking-widest ${isLight ? 'text-slate-400' : 'text-gray-600'}`}>İhlal uyarı sistemi</p>
              </div>
            </div>
            {/* Enable/Disable Toggle */}
            <button
              onClick={() => setEmailCfg(p => ({ ...p, enabled: !p.enabled }))}
              className={`relative w-16 h-8 rounded-full transition-colors duration-300 ${emailCfg.enabled ? 'bg-green-500' : isLight ? 'bg-slate-300' : 'bg-white/10'}`}
            >
              <span className={`absolute top-1 w-6 h-6 rounded-full bg-white shadow-lg transition-all duration-300 ${emailCfg.enabled ? 'left-9' : 'left-1'}`}></span>
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <Loader size={24} className="animate-spin text-gray-500" />
            </div>
          ) : (
            <div className="space-y-5">
              {/* SMTP Host + Port */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2 space-y-2">
                  <label className={`text-xs font-black uppercase tracking-widest flex items-center gap-2 ${isLight ? 'text-slate-500' : 'text-gray-500'}`}>
                    <Server size={12} /> SMTP Sunucu
                  </label>
                  <input
                    type="text"
                    value={emailCfg.smtp_host}
                    onChange={e => setEmailCfg(p => ({ ...p, smtp_host: e.target.value }))}
                    placeholder="smtp.gmail.com"
                    className={`w-full ${input} rounded-2xl py-3.5 px-5 text-sm outline-none transition-all`}
                  />
                </div>
                <div className="space-y-2">
                  <label className={`text-xs font-black uppercase tracking-widest flex items-center gap-2 ${isLight ? 'text-slate-500' : 'text-gray-500'}`}>
                    <ChevronRight size={12} /> Port
                  </label>
                  <input
                    type="number"
                    value={emailCfg.smtp_port}
                    onChange={e => setEmailCfg(p => ({ ...p, smtp_port: e.target.value }))}
                    placeholder="587"
                    className={`w-full ${input} rounded-2xl py-3.5 px-5 text-sm outline-none transition-all`}
                  />
                </div>
              </div>

              {/* Sender Email */}
              <div className="space-y-2">
                <label className={`text-xs font-black uppercase tracking-widest flex items-center gap-2 ${isLight ? 'text-slate-500' : 'text-gray-500'}`}>
                  <AtSign size={12} /> Gönderen E-posta (From)
                </label>
                <input
                  type="email"
                  value={emailCfg.sender_email}
                  onChange={e => setEmailCfg(p => ({ ...p, sender_email: e.target.value }))}
                  placeholder="gonderici@gmail.com"
                  className={`w-full ${input} rounded-2xl py-3.5 px-5 text-sm outline-none transition-all`}
                />
              </div>

              {/* Sender Password */}
              <div className="space-y-2">
                <label className={`text-xs font-black uppercase tracking-widest flex items-center gap-2 ${isLight ? 'text-slate-500' : 'text-gray-500'}`}>
                  <Lock size={12} /> Uygulama Şifresi
                  {emailCfg.has_password && !password && (
                    <span className="text-green-500 text-[10px] font-bold ml-2">● Kayıtlı şifre mevcut</span>
                  )}
                </label>
                <div className="relative">
                  <input
                    type={showPass ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder={emailCfg.has_password ? '(değiştirmek için girin)' : 'Gmail App Password'}
                    className={`w-full ${input} rounded-2xl py-3.5 px-5 pr-14 text-sm outline-none transition-all`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className={`absolute right-4 top-1/2 -translate-y-1/2 ${isLight ? 'text-slate-400 hover:text-slate-700' : 'text-gray-600 hover:text-gray-300'}`}
                  >
                    {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <p className={`text-[11px] ${isLight ? 'text-slate-400' : 'text-gray-600'}`}>
                  Gmail kullanıcıları için: Google hesabı → Güvenlik → 2FA → Uygulama Şifreleri
                </p>
              </div>

              {/* Recipient Email */}
              <div className="space-y-2">
                <label className={`text-xs font-black uppercase tracking-widest flex items-center gap-2 ${isLight ? 'text-slate-500' : 'text-gray-500'}`}>
                  <Mail size={12} /> Alıcı E-posta (To)
                </label>
                <input
                  type="email"
                  value={emailCfg.recipient_email}
                  onChange={e => setEmailCfg(p => ({ ...p, recipient_email: e.target.value }))}
                  placeholder="guvenlik@sirket.com"
                  className={`w-full ${input} rounded-2xl py-3.5 px-5 text-sm outline-none transition-all`}
                />
              </div>

              {/* Status indicator */}
              <div className={`flex items-center gap-3 p-4 rounded-2xl border ${emailCfg.enabled ? 'border-green-500/30 bg-green-500/5' : isLight ? 'border-slate-200 bg-slate-50' : 'border-white/5 bg-white/[0.02]'}`}>
                <div className={`w-2.5 h-2.5 rounded-full ${emailCfg.enabled ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                <span className={`text-sm font-bold ${emailCfg.enabled ? 'text-green-500' : isLight ? 'text-slate-500' : 'text-gray-500'}`}>
                  {emailCfg.enabled
                    ? 'Bildirimler AKTİF — her ihlalde e-posta gönderilecek'
                    : 'Bildirimler KAPALI — e-posta gönderilmeyecek'}
                </span>
              </div>

              {/* Buttons */}
              <div className="flex flex-wrap gap-4 pt-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-3 px-8 py-3.5 rounded-2xl bg-red-600 hover:bg-red-700 text-white font-black text-sm transition-all shadow-lg shadow-red-600/20 disabled:opacity-50"
                >
                  {saving ? <Loader size={16} className="animate-spin" /> : <Shield size={16} />}
                  {saving ? 'Kaydediliyor...' : 'Ayarları Kaydet'}
                </button>

                <button
                  onClick={handleTest}
                  disabled={testing || !emailCfg.enabled || !emailCfg.sender_email || !emailCfg.recipient_email}
                  className={`flex items-center gap-3 px-8 py-3.5 rounded-2xl font-black text-sm transition-all border disabled:opacity-40 disabled:cursor-not-allowed ${isLight ? 'bg-slate-100 border-slate-200 hover:bg-slate-200' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}
                >
                  {testing ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
                  {testing ? 'Gönderiliyor...' : 'Test E-postası Gönder'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Info Box */}
        <div className={`rounded-2xl p-5 border text-sm ${isLight ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-blue-600/5 border-blue-600/20 text-blue-400'}`}>
          <p className="font-black mb-1 flex items-center gap-2"><Mail size={14} /> Gmail SMTP Kurulumu</p>
          <ol className={`list-decimal ml-4 space-y-1 text-xs ${isLight ? 'text-blue-600' : 'text-blue-400/80'}`}>
            <li>Google hesabınızda 2 Adımlı Doğrulamayı açın</li>
            <li>Google Hesabı → Güvenlik → Uygulama Şifreleri bölümüne gidin</li>
            <li>"SafetySense" adıyla yeni bir uygulama şifresi oluşturun</li>
            <li>Oluşturulan 16 haneli şifreyi yukarıdaki "Uygulama Şifresi" alanına girin</li>
          </ol>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
