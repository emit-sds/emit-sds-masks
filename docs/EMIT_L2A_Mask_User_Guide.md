# Earth Surface Mineral Dust Source Investigation (EMIT)

## Level 2A Mask Product User Guide


**Version:** 0.1 </br>
**Release Date:** TBD </br>
**JPL- D-107874** </br>

Jet Propulsion Laboratory
California Institute of Technology
Pasadena, California 91109

**Change Log**
| Version | Date       | Comments |
|---------|------------|----------|
| 0.0     | 2025-09-09 | Initial Draft |
| 0.1     | 2025-12-02 | Cleanup for initial V002 release |

<div style="page-break-after: always;"></div>

## Table of Contents
- [1 Introduction](#1-introduction)
  - [1.1 Identification](#11-identification)
  - [1.2 Overview](#12-overview)
  - [1.3 File Formats](#13-file-formats)
    - [1.3.1 Metadata Structure](#131-metadata-structure)
    - [1.3.2 Data Products](#132-data-products)
  - [1.4 Product Availability](#14-product-availability)
- [2 Cloud Mask Generation](#2-cloud-mask-generation)
- [3 References](#3-references)
- [4 Acronyms](#4-acronyms)

## 1	Introduction

### 1.1	Identification
This document describes information about the file structure and datasets provided in the EMIT L2A Mask data product. The algorithms and data content of the L2A Mask data products are described briefly in this guide, with the purpose of providing the user with sufficient information about the content and structure of the data files to enable the user to access and use the data, in addition to understanding the uncertainties involved in the products.

### 1.2	Overview
The EMIT Project delivers space-based measurements of surface mineralogy of the Earth's arid dust source regions. These measurements are used to initialize Earth System Models (ESM) of the dust cycle, which describe the generation, lofting, transport, and deposition of mineral dust. Earth System Models incorporate the dust cycle to estimate the impacts of mineral dust on the optical and radiative properties of the atmosphere, and a variety of environmental and ecological processes. EMIT on the ISS makes measurements over the sunlit Earth's surface in the range of ±52° latitude. EMIT-based maps of the fractional cover of surface classes is an essential product needed for analysis of the relative abundance of source minerals to address the prime mission science questions, as well as supporting additional science and applications uses.

The EMIT instrument is a Dyson imaging spectrometer that uses contiguous spectroscopic measurements in the visible to short wavelength infrared region of the spectrum to resolve absorption features of dust-forming minerals. From the instrument's focal plane array, on-board avionics reads out raw detector counts at 1.6 Gbps, then digitizes and stores this data to a high-speed Solid-State Data Recorder (SSDR).  From there, the avionics software reads the raw uncompressed data, packages this data into frames of 32 instrument lines, screens for cloudy pixels within the frames, and performs a lossless 4:1 compression of the frame's science data before storing the processed, compressed data back onto the SSDR. The data is later read from the SSDR, wrapped in CCSDS packets and then formatted as ethernet packets for transmission over the International Space Station (ISS) network and downlinked to the EMIT Instrument Operation System (IOS). Once on the ground, the EMIT IOS delivers the raw ethernet data to the SDS where Level 0 processing removes the Huntsville Operations and Support Center (HOSC) ethernet headers, groups CCSDS packet streams by APID, and sorts them by course and fine time.

The Level 2A Mask (EMITL2AMASK) data product contains mask information generated from L1B Radiance data and the L2A surface and atmospheric modeling step. The V002 mask contains both traditional mask data (which was previously part of the EMITL2ARFL collection inside the L2A_Mask file) along with cloud mask results from a deep learning model (Lee et al., 2025). In addition, the geolocation of all pixel centers is included as well as the calculation of observation geometry and illumination angles on a pixel-by-pixel basis. Each image line of the data product is also UTC time-tagged.

The EMIT L2A Mask products are delivered as NetCDF files, with quicklooks as PNG files.

### 1.3 File Formats

#### 1.3.1 Metadata Structure

EMIT is operating from the ISS, orbiting Earth approx. 16 times in a 24-hour day period. EMIT starts and stops data recording based on a surface coverage acquisition mask. The top-level metadata identifier for EMIT data is an orbit, representing a single rotation of the ISS around Earth. Within an orbit, a period of continuous data acquisition is called an orbit segment.  An orbit contains multiple orbit segments, where each orbit segment can cover up to thousands of kilometers down-track, depending on the acquisition mask map. Each orbit segment is subsequently chunked into granules of 1280 lines down-track called scenes. The last scene in an orbit segment is merged into the one before, making the last scene to be between 1280 and 2560 lines down-track. Scenes, also referred to as "granules", can be downloaded as NetCDF files, and are identified by a date-time string in the file name.  

#### 1.3.2 Data Products

The "EMIT L2A Mask 60 m V002" collection (EMITL2AMASK) contains a single NetCDF file with multiple layers. Each granule represents a single scene and comes with a quicklook PNG file (Browse), as described in Table 1-1.

**Table 1-1:** EMITL2AMASK collection file list and naming convention

|  File  |  Description  |
|--------|----------------|
| `EMIT_L2A_MASK_<VVV>_<YYYYMMDDTHHMMSS>_<OOOOOOO>_<SSS>.nc`  | Mask Data|
| `EMIT_L2A_MASK_<VVV>_<YYYYMMDDTHHMMSS>_<OOOOOOO>_<SSS>.png`  | Browse |

`<VVV>` gives the product version number, e.g., 002

`<YYYYMMDDTHHMMSS>` is a time stamp, e.g., 20220101T083015

`<OOOOOOO>` is the unique orbit identification number, e.g., 2530101

`<SSS>` is the scene identification number within an orbit, e.g., 007

The file structure for the EMIT_L2A_Mask netcdf file is described in Table 1-2.

**Table 1-2:** EMIT L2A Mask NetCDF File Structure

Group | Field Name | Type | Units | Comments
---------|----------------|-------|-------|----------------
Root | mask | float32 | Unitless | Masks
location | glt_x | int32 | Pixel location | GLT Sample Lookup
location | glt_y | int32 | Pixel location | GLT Line Lookup
location | lat | float64 | Decimal degrees north | Latitude (WGS-84)
location | lon | float64 | Decimal degrees east | Longitude (WGS-84)
location | elev | float32 | Meters | Surface Elevation
sensor_band_parameters | mask_bands | str Array | Labels | Array of strings indicating the name of each mask band

Each band in the 3D mask array corresponds to a row entry in Table 1-3.  See the ATBD for more details about the generation of each band.

**Table 1-3:** EMIT L2A Mask Bands

IDX | Band Name | Band Description
----|----------------|----------------
1 | Cloud Flag | Cloud Coverage
2 | Cirrus Flag | Dense Cirrus Clouds
3 | Water Flag | Water Bodies
4 | Spacecraft Flag | Spacecraft or space station components that intersect the EMIT field of view
5 | Dilated Cloud Flag | Cloud coverage + buffer
6 | AOD550 (unitless) | AOD at 550nm estimate from L2ARFL
7 | H2O (g cm<sup>-2</sup>) | Water vapor column estimate from L2ARFL
8 | Aggregate Flag | Aggregate of all mask flags
9 | SpecTf Cloud Probability | Probability of cloud presence from SpecTf model
10 | SpecTf Cloud Flag | Binary cloud flag from SpecTf model
11 | SpecTf-Buffer Distance | Distance to nearest cloud pixel from SpecTf model


### 1.4 Product Availability
The EMIT L2AMASK products will be available at the NASA Land Processes Distributed Active Archive Center (LP DAAC, https://lpdaac.usgs.gov/) and through NASA Earthdata (https://earthdata.nasa.gov/).


## 2	Cloud Mask Generation
EMIT's Level 2A Mask (L2AMASK) product is generated using outputs from simple band thresholding, atmospheric results from the optimal-estimation based surface and atmospheric modeling in the L2ARFL collection, and a new deep learning model for cloud detection called SpecTf (Lee et al., 2025). Code for the collection is available in the [emit-sds-masks](https://github.com/emit-sds/emit-sds-masks) repository. Code to generate the optimal-estimation based atmospheric components is available as part of the [isofit](https://github.com/isofit/isofit/pulls) repository, and the spectral transformer model is available at the [SpecTF](https://github.com/emit-sds/SpecTf/tree/main/spectf_cloud) repository. 

## 3 References

* J.H. Lee, M. Kiper, D.R. Thompson, and P.G. Brodrick, SpecTf: Transformers enable data-driven imaging spectroscopy cloud detection, Proc. Natl. Acad. Sci. U.S.A. 122 (27) e2502903122, https://doi.org/10.1073/pnas.2502903122 (2025).

## 4	Acronyms
| Acronym | Definition |
|---------|------------|
| ATBD    | Algorithm Theoretical Basis Document |
| APID    | Application Process Identifier |
| CCSDS   | Consultative Committee for Space Data Systems |
| DAAC    | Distributed Active Archive Center |
| ESM     | Earth System Models |
| EMIT    | Earth Surface Mineral Dust Source Investigation |
| HOSC    | Huntsville Operations and Support Center |
| IOS     | Instrument Operation System |
| ISS     | International Space Station |
| L2AMASK | Level 2A Mask |
| LP DAAC | Land Processes Distributed Active Archive Center |
| PNG     | Portable Network Graphics |
| QC      | Quality Control |
| SDS     | Science Data System |
| SpecTf  | Spectral Transformer Model |
| SSDR    | Solid-State Data Recorder |

