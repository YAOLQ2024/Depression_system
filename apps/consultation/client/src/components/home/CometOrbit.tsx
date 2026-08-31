import { useMemo } from "react";

/** 彗星轨道与流星光焰集中配置参数，便于后续快速微调视觉效果与运动节奏。 */
export const COMET_CONFIG = {
  orbitDuration: 6.5,
  trailAngle: 75,
  headWidth: 18,
  headLength: 28,
  outerRadius: 396,
  innerRadius: 374,
  trackStrokeWidth: 1.65,
  trackColor: "rgba(14, 165, 233, 0.76)",
  innerTrackColor: "rgba(37, 99, 235, 0.7)",
  glowIntensity: 1.0,
} as const;

type CometOrbitProps = {
  className?: string;
};

/** AI Studio reference implementation, copied into the application instead of referenced from refer/. */
export function CometOrbit({ className = "" }: CometOrbitProps) {
  const { orbitDuration, trailAngle, headWidth, headLength, outerRadius, innerRadius, trackStrokeWidth, trackColor, innerTrackColor } = COMET_CONFIG;
  const center = 400;
  const trackMidRadius = (outerRadius + innerRadius) / 2;

  const interpolateColor = (color1: [number, number, number], color2: [number, number, number], factor: number) => {
    const value = Math.max(0, Math.min(1, factor));
    const red = Math.round(color1[0] + (color2[0] - color1[0]) * value);
    const green = Math.round(color1[1] + (color2[1] - color1[1]) * value);
    const blue = Math.round(color1[2] + (color2[2] - color1[2]) * value);
    return `rgb(${red}, ${green}, ${blue})`;
  };

  const segments = useMemo(() => {
    const segmentCount = 80;
    const segmentList: Array<{ path: string; fill: string; opacity: number }> = [];
    const headColor: [number, number, number] = [235, 248, 255];
    const middleColorOne: [number, number, number] = [56, 189, 248];
    const middleColorTwo: [number, number, number] = [2, 132, 199];
    const tailColor: [number, number, number] = [30, 58, 138];

    for (let index = 0; index < segmentCount; index += 1) {
      const progressStart = index / segmentCount;
      const progressEnd = (index + 1) / segmentCount;
      const progress = (progressStart + progressEnd) / 2;
      const startRadians = (-progressStart * trailAngle - 90) * (Math.PI / 180);
      const endRadians = (-progressEnd * trailAngle - 90) * (Math.PI / 180);
      const startWidth = (headWidth / 2) * Math.pow(1 - progressStart, 1.35);
      const endWidth = (headWidth / 2) * Math.pow(1 - progressEnd, 1.35);
      const startOuterX = center + (trackMidRadius + startWidth) * Math.cos(startRadians);
      const startOuterY = center + (trackMidRadius + startWidth) * Math.sin(startRadians);
      const endOuterX = center + (trackMidRadius + endWidth) * Math.cos(endRadians);
      const endOuterY = center + (trackMidRadius + endWidth) * Math.sin(endRadians);
      const endInnerX = center + (trackMidRadius - endWidth) * Math.cos(endRadians);
      const endInnerY = center + (trackMidRadius - endWidth) * Math.sin(endRadians);
      const startInnerX = center + (trackMidRadius - startWidth) * Math.cos(startRadians);
      const startInnerY = center + (trackMidRadius - startWidth) * Math.sin(startRadians);
      const path = `M ${startOuterX.toFixed(2)} ${startOuterY.toFixed(2)} L ${endOuterX.toFixed(2)} ${endOuterY.toFixed(2)} L ${endInnerX.toFixed(2)} ${endInnerY.toFixed(2)} L ${startInnerX.toFixed(2)} ${startInnerY.toFixed(2)} Z`;

      const fill = progress <= 0.25
        ? interpolateColor(headColor, middleColorOne, progress / 0.25)
        : progress <= 0.6
          ? interpolateColor(middleColorOne, middleColorTwo, (progress - 0.25) / 0.35)
          : interpolateColor(middleColorTwo, tailColor, (progress - 0.6) / 0.4);
      segmentList.push({ path, fill, opacity: Math.max(0, Math.min(1, Math.pow(1 - progress, 1.5))) });
    }
    return segmentList;
  }, [headWidth, trackMidRadius, trailAngle]);

  const headCenterX = center;
  const headCenterY = center - trackMidRadius;
  const orbitParticles = Array.from({ length: 18 }, (_, index) => {
    const angle = ((index * 37 - 90) * Math.PI) / 180;
    const radius = index % 3 === 0 ? outerRadius : index % 3 === 1 ? innerRadius : trackMidRadius;
    return {
      key: index,
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
      radius: index % 4 === 0 ? 2.9 : index % 4 === 1 ? 2.1 : 1.45,
      delay: `${-(index % 7) * 0.52}s`,
    };
  });
  const cometParticles = Array.from({ length: 14 }, (_, index) => {
    const angle = ((-90 - index * 5.2) * Math.PI) / 180;
    const radius = trackMidRadius + ((index % 3) - 1) * 7;
    return {
      key: index,
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
      radius: Math.max(1.15, 3.2 - index * 0.14),
      opacity: Math.max(0.18, 0.92 - index * 0.05),
      delay: `${-index * 0.12}s`,
    };
  });

  return (
    <div className={`pointer-events-none absolute inset-0 select-none ${className}`}>
      <svg className="absolute inset-0 h-full w-full overflow-visible" viewBox="0 0 800 800" fill="none" aria-hidden="true">
        <defs>
          <filter id="comet-track-glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.2" /></filter>
          <filter id="comet-particle-glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.2" /></filter>
        </defs>
        <circle cx={center} cy={center} r={outerRadius} stroke="#0ea5e9" strokeOpacity="0.28" strokeWidth={trackStrokeWidth * 5} filter="url(#comet-track-glow)" />
        <circle cx={center} cy={center} r={innerRadius} stroke="#2563eb" strokeOpacity="0.25" strokeWidth={trackStrokeWidth * 5} filter="url(#comet-track-glow)" />
        <circle cx={center} cy={center} r={outerRadius} stroke={trackColor} strokeWidth={trackStrokeWidth} />
        <circle cx={center} cy={center} r={innerRadius} stroke={innerTrackColor} strokeWidth={trackStrokeWidth} />
        <circle cx={center} cy={center} r={outerRadius} stroke="#e0f2fe" strokeOpacity="0.62" strokeWidth="0.52" />
        <circle cx={center} cy={center} r={innerRadius} stroke="#bfdbfe" strokeOpacity="0.52" strokeWidth="0.48" />
        {orbitParticles.map((particle) => (
          <g key={`orbit-particle-${particle.key}`} style={{ animation: "orbitParticlePulse 2.8s ease-in-out infinite", animationDelay: particle.delay }}>
            <circle cx={particle.x} cy={particle.y} r={particle.radius * 2.5} fill="#38bdf8" fillOpacity="0.3" filter="url(#comet-particle-glow)" />
            <circle cx={particle.x} cy={particle.y} r={particle.radius} fill="#e0f2fe" fillOpacity="0.9" />
          </g>
        ))}
      </svg>

      <div className="absolute inset-0" style={{ animation: `cometOrbitSpin ${orbitDuration}s linear infinite`, willChange: "transform", transformOrigin: "50% 50%" }}>
        <svg className="h-full w-full" viewBox="0 0 800 800" fill="none" aria-hidden="true">
          <defs>
            <filter id="comet-glow-ambient" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur in="SourceGraphic" stdDeviation="14" result="blurWide" /></filter>
            <filter id="comet-glow-plasma" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blurMid" /></filter>
            <filter id="comet-glow-crisp" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blurCrisp" /></filter>
            <radialGradient id="cometHeadCoreGrad" cx="65%" cy="50%" r="50%"><stop offset="0%" stopColor="#ffffff" stopOpacity="1" /><stop offset="35%" stopColor="#bae6fd" stopOpacity="0.95" /><stop offset="70%" stopColor="#38bdf8" stopOpacity="0.75" /><stop offset="100%" stopColor="#0284c7" stopOpacity="0" /></radialGradient>
            <linearGradient id="cometHeadFlameGrad" x1="100%" y1="50%" x2="0%" y2="50%"><stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" /><stop offset="25%" stopColor="#67e8f9" stopOpacity="0.8" /><stop offset="70%" stopColor="#0284c7" stopOpacity="0.3" /><stop offset="100%" stopColor="#1e3a8a" stopOpacity="0" /></linearGradient>
          </defs>

          <g filter="url(#comet-glow-ambient)" opacity="0.4">
            {segments.map((segment, index) => <path key={`glow-ambient-${index}`} d={segment.path} fill="#0284c7" opacity={segment.opacity * 0.7} />)}
            <circle cx={headCenterX} cy={headCenterY} r={headWidth * 1.8} fill="#38bdf8" opacity="0.8" />
          </g>
          <g filter="url(#comet-glow-plasma)" opacity="0.85">
            {segments.map((segment, index) => <path key={`glow-plasma-${index}`} d={segment.path} fill={segment.fill} opacity={segment.opacity} />)}
            <ellipse cx={headCenterX} cy={headCenterY} rx={headLength * 0.65} ry={headWidth * 0.7} fill="url(#cometHeadFlameGrad)" />
          </g>
          <g>{segments.map((segment, index) => <path key={`trail-entity-${index}`} d={segment.path} fill={segment.fill} opacity={segment.opacity} />)}</g>
          <g>
            <ellipse cx={headCenterX + 3} cy={headCenterY} rx={headLength * 0.55} ry={headWidth * 0.55} fill="#38bdf8" opacity="0.9" filter="url(#comet-glow-crisp)" />
            <ellipse cx={headCenterX} cy={headCenterY} rx={headLength * 0.45} ry={headWidth * 0.42} fill="url(#cometHeadCoreGrad)" />
            <ellipse cx={headCenterX + 4} cy={headCenterY} rx={headLength * 0.22} ry={headWidth * 0.22} fill="#ffffff" opacity="1" />
          </g>
          <g>
            {cometParticles.map((particle) => (
              <g key={`comet-particle-${particle.key}`} style={{ animation: "cometParticlePulse 1.35s ease-in-out infinite", animationDelay: particle.delay }}>
                <circle cx={particle.x} cy={particle.y} r={particle.radius * 2.8} fill="#38bdf8" fillOpacity={particle.opacity * 0.34} filter="url(#comet-glow-plasma)" />
                <circle cx={particle.x} cy={particle.y} r={particle.radius} fill="#e0f2fe" fillOpacity={particle.opacity} />
              </g>
            ))}
          </g>
        </svg>
      </div>

      <style>{`@keyframes cometOrbitSpin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } } @keyframes orbitParticlePulse { 0%, 100% { opacity: 0.36; transform: scale(0.74); } 50% { opacity: 1; transform: scale(1.18); } } @keyframes cometParticlePulse { 0%, 100% { opacity: 0.35; } 50% { opacity: 1; } }`}</style>
    </div>
  );
}
