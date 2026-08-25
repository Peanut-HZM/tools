import React, { useState, useEffect } from 'react';
import { getGeoInfo, operateGeo } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

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
      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-canvas text-ink-muted">
            <tr><th className="px-3 py-2 text-left">Member</th><th className="px-3 py-2 text-left">Longitude</th><th className="px-3 py-2 text-left">Latitude</th></tr>
          </thead>
          <tbody>
            {info?.members?.map((m: any) => (
              <tr key={m.member} className="border-t border-border">
                <td className="px-3 py-2 text-ink-muted">{m.member}</td>
                <td className="px-3 py-2 font-mono text-ink-muted">{m.longitude?.toFixed(6) || '-'}</td>
                <td className="px-3 py-2 font-mono text-ink-muted">{m.latitude?.toFixed(6) || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border border-border rounded-md p-3 space-y-2">
        <div className="text-sm font-medium text-ink-muted">Add Location</div>
        <div className="flex space-x-2">
          <Input value={member} onChange={e => setMember(e.target.value)} placeholder="Member" className="flex-1" />
          <Input value={longitude} onChange={e => setLongitude(e.target.value)} placeholder="Longitude" className="w-28" />
          <Input value={latitude} onChange={e => setLatitude(e.target.value)} placeholder="Latitude" className="w-28" />
          <Button size="sm" onClick={handleAdd}>Add</Button>
        </div>
      </div>
    </div>
  );
};
