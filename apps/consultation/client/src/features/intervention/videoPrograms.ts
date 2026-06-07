export type InterventionVideoProgram = {
  id: string;
  title: string;
  subtitle: string;
  audioSrc: string;
  videoSrc: string;
};

const SHARED_VIDEO_SRC = "/intervention/video/四景循环无声.mp4";

export const INTERVENTION_VIDEO_PROGRAMS: InterventionVideoProgram[] = [
  {
    id: "chopin-nocturne-eb-major",
    title: "肖邦《降 E 大调夜曲》",
    subtitle: "温和舒缓，适合先慢下来。",
    audioSrc: "/intervention/audio/肖邦《降E大调夜曲》.mp3",
    videoSrc: SHARED_VIDEO_SRC,
  },
  {
    id: "bach-goldberg-variations",
    title: "巴赫《哥德堡变奏曲》",
    subtitle: "结构稳定，适合做一段安静陪伴。",
    audioSrc: "/intervention/audio/巴赫《哥德堡变奏曲》.mp3",
    videoSrc: SHARED_VIDEO_SRC,
  },
  {
    id: "mozart-sonata-c-major-second-movement",
    title: "莫扎特《C 大调钢琴奏鸣曲》第二乐章",
    subtitle: "旋律轻盈，适合做一段松弛调节。",
    audioSrc: "/intervention/audio/莫扎特《C大调钢琴奏鸣曲》第二乐章.mp3",
    videoSrc: SHARED_VIDEO_SRC,
  },
];
