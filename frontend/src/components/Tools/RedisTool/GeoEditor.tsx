import React, { useState, useEffect } from 'react';
import { getGeoInfo, operateGeo } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const GeoEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [member, setMember] = useState('');
  const [longitude, setLongitude] = useState('');
  const [latitude, setLatitude] = useState('');

  const load = async () => {
    try {
      const data = await getGeoInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load geo', 'error');
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleAdd = async () => {
    if (!member || !longitude || !latitude) return;
    try {
      await operateGeo(configId, keyName, {
        action: 'add',
        member,
        longitude: parseFloat(longitude),
        latitude: parseFloat(latitude)
      });
      addToast('Location added', 'success');
      setMember('');
      setLongitude('');
      setLatitude('');
      load();
    } catch (e) {
      addToast('Failed to add', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="border border-slate-700 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr><th className="px-3 py-2 text-left">Member</th><th className="px-3 py-2 text-left">Longitude</th><th className="px-3 py-2 text-left">Latitude</th></tr>
          </thead>
          <tbody>
            {info?.members?.map((m: any) => (
              <tr key={m.member} className="border-t border-slate-700">
                <td className="px-3 py-2 text-slate-300">{m.member}</td>
                <td className="px-3 py-2 font-mono text-slate-400">{m.longitude?.toFixed(6) || '-'}</td>
                <td className="px-3 py-2 font-mono text-slate-400">{m.latitude?.toFixed(6) || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border border-slate-700 rounded-md p-3 space-y-2">
        <div className="text-sm font-medium text-slate-300">Add Location</div>
        <div className="flex space-x-2">
          <input value={member} onChange={e => setMember(e.target.value)} placeholder="Member" className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <input value={longitude} onChange={e => setLongitude(e.target.value)} placeholder="Longitude" className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <input value={latitude} onChange={e => setLatitude(e.target.value)} placeholder="Latitude" className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          <button onClick={handleAdd} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Add</button>
        </div>
      </div>
    </div>
  );
};
