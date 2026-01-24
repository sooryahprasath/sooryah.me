import Navigation from '@/components/Navigation';
import HeroSection from '@/components/HeroSection';
import PathSection from '@/components/PathSection';
import WorksSection from '@/components/WorksSection';
import ContactSection from '@/components/ContactSection';
import Footer from '@/components/Footer';
import A320Silhouette from '@/components/A320Silhouette';

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <A320Silhouette />
      <Navigation />
      <HeroSection />
      <PathSection />
      <WorksSection />
      <ContactSection />
      <Footer />
    </div>
  );
};

export default Index;
