# OpenClaw 聊天页面滚动条美化设计

**目标：** 让消息区域的滚动条在深色主题下不再突兀

**方案：** 自定义 WebKit 滚动条样式，使用与主题融合的深灰色细条

**实现方式：**
- 在 OpenClawChat 组件的消息容器 div 上添加自定义 CSS
- 滚动条轨道（track）：透明或接近背景色
- 滚动条滑块（thumb）：深灰色（slate-600/50），hover 时稍亮
- 滚动条宽度：细（8px），圆角

**文件：** `frontend/src/components/Tools/OpenClawChat/OpenClawChat.tsx`
