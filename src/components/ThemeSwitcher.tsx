import { useState, useEffect } from 'react';
import { Moon, Sun, Plane } from 'lucide-react';

type Theme = 'dark' | 'light' | 'aviation';

const themes: { id: Theme; label: string; icon: React.ReactNode }[] = [
  { id: 'dark', label: 'Dark', icon: <Moon className="w-4 h-4" /> },
  { id: 'light', label: 'Light', icon: <Sun className="w-4 h-4" /> },
  { id: 'aviation', label: 'Aviation', icon: <Plane className="w-4 h-4" /> },
];

const ThemeSwitcher = () => {
  const [theme, setTheme] = useState<Theme>('dark');
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem('portfolio-theme') as Theme | null;
    if (savedTheme && ['dark', 'light', 'aviation'].includes(savedTheme)) {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    }
  }, []);

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('portfolio-theme', newTheme);
    setIsOpen(false);
  };

  const currentTheme = themes.find((t) => t.id === theme);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 hover:bg-muted border border-border text-foreground transition-all duration-200"
        aria-label="Toggle theme"
      >
        {currentTheme?.icon}
        <span className="text-xs font-medium hidden sm:inline">{currentTheme?.label}</span>
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full mt-2 z-50 bg-card border border-border rounded-lg shadow-lg overflow-hidden min-w-[140px]">
            {themes.map((t) => (
              <button
                key={t.id}
                onClick={() => handleThemeChange(t.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-muted/50 ${
                  theme === t.id ? 'bg-primary/10 text-primary' : 'text-foreground'
                }`}
              >
                {t.icon}
                <span>{t.label}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default ThemeSwitcher;
