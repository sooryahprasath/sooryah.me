import ThemeSwitcher from './ThemeSwitcher';

const Navigation = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-40 bg-background/80 backdrop-blur-md border-b border-border/50 theme-transition">
      <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="font-pixel text-primary text-sm hover:text-teal-glow transition-colors">
          &lt;SP/&gt;
        </a>

        <div className="flex items-center gap-6 md:gap-8">
          <a
            href="#path"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors hidden sm:block"
          >
            Path
          </a>
          <a
            href="#works"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors hidden sm:block"
          >
            Works
          </a>
          <a
            href="#contact"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors hidden sm:block"
          >
            Contact
          </a>
          <ThemeSwitcher />
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
