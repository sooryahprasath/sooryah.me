import { useEffect, useState, useRef } from 'react';
import mountainsHero from '@/assets/mountains-hero.jpg';

const HeroSection = () => {
  const [scrollY, setScrollY] = useState(0);
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (heroRef.current) {
        const rect = heroRef.current.getBoundingClientRect();
        if (rect.bottom > 0) {
          setScrollY(window.scrollY);
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <section
      ref={heroRef}
      className="relative h-screen w-full overflow-hidden"
    >
      {/* Parallax Background with theme-aware filter */}
      <div
        className="absolute inset-0 w-full h-[120%]"
        style={{
          transform: `translateY(${scrollY * 0.5}px)`,
          willChange: 'transform',
        }}
      >
        <img
          src={mountainsHero}
          alt="Dark moody mountains"
          className="w-full h-full object-cover transition-all duration-500"
          style={{
            filter: `brightness(var(--hero-brightness)) contrast(var(--hero-contrast)) saturate(var(--hero-saturate))`,
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background/30 via-transparent to-background" />
      </div>

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col justify-center items-center px-6">
        <div className="max-w-3xl text-center">
          <h1 className="font-pixel text-3xl md:text-4xl lg:text-5xl text-foreground mb-4 text-glow animate-fade-in">
            Sooryah Prasath
          </h1>
          <p
            className="font-pixel text-sm md:text-base text-primary mb-6 opacity-0"
            style={{ animation: 'fade-in 0.6s ease-out 0.2s forwards' }}
          >
            Senior Network Automation Engineer
          </p>
          <p
            className="text-lg md:text-xl text-muted-foreground max-w-xl mx-auto opacity-0"
            style={{ animation: 'fade-in 0.6s ease-out 0.4s forwards' }}
          >
            I solve network problems with modern automation using cloud solutions. I like mountains and planes.
          </p>
        </div>

        {/* Scroll indicator */}
        <div
          className="absolute bottom-12 left-1/2 -translate-x-1/2 opacity-0"
          style={{ animation: 'fade-in 0.6s ease-out 0.8s forwards' }}
        >
          <div className="w-6 h-10 border-2 border-primary/50 rounded-full flex justify-center p-2">
            <div className="w-1 h-2 bg-primary rounded-full animate-bounce" />
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
