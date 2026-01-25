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
    <section ref={heroRef} className="relative h-screen w-full overflow-hidden">
      <div
        className="absolute inset-0 w-full h-[120%]"
        style={{ transform: `translateY(${scrollY * 0.5}px)`, border: 'none' }}
      >
        <img
          src={mountainsHero}
          alt="Mountains"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background/30 via-transparent to-background" />
      </div>

      <div className="relative z-10 h-full flex flex-col justify-center items-center px-6 text-center">
        <h1 className="font-pixel text-3xl md:text-4xl lg:text-5xl text-foreground mb-4">
          Sooryah Prasath
        </h1>
        
        {/* REMOVED ALL ANIMATION CLASSES TEMPORARILY TO FORCE VISIBILITY */}
        <p className="font-pixel text-sm md:text-base text-primary mb-6 block">
          Senior Network Automation Engineer
        </p>
        
        <p className="text-lg md:text-xl text-muted-foreground max-w-xl mx-auto block">
          I solve network problems with modern automation using cloud solutions. I like mountains and planes.
        </p>
      </div>
    </section>
  );
};

export default HeroSection;