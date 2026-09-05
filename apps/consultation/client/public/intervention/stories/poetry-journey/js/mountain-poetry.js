(function () {
  "use strict";
  const chapters = [
    { id: "tai", title: "苔", author: "清·袁枚", start: 0, end: 12.80, dissolveStart: 12.30, lines: [{ text: "白日不到处", start: 1.53, end: 3.42 }, { text: "青春恰自来", start: 3.81, end: 5.74 }, { text: "苔花如米小", start: 6.68, end: 8.43 }, { text: "也学牡丹开", start: 8.71, end: 10.80 }] },
    { id: "caigentan", title: "菜根谭", author: "洪应明", visualStart: 12.80, start: 14.01, end: 33.75, dissolveStart: 33.25, lines: [{ text: "风来疏竹", start: 14.01, end: 15.62 }, { text: "风过而竹不留声", start: 16.13, end: 18.82 }, { text: "雁渡寒潭", start: 20.02, end: 21.28 }, { text: "雁去而潭不留影", start: 21.71, end: 24.85 }, { text: "故君子事来而心始现", start: 26.02, end: 29.20 }, { text: "事去而心随空", start: 29.88, end: 32.48 }] },
    { id: "dingfengbo", title: "定风波·莫听穿林打叶声", author: "苏轼", visualStart: 33.75, start: 34.82, end: 70.84, dissolveStart: 70.84, lines: [{ text: "莫听穿林打叶声", start: 34.82, end: 37.72 }, { text: "何妨吟啸且徐行", start: 38.32, end: 42.16 }, { text: "竹杖芒鞋轻胜马", start: 42.85, end: 46.05 }, { text: "谁怕", start: 46.58, end: 47.24 }, { text: "一蓑烟雨任平生", start: 48.00, end: 51.30 }, { text: "料峭春风吹酒醒", start: 52.01, end: 55.34 }, { text: "微冷", start: 56.18, end: 56.95 }, { text: "山头斜照却相迎", start: 57.48, end: 60.61 }, { text: "回首向来萧瑟处", start: 61.29, end: 64.35 }, { text: "归去", start: 65.06, end: 65.91 }, { text: "也无风雨也无晴", start: 66.78, end: 70.84 }] }
  ];
  window.MOUNTAIN_POETRY = { duration: 70.84, chapters, getChapter(time) { for (let i = chapters.length - 1; i >= 0; i -= 1) if (time >= (chapters[i].visualStart ?? chapters[i].start)) return { chapter: chapters[i], index: i }; return { chapter: chapters[0], index: 0 }; } };
})();
