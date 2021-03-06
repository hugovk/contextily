"""Tools for generating maps from a text search."""
import geopy as gp
import numpy as np
import matplotlib.pyplot as plt
from warnings import warn
from .tile import howmany, bounds2raster, bounds2img, _sm2ll, _calculate_zoom
from .plotting import ATTRIBUTION, INTERPOLATION, ZOOM

class Place(object):
    """Geocode a place by name and get its map.

    This allows you to search for a name (e.g., city, street, country) and
    grab map and location data from the internet.

    Parameters
    ----------
    search : string
        The location to be searched.
    zoom : int | None
        The level of detail to include in the map. Higher levels mean more
        tiles and thus longer download time. If None, the zoom level will be
        automatically determined.
    path : string | None
        Path to a raster file that will be created after getting the place map.
        If None, no raster file will be downloaded.
    zoom_adjust : int | None
        The amount to adjust a chosen zoom level if it is chosen automatically.
    url : string
        The URL to use for downloading map tiles. See the ``cx.tile_providers`` module
        for some options, as well as ``cx.bounds2image`` for guidance.

    Attributes
    ----------
    geocode : geopy object
        The result of calling ``geopy.geocoders.Nominatim`` with ``search`` as input.
    s : float
        The southern bbox edge.
    n : float
        The northern bbox edge.
    e : float
        The eastern bbox edge.
    w : float
        The western bbox edge.
    im : ndarray
        The image corresponding to the map of ``search``.
    bbox : list
        The bounding box of the returned image, expressed in lon/lat, with the
        following order: [minX, minY, maxX, maxY]
    bbox_map : tuple
        The bounding box of the returned image, expressed in Web Mercator, with the
        following order: [minX, minY, maxX, maxY]
    """

    def __init__(self, search, zoom=None, path=None, zoom_adjust=None, url=None):
        self.path = path
        self.url = url
        self.zoom_adjust = zoom_adjust

        # Get geocoded values
        resp = gp.geocoders.Nominatim().geocode(search)
        bbox = np.array([float(ii) for ii in resp.raw['boundingbox']])

        if 'display_name' in resp.raw.keys():
            place = resp.raw['display_name']
        elif 'address' in resp.raw.keys():
            place = resp.raw['address']
        else:
            place = search
        self.place = place
        self.search = search
        self.s, self.n, self.w, self.e = bbox
        self.bbox = [self.w, self.s, self.e, self.n]  # So bbox is standard
        self.latitude = resp.latitude
        self.longitude = resp.longitude
        self.geocode = resp

        # Get map params
        self.zoom = _calculate_zoom(self.w, self.s, self.e, self.n) if zoom is None else zoom
        self.zoom = int(self.zoom)
        if self.zoom_adjust is not None:
            self.zoom += zoom_adjust
        self.n_tiles = howmany(self.w, self.s, self.e, self.n, self.zoom, verbose=False)

        # Get the map
        self._get_map()


    def _get_map(self):
        kwargs = {'ll': True}
        if self.url is not None:
            kwargs['url'] = self.url

        try:
            if isinstance(self.path, str):
                im, bbox = bounds2raster(self.w, self.s, self.e, self.n, self.path, zoom=self.zoom, **kwargs)
            else:
                im, bbox = bounds2img(self.w, self.s, self.e, self.n, self.zoom, **kwargs)
        except Exception as err:
            raise ValueError('Could not retrieve map with parameters: {}, {}, {}, {}, zoom={}\n{}\nError: {}'.format(
                self.w, self.s, self.e, self.n, self.zoom, kwargs, err))

        self.im = im
        self.bbox_map = bbox
        return im, bbox

    def plot(self, ax=None, zoom=ZOOM, interpolation=INTERPOLATION, 
             attribution_text = ATTRIBUTION):
        '''
        Plot a `Place` object
        ...

        Arguments
        ---------
        ax                  : AxesSubplot
                              Matplotlib axis with `x_lim` and `y_lim` set in Web
                              Mercator (EPSG=3857). If not provided, a new
                              12x12 figure will be set and the name of the place
                              will be added as title
        zoom                : int/'auto'
                              [Optional. Default='auto'] Level of detail for the
                              basemap. If 'auto', if calculates it automatically.
                              Ignored if `url` is a local file.
        interpolation       : str
                              [Optional. Default='bilinear'] Interpolation
                              algorithm to be passed to `imshow`. See
                              `matplotlib.pyplot.imshow` for further details.
        attribution_text    : str
                              [Optional. Default=''] Text to be added at the
                              bottom of the axis.

        Returns
        -------
        ax                  : AxesSubplot
                              Matplotlib axis with `x_lim` and `y_lim` set in Web
                              Mercator (EPSG=3857) containing the basemap

        Example
        -------

        >>> lvl = ctx.Place('Liverpool')
        >>> lvl.plot()

        '''
        im = self.im
        bbox = self.bbox_map

        title = None
        axisoff = False
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 12))
            title = self.place 
            axisoff = True
        ax.imshow(im, extent=bbox, interpolation=interpolation)
        ax.set(xlabel="X", ylabel="Y")
        if title is not None:
            ax.set(title=title)
        if axisoff:
            ax.set_axis_off()
        return ax

    def __repr__(self):
        s = 'Place : {} | n_tiles: {} | zoom : {} | im : {}'.format(
            self.place, self.n_tiles, self.zoom, self.im.shape[:2])
        return s

def plot_map(place, bbox=None, title=None, ax=None, axis_off=True, latlon=True):
    """Plot a map of the given place.

    Parameters
    ----------
    place : instance of Place | ndarray
        The map to plot. If an ndarray, this must be an image corresponding
        to a map. If an instance of ``Place``, the extent of the image and name
        will be inferred from the bounding box.
    ax : instance of matplotlib Axes object | None
        The axis on which to plot. If None, one will be created.
    axis_off : bool
        Whether to turn off the axis border and ticks before plotting.

    Returns
    -------
    ax : instance of matplotlib Axes object | None
        The axis on the map is plotted.
    """
    warn( ("The method `plot_map` is deprecated and will be removed from the"\
            " library in future versions. Please use either `add_basemap` or"\
            " the internal method `Place.plot`"), DeprecationWarning)
    if not isinstance(place, Place):
        im = place
        bbox = bbox
        title = title
    else:
        im = place.im
        if bbox is None:
            bbox = place.bbox_map
            if latlon is True:
                # Convert w, s, e, n into lon/lat
                w, e, s, n = bbox
                w, s = _sm2ll(w, s)
                e, n = _sm2ll(e, n)
                bbox = [w, e, s, n]

        title = place.place if title is None else title

    if ax is None:
        fig, ax = plt.subplots(figsize=(15, 15))
    ax.imshow(im, extent=bbox)
    ax.set(xlabel="X", ylabel="Y")
    if title is not None:
        ax.set(title=title)

    if axis_off is True:
        ax.set_axis_off()
    return ax
