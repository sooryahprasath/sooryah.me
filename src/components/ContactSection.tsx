import { Send, Linkedin, Github } from 'lucide-react';

const ContactSection = () => {
  return (
    <section id="contact" className="py-24 px-6 bg-charcoal-deep">
      <div className="max-w-2xl mx-auto text-center">
        <h2 className="font-pixel text-3xl md:text-4xl text-primary mb-8">
          // CONTACT
        </h2>

        <p className="text-muted-foreground mb-12">
          Let's connect. I'm always open to discussing network automation, infrastructure challenges, or just talking about planes.
        </p>

        <div className="flex justify-center gap-6">
          <a
            href="mailto:hello@example.com"
            className="group flex items-center gap-3 px-6 py-3 bg-card border border-border rounded-lg card-hover"
          >
            <Send className="w-5 h-5 text-primary group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform duration-300" />
            <span className="text-foreground">Email</span>
          </a>

          <a
            href="https://linkedin.com"
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 px-6 py-3 bg-card border border-border rounded-lg card-hover"
          >
            <Linkedin className="w-5 h-5 text-secondary group-hover:scale-110 transition-transform duration-300" />
            <span className="text-foreground">LinkedIn</span>
          </a>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 px-6 py-3 bg-card border border-border rounded-lg card-hover"
          >
            <Github className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors duration-300" />
            <span className="text-foreground">GitHub</span>
          </a>
        </div>
      </div>
    </section>
  );
};

export default ContactSection;
