import React, { useState } from 'react';
import { Smartphone, Tablet, Monitor } from 'lucide-react';

interface Screenshots {
  mobile?: string;
  tablet?: string;
  desktop?: string;
}

interface VibeScreenshotsProps {
  screenshots: Screenshots;
  onOpenLightbox: (url: string, desc: string) => void;
}

export function VibeScreenshots({ screenshots, onOpenLightbox }: VibeScreenshotsProps) {
  type DeviceType = 'desktop' | 'tablet' | 'mobile';
  const [activeTab, setActiveTab] = useState<DeviceType>('desktop');

  const activeImage = screenshots[activeTab];

  return (
    <div className="vibe-screenshots bg-gray-900 rounded-xl overflow-hidden shadow-lg border border-gray-800">
      {/* Tab Header */}
      <div className="flex border-b border-gray-800 bg-gray-950">
        {([
          { id: 'desktop' as DeviceType, icon: Monitor, label: 'Desktop' },
          { id: 'tablet' as DeviceType, icon: Tablet, label: 'Tablet' },
          { id: 'mobile' as DeviceType, icon: Smartphone, label: 'Mobile' }
        ] as const).map(device => (
          <button
            key={device.id}
            onClick={() => setActiveTab(device.id)}
            className={`flex-1 py-3 text-sm font-medium flex items-center justify-center transition-colors
              ${activeTab === device.id ? 'bg-gray-800 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-900'}`}
          >
            <device.icon size={16} className="mr-2" />
            {device.label}
          </button>
        ))}
      </div>

      {/* Viewport */}
      <div className="relative bg-gray-900 flex items-center justify-center p-8 min-h-[400px]">
        {activeImage ? (
          <div 
            className="relative cursor-zoom-in transition-transform hover:scale-[1.02]"
            onClick={() => onOpenLightbox(activeImage, `${activeTab} Screenshot`)}
          >
            <img 
              src={activeImage} 
              alt={`${activeTab} screenshot`} 
              className={`rounded-lg shadow-2xl border border-gray-700
                ${activeTab === 'mobile' ? 'max-w-[300px]' : activeTab === 'tablet' ? 'max-w-[500px]' : 'max-w-full'}`} 
            />
            <div className="absolute inset-0 bg-black/0 hover:bg-black/10 transition-colors rounded-lg flex items-center justify-center group">
              <span className="opacity-0 group-hover:opacity-100 bg-black/75 text-white px-3 py-1 rounded-full text-xs font-medium backdrop-blur-sm">
                Click to Enlarge
              </span>
            </div>
          </div>
        ) : (
          <div className="text-center text-gray-600">
            <div className="mb-2 text-4xl">📷</div>
            <p>No screenshot available for {activeTab}</p>
          </div>
        )}
      </div>
    </div>
  );
}

