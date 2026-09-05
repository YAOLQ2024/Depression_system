(function () {
  "use strict";
  window.MODERN_POETRY = {
    duration: 80.11,
    lines: [
      { text: "如果你不能成为山顶上的高松，", start: 2.31, end: 6.61 },
      { text: "那就当棵山谷里的小树吧，", start: 7.92, end: 10.71 },
      { text: "但要当棵溪边最好的小树。", start: 11.66, end: 15.40 },
      { text: "如果你不能成为一棵大树，", start: 16.68, end: 19.34 },
      { text: "那就当丛小灌木；", start: 20.02, end: 24.17 },
      { text: "如果你不能成为一丛小灌木，", start: 24.17, end: 27.10 },
      { text: "那就当一片小草地。", start: 27.99, end: 30.43 },
      { text: "如果你不能是一只香獐，", start: 31.43, end: 33.44 },
      { text: "那就当尾小鲈鱼，", start: 34.09, end: 36.21 },
      { text: "但要当湖里最活泼的小鲈鱼。", start: 36.89, end: 40.75 },
      { text: "我们不能全是船长，", start: 42.55, end: 44.42 },
      { text: "必须有人来当水手。", start: 45.53, end: 47.38 },
      { text: "这里有许多事让我们去做，", start: 48.37, end: 50.30 },
      { text: "有大事，有小事，", start: 51.58, end: 53.97 },
      { text: "但最重要的是我们身旁的事。", start: 55.00, end: 57.29 },
      { text: "如果你不能成为大道，", start: 60.08, end: 61.65 },
      { text: "那就当一条小路；", start: 62.43, end: 63.71 },
      { text: "如果你不能成为太阳，", start: 65.15, end: 66.70 },
      { text: "那就当一颗星星。", start: 67.67, end: 68.98 },
      { text: "决定成败的不是你尺寸的大小，", start: 70.69, end: 73.56 },
      { text: "—— 而在于做一个最好的你。", start: 74.65, end: 77.75 }
    ],
    getLineIndex(time) {
      let index = -1;
      for (let i = 0; i < this.lines.length; i += 1) {
        if (time >= this.lines[i].start) index = i;
        else break;
      }
      return index;
    }
  };
})();
