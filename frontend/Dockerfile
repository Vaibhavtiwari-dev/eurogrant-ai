FROM node:20-bookworm-slim

WORKDIR /home/node/app

COPY package*.json ./
RUN npm install

COPY --chown=node:node . .

EXPOSE 3000

USER node
CMD ["npm", "run", "dev"]
