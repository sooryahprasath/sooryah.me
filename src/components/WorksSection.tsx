import { Server, Container, Home } from 'lucide-react';

interface Project {
  icon: React.ReactNode;
  title: string;
  tags: string[];
  description: string;
}

const projects: Project[] = [
  {
    icon: <Server className="w-6 h-6" />,
    title: "Palo Alto APIs",
    tags: ["Python", "REST API", "Security"],
    description: "Automated firewall rule deployment and policy management via PAN-OS XML API. Reduced change implementation time by 80%.",
  },
  {
    icon: <Container className="w-6 h-6" />,
    title: "Docker Infrastructure",
    tags: ["Docker", "Compose", "CI/CD"],
    description: "Containerized network monitoring stack: Prometheus, Grafana, SNMP exporters. Deployed across multiple environments.",
  },
  {
    icon: <Home className="w-6 h-6" />,
    title: "Homelab",
    tags: ["Proxmox", "pfSense", "Ansible"],
    description: "Production-grade home infrastructure. VLANs, VPNs, automated backups. Testing ground for enterprise solutions.",
  },
];

const WorksSection = () => {
  return (
    <section id="works" className="py-24 px-6 bg-background">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-pixel text-3xl md:text-4xl text-primary mb-16 text-center">
          // WORKS
        </h2>

        <div className="grid md:grid-cols-3 gap-6">
          {projects.map((project, index) => (
            <div
              key={project.title}
              className="group bg-card border border-border rounded-lg p-6 card-hover"
              style={{
                opacity: 0,
                animation: `fade-in 0.5s ease-out ${index * 0.15}s forwards`,
              }}
            >
              {/* Icon */}
              <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center text-primary mb-4 group-hover:bg-primary group-hover:text-primary-foreground transition-colors duration-300">
                {project.icon}
              </div>

              {/* Title */}
              <h3 className="font-pixel text-lg text-foreground mb-3">
                {project.title}
              </h3>

              {/* Tags */}
              <div className="flex flex-wrap gap-2 mb-4">
                {project.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs px-2 py-1 rounded bg-muted text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              {/* Description */}
              <p className="text-sm text-muted-foreground leading-relaxed">
                {project.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default WorksSection;
