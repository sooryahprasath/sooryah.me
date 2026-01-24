import ThemeSwitcher from './ThemeSwitcher';

const Navigation = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/70 backdrop-blur-xl border-b border-border/30">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="text-primary font-semibold text-lg tracking-tight hover:opacity-80 transition-opacity">
          SP
        </a>
        <ThemeSwitcher />
      </div>
    </nav>
  );
};

export default Navigation;
