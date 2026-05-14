# Frontend Style Guide

本项目的患者端前端默认采用 `React + Tailwind CSS + 组件化` 写法。

## 基本原则

1. 页面样式优先写在 JSX 里，直接使用 Tailwind utility classes。
2. `styles.css` 只保留 Tailwind 入口、全局 reset、字体变量和真正跨页面的基础规则。
3. 不再为单个页面创建原生 CSS 类，例如 `cover-*`、`auth-*`、`consultation-*`。
4. 一旦出现重复 UI，优先抽成 React 组件，而不是复制 class 字符串。

## 什么时候应该抽组件

- 同一种按钮出现 2 次以上
- 同一种卡片容器出现 2 次以上
- 同一种表单字段出现 2 次以上
- 同一种状态胶囊、步骤条、结果摘要块出现 2 次以上

当前公共 UI 统一放在：

- `src/components/patient-ui.tsx`

如果一个新页面需要“按钮、卡片、字段、步骤条”这类基础结构，先看这个文件里是否已经有可复用组件。

## 什么时候才允许写 CSS

只有下面几类内容可以进入 `styles.css`：

- Tailwind 的 `@import`
- 全局字体与主题变量
- `html/body/#root` 级别 reset
- 浏览器统一行为，例如 `box-sizing`、`selection`、抗锯齿

下面这些内容不应该进入 `styles.css`：

- 页面 Hero 的布局
- 登录页/封面页/问诊页的局部样式
- 某个按钮或卡片的单独视觉
- 为了省事而新建的命名类

## 页面开发流程

每次新改一个页面时，按这个顺序判断：

1. 这能不能直接用 Tailwind utility classes 写完？
2. 如果有重复结构，能不能抽成 React 组件？
3. 如果真的是全局规则，才放进 `styles.css`。

## 推荐做法

- 用语义化小组件组织 JSX，而不是靠大段原生 CSS 命名类维持结构
- 保持一页只围绕一个视觉锚点
- 文本内容写真实业务信息，不写假状态和演示性标签
- 大块视觉改动优先改组件，不回退到全局 CSS 覆盖

## 不推荐做法

- 在页面里继续新增 `xxx-page`、`xxx-card`、`xxx-panel` 这类类名
- 在 `styles.css` 里堆页面级 media query
- 复制一整段 Tailwind classes 到多个地方却不抽组件
- 为了局部效果去污染全局 input/button 默认样式
