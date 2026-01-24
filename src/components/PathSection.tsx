interface TimelineItem {
  year: string;
  title: string;
  company: string;
  description: string;
}

const timelineData: TimelineItem[] = [
  {
    year: "2024",
    title: "Senior Network Automation Engineer",
    company: "Enterprise Corp",
    description: "Leading infrastructure automation initiatives with Python, Ansible, and Terraform.",
  },
  {
    year: "2022",
    title: "Network Engineer II",
    company: "Tech Solutions Inc",
    description: "Designed and deployed SD-WAN solutions across 50+ sites. Palo Alto firewall management.",
  },
  {
    year: "2021",
    title: "Network Engineer",
    company: "DataCenter Systems",
    description: "Cisco ACI fabric administration. BGP/OSPF routing optimization.",
  },
  {
    year: "2020",
    title: "Junior Network Engineer",
    company: "ISP Networks",
    description: "NOC operations, troubleshooting L2/L3 issues, monitoring infrastructure.",
  },
  {
    year: "2019",
    title: "IT Support Specialist",
    company: "StartupHub",
    description: "Network setup and maintenance for growing startup environment.",
  },
];

const PathSection = () => {
  return (
    <section id="path" className="py-24 px-6 bg-charcoal-deep">
      <div className="max-w-4xl mx-auto">
        <h2 className="font-pixel text-3xl md:text-4xl text-primary mb-16 text-center">
          // PATH
        </h2>

        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-4 md:left-1/2 md:-translate-x-px top-0 bottom-0 w-0.5 timeline-line" />

          {/* Timeline items */}
          <div className="space-y-16">
            {timelineData.map((item, index) => (
              <div
                key={item.year}
                className="relative flex items-start"
              >
                {/* Marker */}
                <div className="absolute left-4 md:left-1/2 -translate-x-1/2 timeline-marker z-10 mt-1" />

                {/* Left side (even items on desktop) */}
                <div className={`hidden md:block md:w-1/2 ${index % 2 === 0 ? 'pr-12 text-right' : ''}`}>
                  {index % 2 === 0 && (
                    <>
                      <span className="font-pixel text-primary text-sm">{item.year}</span>
                      <h3 className="text-lg font-medium text-foreground mt-1">{item.title}</h3>
                      <p className="text-light-blue text-sm mt-0.5">{item.company}</p>
                      <p className="text-muted-foreground text-sm mt-2">{item.description}</p>
                    </>
                  )}
                </div>

                {/* Right side (odd items on desktop) */}
                <div className={`ml-12 md:ml-0 md:w-1/2 ${index % 2 === 1 ? 'md:pl-12' : 'md:hidden'}`}>
                  {(index % 2 === 1 || true) && (
                    <div className="md:hidden block">
                      <span className="font-pixel text-primary text-sm">{item.year}</span>
                      <h3 className="text-lg font-medium text-foreground mt-1">{item.title}</h3>
                      <p className="text-light-blue text-sm mt-0.5">{item.company}</p>
                      <p className="text-muted-foreground text-sm mt-2">{item.description}</p>
                    </div>
                  )}
                  {index % 2 === 1 && (
                    <div className="hidden md:block">
                      <span className="font-pixel text-primary text-sm">{item.year}</span>
                      <h3 className="text-lg font-medium text-foreground mt-1">{item.title}</h3>
                      <p className="text-light-blue text-sm mt-0.5">{item.company}</p>
                      <p className="text-muted-foreground text-sm mt-2">{item.description}</p>
                    </div>
                  )}
                </div>

                {/* Hidden placeholder for even items on right side */}
                {index % 2 === 0 && (
                  <div className="hidden md:block md:w-1/2 md:pl-12">
                    <div className="invisible">
                      <span className="font-pixel text-primary text-sm">{item.year}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default PathSection;
