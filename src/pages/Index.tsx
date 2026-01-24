import Navigation from '@/components/Navigation';
import BentoGrid from '@/components/BentoGrid';
import Footer from '@/components/Footer';
import A320Silhouette from '@/components/A320Silhouette';

const Index = () => {
  return (
    <div className="min-h-screen bg-background relative">
      {/* A320 flies behind everything */}
      <A320Silhouette />
      
      {/* Content layer */}
      <div className="relative z-10">
        <Navigation />
        <main className="pt-20">
          <BentoGrid />
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default Index;
