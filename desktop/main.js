const { app, BrowserWindow, screen, nativeImage, shell } = require('electron');
const path = require('path');

let win = null;

function repositionTopRight(contentWidth) {
  if (!win || win.isDestroyed()) return;
  const primaryDisplay = screen.getPrimaryDisplay();
  const { x, y, width } = primaryDisplay.workArea;
  const posX = Math.round(x + width - contentWidth);
  const posY = Math.round(y);
  win.setPosition(posX, posY);
}

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { x, y, width } = primaryDisplay.workArea;
  const initialWidth = 72;
  const initialHeight = 72;
  const posX = Math.round(x + width - initialWidth);
  const posY = Math.round(y);

  const iconPath = path.join(__dirname, 'assets/understudy-icon.png');

  win = new BrowserWindow({
    width: initialWidth,
    height: initialHeight,
    x: posX,
    y: posY,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    hasShadow: false,
    alwaysOnTop: true,
    resizable: false,
    icon: iconPath,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  const url = process.env.COMPANION_URL || 'http://localhost:5173/companion';
  win.loadURL(url);

  // Open any target=_blank / window.open link (e.g. "Open dashboard →") in the
  // user's default browser instead of hijacking the tiny companion window.
  win.webContents.setWindowOpenHandler(({ url: openUrl }) => {
    shell.openExternal(openUrl);
    return { action: 'deny' };
  });

  let lastW = 0;
  let lastH = 0;

  const measureJs = `(() => {
    const el = document.querySelector('.companion-root');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    const ml = parseFloat(style.marginLeft) || 0;
    const mr = parseFloat(style.marginRight) || 0;
    const mt = parseFloat(style.marginTop) || 0;
    const mb = parseFloat(style.marginBottom) || 0;
    return {
      width: Math.ceil(r.width + ml + mr),
      height: Math.ceil(r.height + mt + mb),
    };
  })()`;

  const adjustWindowSize = async () => {
    if (!win || win.isDestroyed()) return;
    try {
      const dims = await win.webContents.executeJavaScript(measureJs, true);
      if (dims && dims.width > 0 && dims.height > 0) {
        const w = dims.width;
        const h = dims.height;
        if (w !== lastW || h !== lastH) {
          lastW = w;
          lastH = h;
          win.setContentSize(w, h);
          repositionTopRight(w);
        }
      }
    } catch (e) {
      // page still loading; ignore
    }
  };

  win.webContents.on('did-finish-load', () => {
    adjustWindowSize();
  });

  const intervalId = setInterval(adjustWindowSize, 750);
  win.on('closed', () => {
    clearInterval(intervalId);
    win = null;
  });
}

app.whenReady().then(() => {
  if (process.platform === 'darwin' && app.dock) {
    app.dock.setIcon(nativeImage.createFromPath(path.join(__dirname, 'assets/understudy-icon.png')));
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

