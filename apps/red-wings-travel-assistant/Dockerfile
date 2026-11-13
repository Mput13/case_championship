FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3080 ENABLE_CHAT=true PUBLIC_DIRECTORY=./public-chat
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund && npm cache clean --force
COPY --chown=node:node server.mjs ./
COPY --chown=node:node src ./src
COPY --chown=node:node data ./data
COPY --chown=node:node public ./public
COPY --chown=node:node public-chat ./public-chat
COPY --chown=node:node certs ./certs
RUN mkdir -p /app/.runtime && chown node:node /app/.runtime
USER node
EXPOSE 3080
CMD ["node", "server.mjs"]
