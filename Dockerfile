FROM node:24.19.0-bookworm-slim AS frontend-build

WORKDIR /source/app/frontend
RUN npm install --global npm@11.17.0 \
    && test "$(npm --version)" = "11.17.0"
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci
COPY app/frontend/ ./

ARG VITE_PORTFOLIO_GITHUB_URL=""
ARG VITE_PORTFOLIO_RELEASE_URL=""
ARG VITE_PORTFOLIO_EVIDENCE_URL=""
ENV VITE_PORTFOLIO_URL=/ \
    VITE_PORTFOLIO_DEMO_URL=/demo \
    VITE_PORTFOLIO_GITHUB_URL=${VITE_PORTFOLIO_GITHUB_URL} \
    VITE_PORTFOLIO_RELEASE_URL=${VITE_PORTFOLIO_RELEASE_URL} \
    VITE_PORTFOLIO_EVIDENCE_URL=${VITE_PORTFOLIO_EVIDENCE_URL}
RUN npm run build


FROM python:3.13.15-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/app/backend \
    OT_DEMO_RUNTIME_ROOT=/tmp/ot-showcase
WORKDIR /app

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
    --requirement requirements.lock

COPY . ./
COPY --from=frontend-build /source/app/frontend/dist ./app/frontend/dist

RUN addgroup --system showcase \
    && adduser --system --ingroup showcase --home /nonexistent showcase \
    && mkdir -p /tmp/ot-showcase \
    && chown -R showcase:showcase /tmp/ot-showcase
USER showcase

EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn ot_demo.api.hosted:create_hosted_app --factory --host 0.0.0.0 --port \"${PORT:-8000}\""]
