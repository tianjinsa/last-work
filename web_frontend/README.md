# 专家系统 Web 版 - 前端

基于 Vue 3 + Element Plus 的专家系统前端

## 开发环境运行

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 构建生产版本

```bash
npm run build
```

构建后的文件在 `dist` 目录下，会被后端服务器自动提供。

## 项目结构

```
web_frontend/
├── src/
│   ├── api/           # API 接口
│   ├── router/        # 路由配置
│   ├── stores/        # Pinia 状态管理
│   ├── views/         # 页面组件
│   ├── App.vue        # 根组件
│   └── main.js        # 入口文件
├── index.html
├── package.json
└── vite.config.js
```
