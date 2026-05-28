# SamBot

This project is now configured for deployment on DigitalOcean using Docker.

## What was added

- `Dockerfile` for building a Python + Playwright container
- `.dockerignore` to keep the image clean
- `gunicorn` in `requirements.txt` for production serving
- `app.py` updated to use `http://localhost:5000` for direct local runs and still honor `HOST` / `PORT` from env
- `main.py` updated to support headless Playwright by default
- dashboard updated to display a remote WhatsApp QR screenshot

## Deploying on DigitalOcean App Platform

1. Push this repository to GitHub.
2. In DigitalOcean, create a new App.
3. Connect your GitHub repo and choose the `SamBot` project.
4. Use the existing `Dockerfile` build settings.
5. Set the service port to `5000`.
6. Deploy.

## Running on a DigitalOcean Droplet

1. Create a droplet with Docker installed.
2. Copy the project files to the droplet.
3. Build the image:
   ```bash
   docker build -t sambot .
   ```
4. Run the container:
   ```bash
   docker run -d -p 5000:5000 --name sambot sambot
   ```
5. Visit `http://<droplet-ip>:5000`.

## Notes

- The app uses Playwright and installs Chromium during build.
- WhatsApp login is captured as a screenshot for remote QR scanning.
- For local testing, set `PLAYWRIGHT_HEADLESS=0` if you want a visible browser.
- Run locally with `python app.py`, then open `http://localhost:5000`.
