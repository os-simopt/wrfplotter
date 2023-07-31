import panel as pn
import holoviews as hv

try:
    import cartopy.crs as crs

    enable_maps = True
except ModuleNotFoundError:
    enable_maps = False

from src.wrftamer.Statistics import Statistics


########################################################################################################################
#                                                 Create Plots
########################################################################################################################


def create_hv_plot(infos: dict, data=None, map_data=None):
    plottype = infos["plottype"]
    var = infos["var"]

    # font_size = infos.get("font_size", 15)
    xlim = infos.get("xlim", (0, 1))
    tlim = infos.get("tlim", (0, 1))
    ylim = infos.get("ylim", (0, 1))
    clim = infos.get("clim", (0, 1))
    xlabel = infos.get("xlabel", "")
    ylabel = infos.get("ylabel", "")
    title = infos.get("title", "")

    if plottype == "Timeseries":

        stats = Statistics(data, **infos)

        size = 5

        for idx, item in enumerate(data):
            if idx == 0:
                if var == "DIR":
                    figure = (
                        data[item]
                            .dropna()
                            .hvplot.scatter(
                            xlim=tlim,
                            ylim=ylim,
                            size=size,
                            xlabel=xlabel,
                            ylabel=ylabel,
                            title=title,
                        )
                    )
                else:
                    figure = (
                        data[item]
                            .dropna()
                            .hvplot(xlim=tlim, ylim=ylim, xlabel=xlabel, ylabel=ylabel, title=title)
                    )
            else:
                if var == "DIR":
                    figure = figure * data[item].dropna().hvplot.scatter(
                        xlim=tlim, ylim=ylim, size=size, xlabel=xlabel, ylabel=ylabel, title=title
                    )
                else:
                    figure = figure * data[item].dropna().hvplot(
                        xlim=tlim, ylim=ylim, xlabel=xlabel, ylabel=ylabel, title=title
                    )

        if len(data.columns) > 1:
            figure.opts(legend_position="bottom_right")

        figure = pn.Column(figure, stats)

    elif plottype == 'Histogram':

        stats = Statistics(data, **infos)

        size = 5
        # width = 400
        # height = 600

        figure = data.hvplot.hist(
            size=size,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )
        figure = pn.Column(figure, stats)

    elif plottype == "Profiles":

        size = 10
        width = 400
        height = 600

        for num, item in enumerate(data):
            if num == 0:
                if var == "DIR":
                    figure = item.hvplot.scatter(
                        y="ALT",
                        x=item.columns[1],
                        size=size,
                        xlim=xlim,
                        ylim=ylim,
                        xlabel=xlabel,
                        ylabel=ylabel,
                        width=width,
                        height=height,
                        label=item.columns[1],
                        title=title,
                    )
                else:
                    figure = item.hvplot(
                        y="ALT",
                        x=item.columns[1],
                        size=size,
                        xlabel=xlabel,
                        ylabel=ylabel,
                        xlim=xlim,
                        ylim=ylim,
                        width=width,
                        height=height,
                        label=item.columns[1],
                        title=title,
                    )
            else:
                if var == "DIR":
                    figure = figure * item.hvplot.scatter(
                        y="ALT",
                        x=item.columns[1],
                        size=size,
                        xlabel=xlabel,
                        ylabel=ylabel,
                        xlim=xlim,
                        ylim=ylim,
                        width=width,
                        height=height,
                        label=item.columns[1],
                        title=title,
                    )
                else:
                    figure = figure * item.hvplot(
                        y="ALT",
                        x=item.columns[1],
                        size=size,
                        xlabel=xlabel,
                        ylabel=ylabel,
                        xlim=xlim,
                        ylim=ylim,
                        width=width,
                        height=height,
                        label=item.columns[1],
                        title=title,
                    )

        if len(data) > 1:
            figure.opts(legend_position="bottom_right")
        stats = None

    elif plottype == "Obs vs Mod":

        mods = infos["Expvec"]
        obs = infos["Obsvec"][0]

        stats = Statistics(data, **infos)

        # For the plot.
        size = 5
        height, width = 500, 650

        figure = hv.Curve([[0, 0], [xlim[1], xlim[1]]]).opts(color="grey")
        for mod in mods:
            figure = figure * data.hvplot.scatter(
                x=obs,
                y=mod,
                xlim=xlim,
                ylim=ylim,
                size=size,
                width=width,
                height=height,
                label=mod,
                xlabel=xlabel,
                ylabel=ylabel,
                title=title,
            )

        figure.opts(legend_position="bottom_right")

        figure = pn.Column(figure, stats)

    elif plottype in ["Map", "Diff Map"]:

        if map_data is None:
            print("Must provide map_data")
            return None, None

        figure = Map_hvplots(map_data, **infos)
        stats = None

    elif plottype == "zt-Plot":
        figure = data.hvplot.quadmesh(
            x="time",
            y="ALT",
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
            xlim=tlim,
            ylim=ylim,
            clim=tuple(clim),
        )
        stats = None

    else:
        print("Not yet implemented 01")
        figure = None
        stats = None

    return figure, stats


def Map_hvplots(map_data, **infos):
    if not enable_maps:
        print('You must install Cartopy to use this feature.')
        return

    if map_data is None:
        print("Must provide map_data")
        return None, None

    # font_size = infos.get("font_size", 10)
    clim = infos.get("clim", (0, 1))
    xlim = infos.get("xlim", (0, 1))
    ylim = infos.get("ylim", (0, 1))
    xlabel = infos.get("xlabel", "")
    ylabel = infos.get("ylabel", "")
    title = infos.get("title", "")
    # factor = infos.get("size_factor", 1.5)
    cmap = infos.get("cmapname", "viridis")
    # myticks = infos.get("myticks", np.linspace(clim[0], clim[1], 10))
    points_to_mark = infos.get("poi", None)
    coastline = infos.get("coastline", "10m")
    levels = infos.get("levels", 25)

    stand_lon = map_data.projection.stand_lon
    moad_cen_lat = map_data.projection.moad_cen_lat

    # Not 100% sure
    mycrs = crs.LambertConformal(central_longitude=stand_lon, central_latitude=moad_cen_lat)

    figure = map_data.hvplot.contourf(
        x="XLONG",
        y="XLAT",
        projection=mycrs,
        xlim=tuple(xlim),
        ylim=tuple(ylim),
        clim=tuple(clim),
        frame_width=400,
        cmap=cmap,
        levels=levels,
        coastline=coastline,
        geo=True,
        xlabel=xlabel,
        ylabel=ylabel,
        title=title,
    )

    if points_to_mark is not None and "lat" in points_to_mark:
        figure = figure * points_to_mark.hvplot.points(x="lon", y="lat", projection=mycrs, frame_width=400)

    return figure
