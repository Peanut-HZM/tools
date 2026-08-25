/**
 * CrossShare 入口卡片组件
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';

interface CrossShareCardProps {
  progress?: number;
  transferredFiles?: number;
}

const CrossShareCard: React.FC<CrossShareCardProps> = ({
  progress = 0,
  transferredFiles = 0,
}) => {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate('/tools/cross-share')}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 cursor-pointer transform transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/30"
    >
      {/* Animated Background Pattern */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-0 left-0 w-40 h-40 bg-white rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-0 w-60 h-60 bg-yellow-400 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      {/* Content */}
      <div className="relative p-8">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {/* Badge */}
            <div className="inline-flex items-center px-3 py-1 bg-accent-warning/20 border border-yellow-400 text-yellow-300 rounded-full text-xs font-semibold mb-4">
              ✨ 跨设备共享
            </div>

            {/* Title */}
            <h3 className="text-3xl font-bold text-ink-inverse mb-2">
              📡 CrossShare 设备传传
            </h3>
            <p className="text-ink-inverse/80 mb-4 max-w-xl">
              跨设备消息和文件共享 | 登录即用，全平台同步
            </p>

            {/* Features */}
            <div className="flex flex-wrap gap-3 mb-6">
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-ink-inverse rounded-full text-sm">
                💬 消息同步
              </span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-ink-inverse rounded-full text-sm">
                📁 文件传输
              </span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-ink-inverse rounded-full text-sm">
                📋 剪贴板
              </span>
              <span className="px-3 py-1 bg-white/10 backdrop-blur-sm text-ink-inverse rounded-full text-sm">
                📱 多设备
              </span>
            </div>

            {/* Stats */}
            {transferredFiles > 0 && (
              <div className="mb-4">
                <div className="text-ink-inverse/60 text-sm">
                  已传输 {transferredFiles} 个文件
                </div>
              </div>
            )}

            {/* CTA Button */}
            <button className="px-6 py-3 bg-yellow-500 hover:bg-yellow-600 text-black font-semibold rounded-xl transition-colors inline-flex items-center space-x-2">
              <span>打开 CrossShare</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>

          {/* Decorative Icon */}
          <div className="hidden lg:block text-8xl opacity-50">
            🔄
          </div>
        </div>
      </div>
    </div>
  );
};

export default CrossShareCard;
