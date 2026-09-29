FROM node:24-alpine

WORKDIR /app

COPY frontend/package*.json ./

RUN npm install

COPY frontend/ .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]