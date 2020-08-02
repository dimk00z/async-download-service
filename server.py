import aiofiles
import asyncio
import os
import signal
import argparse
from aiohttp import web
from pathlib import Path
from functools import partial

IMAGE_DIR = 'test_photos'
CHUNK_SIZE = 1024 * 1024
DELAY = 1


def make_zip_cmd(path, archive_hash='test', compression_ratio=9):
    return 'zip', '-r', f'-{compression_ratio}', '-', path


async def archivate(request, image_dir, delay):

    archive_hash = request.match_info['archive_hash']
    full_path = Path.joinpath(Path.cwd(), IMAGE_DIR, archive_hash)
    if not (Path.exists(full_path) and Path.is_dir(full_path)):
        raise web.HTTPNotFound(
            text=f'Архив {archive_hash} не существует или был удален')

    zip_cmd = make_zip_cmd(path=str(archive_hash))
    zip_process = await asyncio.create_subprocess_exec(
        *zip_cmd,
        cwd=IMAGE_DIR,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    response = web.StreamResponse()
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'
    await response.prepare(request)

    try:
        counter = 0
        while True:
            zip_chunk = await zip_process.stdout.read(CHUNK_SIZE)
            counter += 1
            # logging.debug(
            #     'Download chunk {} - delay={}'.format(counter, delay))
            await response.write(zip_chunk)
            await asyncio.sleep(DELAY)

            if not zip_chunk:
                break

    except (ConnectionResetError, asyncio.CancelledError):
        print('Download was interrupted')
        # logging.debug('Download was interrupted')
        raise
    finally:
        try:
            os.kill(zip_process.pid, signal.SIGKILL)
        except OSError:
            pass
        response.force_close()
        # logging.debug('Download finished')

    return response


def parse_args():
    parser = argparse.ArgumentParser(description='Async download service')
    parser.add_argument('--delay', type=int, default=1,
                        help="set delay in senonds, default=1")
    parser.add_argument('--image_dir', type=int, default="test_photos",
                        help="get image directory, delault='test_photos'")
    parser.add_argument('--enable_logs', type=bool, default=True,
                        help="enable or disable logging, default=True")
    args = parser.parse_args()
    return args.image_dir, args.delay, args.enable_logs


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    image_dir, delay, enable_logs = parse_args()
    partial_archivate = functools.partial(
        archivate, image_dir=image_dir, delay=delay)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', partial_archivate),
    ])
    web.run_app(app)
