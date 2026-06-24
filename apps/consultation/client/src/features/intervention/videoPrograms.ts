export type InterventionVideoProgram = {
  id: string;
  title: string;
  subtitle: string;
  videoSrc: string;
  posterSrc: string;
};

export const INTERVENTION_VIDEO_PROGRAMS: InterventionVideoProgram[] = [
  {
    id: "town-001",
    title: "\u5c0f\u9547",
    subtitle: "\u8282\u594f\u8212\u7f13\uff0c\u9002\u5408\u5b89\u9759\u5730\u770b\u4e00\u4f1a\u513f\uff0c\u8ba9\u6ce8\u610f\u529b\u6162\u6162\u653e\u4e0b\u6765\u3002",
    videoSrc: "/intervention/video/town-001.mp4",
    posterSrc: "/intervention/video/posters/town-001-poster.jpg",
  },
  {
    id: "starry-sky-001",
    title: "\u661f\u7a7a",
    subtitle: "\u753b\u9762\u66f4\u5f00\u9614\uff0c\u9002\u5408\u6c89\u6d78\u5f0f\u5730\u770b\u4e00\u6bb5\uff0c\u987a\u7740\u753b\u9762\u6162\u6162\u653e\u677e\u3002",
    videoSrc: "/intervention/video/starry-sky-001.mp4",
    posterSrc: "/intervention/video/posters/starry-sky-001-poster.jpg",
  },
];
