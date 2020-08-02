import asyncio
import sys


CHUNK_SIZE = 1024 * 1024


def make_zip_cmd(path, archive_hash='test', compression_ratio=9):
    return 'zip', '-r', f'-{compression_ratio}', '-', path


async def create_zip():
    zip_cmd = make_zip_cmd(
        'test_photos')
    zip_process = await asyncio.create_subprocess_exec(
        *zip_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    try:
        while True:
            archive_chunk = await zip_process.stdout.read(CHUNK_SIZE)

            if not archive_chunk:
                break
            print(len(archive_chunk))
            # await zip_process.wait()
    except asyncio.CancelledError:
        zip_process.kill()
    finally:
        zip_process.kill()
    # return data

date = asyncio.run(create_zip())
# print(f"Current date: {date}")
# with open('test.zip', 'wb') as file:
#     file.write(date)
