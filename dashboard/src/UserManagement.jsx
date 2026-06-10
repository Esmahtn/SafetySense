import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { User, Trash2, ArrowLeft } from 'lucide-react';

function UserManagement({ onBack, embedded = false }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [message, setMessage] = useState(null);

  const fetchUsers = async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/users');
      setUsers(res.data);
    } catch (err) {
      console.error('Kullanıcılar alınamadı:', err);
      setMessage({ type: 'error', text: 'Kullanıcılar alınamadı.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const showMessage = (type, text) => {
    setMessage({ type, text });
    window.setTimeout(() => setMessage(null), 5000);
  };

  const handleDelete = async (id) => {
    const confirmDelete = window.confirm('Kullanıcıyı silmek istediğinize emin misiniz?');
    if (!confirmDelete) return;
    try {
      await axios.delete(`http://localhost:5000/api/users/${id}`);
      setUsers(prev => prev.filter(u => u.id !== id));
      showMessage('success', 'Kullanıcı silindi.');
    } catch (err) {
      showMessage('error', err?.response?.data?.message || 'Silme işlemi başarısız oldu.');
    }
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!username.trim() || !password.trim()) {
      showMessage('error', 'Kullanıcı adı ve şifre zorunludur.');
      return;
    }
    try {
      await axios.post('http://localhost:5000/api/users', { username: username.trim(), password: password.trim(), role });
      setUsername('');
      setPassword('');
      setRole('user');
      fetchUsers();
      showMessage('success', 'Kullanıcı oluşturuldu.');
    } catch (err) {
      showMessage('error', err?.response?.data?.message || 'Kullanıcı oluşturulamadı.');
    }
  };

  const handleRoleChange = async (username, newRole) => {
    try {
      await axios.post('http://localhost:5000/admin/set_role', { username, role: newRole });
      fetchUsers();
      showMessage('success', `Rol güncellendi: ${username}.`);
    } catch (err) {
      showMessage('error', err?.response?.data?.message || 'Rol güncelleme başarısız oldu.');
    }
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto p-8">
        <p className="text-gray-400">Yükleniyor...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-8 bg-white/5 rounded-3xl backdrop-blur-xl border border-white/10">
      {!embedded && onBack && (
        <button onClick={onBack} className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
          <ArrowLeft size={20} /> Geri Dön
        </button>
      )}
      <h2 className="text-3xl font-outfit font-black text-white mb-4">Kullanıcı Yönetimi</h2>

      {message && (
        <div className={`mb-6 rounded-3xl px-5 py-4 ${message.type === 'success' ? 'bg-emerald-600/15 border border-emerald-500/20 text-emerald-100' : 'bg-red-600/15 border border-red-500/20 text-red-100'}`}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleCreate} className="grid gap-4 mb-10 lg:grid-cols-3">
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Kullanıcı adı"
          className="rounded-3xl border border-white/10 bg-black/20 px-4 py-4 text-sm outline-none"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Şifre"
          className="rounded-3xl border border-white/10 bg-black/20 px-4 py-4 text-sm outline-none"
        />
        <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-3xl border border-white/10 bg-black/20 px-4 py-4 text-sm outline-none">
          <option value="user">Kullanıcı</option>
          <option value="admin">Admin</option>
        </select>
        <button type="submit" className="lg:col-span-3 rounded-3xl bg-red-600 px-6 py-4 text-sm font-black uppercase tracking-[0.2em] text-white hover:bg-red-700 transition-all">
          Yeni Kullanıcı Ekle
        </button>
      </form>

      <div className="space-y-4">
        {users.length === 0 ? (
          <p className="text-gray-400">Kullanıcı bulunamadı.</p>
        ) : (
          users.map(user => (
            <div key={user.id} className="flex flex-col gap-4 p-4 bg-black/20 rounded-3xl border border-white/10 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-3">
                <User size={20} className="text-gray-400" />
                <div>
                  <p className="font-black text-white">{user.username}</p>
                  <p className="text-sm text-gray-400">Rol: {user.role}</p>
                </div>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <select
                  value={user.role}
                  onChange={(e) => handleRoleChange(user.username, e.target.value)}
                  className="rounded-3xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none"
                >
                  <option value="user">Kullanıcı</option>
                  <option value="admin">Admin</option>
                </select>
                <button
                  onClick={() => handleDelete(user.id)}
                  className="inline-flex items-center gap-2 rounded-3xl bg-red-600 px-4 py-3 text-sm font-black uppercase tracking-[0.2em] text-white hover:bg-red-700 transition-all"
                >
                  <Trash2 size={16} /> Sil
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default UserManagement;
