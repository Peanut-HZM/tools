import { create } from 'zustand';

interface DeviceStore {
  deviceId: string | null;
  deviceName: string;
  setDeviceId: (id: string) => void;
  setDeviceName: (name: string) => void;
}

export const useDeviceStore = create<DeviceStore>((set) => ({
  deviceId: null,
  deviceName: 'My Phone',
  setDeviceId: (id) => set({ deviceId: id }),
  setDeviceName: (name) => set({ deviceName: name })
}));
