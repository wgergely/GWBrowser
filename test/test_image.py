import bookmarks.images as images
import sys
import bookmarks.common as common

if __name__ == '__main__':
    images.ImageCache.oiio_make_thumbnail(
        sys.argv[1],
        sys.argv[2],
        common.THUMBNAIL_IMAGE_SIZE,
    )
