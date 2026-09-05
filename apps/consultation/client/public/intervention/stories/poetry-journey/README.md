# 山水诗境（poetry-journey）

“调节干预 → 听一段诗歌”模块的沉浸式古诗词朗读体验。

页面作为静态资源由主前端以 iframe 加载：

```text
/intervention/stories/poetry-journey/index.html
```

## 资源组成

```text
poetry-journey/
├── index.html
├── mountain.css
├── assets/mountain-background.mp4
├── audio/mountain-background.mp3
├── audio/mountain-recitation.wav
└── js/
    ├── mountain-app.js
    └── mountain-poetry.js
```

不依赖外部 CDN 或额外的前端包。退出时会向父页面发送既有的
`intervention-exit` 消息，由主系统返回调节干预首页。
