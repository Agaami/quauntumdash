import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { type ReactNode } from 'react';

interface AnalysisCardProps {
  title: string;
  children: ReactNode;
}

export const AnalysisCard = ({ title, children }: AnalysisCardProps) => {
  // --- 3D Hover Logic ---
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const mouseX = useSpring(x, { stiffness: 100, damping: 20 });
  const mouseY = useSpring(y, { stiffness: 100, damping: 20 });

  // Create a 3D tilt effect
  const rotateX = useTransform(mouseY, [-0.5, 0.5], ['7.5deg', '-7.5deg']);
  const rotateY = useTransform(mouseX, [-0.5, 0.5], ['-7.5deg', '7.5deg']);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    // Convert mouse position to a range from -0.5 to 0.5
    const xPct = mouseX / width - 0.5;
    const yPct = mouseY / height - 0.5;

    x.set(xPct);
    y.set(yPct);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };
  // --- End 3D Logic ---

  return (
    <motion.div
      // Use a pure white, non-frosted card for better shadow visibility
      className="rounded-lg border border-border-light bg-white p-6 shadow-lg"
      style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div style={{ transform: "translateZ(50px)" }}> {/* Lifts content */}
        <h3 className="text-lg font-semibold text-text-dark mb-4">
          {title}
        </h3>
        <div className="text-text-light">
          {children}
        </div>
      </div>
    </motion.div>
  );
};