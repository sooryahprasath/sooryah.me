import { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';

type Theme = 'light' | 'dark';

const ThemeSwitcher = () => {
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => {
    const savedTheme = localStorage.getItem('portfolio-theme') as Theme | null;
    if (savedTheme && ['light', 'dark'].includes(savedTheme)) {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('portfolio-theme', newTheme);
  };

  return (
    <button
      onClick={toggleTheme}
      className="relative w-14 h-8 bg-secondary rounded-full p-1 transition-colors duration-300 hover:bg-secondary/80"
      aria-label="Toggle theme"
    >
      <div
        className={`absolute top-1 w-6 h-6 bg-card rounded-full shadow-sm flex items-center justify-center transition-transform duration-300 ${
          theme === 'dark' ? 'translate-x-6' : 'translate-x-0'
        }`}
      >
        {theme === 'light' ? (
          <Sun className="w-3.5 h-3.5 text-primary" />
        ) : (
          <Moon className="w-3.5 h-3.5 text-primary" />
        )}
      </div>
    </button>
  );
};

export default ThemeSwitcher;
