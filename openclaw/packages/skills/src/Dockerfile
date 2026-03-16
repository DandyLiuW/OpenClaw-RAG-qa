# 构建阶段
FROM node:22-alpine AS builder

WORKDIR /app

# 复制package.json和pnpm-lock.yaml
COPY package.json pnpm-lock.yaml ./
COPY packages/skills/package.json ./packages/skills/

# 安装pnpm
RUN npm install -g pnpm

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源码
COPY . .

# 构建项目
RUN pnpm build

# 运行阶段
FROM node:22-alpine

WORKDIR /app

# 复制构建产物
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages/skills/dist ./packages/skills/dist
COPY --from=builder /app/package.json ./package.json

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["pnpm", "dev"]