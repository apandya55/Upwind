import React from "react";
import { HeroSection } from "@/components/ui/dynamic-hero";

const DemoOne: React.FC = () => {
  return (
    <div>
      <HeroSection
        heading="Dynamic Design, Direct Action"
        tagline="Experience a hero section that not only looks great but actively leads your audience. Get started with a click."
        buttonText="Learn More"
        imageUrl="https://cdn.21st.dev/assets/mirror/54/5463629f1d5c925ed9edc8714d89f8d639ba720eccaa41d7cb4d5419ff640ec1.jpg"
        videoUrl="https://cdn.21st.dev/assets/mirror/3b/3bb938fb70049e3e45f533b37ccae995ae96516e04c2f35b0c1142e47b2a39c1.mp4" // A sample video
      />
    </div>
  );
};

export { DemoOne };

