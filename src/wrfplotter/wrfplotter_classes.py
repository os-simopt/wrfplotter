import matplotlib.pyplot as plt
from netCDF4 import Dataset
import numpy as np
import pandas as pd
import wrf
import xarray as xr
import datetime as dt
from pathlib import PosixPath, Path
import os
import yaml
from typing import Union
from wrfplotter.mpl_plots import Availability, Map_Cartopy
from wrfplotter.hv_plots import Map_hvplots
from wrfplotter.load_and_prepare import get_limits_and_labels


class Map:
    """
    Management of wrfdata for Map plotting. Loads data, manages units, cmaps and vlims.
    """

    def __init__(self, **kwargs):

        self.data = xr.DataArray()
        self.hgt = xr.DataArray()
        self.ivg = xr.DataArray()
        self.fig = None

        # have a default plot path
        if "plot_path" in kwargs:
            self.plot_path = Path(kwargs["plot_path"])
        else:
            self.plot_path = Path("/")

        if "intermediate_path" in kwargs:
            self.intermediate_path = Path(kwargs["intermediate_path"])
        else:
            self.intermediate_path = Path("/")

        if "fmt" in kwargs:
            self.fmt = kwargs["fmt"]
        else:
            self.fmt = "png"

    # ----------------------------------------------------------------------
    def extract_data_from_wrfout(self, filename: PosixPath, dom: str, var: str, ml: int, select_time=-1) -> None:
        """

        This function is basically a wrapper to the wrf.getvar function. It loads the required data and
        sets metadata accordingly.

        It has a major advantage. Using the wrf-python package allows a user to calculate de-staggered data,
        apply transformations (grid to earth rotated etc.) This is VERY powerful.
        HOWEVER, wrf-python does not work with DASK and therefore it cannot lazy-load data. This makes everything
        EXTREMELY slow. if one wants to read a lot of files.
        # I may have to look at the code of wrf.get_var at some point and re-write it to work with dask...
        # Or wait for the guys at NCAR do do it.

        filename: a wrfout file
        dom: domain of the wrfoutfile (could be extracted from filename)
        var: the variable to load
        select_time: the time to load. If all times of a file should be loaded, set select_time == -1
        ml: model level
        """

        fid = Dataset(filename, "r", format="NETCDF4_CLASSIC")
        time = wrf.getvar(fid, "times", wrf.ALL_TIMES)

        if select_time == -1:
            idx = wrf.ALL_TIMES
        else:
            now = np.datetime64(select_time)
            idx = np.where(time == now)[0][0]

        if var == "T":
            data = wrf.getvar(fid, "tk", timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs["model_level"] = ml
        elif var == "PT":
            data = wrf.getvar(fid, "theta", units="K", timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs["model_level"] = ml
        elif var == "WSP":
            data = wrf.getvar(fid, "uvmet_wspd_wdir", units="m s-1", timeidx=idx, squeeze=False)[0][:, ml, :, :]
            data.name = "WSP"
            data = data.drop_vars("wspd_wdir")
            data.attrs["description"] = "earth rotated wspd"
            data.attrs["units"] = "m s-1"
            data.attrs["model_level"] = ml
        elif var == "DIR":
            data = wrf.getvar(fid, "uvmet_wspd_wdir", units="m s-1", timeidx=idx, squeeze=False)[1][:, ml, :, :]
            data.name = "DIR"
            data = data.drop_vars("wspd_wdir")
            data.attrs["description"] = "earth rotated wdir"
            data.attrs["units"] = "degrees"
            data.attrs["model_level"] = ml
        elif var in ["U", "V", "W"]:
            data = wrf.getvar(fid, var.lower() + "a", units="m s-1", timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs["model_level"] = ml
        elif var == "WSP10":
            data = wrf.getvar(fid, "wspd_wdir10", units="m s-1", timeidx=idx, squeeze=False)[0][:, :, :]
            data.name = "WSP10"
            data = data.drop_vars("wspd_wdir")
            data.attrs["units"] = "m s-1"
            data.attrs["model_level"] = "sfc"
        elif var == "DIR10":
            data = wrf.getvar(fid, "wspd_wdir10", units="m s-1", timeidx=idx, squeeze=False)[1][:, :, :]
            data.name = "DIR10"
            data = data.drop_vars("wspd_wdir")
            data.attrs["description"] = "earth rotated wdir at 10 m"
            data.attrs["units"] = "degrees"
            data.attrs["model_level"] = "sfc"
        elif var in ["PRES", "P"]:
            data = wrf.getvar(fid, "p", units="Pa", timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs["model_level"] = ml
        # These lines should work in principle. However, I do not have testdata at the ready, so remove these lines.
        # elif var in ["QV", "QVAPOR"]:
        #    data = wrf.getvar(fid, "QVAPOR", timeidx=idx, squeeze=False)[:, ml, :, :]
        #    data.attrs["model_level"] = ml
        elif var == "U10":
            data = wrf.getvar(
                fid, "uvmet10", units="m s-1", timeidx=idx, squeeze=False
            )[0][:, :, :]
            data.attrs["units"] = "m s-1"
            data.attrs["model_level"] = "sfc"
        elif var == "V10":
            data = wrf.getvar(
                fid, "uvmet10", units="m s-1", timeidx=idx, squeeze=False
            )[1][:, :, :]
            data.attrs["units"] = "m s-1"
            data.attrs["model_level"] = "sfc"
        elif var in ["HFX", "GRDFLX", "LH", "PSFC"]:
            data = wrf.getvar(fid, var, timeidx=idx, squeeze=False)[:, :, :]
            data.attrs["model_level"] = "sfc"
        elif var in ["LU_INDEX"]:
            data = wrf.getvar(fid, var, timeidx=0, squeeze=False)[:, :, :]
            data.attrs["model_level"] = "sfc"
        elif var in ["HGT"]:
            data = wrf.getvar(fid, "ter", units="m", timeidx=0, squeeze=False)[:, :, :]
            data.attrs["model_level"] = "sfc"
        else:
            data = wrf.getvar(fid, var, timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs["model_level"] = ml

        self.hgt = wrf.getvar(fid, "ter", units="m", timeidx=0, squeeze=True)
        self.ivg = wrf.getvar(fid, "LU_INDEX", timeidx=0, squeeze=True)

        # Set everything but forest to Nan, for highlighting only forest in Maps.
        tmp1 = (self.ivg.values > 1) & (self.ivg.values < 11)  # other
        tmp2 = (self.ivg.values > 10) & (self.ivg.values < 16)  # Forest
        tmp3 = self.ivg.values > 15  # Other
        self.ivg.values[tmp1] = 0
        self.ivg.values[tmp2] = 1
        self.ivg.values[tmp3] = 0
        tmp4 = self.ivg.values == 0
        self.ivg.values[tmp4] = np.nan

        self.data = data
        self.data.attrs["dom"] = dom

    def store_intermediate(self):
        """
        Extraction a subsample of Data from the full WRF Model output seems to be the best option to deal
        with the ploblem of large datasets and wrf-python being unable to use dask (creating a bottleneck).
        """

        # I need to replace the attribute 'projection' before I can store it as netcdf.

        def replace_proj(data_array: xr.DataArray):

            proj = data_array.projection
            new_attrs = dict()
            new_attrs["stand_lon"] = proj.stand_lon
            new_attrs["moad_cen_lat"] = proj.moad_cen_lat
            new_attrs["truelat1"] = proj.truelat1
            new_attrs["truelat2"] = proj.truelat2
            new_attrs["pole_lat"] = proj.pole_lat
            new_attrs["pole_lon"] = proj.pole_lon

            del data_array.attrs["projection"]

            data_array = data_array.assign_attrs(new_attrs)

            return data_array

        self.data = replace_proj(self.data)
        self.hgt = replace_proj(self.hgt)
        self.ivg = replace_proj(self.ivg)

        date = self.data.Time.values[0]
        t = pd.to_datetime(str(date))
        timestring = t.strftime("%Y%m%d_%H%M%S")

        if self.data.model_level == "sfc":
            savename = (
                    self.intermediate_path
                    / f"Interm_{self.data.dom}_{self.data.name}_{timestring}.nc"
            )
        else:
            savename = (
                    self.intermediate_path
                    / f"Interm_{self.data.dom}_{self.data.name}_{timestring}_ml{self.data.model_level}.nc"
            )

        self.data.to_netcdf(savename)
        self.hgt.to_netcdf(self.intermediate_path / f"hgt_{self.data.dom}.nc")
        self.ivg.to_netcdf(self.intermediate_path / f"ivg_{self.data.dom}.nc")

    def load_intermediate(self, dom: str, var: str, model_level, timestring: str):
        def replace_proj2(data_array: xr.DataArray):

            proj = wrf.projection.LambertConformal(
                stand_lon=data_array.stand_lon,
                moad_cen_lat=data_array.moad_cen_lat,
                truelat1=data_array.truelat1,
                truelat2=data_array.truelat2,
                pole_lat=data_array.pole_lat,
                pole_lon=data_array.pole_lon,
            )

            new_attrs = dict()
            new_attrs["projection"] = proj
            del data_array.attrs["stand_lon"]
            del data_array.attrs["moad_cen_lat"]
            del data_array.attrs["truelat1"]
            del data_array.attrs["truelat2"]
            del data_array.attrs["pole_lat"]
            del data_array.attrs["pole_lon"]

            data_array = data_array.assign_attrs(new_attrs)

            return data_array

        if model_level == "sfc":
            savename = self.intermediate_path / f"Interm_{dom}_{var}_{timestring}.nc"
        else:
            savename = (
                    self.intermediate_path
                    / f"Interm_{dom}_{var}_{timestring}_ml{model_level}.nc"
            )

        if timestring == "*":
            xa = xr.open_mfdataset(str(savename))
            self.data = xa[var]
        else:
            self.data = xr.open_dataarray(savename)

        self.hgt = xr.open_dataarray(self.intermediate_path / f"hgt_{dom}.nc")
        self.ivg = xr.open_dataarray(self.intermediate_path / f"ivg_{dom}.nc")

        self.data = replace_proj2(self.data)
        self.hgt = replace_proj2(self.hgt)
        self.ivg = replace_proj2(self.ivg)

    def plot(self, map_t="Cartopy", store=False, **kwargs) -> None:
        """
        This methods prepares the data for plotting cartopy or hvplot. Limits are set, cmaps
        are prepared. For IVGTYP, a simplification is applied (still?)
        """

        ttp = kwargs.get("time_to_plot", None)
        var = kwargs.get("var", None)
        plottype = kwargs.get("plottype", "Map")

        infos = get_limits_and_labels(plottype, var, map_data=self.data)
        infos["pcmesh"] = kwargs.get("pcmesh", False)
        infos["poi"] = kwargs.get("poi", None)

        if store:  # loop over all indices and save files
            tdim = self.data.shape[0]
            for tidx in range(0, tdim):

                tmp_data = self.data[tidx, :, :]

                if map_t == "Cartopy":
                    figure = Map_Cartopy(tmp_data, hgt=self.hgt, ivg=self.ivg, **infos)
                else:
                    figure = Map_hvplots(tmp_data, **infos)

                date = tmp_data.Time.values
                t = pd.to_datetime(str(date))
                timestring = t.strftime("%Y%m%d_%H%M%S")

                if self.data.model_level == "sfc":
                    savename = f"{self.plot_path}/Map_{self.data.dom}_{self.data.name}_{timestring}.{self.fmt}"
                else:
                    savename = (
                            f"{self.plot_path}/Map_{self.data.dom}_"
                            + f"{self.data.name}_{timestring}_ml{self.data.model_level}.{self.fmt}"
                    )

                if map_t == "Cartopy":
                    if figure is not None:
                        figure.savefig(savename, dpi=400)
                        plt.close(figure)
                else:
                    print("hvplot cannot be stored this way...")
                    raise NotImplementedError

        else:  # display only required tidx and return figure

            if ttp is not None:
                timestamp = ttp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp = self.data.indexes["Time"][0]

            tmp_data = self.data.sel({"Time": timestamp})

            if map_t == "Cartopy":
                figure = Map_Cartopy(tmp_data, hgt=self.hgt, ivg=self.ivg, **infos)
            else:
                figure = Map_hvplots(tmp_data, **infos)

            return figure


# ----------------------------------------------------------------------------------------------------------------------

# some helperfunctions

def get_list_of_filenames(name_of_dataset: str, dtstart: dt.datetime, dtend: dt.datetime, split=None):
    # this is for writing...
    """

    Args:
        name_of_dataset: Name of the dataset
        dtstart: start of timeseries
        dtend: end of timeseries
        split: if None, no splitting is done, otherwise use a pandas freq string
        (i.e. YS for split by year and MS for split by month)

    Returns: a list of filenames.

    """

    # The user provides an observation path and a stationname to be read in.
    # i.e. the structure is
    # obs_path/name_of_dataset1/<name_of_dataset1_start1_end1.nc>
    # obs_path/name_of_dataset1/<name_of_dataset1_start2_end2.nc>
    # obs_path/name_of_dataset1/...
    # obs_path/name_of_dataset2/<name_of_dataset2_start1_end1.nc>
    # obs_path/...

    # All of them must be in the CF-conform filetpye

    # The WRFplotter can provide startdate_enddate. The Stationname can be selected.

    #############################################################################
    # CONVENTION: Each file must be named Stationname_starttime_endtime.nc
    #############################################################################

    # Removing time info, to fit convention.
    dtstart2 = dt.datetime(dtstart.year, dtstart.month, dtstart.day)
    dtend2 = dt.datetime(dtend.year, dtend.month, dtend.day)

    filepath = Path(os.environ["OBSERVATIONS_PATH"]) / f"{name_of_dataset}/"

    # I may autodetect split in the future, or have some rules...
    if split is None:
        tvec = pd.date_range(start=dtstart2, end=dtend2, periods=2)
    else:
        tvec = pd.date_range(start=dtstart2, end=dtend2, freq=split)

    filenames = [filepath / f"{name_of_dataset}_{tvec[idx].strftime('%Y%m%d')}_{tvec[idx + 1].strftime('%Y%m%d')}.nc"
                 for idx in range(0, len(tvec) - 1)]
    return filenames, tvec


def get_max_timerange(name_of_dataset):
    filepath = Path(os.environ["OBSERVATIONS_PATH"]) / f"{name_of_dataset}/"
    list_of_files = list(filepath.glob(f"{name_of_dataset}*.nc"))
    list_of_files.sort()

    list_of_starts = [
        item.stem.replace(name_of_dataset, "").split("_")[1] for item in list_of_files
    ]
    list_of_ends = [
        item.stem.replace(name_of_dataset, "").split("_")[2] for item in list_of_files
    ]

    starts = np.asarray([dt.datetime.strptime(item, "%Y%m%d") for item in list_of_starts])
    ends = np.asarray([dt.datetime.strptime(item, "%Y%m%d") for item in list_of_ends])

    try:
        start = starts[0]
    except IndexError:
        start = dt.datetime(1970, 1, 1)

    try:
        end = ends[-1]
    except IndexError:
        end = dt.datetime(2070, 1, 1)

    tvec = list(pd.date_range(start, end, periods=10))

    return tvec


def calc_PT(data):
    """
    Calculate PT from P and T if these variables exists.
    This function assumes the name of the variables to be P_level and T_level.
    This may not be general enough!
    """

    def calc_PT_single_station(sdata):

        tmp_p = [i for i in list(sdata.variables) if i.startswith("P_")]
        tmp_t = [i for i in list(sdata.variables) if i.startswith("T_")]
        hgt = sdata["station_elevation"].values

        zp = [int(item.split("_")[1]) for item in tmp_p]
        zlow, zhigh = min(zp), max(zp)

        if sdata["P_" + str(zlow)].units == "hPa":
            factor = 100
        elif sdata["P_" + str(zlow)].units == "Pa":
            factor = 1
        else:
            raise ValueError

        plow = sdata["P_" + str(zlow)].values.T * factor
        phigh = sdata["P_" + str(zhigh)].values.T * factor

        ztarget = np.asarray([int(item.split("_")[1]) for item in tmp_t])

        # z amsl
        zlow = float(zlow) + hgt
        zhigh = float(zhigh) + hgt
        ztarget = ztarget.astype(float) + hgt

        # Transform T in PT
        # Calculate pressure at each Height.
        # This is based on the pressure measurements at two levels.
        # The expontential Formula is p=p0*exp(-z/H)
        # 1) calc H; 2) calc p0; 3) calc p(all relevant z)

        H = (zhigh - zlow) / np.log(plow / phigh)
        p0 = phigh / np.exp(-zhigh / H)

        for zlev in ztarget:
            ptarget = p0 * np.exp(-zlev / H)
            ##############################################
            kappa = 2.0 / 7.0  # R/cp
            p00 = 10 ** 5  # Pa
            ##############################################

            pt = (sdata["T_" + str(int(zlev))][:] + 273.15) * (p00 / ptarget) ** kappa
            pt = pt.assign_attrs(units="K")
            pt = pt.assign_attrs(standard_name="potential_temperature")
            pt = pt.assign_attrs(long_name="potential temperature")
            sdata = sdata.assign({"PT_" + str(int(zlev)): pt})
        ####################################################################################
        return sdata

    tmp1 = [i for i in list(data.variables) if i.startswith("P_")]
    tmp2 = [i for i in list(data.variables) if i.startswith("T_")]

    if len(tmp1) <= 1 or len(tmp2) == 0:
        return data

    if "station_name" in data.dims:
        nstat = data.dims["station_name"]
        tmp_all = []
        for idx in range(0, nstat):
            tmp_data = data.isel(station_name=idx)
            tmp_data = calc_PT_single_station(tmp_data)
            tmp_all.append(tmp_data)
        data = xr.concat(tmp_all, dim="station_name")
        data = data.set_coords({"station_name": "station_name"})
    else:
        data = calc_PT_single_station(data)

    return data


class Timeseries:
    """
    For reading, checking and writing timeseries data.

    Files must follow the following convention:
    1. they must follow this structure:
        OBSERVATIONS_PATH/<Stationname>/<Stationname_startdate_enddate.nc>
        OBSERVATIONS_PATH: environment variable (the absolute path)
        Stationname: Name of the Station or whatever the source of the Timeseries
        startdate, enddate: Format YYYYMMDD (== %Y%m%d)
    2. the files must be netcdf files that can be read by xarray
    3. Multiple files can be read at once.

    Data stored by this calss is stored in a netcdf file that follows the CF-Conventions.

    This class should be able to:
    - Read and write CF-conform ncfiles.
    - Accept data from outside sources along with metadata to write into a CF conform file
    - make some simple calculations (like calc PT)

    ****
    Be aware that right now, ds.to_netcdf is not able to write cf-conform netcdf files.
    One issue is, that a string variable, as used for the station_name has a variable length (VLEN),
    which is not allowed by the CF standard (and the cf-checker complains)

    This may be resolved with future version of either ds.to_netcdf or a less strict CF-convention.
    ****


    Daniel Leukauf, 07.03.2022
    """

    # I have removed plots for profiles and timeseries as such basic plots won't be used anyway.
    # The methods of hvplot.xarray take care of that and more sophisticated plots
    # are done by the plotter. I keep the availability plot though as this is quite useful.

    def __init__(self, name_of_dataset: str, data=None):
        """
        There are multiple ways to initialize this class:
        1) Provide "data". Must be an xr.Dataset or xr.DataArray.
        2) Read data conform with this class. -> read_cfconform_data
        3) Read non-conform nc-data. -> read_non_conform_ncdata
        4) to be extended.

        Args:
            name_of_dataset: The name of the Dataset. Used to create a folderstructure and search for data.
            data: optional, an xr.Dataset or an xr.DataArray
        """

        if not isinstance(name_of_dataset, str):
            print("name_of_dataset must be of type str")
            raise TypeError

        if (
                isinstance(data, xr.Dataset)
                or isinstance(data, xr.DataArray)
                or data is None
        ):
            self.data = data
        else:
            print("data must be of type xarray.Dataset of xarray.DataArray.")
            raise TypeError

        self.dataset = name_of_dataset

    # ----------------------------------------------------------------------
    #  Getters
    # ----------------------------------------------------------------------
    def read_cfconform_data(
            self,
            dtstart: dt.datetime,
            dtend: dt.datetime,
            metadata=None,
            calc_pt=False,
            verbose=False,
            use_dask=False,
            split=None,
    ):
        """
        Read timeseries data that is already conform with this class, i.e. get_list_of_filenames can find the data
        based on dataset name, dtstart and dtend and data is already in the correct format and has metadata.
        Data must be stored in the folder os.environ['OBSERVATIONS_PATH']/name_of_dataset/
        Args:
            dtstart: start of the dataset as YYYYMMDD
            dtend: end of the dataset as YYYYMMDD
            metadata: additional metadata or changes to the metadata that should be made.
            calc_pt: if potential temperature should be caluclated from temperature and pressure.
            verbose: Speak with user.
            use_dask: open as dask array
            split: YS for yearly, MS for monthly or None for no splitting

        Returns: None

        """

        if metadata is None:
            metadata = dict()

        filenames, disc = get_list_of_filenames(self.dataset, dtstart, dtend, split)
        if len(filenames) == 0:
            if verbose:
                print("No filenames found")
            return

        if verbose:
            for filename in filenames:
                print(f"Loading File {filename}")

        if use_dask:
            data = xr.open_mfdataset(filenames)
        else:
            data = []
            for filename in filenames:
                tmp = xr.load_dataset(filename)
                data.append(tmp)
            data = xr.concat(data, dim="time")
            # drop duplicates
            _, index = np.unique(data['time'], return_index=True)
            data = data.isel(time=index)

        if calc_pt:
            # This will only do something if T_X and P_Y exists.
            try:
                data = calc_PT(data)
            except:
                pass

        # CF Conform data already has attributes, but I can add more medadata here.
        # If these already exist, they are overwritten.
        data = data.assign_attrs(metadata)
        self.data = data

    def read_non_conform_ncdata(
            self,
            filenames: Union[str, list, PosixPath, os.PathLike],
            concat_dim: str,
            meta_table: pd.DataFrame,
            translator=None,
            metadata=None,
            old_attrs=None,
            verbose=False,
    ):
        """
        Reads netcdf data that are not conform with this class and puts everything into a dataset
         that is conform with this class.
        Args:
            filenames: a path or a list of paths to the filenames to be read.
            concat_dim: the name of the dimension along whicht the files in filenames should be concatenated.
            meta_table: a pandas dataframe with the following entries: station_name, lat, lon, elev. station_name must
                be declared as the index of the table; lat,lon,elev declare the latitude, longitude and elevation of each
                station_name. latitude and longitude are assumend to be in degrees, elevation in meters.
            translator: a dict that translated variable names in the dataset to variable names used with this class.
            metadata: a dict of attributes that will be used as metadata. Do not provide station_name, lat, lon and
                station_elecation, as these will be read from the meta_table.
            old_attrs: a list of attributes that may exist in the ncdata and should be removed.
            verbose: if True, speak with user

        Returns: None

        """
        if isinstance(filenames, list) is False:
            filenames = [filenames]
        if metadata is None:
            metadata = dict()
            metadata["featureType"] = "timeSeries"  # assuming the feature
        if old_attrs is None:
            old_attrs = []
        if translator is None:
            translator = dict()

        all_data = []
        for idx, filename in enumerate(filenames):
            data = xr.open_dataset(filename)
            data = data.rename(translator)

            # Preparing metadata:
            metadata["station_name"] = meta_table.iloc[idx].name
            metadata["lat"] = meta_table.iloc[idx].lat
            metadata["lon"] = meta_table.iloc[idx].lon
            metadata["station_elevation"] = meta_table.iloc[idx].elev

            cf_table = (
                    os.path.split(os.path.realpath(__file__))[0]
                    + "/resources/cf_table_timeseries_fields.yaml"
            )

            data = assign_cf_attributes_tslist(data, metadata, cf_table, old_attrs, verbose)
            all_data.append(data)
            data.close()

        self.data = xr.concat(all_data, dim=concat_dim)
        save_attts = self.data[concat_dim].attrs
        # leads to loss of attributes for some reason.
        self.data = self.data.set_index({concat_dim: concat_dim})
        self.data[concat_dim].attrs = save_attts

    def read_non_conform_csvdata(self):
        raise NotImplementedError

    def apply_cf_attributes(self, station_name: str, lat: float, lon: float, elev: float, verbose=False):
        # Will need this method later anyway.
        # I may have to modify this method once I get to writing the csv reader.
        # I.e. have a single non_conform reader and call this method afterwards.
        # In the end, there would be three sources for non-conform data: netcdf, csv and as an argument from
        # __init__

        old_attrs = []
        # Preparing metadata:
        metadata = dict()
        metadata["featureType"] = "timeSeries"  # assuming the feature
        metadata["station_name"] = station_name
        metadata["lat"] = lat
        metadata["lon"] = lon
        metadata["station_elevation"] = elev

        cf_table = (os.path.split(os.path.realpath(__file__))[0]
                    + "/resources/cf_table_timeseries_fields.yaml")

        self.data = assign_cf_attributes_tslist(self.data, metadata, cf_table, old_attrs, verbose)

    # ----------------------------------------------------------------------
    #  Writers
    # ----------------------------------------------------------------------
    def write_cfconform_data(self, overwrite=False, concat_dim="station_name", split=None, verbose=False):
        """
        Write data to
        Args:
            overwrite: if True, an existing file will be overwritten. If False, and the file exists,
            data will be appended along the dimension concat_dim.
            concat_dim: the dimension along which data will be concatenated if a file already exists.
            split: YS for yearly, MS for monthly or None for no splitting
            verbose: if True, speak with user

        Returns: None

        """

        # Create class conform filename.
        t1 = self.data.time[0].values
        t2 = self.data.time[-1].values
        dtstart = dt.datetime.fromtimestamp(t1.item() / 10 ** 9)
        dtend = dt.datetime.fromtimestamp(t2.item() / 10 ** 9)

        filenames, tvec_split = get_list_of_filenames(self.dataset, dtstart, dtend, split)

        for idx in range(0, len(filenames)):
            targetfile = filenames[idx]
            subset = self.data.sel(time=slice(tvec_split[idx], tvec_split[idx + 1]))

            if os.path.exists(targetfile) and not overwrite:
                if verbose:
                    print(f"merging into {targetfile}")
                old_data = xr.open_dataset(targetfile)
                all_data = xr.concat([old_data, subset], dim=concat_dim)
                old_data.close()

                if concat_dim not in all_data.indexes:
                    all_data = all_data.set_index({concat_dim: concat_dim})

                old_data.close()

                all_data.to_netcdf(targetfile, mode="w", unlimited_dims="time")
                all_data.close()
            elif os.path.exists(targetfile) and overwrite:
                if verbose:
                    print(f"Write new file {targetfile}")
                subset.to_netcdf(targetfile, mode="w", unlimited_dims="time")
            elif not os.path.exists(targetfile):
                targetfile.parent.mkdir(exist_ok=True)
                subset.to_netcdf(targetfile, mode="w", unlimited_dims="time")

    # ----------------------------------------------------------------------
    #  Plotters
    # ----------------------------------------------------------------------

    def plot_Availability(self, var: str, station_name: str, year: str, zz: float, savename):

        """
        Creates a plot of the data availability.

        Args:
            station_name: Name of the station (if available)
            var: short name of the variable
            year: the year for which the plot should be shown
            zz: the height. Only used for labeling.
            savename:  Name of the file to be stored. If None, plot will be just displayed.

        Returns: None

        DLeuk, 21.05.2021

        """

        # first, get timeseries of the chosen variable and dtvec
        if "station_name" in self.data.indexes:
            data = self.data.sel({"station_name": station_name})[var].values
        else:
            data = self.data[var].values

        dtvec = self.data.time.values

        dtvec_dt = []
        for dt64 in dtvec:
            ts = (dt64 - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s")
            dtvec_dt.append(dt.datetime.utcfromtimestamp(ts))

        # now, calculate the Availability Matrix for each day of the year [0-100 %]
        Avail = np.zeros([12, 31]) * np.nan
        for mon in np.arange(1, 13):
            for day in np.arange(1, 32):
                mask = [item.day == day and item.month == mon for item in dtvec_dt]
                tmp_data = data[mask]

                tmp_dtvec = np.asarray(dtvec_dt)
                tmp_dtvec = tmp_dtvec[mask]
                if len(tmp_dtvec) > 0:
                    Avail[mon - 1, day - 1] = (
                                                      1 - sum(np.isnan(tmp_data)) / len(tmp_data)
                                              ) * 100.0

        Availability(Avail, zz, var, year, savename)
