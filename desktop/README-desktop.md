# Understudy Desktop Companion

Self-contained Electron desktop wrapper that renders the Understudy `/companion` route in a lightweight, always-on-top, frameless window positioned at the top-right of your primary screen.

## Prerequisites

Start the web application first:

```bash
cd web
npm run dev:firestore
```

*(Alternatively, use `npm run dev` or `npm run dev:mock`)*

## Running the Desktop App

From the repository root:

```bash
cd desktop
npm install
npm start
```

## Configuration

By default, the desktop wrapper loads `http://localhost:5173/companion`. You can override this URL by setting the `COMPANION_URL` environment variable:

```bash
COMPANION_URL=http://localhost:3000/companion npm start
```
