import { useFrame } from '@react-three/fiber';
import { Vector3 } from 'three';

const isMobile = window.innerWidth < 768;
const targetPosition = new Vector3();

export const InteractiveCameraRig = () => {
  useFrame((state) => {
    const { mouse } = state;
    if (isMobile) {
      const t = state.clock.getElapsedTime();
      targetPosition.set(Math.sin(t * 0.1) * 2, 0.5, Math.cos(t * 0.1) * 2);
    } else {
      targetPosition.set(mouse.x * 2, mouse.y * 2, 4);
    }
    state.camera.position.lerp(targetPosition, 0.05);
    state.camera.lookAt(0, 0, 0);
  });
  return null; 
};