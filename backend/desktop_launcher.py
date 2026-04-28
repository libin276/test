import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.main import app


def resolve_project_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def resolve_frontend_dist() -> Path:
    return resolve_project_root() / 'frontend' / 'dist'


def configure_static_assets() -> None:
    frontend_dist = resolve_frontend_dist()
    assets_dir = frontend_dist / 'assets'
    if not frontend_dist.exists() or not assets_dir.exists():
        return

    existing_paths = {getattr(route, 'path', None) for route in app.routes}
    if '/assets' not in existing_paths:
        app.mount('/assets', StaticFiles(directory=str(assets_dir)), name='assets')

    @app.get('/', include_in_schema=False)
    async def serve_index():
        return FileResponse(frontend_dist / 'index.html')

    @app.get('/{full_path:path}', include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith('api/'):
            raise HTTPException(status_code=404, detail='Not Found')
        target = frontend_dist / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dist / 'index.html')


def maybe_open_browser(url: str) -> None:
    if os.getenv('MQTT_MANAGER_NO_BROWSER') == '1':
        return

    def _open() -> None:
        webbrowser.open(url)

    timer = threading.Timer(1.2, _open)
    timer.daemon = True
    timer.start()


def main() -> None:
    host = os.getenv('MQTT_MANAGER_HOST', '127.0.0.1')
    port = int(os.getenv('MQTT_MANAGER_PORT', '9527'))
    configure_static_assets()
    maybe_open_browser(f'http://{host}:{port}')
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()