import React from 'react';
import { motion } from 'motion/react';

const colors = [
  'bg-blue-400/20',
  'bg-emerald-400/20',
  'bg-rose-400/10',
  'bg-indigo-400/15',
  'bg-cyan-400/20',
];

const FloatingBubbles: React.FC = () => {
  // 生成 15 个随机气泡
  const bubbles = Array.from({ length: 15 }).map((_, i) => ({
    id: i,
    size: Math.random() * 300 + 100, // 100px - 400px
    x: Math.random() * 100, // 0 - 100vw
    y: Math.random() * 100, // 0 - 100vh
    color: colors[Math.floor(Math.random() * colors.length)],
    duration: Math.random() * 20 + 20, // 20s - 40s
    delay: Math.random() * -20, // 负延迟让动画立即看起来是运行中的
  }));

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {bubbles.map((bubble) => (
        <motion.div
          key={bubble.id}
          className={`absolute rounded-full blur-[80px] ${bubble.color}`}
          style={{
            width: bubble.size,
            height: bubble.size,
            left: `${bubble.x}%`,
            top: `${bubble.y}%`,
          }}
          animate={{
            x: [0, Math.random() * 200 - 100, Math.random() * 200 - 100, 0],
            y: [0, Math.random() * 200 - 100, Math.random() * 200 - 100, 0],
            scale: [1, 1.2, 0.9, 1],
          }}
          transition={{
            duration: bubble.duration,
            repeat: Infinity,
            delay: bubble.delay,
            ease: "linear",
          }}
        />
      ))}
    </div>
  );
};

export default FloatingBubbles;
