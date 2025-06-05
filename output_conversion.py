"""
This code contains support code for formatting L2A products for the LP DAAC.

Authors: Philip G. Brodrick, philip.brodrick@jpl.nasa.gov
"""

import argparse
from netCDF4 import Dataset
from emit_utils.daac_converter import add_variable, makeDims, makeGlobalAttr, add_loc, add_glt
from emit_utils.file_checks import netcdf_ext, envi_header
from spectral.io import envi
import logging
import numpy as np


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description='''This script \
    converts L2AMaskTf PGE output to DAAC compatable formats, with supporting metadata''', add_help=True)

    parser.add_argument('mask_output_filename', type=str, help="Output Mask netcdf filename")
    parser.add_argument('mask_file', type=str, help="EMIT L2A water/cloud mask ENVI file")
    parser.add_argument('loc_file', type=str, help="EMIT L1B location data ENVI file")
    parser.add_argument('glt_file', type=str, help="EMIT L1B glt ENVI file")
    parser.add_argument('version', type=str, help="3 digit (with leading V) version number")
    parser.add_argument('software_delivery_version', type=str, help="The extended build number at delivery time")
    parser.add_argument('--ummg_file', type=str, help="Output UMMG filename")
    parser.add_argument('--log_file', type=str, default=None, help="Logging file to write to")
    parser.add_argument('--log_level', type=str, default="INFO", help="Logging level")
    args = parser.parse_args()

    if args.log_file is None:
        logging.basicConfig(format='%(message)s', level=args.log_level)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=args.log_level, filename=args.log_file)

    mask_ds = envi.open(envi_header(args.mask_file))

    # Start Mask File

    # make the netCDF4 file
    logging.info(f'Creating netCDF4 file: {args.mask_output_filename}')
    nc_ds = Dataset(args.mask_output_filename, 'w', clobber=True, format='NETCDF4')

    # make global attributes
    logging.debug('Creating global attributes')
    makeGlobalAttr(nc_ds, args.mask_file, args.software_delivery_version, glt_envi_file=args.glt_file)

    #TODO: UPDATE TITLE AND SUMMARY
    nc_ds.title = "EMIT L2A Masks 60 m " + args.version   
    nc_ds.summary = nc_ds.summary + \
        f"\\n\\nThis file contains masks for L2A estimated surface reflectances \
and geolocation data. Masks account for clouds and cloud shadows. \
Geolocation data (latitude, longitude, height) and a lookup table to project the data are also included."
    nc_ds.sync()

    logging.debug('Creating dimensions')
    makeDims(nc_ds, args.mask_file, args.glt_file)

    logging.debug('Creating and writing mask metadata')
    add_variable(nc_ds, "sensor_band_parameters/mask_bands", str, "Mask Band Names", None,
                 mask_ds.metadata['band names'], {"dimensions": ("bands",)})

    logging.debug('Creating and writing location data')
    add_loc(nc_ds, args.loc_file)

    logging.debug('Creating and writing glt data')
    add_glt(nc_ds, args.glt_file)

    logging.debug('Write mask data')
    add_variable(nc_ds, 'mask', "f4", "Masks", "unitless", mask_ds.open_memmap(interleave='bip')[...].copy(),
                 {"dimensions":("downtrack", "crosstrack", "bands"), "zlib": True, "complevel": 9})
    nc_ds.sync()
    nc_ds.close()
    del nc_ds
    logging.debug(f'Successfully created {args.mask_output_filename}')

    return


if __name__ == '__main__':
    main()
