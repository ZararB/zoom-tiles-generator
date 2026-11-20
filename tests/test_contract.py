import base64
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PIL import Image
from fastapi import HTTPException
try:
    import pod_server as worker
except ModuleNotFoundError as exc:
    if exc.name=='torch':raise unittest.SkipTest('Install the optional GPU dependencies for worker contract tests')
    raise


def encoded(color):
    buffer = io.BytesIO()
    Image.new('RGB', (256, 256), color).save(buffer, 'PNG')
    return base64.b64encode(buffer.getvalue()).decode()


class Contract(unittest.TestCase):
    def test_overlong_model_prompt_is_rejected_before_inference(self):
        tokenizer=SimpleNamespace(model_max_length=77)
        class FakeTokenizer:
            model_max_length=77
            def __call__(self,*args,**kwargs):return {'input_ids':list(range(78))}
        with patch.object(worker,'pipe',SimpleNamespace(tokenizer=FakeTokenizer())):
            with self.assertRaises(HTTPException) as error:
                worker.edit(worker.Edit(image_base64=encoded('blue'),prompt='too many tokens'))
            self.assertEqual(error.exception.status_code,422)
            self.assertIn('77',error.exception.detail)

    def test_pixel_space_shire_coordinates_and_invalid_geometry(self):
        fake = lambda **kwargs: SimpleNamespace(images=[kwargs['image']], nsfw_content_detected=[False])
        with patch.object(worker, 'pipe', fake):
            body = worker.Edit(image_base64=encoded('blue'), prompt='fantasy map', coordinate_space='pixel',
                               map_geometry={'map_width_px':7680,'map_height_px':4386,'native_max_z':2}, z=2,x=10,y=4,steps=1)
            self.assertEqual(worker.edit(body)['coordinate_space'], 'pixel')
            body.x=30
            with self.assertRaises(HTTPException) as error: worker.edit(body)
            self.assertEqual(error.exception.status_code,422)

    def test_invalid_image(self):
        with self.assertRaises(HTTPException) as error:
            worker.decode_image('not base64')
        self.assertEqual(error.exception.status_code, 422)

    def test_mosaic_crop_and_coordinates(self):
        canvas = worker.compose(Image.new('RGB', (256, 256), 'blue'), Image.new('RGB', (256, 256), 'red'))
        fake = lambda **kwargs: SimpleNamespace(images=[kwargs['image']], nsfw_content_detected=[False])
        with patch.object(worker, 'pipe', fake):
            result = worker.edit(worker.Edit(image_base64=encoded('blue'), context_mosaic_base64=encoded('red'),
                                            prompt='preserve roads', z=3, x=2, y=1, steps=1,
                                            world_revision='test-revision',world_sha256='a'*64,scene_id='two-lakes'))
        image = worker.decode_image(result['image_base64'])
        self.assertEqual(image.size, (256, 256))
        self.assertEqual(image.getpixel((100, 100)), (0, 0, 255))
        self.assertTrue(result['context_used'])
        self.assertEqual((result['z'], result['x'], result['y']), (3, 2, 1))
        self.assertEqual(result['world_revision'],'test-revision')
        self.assertEqual(result['world_sha256'],'a'*64)
        self.assertEqual(result['scene_id'],'two-lakes')
        self.assertEqual(canvas.getpixel((0, 0)), (255, 0, 0))

    def test_busy_and_invalid_coordinates(self):
        with patch.object(worker, 'pipe', object()):
            with self.assertRaises(HTTPException) as error:
                worker.edit(worker.Edit(image_base64=encoded('blue'), prompt='map', z=1, x=2))
            self.assertEqual(error.exception.status_code, 422)
            with worker.lock:
                with self.assertRaises(HTTPException) as busy:
                    worker.edit(worker.Edit(image_base64=encoded('blue'), prompt='map'))
            self.assertEqual(busy.exception.status_code, 429)

    def test_failure_releases_gpu_lock(self):
        def fail(**kwargs):
            raise RuntimeError('simulated inference failure')
        with patch.object(worker, 'pipe', fail):
            with self.assertRaises(HTTPException) as error:
                worker.edit(worker.Edit(image_base64=encoded('blue'), prompt='map'))
            self.assertEqual(error.exception.status_code, 500)
        self.assertFalse(worker.lock.locked())


if __name__ == '__main__':
    unittest.main()
