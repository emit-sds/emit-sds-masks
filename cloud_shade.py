import click
import numpy as np

from osgeo import gdal
import bresenham_line
import logging
from scipy.interpolate import griddata
from scipy.ndimage import distance_transform_edt


def edge_coords_from_target(target_px_x: np.array, target_px_y: np.array, angle: np.array, bounds):
    """ Get the coordinates of the edge pixel in the direction of the given angle from a target pixel.

    Args:
        target_px_x (array, int): array of x-coordinate of the target pixel.
        target_px_y (array, int): array of y-coordinate of the target pixel.
        angle (array, float): angle in degrees, clockwise from North.
        bounds (tuple): bounds of the image in the format (min_x, min_y, max_x, max_y).
    """

    # Compute direction vector (dx, dy) in image coordinates
    dy = np.sin(np.deg2rad(angle))  
    dx = np.cos(np.deg2rad(angle))  
    #dy = -dy  # Invert y direction for image coordinates

    invert = np.zeros_like(angle, dtype=bool)
    invert[np.logical_and(angle > 180, angle < 360)] = True
    invert[np.logical_and(angle < 0, angle > -180)] = True

    xdelta = np.ones_like(angle, dtype=int) * target_px_x
    ydelta = np.ones_like(angle, dtype=int) * target_px_y

    if np.any(invert):
        print('inverting')
        xdelta[invert] = bounds[2] - target_px_x
        ydelta[invert] = bounds[3] - target_px_y
        xdelta[invert] *= -1
        ydelta[invert] *= -1

    # There will be two candidate edges, one on the x-axis, and one the y-axis.
    # Start by finding both
    edge_px_horizontal_y = np.zeros_like(angle, dtype=int) 
    if np.any(invert):
        edge_px_horizontal_y[invert] = bounds[3]
    edge_px_horizontal_x = dx / dy * ydelta  + target_px_x

    edge_px_vertical_x = np.zeros_like(angle, dtype=int)
    if np.any(invert):
        edge_px_vertical_x[invert] = bounds[2]
    edge_px_vertical_y = dy / dx * xdelta + target_px_y

    vertical_select = np.logical_or.reduce((
        edge_px_horizontal_x < bounds[0],
        edge_px_horizontal_x > bounds[2],
        edge_px_horizontal_y < bounds[1],
        edge_px_horizontal_y > bounds[3]
    ))

    edge_px_x_out = edge_px_horizontal_x.copy()
    edge_px_y_out = edge_px_horizontal_y.copy()
    edge_px_x_out[vertical_select] = edge_px_vertical_x[vertical_select]
    edge_px_y_out[vertical_select] = edge_px_vertical_y[vertical_select]
    slope = dy / dx
    return edge_px_x_out, edge_px_y_out, slope


def distance_of_ray(sza, solar_slope, pixel_size, cloud_height_above_surface_m=4000):
    straight_distance = np.cos(np.deg2rad(sza)) * cloud_height_above_surface_m
    x_fraction = np.abs(np.cos(np.arctan(solar_slope)))
    x_distance_m = x_fraction * straight_distance
    x_distance_px = x_distance_m / pixel_size

    return x_distance_px


def cwn_to_math(angle_cw_from_north):
    return (90 - angle_cw_from_north) % 360


def ortho(img_dat, glt, glt_nodata_value=0):
    """Orthorectify a single image

    Args:
        img_dat (array like): raw input image
        glt (array like): glt - 2 band 1-based indexing for output file(x, y)
        glt_nodata_value (int, optional): Value from glt to ignore. Defaults to 0.

    Returns:
        array like: orthorectified version of img_dat
    """
    outdat = np.zeros((glt.shape[0], glt.shape[1], img_dat.shape[-1]))
    outdat[...] = np.nan
    valid_glt = np.all(glt != glt_nodata_value, axis=-1)
    glt[valid_glt] -= 1 # account for 1-based indexing
    outdat[valid_glt, :] = img_dat[glt[valid_glt, 1], glt[valid_glt, 0], :]
    return outdat


def unortho(img_dat, glt, outshape, glt_nodata_value=0, interpolate=False):
    """Unorthorectify a single image

    Args:
        img_dat (array like): raw input image
        glt (array like): glt - 2 band 1-based indexing for output file(x, y)
        glt_nodata_value (int, optional): Value from glt to ignore. Defaults to 0.

    Returns:
        array like: unorthorectified version of img_dat
    """
    outdat = np.zeros(outshape, dtype=np.float32)
    outdat[:] = np.nan
    valid_glt = np.all(glt != glt_nodata_value, axis=-1)
    glt[valid_glt] -= 1 # account for 1-based indexing
    outdat[glt[valid_glt, 1], glt[valid_glt, 0], :] = img_dat[valid_glt]

    if interpolate:
        # use 2d linear interpolation from scipy to interpolate the nans
        x = np.arange(outdat.shape[1])
        y = np.arange(outdat.shape[0])
        xx, yy = np.meshgrid(x, y)
        valid_mask = ~np.isnan(outdat[:, :])
        points = np.column_stack((xx[valid_mask], yy[valid_mask]))
        values = outdat[valid_mask]
        outdat = griddata(points, values, (xx, yy), method='nearest', fill_value=np.nan)
        

    return outdat


