import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
try:
    import download_model as downloader
except ModuleNotFoundError as exc:
    if exc.name=='huggingface_hub':raise unittest.SkipTest('Install the optional GPU dependencies for download contract tests')
    raise


class Download(unittest.TestCase):
    def test_resumes_partial_ranges_and_verifies_hash(self):
        raw = b'0123456789'
        file = SimpleNamespace(rfilename='unet/test.safetensors', size=len(raw),
                               lfs=SimpleNamespace(sha256=hashlib.sha256(raw).hexdigest()))
        requested = []

        class Response:
            status_code = 206

            def __init__(self, start, end):
                self.start, self.end = start, end
                self.headers = {'Content-Range': f'bytes {start}-{end}/{len(raw)}'}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_content(self, size):
                yield raw[self.start:self.end+1]

        def get(url, headers, **kwargs):
            start, end = map(int, headers['Range'].split('=')[1].split('-'))
            requested.append((start, end))
            return Response(start, end)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parts = root / 'unet/test.safetensors.parts'
            parts.mkdir(parents=True)
            (parts / '00000').write_bytes(raw[:4])
            (parts / '00001.tmp').write_bytes(raw[4:6])
            with patch.object(downloader, 'MODEL_PATH', root), patch.object(downloader, 'CHUNK', 4), \
                 patch.object(downloader.shutil, 'disk_usage', return_value=SimpleNamespace(free=32*1024**3)), \
                 patch.object(downloader, 'get_hf_file_metadata', return_value=SimpleNamespace(location='https://example.invalid/model')), \
                 patch.object(downloader.requests, 'get', side_effect=get):
                downloader.download_file(file)
            self.assertEqual((root / file.rfilename).read_bytes(), raw)
            self.assertCountEqual(requested, [(6, 7), (8, 9)])
            self.assertFalse(parts.exists())


if __name__ == '__main__':
    unittest.main()
