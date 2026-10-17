# The image the agent's shell runs in (episode 4): Python and pytest for the project's tests, git and curl because agents
# reach for them. At run time the container has no network and sees one folder of your machine: the project.
FROM python:3.14.6-slim
RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==9.1.1 tzdata==2026.5
ENV LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
