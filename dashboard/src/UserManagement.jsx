import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { User, Trash2, ArrowLeft } from 'lucide-react';

function UserManagement({ onBack }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchUsers = async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/users');
      setUsers(res.data);
    } catch (err) {
      console.error('Kullanıcılar alınamadı:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleDelete = async (id) => {
    const confirm = window.confirm('Kullanıcıyı silmek istediğinize emin misiniz?');
    if (!confirm) return;
    try {
      await axios.delete(`http://localhost:5000/api/users/${id}`);
      // Refresh list
      setUsers(prev => prev.filter(u => u.id !== id));
    } catch (err) {
      alert('Silme işlemi başarısız oldu.');
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto p-8">
        <p className="text-gray-400">Yükleniyor...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-8 bg-white/5 rounded-3xl backdrop-blur-xl border border-white/10">
      <button onClick={onBack} className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
        <ArrowLeft size={20} /> Geri Dön
      </button>
      <h2 className="text-3xl font-outfit font-black text-white mb-4">Kullanıcı Yönetimi</h2>
      <div className="space-y-4">
        {users.map(user => (
          <div key={user.id} className="flex items-center justify-between p-4 bg-black/20 rounded-2xl border border-white/5">
            <div className="flex items-center gap-3">
              <User size={20} className="text-gray-400" />
              <span className="text-white">{user.username}</span>
            </div>
            <button
              onClick={() => handleDelete(user.id)}
              className="flex items-center gap-1 text-red-500 hover:text-white"
            >
              <Trash2 size={16} /> Sil
            </button>
          </div>
        ))}
        {users.length === 0 && (
          <p className="text-gray-400">Kullanıcı bulunamadı.</p>
        )}
      </div>
    </div>
  );
}

export default UserManagement;
