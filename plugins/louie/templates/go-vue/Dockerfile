# The server's image (ADR stack): the app's build and the Go server, cross-compiled, on distroless.
# Every stage but the last runs on the builder's own platform, so building for another architecture
# emulates nothing; the last stage only copies files. The Node, pnpm and Go versions follow
# mise.toml's: raising one there raises it here.

FROM --platform=$BUILDPLATFORM node:24.22.1-alpine AS app
RUN npm install --global pnpm@11.28.8
WORKDIR /src
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/app/package.json apps/app/
RUN pnpm install --frozen-lockfile
COPY apps/app apps/app
WORKDIR /src/apps/app
RUN pnpm exec vite build

FROM --platform=$BUILDPLATFORM golang:1.26.10-alpine AS api
ARG TARGETOS TARGETARCH
WORKDIR /src
COPY apps/api/go.mod apps/api/go.sum ./
RUN go mod download
COPY apps/api ./
RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH go build -trimpath -o /out/server ./cmd/server

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=api /out/server /usr/local/bin/server
COPY --from=app /src/apps/app/dist /app
ENV APP_DIR=/app ADDR=:8080
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/server"]
