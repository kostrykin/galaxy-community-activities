import warnings
import os, os.path
from datetime import (
    datetime,
    timedelta,
)

import numpy as np
import pandas as pd
import skimage, skimage.io, skimage.transform
import scipy.ndimage as ndi
from PIL import Image, ImageDraw


node_label_prefix = '\n\n\n\n\n'
node_kwargs = dict(shape='box')


def load_image_url(url):
    img = skimage.io.imread(url, plugin='matplotlib')
    return skimage.img_as_float(img)


def image_to_disk(img):
    mask = np.ones(img.shape[:2], bool)
    mask[mask.shape[0] // 2, mask.shape[1] // 2] = False
    mask = ndi.distance_transform_edt(mask) < min(mask.shape) // 2 - 2
    return np.concatenate([img[:, :, :3], mask[:, :, None]], axis=2)


def image_to_rounded_square(img):
    assert img.shape[2] in (3, 4), img.shape
    
    # Create mask of appropriate size (square with rounded corners)
    size = max(img.shape[:2])
    mask = Image.new('RGB', (size, size), 'black')
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), fill='white', width=0, radius=round(size * 0.2))
    mask = np.asarray(mask)[:, :, 0].copy()
    
    # Convert RGBA image to RGB with white background
    if img.shape[2] == 4:
        img_RGB = img[:, :, :3]
        img_A = img[:, :, 3][:, :, None]
        img = (1 + (img_RGB - 1) * img_A)
    
    # Convert to RGBA using the alpha channel from the mask
    result = np.concatenate([img, mask[:, :, None]], axis=2)
    return result.clip(0, 1)


class AvatarCache:

    def __init__(self, cache_dir='cache/avatars'):
        self.cache_dir = cache_dir

    def get_filename(self, name):
        return f'{self.cache_dir}/{name}.png'

    def load(self, authors, repositories):
        df_avatars = pd.read_csv('report/_data/avatars.csv')
        df_avatars.set_index('name', inplace=True)
        os.makedirs(self.cache_dir, exist_ok=True)
    
        # Check which avatars need to be created
        is_cached = lambda name: os.path.isfile(self.get_filename(name))
    
        # Create avatar images
        avatars = {'.blank': image_to_disk(np.ones((128, 128, 4), float))}
        for username in authors:
            if is_cached(username): continue
            avatars[username] = image_to_disk(load_image_url(df_avatars.loc[username.lower()].avatar_url))
        for reponame in repositories:
            if is_cached(reponame): continue
            avatars[reponame] = image_to_rounded_square(load_image_url(df_avatars.loc[reponame.lower()].avatar_url))
    
        # Write created images to cache
        for name, avatar in avatars.items():
            name_parts = name.split('/')
            if len(name_parts) > 1:
                owner = name_parts[0]
                os.makedirs(f'{self.cache_dir}/{owner}', exist_ok=True)
            avatar = skimage.transform.resize(avatar, (128, 128), anti_aliasing=True)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                skimage.io.imsave(self.get_filename(name), skimage.img_as_ubyte(avatar))


def filter_by_timestamp(df, first_day=None, last_day=None):
    if first_day is not None and len(df) > 0:
        datetimes = pd.to_datetime(df['timestamp'])
        df = df[datetimes >= first_day.replace(hour=0, minute=0, second=0, microsecond=0)]
    if last_day is not None and len(df) > 0:
        datetimes = pd.to_datetime(df['timestamp'])
        df = df[datetimes < last_day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)]
    return df