@click.command()
@click.argument('cloud_file', '-c', type=click.Path(exists=True), required=True,
              help='Path to cloud file')
@click.argument('obs_file', '-o', type=click.Path(exists=True), required=True,
              help='Path to observation file')
@click.argument('glt_file', '-o', type=click.Path(exists=True), required=True,
              help='Path to the glt file')
@click.argument('output_file', '-out', type=click.Path(), 
              help='Output file path')
@click.option('--solar_azimuth_band', '-sa', type=int, default=4)
@click.option('--solar_zenith_band', '-sz', type=int, default=5)
@click.option('--log_level', '-l', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), default='INFO',
              help='Set the logging level')
@click.option('--log_file', '-lf', type=click.Path(), default=None,
              help='Path to the log file. If not provided, logs will be printed to console.')
def main(cloud_file, obs_file, output_file, glt_file,
         solar_azimuth_band, solar_zenith_band, log_level, log_file):
    """Process cloud and observation files."""

    logging.basicConfig(level=log_level, filename=log_file, filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info('Starting cloud processing')
    logging.info('Arguments: %s', {
        'cloud_file': cloud_file,
        'obs_file': obs_file,
        'glt_file': glt_file,
        'output_file': output_file,
        'solar_azimuth_band': solar_azimuth_band,
        'solar_zenith_band': solar_zenith_band,
        'log_level': log_level,
        'log_file': log_file
    })
    
    
    logging.info(f"Reading cloud file: {cloud_file}")
    cloud_set = gdal.Open(cloud_file, gdal.GA_ReadOnly)
    clouds = cloud_set.ReadAsArray()
    
    logging.info(f"Reading observation file: {obs_file}")
    obs_set = gdal.Open(obs_file, gdal.GA_ReadOnly)
    solar_azimuth = obs_set.GetRasterBand(solar_azimuth_band).ReadAsArray()
    solar_zenith = obs_set.GetRasterBand(solar_zenith_band).ReadAsArray()

    logging.info(f"Reading GLT file: {glt_file}")
    glt_set = gdal.Open(glt_file, gdal.GA_ReadOnly)
    glt = glt_set.ReadAsArray()


    logging.info("Ortho files")
    solar_azimuth = ortho(solar_azimuth[..., np.newaxis], glt).squeeze()
    solar_zenith = ortho(solar_zenith[...,np.newaxis], glt).squeeze()
    clouds = ortho(clouds[...,np.newaxis], glt).squeeze() == 1

    logging.info("Run ray trace")
    bounds = (0, 0, solar_azimuth.shape[1] - 1, solar_azimuth.shape[0] - 1)
    clouds_loc = np.where(clouds)
    antisolar_edge_px_x, antisolar_edge_px_y, antisolar_s = edge_coords_from_target(clouds_loc[1], clouds_loc[0], cwn_to_math(solar_azimuth[clouds] +15 - 180), bounds)
    num_x_pixels = distance_of_ray(solar_zenith[clouds], antisolar_s, 60)
    out_mask = np.ones_like(solar_azimuth)*1e6
    for _l in range(len(clouds_loc[0])):
        linepx = bresenham_line.bresenhamline(np.array([clouds_loc[1][_l], clouds_loc[0][_l]]).reshape(1,-1), np.array([antisolar_edge_px_x[_l], antisolar_edge_px_y[_l]]).reshape(1,-1), max_iter=num_x_pixels[_l])
        valid = linepx[:,0] < bounds[2]
        valid[linepx[:,1] >= bounds[3]] = False

        linepx = linepx[valid,:]
        px_dist = np.sqrt((linepx[:,0] - clouds_loc[1][_l])**2 + (linepx[:,1] - clouds_loc[0][_l])**2)
        out_mask[linepx[:,1], linepx[:,0]] = np.minimum(px_dist, out_mask[linepx[:,1], linepx[:,0]])
    out_mask[out_mask == 1e6] = 0
    out_mask[clouds_loc[0], clouds_loc[1]] = 0


    logging.info("Unortho output mask")
    out_mask = unortho(out_mask, glt, (cloud_set.RasterYSize, cloud_set.RasterXSize), interpolate=True)

    logging.info(f"Writing output to {output_file}")
    driver = gdal.GetDriverByName('GTiff')
    outDataset = driver.Create(output_file, cloud_set.RasterXSize, cloud_set.RasterYSize, 1, gdal.GDT_Float32, ['COMPRESS=LZW'])
    outDataset.GetRasterBand(1).WriteArray(out_mask, 0, 0)
    del outDataset

    

if __name__ == '__main__':
    main()