FROM node:20-alpine

WORKDIR /app
# The build context is ./ui
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps || true

COPY . ./
EXPOSE 3000
ENV PORT=3000
CMD ["npm", "run", "dev"]
