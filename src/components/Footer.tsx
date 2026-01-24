import { Compass, Crosshair, Circle } from 'lucide-react';

// Custom steering wheel icon as a simple SVG
const SteeringWheelIcon = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="w-5 h-5"
  >
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="3" />
    <line x1="12" y1="3" x2="12" y2="9" />
    <line x1="12" y1="15" x2="12" y2="21" />
    <line x1="3" y1="12" x2="9" y2="12" />
    <line x1="15" y1="12" x2="21" y2="12" />
  </svg>
);

const Footer = () => {
  return (
    <footer className="py-10 px-6 bg-background border-t border-border theme-transition">
      <div className="max-w-5xl mx-auto flex flex-col items-center gap-6">
        {/* Hobby Icons */}
        <div className="flex items-center gap-8">
          <div className="group flex flex-col items-center gap-2">
            <Compass className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" strokeWidth={1.5} />
            <span className="text-xs text-muted-foreground/60 opacity-0 group-hover:opacity-100 transition-opacity">Explore</span>
          </div>
          <div className="group flex flex-col items-center gap-2">
            <Crosshair className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" strokeWidth={1.5} />
            <span className="text-xs text-muted-foreground/60 opacity-0 group-hover:opacity-100 transition-opacity">Focus</span>
          </div>
          <div className="group flex flex-col items-center gap-2">
            <SteeringWheelIcon />
            <span className="text-xs text-muted-foreground/60 opacity-0 group-hover:opacity-100 transition-opacity">Drive</span>
          </div>
        </div>

        {/* Footer text */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 w-full pt-4 border-t border-border/50">
          <p className="text-sm text-muted-foreground">
            © 2024 Sooryah Prasath — Built with logic and caffeine
          </p>
          <p className="font-pixel text-xs text-primary/60">
            // END_OF_FILE
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
