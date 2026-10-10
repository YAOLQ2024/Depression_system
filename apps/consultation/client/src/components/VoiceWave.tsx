import { useEffect, useId, useRef } from "react";

// Observe the existing recording stream without starting or stopping its tracks.
export function VoiceWave({ active, stream }: { active: boolean; stream?: MediaStream | null }) {
  const gradientId = useId().replace(/:/g, "");
  const paths = useRef<Array<SVGPathElement | null>>([]);

  useEffect(() => {
    let frame = 0;
    let context: AudioContext | undefined;
    let source: MediaStreamAudioSourceNode | undefined;
    let analyser: AnalyserNode | undefined;
    let samples: Uint8Array<ArrayBuffer> | undefined;
    let amplitude = 14;
    let previousTime = 0;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (active && stream && stream.getAudioTracks().some((track) => track.readyState === "live")) {
      try {
        context = new AudioContext();
        source = context.createMediaStreamSource(stream);
        analyser = context.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        samples = new Uint8Array(analyser.fftSize);
        void context.resume().catch(() => {});
      } catch {
        // Visual feedback must never interrupt recording.
      }
    }
    const draw = (time: number) => {
      if (time - previousTime >= 33 || previousTime === 0) {
        previousTime = time;
        let level = 0;
        if (analyser && samples) {
          analyser.getByteTimeDomainData(samples);
          level = Math.sqrt(samples.reduce((sum, sample) => sum + ((sample - 128) / 128) ** 2, 0) / samples.length);
        }
        amplitude += ((active ? 14 + Math.min(1, level * 7) * 38 : 14) - amplitude) * 0.24;
        const phase = active && !reducedMotion.matches ? time / 330 : 0;
        paths.current.forEach((path, layer) => {
          let d = "";
          for (let x = 0; x <= 600; x += 4) {
            const envelope = Math.sin(Math.PI * x / 600) ** 1.2;
            const y = 60 + Math.sin(x / 32 - phase + layer * 1.3) * amplitude * envelope * (1 - layer * 0.16);
            d += `${x ? "L" : "M"}${x},${y.toFixed(2)} `;
          }
          path?.setAttribute("d", d);
        });
      }
      if (active && !reducedMotion.matches) frame = requestAnimationFrame(draw);
    };
    draw(0);
    return () => {
      cancelAnimationFrame(frame);
      source?.disconnect();
      analyser?.disconnect();
      if (context) void context.close().catch(() => {});
    };
  }, [active, stream]);

  return <svg className="voice-wave" viewBox="0 0 600 120" aria-hidden="true" focusable="false">
    <defs><linearGradient id={gradientId}><stop stopColor="#46caff" stopOpacity="0" /><stop offset=".2" stopColor="#72b8ff" /><stop offset=".5" stopColor="#e886ff" /><stop offset=".8" stopColor="#967aff" /><stop offset="1" stopColor="#68c6ff" stopOpacity="0" /></linearGradient></defs>
    {[0, 1, 2].map((layer) => <path key={layer} ref={(node) => { paths.current[layer] = node; }} fill="none" stroke={`url(#${gradientId})`} strokeWidth={layer === 0 ? 3.8 : 2.4} strokeLinecap="round" vectorEffect="non-scaling-stroke" opacity={1 - layer * 0.12} />)}
  </svg>;
}
