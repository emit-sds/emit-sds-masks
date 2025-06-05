import argparse
import os
import subprocess

from osgeo import gdal
import numpy as np
from spectral.io import envi
from emit_utils.file_checks import envi_header


def main():

    parser = argparse.ArgumentParser(description="Remove glint")
    parser.add_argument('rdnfile', type=str, metavar='RADIANCE')
    parser.add_argument('obsfile', type=str, metavar='OBSERVATIONS')
    parser.add_argument('outfile', type=str, metavar='OUTPUT_MASKS')
    args = parser.parse_args()

    rdn_hdr_path = envi_header(args.rdnfile)
    rdn_hdr = envi.read_envi_header(rdn_hdr_path)

    obs_hdr_path = envi_header(args.obsfile)

    tmp_maskTf_path = os.path.join(os.path.dirname(args.outfile),
                                   'temp_clouds.tif')

    cmd = [
        "spectf-cloud", "deploy-pt",
        tmp_maskTf_path,
        obs_hdr_path,
        rdn_hdr_path,
        "--proba"
    ]

    subprocess.run(cmd, check=True)

    # Build output dataset
    cloud_dset = gdal.Open(tmp_maskTf_path)

    maskbands = 2
    mask = np.zeros((cloud_dset.RasterYSize, maskbands, cloud_dset.RasterXSize))
    mask[:,0] = cloud_dset.ReadAsArray()

    rdn_dataset = gdal.Open(args.rdnfile, gdal.GA_ReadOnly)

    driver = gdal.GetDriverByName('ENVI')
    driver.Register()

    outDataset = driver.Create(args.outfile, cloud_dset.RasterXSize, cloud_dset.RasterYSize, maskbands, gdal.GDT_Float32, options=['INTERLEAVE=BIL'])
    outDataset.SetProjection(rdn_dataset.GetProjection())
    outDataset.SetGeoTransform(rdn_dataset.GetGeoTransform())
    del outDataset

    hdr = rdn_hdr.copy()
    hdr['bands'] = str(maskbands)
    hdr['band names'] = ['SpecTf-Cloud probability',
                         'Cloud shadow']
    hdr['interleave'] = 'bil'
    del hdr['wavelength']
    del hdr['fwhm']
    envi.write_envi_header(envi_header(args.outfile), hdr)
    mask.astype(dtype=np.float32).tofile(args.outfile)

    os.remove(tmp_maskTf_path)

if __name__ == "__main__":
    main()
