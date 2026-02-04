import { useRef, useState } from 'react';
import { Compass, Crosshair, Shield, Container, Server, Send, Linkedin, Github } from 'lucide-react';
import mountainsHero from '@/assets/mountains-hero.jpg';

// Custom steering wheel icon
const SteeringWheelIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-8 h-8">
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="2.5" />
    <path d="M12 3v6.5M12 14.5v6.5M3 12h6.5M14.5 12h6.5" />
  </svg>
);

// Mountain tile with mouse parallax
const MountainTile = () => {
  const tileRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!tileRef.current) return;
    const rect = tileRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - rect.width / 2) / 25;
    const y = (e.clientY - rect.top - rect.height / 2) / 25;
    setTransform({ x, y });
  };

  const handleMouseLeave = () => {
    setTransform({ x: 0, y: 0 });
  };

  return (
    <div
      ref={tileRef}
      className="col-span-2 row-span-2 relative overflow-hidden rounded-2xl cursor-pointer group"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <img
        src={mountainsHero}
        alt="Moody mountains"
        className="absolute inset-0 w-[110%] h-[110%] object-cover transition-transform duration-300 ease-out"
        style={{
          transform: `translate(${transform.x}px, ${transform.y}px) scale(1.05)`,
          left: '-5%',
          top: '-5%',
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-card/80 via-transparent to-transparent" />
      <div className="absolute bottom-6 left-6 right-6">
        <p className="text-sm text-foreground/80 font-medium">Where I find clarity</p>
      </div>
    </div>
  );
};

// Identity tile
const IdentityTile = () => (
  <div className="col-span-2 bento-tile flex flex-col justify-center">
    <h1 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight mb-2">
      Sooryah Prasath
    </h1>
    <p className="text-primary font-medium text-lg">
      Senior Network Automation Engineer
    </p>
  </div>
);

// Bio tile
const BioTile = () => (
  <div className="col-span-2 md:col-span-1 bento-tile flex items-center">
    <p className="text-muted-foreground text-lg leading-relaxed">
      I solve network problems with modern automation using cloud solutions. I like mountains and planes.
    </p>
  </div>
);

// Work tiles
const WorkTile = ({ icon: Icon, title, tags, description }: { 
  icon: React.ElementType; 
  title: string; 
  tags: string[];
  description: string;
}) => (
  <div className="bento-tile group hover:-translate-y-1">
    <Icon className="w-8 h-8 text-primary mb-4" strokeWidth={1.5} />
    <h3 className="font-semibold text-foreground text-lg mb-2">{title}</h3>
    <div className="flex flex-wrap gap-2 mb-3">
      {tags.map((tag) => (
        <span key={tag} className="text-xs px-2 py-1 bg-secondary rounded-full text-muted-foreground">
          {tag}
        </span>
      ))}
    </div>
    <p className="text-sm text-muted-foreground">{description}</p>
  </div>
);

// Interest tiles
const InterestTile = ({ icon: Icon, label }: { icon: React.ElementType; label: string }) => (
  <div className="bento-tile flex flex-col items-center justify-center aspect-square hover:-translate-y-1 group">
    <div className="text-muted-foreground group-hover:text-primary transition-colors">
      {typeof Icon === 'function' && Icon.length === 0 ? <Icon /> : <Icon className="w-8 h-8" strokeWidth={1.5} />}
    </div>
    <span className="text-xs text-muted-foreground mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
      {label}
    </span>
  </div>
);

// Contact tile
const ContactTile = () => (
  <div className="col-span-2 bento-tile">
    <h3 className="font-semibold text-foreground text-lg mb-4">Let's Connect</h3>
    <div className="flex flex-wrap gap-3">
      <a
        href="mailto:hello@example.com"
        className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity"
      >
        <Send className="w-4 h-4" />
        Email
      </a>
      <a
        href="#"
        className="flex items-center gap-2 px-4 py-2 bg-secondary text-foreground rounded-lg hover:bg-secondary/80 transition-colors"
      >
        <Linkedin className="w-4 h-4" />
        LinkedIn
      </a>
      <a
        href="#"
        className="flex items-center gap-2 px-4 py-2 bg-secondary text-foreground rounded-lg hover:bg-secondary/80 transition-colors"
      >
        <Github className="w-4 h-4" />
        GitHub
      </a>
    </div>
  </div>
);

const BentoGrid = () => {
  return (
    <div className="max-w-6xl mx-auto px-6 py-20">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
        {/* Row 1: Identity + Mountain */}
        <IdentityTile />
        <MountainTile />

        {/* Row 2: Bio + Interests */}
        <BioTile />
        <InterestTile icon={Compass} label="Explore" />
        <InterestTile icon={Crosshair} label="Focus" />
        <InterestTile icon={SteeringWheelIcon} label="Drive" />

        {/* Row 3: Works */}
        <WorkTile
          icon={Shield}
          title="Palo Alto APIs"
          tags={["Python", "REST API", "Security"]}
          description="Automated firewall rule deployment and policy management via PAN-OS XML API."
        />
        <WorkTile
          icon={Container}
          title="Docker Infrastructure"
          tags={["Docker", "Compose", "CI/CD"]}
          description="Containerized network monitoring stack: Prometheus, Grafana, SNMP exporters."
        />
        <WorkTile
          icon={Server}
          title="Homelab"
          tags={["Proxmox", "pfSense", "Ansible"]}
          description="Production-grade home infrastructure. VLANs, VPNs, automated backups."
        />
        
        {/* Contact spans remaining space */}
        <ContactTile />
      </div>
    </div>
  );
};

export default BentoGrid;