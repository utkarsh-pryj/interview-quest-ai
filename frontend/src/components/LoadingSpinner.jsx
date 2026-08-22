import React from 'react';

export const LoadingSpinner = ({ text = "", size = "md" }) => {
  const pixelSize = size === 'sm' ? 16 : size === 'lg' ? 36 : 24;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
      <div
        style={{
          width: `${pixelSize}px`,
          height: `${pixelSize}px`,
          border: '2px solid #e0e7ff',
          borderTopColor: '#4f46e5',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }}
      />
      {text && <p style={{ fontSize: '11px', color: '#64748b', fontWeight: '500' }}>{text}</p>}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
