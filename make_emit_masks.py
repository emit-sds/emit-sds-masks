"""
Mask generation for imaging spectroscopy, oriented towards EMIT.

Authors: David R. Thompson, david.r.thompson@jpl.nasa.gov,
         Philip G. Brodrick, philip.brodrick@jpl.nasa.gov
"""

import argparse
from osgeo import gdal
import numpy as np
from spectral.io import envi
from scipy.ndimage.morphology import distance_transform_edt
from isofit.core.common import resample_spectrum
from emit_utils.file_checks import envi_header


def haversine_distance(lon1, lat1, lon2, lat2, radius=6335439):
    """ Approximate the great circle distance using Haversine formula

    :param lon1: point one longitude
    :param lat1: point one latitude
    :param lon2: point two longitude
    :param lat2: point two latitude
    :param radius: radius to use (default is approximate radius at equator)

    :return: great circle distance in radius units
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1

    d = 2 * radius * np.arcsin(np.sqrt(np.sin(delta_lat/2)**2 + np.cos(lat1)
                               * np.cos(lat2) * np.sin(delta_lon/2)**2))

    return d

def main():

    parser = argparse.ArgumentParser(description="Remove glint")
    parser.add_argument('rdnfile', type=str, metavar='RADIANCE')
    parser.add_argument('locfile', type=str, metavar='LOCATIONS')
    parser.add_argument('obsfile', type=str, metavar='OBSERVATIONS')
    parser.add_argument('atmfile', type=str, metavar='SUBSET_LABELS')
    parser.add_argument('cloudfile', type=str, metavar='SPECTF_CLOUD_PROB')
    parser.add_argument('irrfile', type=str, metavar='SOLAR_IRRADIANCE')
    parser.add_argument('outfile', type=str, metavar='OUTPUT_MASKS')
    parser.add_argument('--wavelengths', type=str, default=None)
    parser.add_argument('--n_cores', type=int, default=-1)
    parser.add_argument('--aerosol_threshold', type=float, default=0.5)
    args = parser.parse_args()

    rdn_hdr = envi.read_envi_header(envi_header(args.rdnfile))
    rdn_shp = envi.open(envi_header(args.rdnfile)).open_memmap(interleave='bil').shape
    atm_hdr = envi.read_envi_header(envi_header(args.atmfile))
    atm_shp = envi.open(envi_header(args.atmfile)).open_memmap(interleave='bil').shape
    loc_shp = envi.open(envi_header(args.locfile)).open_memmap(interleave='bil').shape

    cloud_dset = gdal.Open(args.cloudfile)

    # Check file size consistency
    if loc_shp[0] != rdn_shp[0] or loc_shp[2] != rdn_shp[2]:
        raise ValueError('LOC and input file dimensions do not match.')
    if atm_shp[0] != rdn_shp[0] or atm_shp[2] != rdn_shp[2]:
        raise ValueError('Label and input file dimensions do not match.')
    if loc_shp[1] != 3:
        raise ValueError('LOC file should have three bands.')
    if cloud_dset.RasterYSize != rdn_shp[0] or cloud_dset.RasterXSize != rdn_shp[2]:
        raise ValueError('Cloud mask and input file dimensions do not match.')

    # Get wavelengths and bands
    if args.wavelengths is not None:
        c, wl, fwhm = np.loadtxt(args.wavelengths).T
    else:
        if 'wavelength' not in rdn_hdr:
            raise IndexError('Could not find wavelength data anywhere')
        else:
            wl = np.array([float(f) for f in rdn_hdr['wavelength']])
        if 'fwhm' not in rdn_hdr:
            raise IndexError('Could not find fwhm data anywhere')
        else:
            fwhm = np.array([float(f) for f in rdn_hdr['fwhm']])

    # Find H2O and AOD elements in state vector
    aod_bands, h2o_band = [], []
    for i, name in enumerate(atm_hdr['band names']):
        if 'H2O' in name:
            h2o_band.append(i)
        elif 'AER' in name or 'AOT' in name or 'AOD' in name:
            aod_bands.append(i)

    # find pixel size
    if 'map info' in rdn_hdr.keys():
        pixel_size = float(rdn_hdr['map info'][5].strip())
    else:
        loc_memmap = envi.open(envi_header(args.locfile)).open_memmap(interleave='bip')
        center_y = int(loc_shp[0]/2)
        center_x = int(loc_shp[2]/2)
        center_pixels = loc_memmap[center_y-1:center_y+1, center_x, :2]
        pixel_size = haversine_distance(
            center_pixels[0, 1], center_pixels[0, 0], center_pixels[1, 1], center_pixels[1, 0])
        del loc_memmap, center_pixels

    # convert from microns to nm
    if not any(wl > 100):
        wl = wl*1000.0

    # irradiance
    irr_wl, irr = np.loadtxt(args.irrfile, comments='#').T
    irr = irr / 10  # convert to uW cm-2 sr-1 nm-1
    irr_resamp = resample_spectrum(irr, irr_wl, wl, fwhm)
    irr_resamp = np.array(irr_resamp, dtype=np.float32)

    rdn_dataset = gdal.Open(args.rdnfile, gdal.GA_ReadOnly)
    maskbands = 11

    # Build output dataset
    driver = gdal.GetDriverByName('ENVI')
    driver.Register()

    outDataset = driver.Create(args.outfile, rdn_shp[2], rdn_shp[0], maskbands, gdal.GDT_Float32, options=['INTERLEAVE=BIL'])
    outDataset.SetProjection(rdn_dataset.GetProjection())
    outDataset.SetGeoTransform(rdn_dataset.GetGeoTransform())
    del outDataset

    # replace previous build_line_masks
    b450 = np.argmin(abs(wl-450))
    b762 = np.argmin(abs(wl-762))
    b780 = np.argmin(abs(wl-780))
    b1000 = np.argmin(abs(wl-1000))
    b1250 = np.argmin(abs(wl-1250))
    b1380 = np.argmin(abs(wl-1380))
    b1650 = np.argmin(abs(wl-1650))

    rdn_ds = envi.open(envi_header(args.rdnfile)).open_memmap(interleave='bip')
    obs_ds = envi.open(envi_header(args.obsfile)).open_memmap(interleave='bip')
    atm_ds = envi.open(envi_header(args.atmfile)).open_memmap(interleave='bip')

    rdn = rdn_ds.copy().astype(np.float32)
    atm = atm_ds.copy().astype(np.float32)
    zen = np.radians(obs_ds[...,4].copy().astype(np.float32))

    rho = rdn * np.pi / irr_resamp[np.newaxis, np.newaxis, :] / np.cos(zen)[..., np.newaxis]

    bad = rdn[..., 0] <= -9990
    rho[bad, :] = -9999.0

    # Cloud threshold from Sandford et al.
    total = np.array(rho[..., b450] > 0.28, dtype=int) + \
        np.array(rho[..., b1250] > 0.46, dtype=int) + \
        np.array(rho[..., b1650] > 0.22, dtype=int)

    maskbands = 11
    mask = np.zeros((rdn_shp[0], rdn_shp[2], maskbands))
    mask[..., 0] = total > 2

    # Cirrus Threshold from Gao and Goetz, GRL 20:4, 1993
    mask[..., 1] = np.array(rho[..., b1380] > 0.1, dtype=int)

    # Water threshold as in CORAL
    mask[..., 2] = np.array(rho[..., b1000] < 0.05, dtype=int)

    # Threshold spacecraft parts using their lack of an O2 A Band
    mask[..., 3] = np.array(rho[..., b762]/rho[..., b780] > 0.8, dtype=int)

    max_cloud_height = 3000.0
    cloud_projection_dist = np.tan(zen) * max_cloud_height / pixel_size

    # AOD 550
    mask[..., 5] = atm[..., aod_bands].sum(axis=1)

    mask[..., 6] = atm[..., h2o_band].squeeze()

    # Remove water and spacecraft flagsg if cloud flag is on (mostly cosmetic)
    mask[np.logical_or(mask[...,0] == 1, mask[...,1] ==1), 2:4] = 0

    # Create buffer around clouds (main and cirrus)
    cloudinv = np.logical_not(np.squeeze(np.logical_or(mask[..., 0], mask[...,1])))
    cloudinv[bad] = 1
    cloud_distance = distance_transform_edt(cloudinv)
    invalid = np.squeeze(cloud_projection_dist) >= cloud_distance
    mask[..., 4] = invalid.copy()

    # Combine Cloud, Cirrus, Water, Spacecraft, and Buffer masks
    mask[..., 7] = np.logical_or(np.sum(mask[...,0:5], axis=-1) > 0, mask[...,5] > args.aerosol_threshold)

    # SpecTF-Cloud probability
    mask[..., 8] = cloud_dset.ReadAsArray()

    # To-do - ideally get this threshold from spectf repository
    mask[..., 9] = mask[..., 8] > 0.51

    tfinv = np.logical_not(mask[..., 9])
    tfinv[bad] = 1
    tf_distance = distance_transform_edt(tfinv)
    tf_distance[cloud_projection_dist <= tf_distance] = 0
    mask[..., 10] = tf_distance

    mask[bad, :] = -9999.0
    mask = mask.transpose((0,2,1))

    hdr = rdn_hdr.copy()
    hdr['bands'] = str(maskbands)
    hdr['band names'] = ['Cloud flag', 'Cirrus flag', 'Water flag',
                         'Spacecraft Flag', 'Dilated Cloud Flag',
                         'AOD550', 'H2O (g cm-2)', 'Aggregate Flag',
                         'SpecTf-Cloud probability', 'SpecTf-Cloud flag',
                         'SpecTF-Buffer Distance']
    hdr['interleave'] = 'bil'
    del hdr['wavelength']
    del hdr['fwhm']
    envi.write_envi_header(envi_header(args.outfile), hdr)
    mask.astype(dtype=np.float32).tofile(args.outfile)


if __name__ == "__main__":
    main()
