const A320Silhouette = () => {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      <div className="absolute top-[25%] left-0 a320-fly">
        {/* Minimalist A320 silhouette */}
        <svg
          width="120"
          height="36"
          viewBox="0 0 80 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          style={{ color: 'hsl(var(--muted-foreground))' }}
          className="opacity-10"
        >
          {/* Fuselage */}
          <rect x="8" y="10" width="64" height="4" fill="currentColor" />
          <rect x="4" y="10" width="4" height="4" fill="currentColor" />
          <rect x="72" y="10" width="4" height="4" fill="currentColor" />
          <rect x="76" y="10" width="2" height="4" fill="currentColor" />
          
          {/* Nose */}
          <rect x="0" y="11" width="4" height="2" fill="currentColor" />
          
          {/* Tail */}
          <rect x="70" y="6" width="4" height="4" fill="currentColor" />
          <rect x="74" y="4" width="4" height="2" fill="currentColor" />
          <rect x="74" y="6" width="2" height="4" fill="currentColor" />
          
          {/* Wings */}
          <rect x="28" y="12" width="4" height="8" fill="currentColor" />
          <rect x="32" y="14" width="4" height="6" fill="currentColor" />
          <rect x="36" y="16" width="4" height="4" fill="currentColor" />
          <rect x="40" y="18" width="4" height="2" fill="currentColor" />
          
          <rect x="28" y="4" width="4" height="8" fill="currentColor" />
          <rect x="32" y="4" width="4" height="6" fill="currentColor" />
          <rect x="36" y="4" width="4" height="4" fill="currentColor" />
          <rect x="40" y="4" width="4" height="2" fill="currentColor" />
          
          {/* Engines */}
          <rect x="30" y="14" width="6" height="2" fill="currentColor" />
          <rect x="30" y="8" width="6" height="2" fill="currentColor" />
        </svg>
      </div>
    </div>
  );
};

export default A320Silhouette;
