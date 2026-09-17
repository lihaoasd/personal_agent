/* 启动器：先拉起本地后端，再启动 Electron 窗口。 */
'use strict';

const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const BACKEND = path.join(ROOT, 'backend');
const HOST = '127.0.0.1';
const PORT = 8000;

const PYTHON =
  process.env.PA_PYTHON ||
  path.join(BACKEND, '.venv', 'Scripts', 'python.exe');

function waitServer(port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    function probe() {
      const sock = net.connect({ host: HOST, port });
      sock.on('connect', () => {
        sock.destroy();
        resolve();
      });
      sock.on('error', () => {
        sock.destroy();
        if (Date.now() > deadline) reject(new Error('后端服务启动超时'));
        else setTimeout(probe, 400);
      });
    }
    probe();
  });
}

async function main() {
  console.log('[pa] 启动本地后端…');
  const backend = spawn(
    PYTHON,
    ['-m', 'uvicorn', 'app.main:app', '--host', HOST, '--port', String(PORT)],
    { cwd: BACKEND, stdio: 'inherit', windowsHide: true },
  );

  backend.on('exit', (code) => {
    console.log('[pa] 后端已退出 code=' + code);
    process.exit(code ?? 0);
  });

  try {
    await waitServer(PORT, 30000);
    console.log('[pa] 后端就绪');
  } catch (err) {
    console.error('[pa] ' + err.message);
    backend.kill();
    process.exit(1);
  }

  const electronPath = require('electron'); // 普通 Node 下返回可执行文件路径
  const electron = spawn(electronPath, [path.join(__dirname, '..', 'main.js')], {
    stdio: 'inherit',
    windowsHide: true,
  });

  electron.on('exit', (code) => {
    backend.kill();
    process.exit(code ?? 0);
  });
}

main().catch((err) => {
  console.error('[pa] 启动失败: ' + err.message);
  process.exit(1);
});
