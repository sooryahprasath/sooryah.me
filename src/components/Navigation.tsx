const Navigation = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-40 bg-background/80 backdrop-blur-md border-b border-border/50">
      <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="font-pixel text-primary text-sm hover:text-teal-glow transition-colors">
          &lt;NE/&gt;
        </a>

        <div className="flex items-center gap-8">
          <a
            href="#path"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Path
          </a>
          <a
            href="#works"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Works
          </a>
          <a
            href="#contact"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Contact
          </a>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
