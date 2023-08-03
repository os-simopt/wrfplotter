
# TODO: Rework, Reintegrate.
#  This is old Code from the wrftamer,
#  Map Plotting routine from the class Project, Method run_postprocessing_protocol

from wrfplotter.wrfplotter_classes import Map


"""
Warning: potentially, these are a LOT of maps, which may require a lot of space!
Specifically: ntime * nvars * nlevs * ndomains
If I can speedup the read and plot process, I might be able to plot the data with
WRFplotter after all.
I want to be able ot click through my maps.
"""

# Insead of plotting everything, I may want to creat a smaller subset of my wrfoutput
# I.e. some map-data,
# And during post processing, all wrfout-data is read and only a small fraction
# (as specified) is cut out to reduce the time it takes to load the data.
# Right now, I have two bottlenecks:
# 1) Loading the data. With wrf-python, since it does not use dask but netCDF4, it is very slow.
# However, I need the nice features of WRF.

# 2) cartopy/basemap. Here, specifically highres coastline data with basemap is very slow (15 s!)
# Time check: Loading a single timeframe: ~2 s
# Time check: Loading 18 timeframes at a time: 18.8 s
# Cartopy plot: 7.27 s
# Basemap plot: 4.02 s (res='h')
# Basemap plot: 980 ms/4.02 s (res='c','h') (but c is really ugly.)

# Loading data of a whole (2day run/16 GB), single VAR and ml: ~6min
# Loading all data with xarray and concating: Kernel dies
# Using open_mfdataset (dask): 6.83 s
# Now, the problem is that my nice wrf-python routines do not work anymore and I am left
# with raw WRF output. This is a hard stop, since both cartopy and basemap are using attributes
# provided by wrf-python
# wrf-python is not able to run with dask, and I cannot change that.
#
# Options:
# Write own code that interpolates and calculates diagnostics (like wrf-python)
# - this will take forever and is prone to errors! I may be able to do it with
# limited functionality.
# - Subsample data, i.e, extract required variables and levels, put into single file and store
# as netcdf. Then, load should be MUCH faster.
# Plotting MAY be much fast as well, if I have to calculate the basemape only once and just replace
# the field(s) plotted.

if ppp[item]:
    if isinstance(ppp[item], dict):
        list_of_mls = ppp[item].get("list_of_mls", [5])
        list_of_vars = ppp[item].get("list_of_vars", ["WSP"])
        list_of_doms = ppp[item].get("list_of_doms", ["d01"])
        poi = ppp[item].get("poi", None)
        store = bool(ppp[item].get("store", True))
    else:
        list_of_mls = [5]
        list_of_vars = ["WSP"]
        list_of_doms = ["d01"]
        poi = None
        store = True

    plot_path = workdir / "plot"
    intermediate_path = workdir / "out"
    fmt = "png"

    cls = Map(
        plot_path=plot_path,
        intermediate_path=intermediate_path,
        fmt=fmt,
    )

    for dom in list_of_doms:
        inpath = workdir / "out"
        filenames = list(sorted(inpath.glob(f"wrfout_{dom}*")))
        for filename in filenames:
            for ml in list_of_mls:
                for var in list_of_vars:
                    cls.extract_data_from_wrfout(
                        filename, dom, var, ml, select_time=-1
                    )

                    if store:
                        cls.store_intermediate()
                    else:
                        cls.plot(map_t="Cartopy", store=True, poi=poi)


