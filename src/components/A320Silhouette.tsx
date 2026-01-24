const A320Silhouette = () => {
  return (
    <div className="fixed top-[15%] left-0 w-full h-20 pointer-events-none z-50 overflow-hidden">
      <div className="a320-fly" style={{ animationDuration: '45s' }}>
        {/* Pixel art A320 silhouette */}
        <svg
          width="80"
          height="24"
          viewBox="0 0 80 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="opacity-70"
        >
          {/* Fuselage */}
          <rect x="8" y="10" width="64" height="4" fill="hsl(var(--primary))" />
          <rect x="4" y="10" width="4" height="4" fill="hsl(var(--primary))" />
          <rect x="72" y="10" width="4" height="4" fill="hsl(var(--primary))" />
          <rect x="76" y="10" width="2" height="4" fill="hsl(var(--primary))" />
          
          {/* Nose */}
          <rect x="0" y="11" width="4" height="2" fill="hsl(var(--primary))" />
          
          {/* Tail */}
          <rect x="70" y="6" width="4" height="4" fill="hsl(var(--primary))" />
          <rect x="74" y="4" width="4" height="2" fill="hsl(var(--primary))" />
          <rect x="74" y="6" width="2" height="4" fill="hsl(var(--primary))" />
          
          {/* Wings */}
          <rect x="28" y="12" width="4" height="8" fill="hsl(var(--primary))" />
          <rect x="32" y="14" width="4" height="6" fill="hsl(var(--primary))" />
          <rect x="36" y="16" width="4" height="4" fill="hsl(var(--primary))" />
          <rect x="40" y="18" width="4" height="2" fill="hsl(var(--primary))" />
          
          <rect x="28" y="4" width="4" height="8" fill="hsl(var(--primary))" />
          <rect x="32" y="4" width="4" height="6" fill="hsl(var(--primary))" />
          <rect x="36" y="4" width="4" height="4" fill="hsl(var(--primary))" />
          <rect x="40" y="4" width="4" height="2" fill="hsl(var(--primary))" />
          
          {/* Engines */}
          <rect x="30" y="14" width="6" height="2" fill="hsl(var(--secondary))" />
          <rect x="30" y="8" width="6" height="2" fill="hsl(var(--secondary))" />
          
          {/* Cockpit windows */}
          <rect x="4" y="10" width="2" height="2" fill="hsl(var(--secondary))" />
        </svg>
      </div>
    </div>
  );
};

export default A320Silhouette;
