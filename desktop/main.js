/* Electron 主进程：窗口 + 托盘常驻 + 通知权限。 */
'use strict';

const { app, BrowserWindow, Tray, Menu, nativeImage, session } = require('electron');
const path = require('path');

const DEV_SERVER = process.env.PA_DEV_SERVER || '';
let win = null;
let tray = null;

/** 运行时生成 16x16 绿色圆点托盘图标，避免依赖资源文件。 */
function buildTrayIcon() {
  const size = 16;
  const buf = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      const dx = x - 7.5;
      const dy = y - 7.5;
      const inside = dx * dx + dy * dy <= 6.5 * 6.5;
      buf[i] = inside ? 0x2f : 0;
      buf[i + 1] = inside ? 0x8f : 0;
      buf[i + 2] = inside ? 0x6e : 0;
      buf[i + 3] = inside ? 255 : 0;
    }
  }
  return nativeImage.createFromBitmap(buf, { width: size, height: size });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 900,
    minHeight: 640,
    title: '个人成长助手',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (DEV_SERVER) {
    win.loadURL(DEV_SERVER);
  } else {
    win.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'));
  }

  win.on('closed', () => {
    win = null;
  });
}

function createTray() {
  tray = new Tray(buildTrayIcon());
  tray.setToolTip('个人成长助手');
  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: '打开主界面',
        click: () => {
          if (!win) createWindow();
          else win.show();
        },
      },
      { type: 'separator' },
      { label: '退出', click: () => app.quit() },
    ]),
  );
  tray.on('click', () => {
    if (!win) createWindow();
    else win.show();
  });
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(permission === 'notifications');
  });
  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// 关闭窗口后保留托盘常驻，不退出进程
app.on('window-all-closed', () => {
  /* 桌面端常驻托盘 */
});
