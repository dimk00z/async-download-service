import aiofiles
import asyncio
import os
import signal
import argparse
import logging
from itertools import count
from aiohttp import web
from pathlib import Path
from functools import partial
from contextlib import suppress

CHUNK_SIZE = 1024 * 1024


def make_zip_cmd(path, archive_hash='test', compression_ratio=9):
    return 'zip', '-r', f'-{compression_ratio}', '-', path


async def archivate(request, image_dir, delay):

    archive_hash = request.match_info['archive_hash']
    full_path = Path.joinpath(Path.cwd(), image_dir, archive_hash)
    if not (Path.exists(full_path) and Path.is_dir(full_path)):
        error_text = f'Архив {archive_hash} не существует или был удален'
        logging.debug(error_text)
        raise web.HTTPNotFound(
            text=error_text)

    zip_cmd = make_zip_cmd(path=str(archive_hash))
    zip_process = await asyncio.create_subprocess_exec(
        *zip_cmd,
        cwd=image_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    logging.debug('Process PID={}'.format(zip_process.pid))
    response = web.StreamResponse()
    response.headers['Content-Disposition'] = \
        f'attachment; filename="{archive_hash}.zip"'
    await response.prepare(request)

    try:
        for chunk_number in count():
            zip_chunk = await zip_process.stdout.read(CHUNK_SIZE)
            logging.debug(
                f'Download chunk {chunk_number} - delay={delay}')
            await response.write(zip_chunk)
            await asyncio.sleep(delay)
            if not zip_chunk:
                break
        logging.debug('Download finished')
        return response
    except (ConnectionResetError, asyncio.CancelledError):
        logging.debug('Download was interrupted')
        zip_process.terminate()
        raise
    finally:
        with suppress(OSError):
            os.kill(zip_process.pid, signal.SIGKILL)
        response.force_close()


def parse_args():
    parser = argparse.ArgumentParser(description='Async download service')
    parser.add_argument('--delay', type=int, default=1,
                        help="set delay as value in seconds, default=0")
    parser.add_argument('--image_dir', type=str, default="test_photos",
                        help="set image directory, default=test_photos")
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
    partial_archivate = partial(
        archivate, image_dir=image_dir, delay=delay)
    if enable_logs:
        logging.basicConfig(level=logging.DEBUG)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', partial_archivate),
    ])
    web.run_app(app)
