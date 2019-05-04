# -*- coding: utf-8 -*-
"""
This module defines a number of general plots, which may be relevant to
for reports of several programs.
"""
from collections import OrderedDict
from cctbx import uctbx

def scale_rmerge_vs_batch_plot(batch_manager, rmerge_vs_b, scales_vs_b=None):
    reduced_batches = batch_manager.reduced_batches
    shapes, annotations, text = batch_manager.batch_plot_shapes_and_annotations()
    if len(annotations) > 30:
        # at a certain point the annotations become unreadable
        annotations = None

    return {
        "scale_rmerge_vs_batch": {
            "data": [
                (
                    {
                        "x": reduced_batches,
                        "y": scales_vs_b,
                        "type": "scatter",
                        "name": "Scale",
                        "opacity": 0.75,
                        "text": text,
                    }
                    if scales_vs_b is not None
                    else {}
                ),
                {
                    "x": reduced_batches,
                    "y": rmerge_vs_b,
                    "yaxis": "y2",
                    "type": "scatter",
                    "name": "Rmerge",
                    "opacity": 0.75,
                    "text": text,
                },
            ],
            "layout": {
                "title": "Scale and Rmerge vs batch",
                "xaxis": {"title": "N"},
                "yaxis": {"title": "Scale", "rangemode": "tozero"},
                "yaxis2": {
                    "title": "Rmerge",
                    "overlaying": "y",
                    "side": "right",
                    "rangemode": "tozero",
                },
                "shapes": shapes,
                "annotations": annotations,
            },
        }
    }


def i_over_sig_i_vs_batch_plot(batch_manager, i_sig_i_vs_batch):

    reduced_batches = batch_manager.reduced_batches
    shapes, annotations, _ = batch_manager.batch_plot_shapes_and_annotations()
    if len(annotations) > 30:
        # at a certain point the annotations become unreadable
        annotations = None

    return {
        "i_over_sig_i_vs_batch": {
            "data": [
                {
                    "x": reduced_batches,
                    "y": i_sig_i_vs_batch,
                    "type": "scatter",
                    "name": "I/sigI vs batch",
                    "opacity": 0.75,
                }
            ],
            "layout": {
                "title": "<I/sig(I)> vs batch",
                "xaxis": {"title": "N"},
                "yaxis": {"title": "<I/sig(I)>", "rangemode": "tozero"},
                "shapes": shapes,
                "annotations": annotations,
            },
        }
    }


class ResolutionPlotterMixin(object):

    """Define additional helper methods for plotting"""

    @staticmethod
    def _d_star_sq_to_d_ticks(d_star_sq, nticks):
        min_d_star_sq = min(d_star_sq)
        dstep = (max(d_star_sq) - min_d_star_sq) / nticks
        tickvals = list(min_d_star_sq + (i * dstep) for i in range(nticks))
        ticktext = ["%.2f" % (uctbx.d_star_sq_as_d(dsq)) for dsq in tickvals]
        return tickvals, ticktext


class IntensityStatisticsPlots(ResolutionPlotterMixin):

    """Generate plots for intensity-derived statistics."""

    def __init__(
        self,
        intensities,
        anomalous=False,
        n_resolution_bins=20,
        xtriage_analyses=None,
        run_xtraige_analysis=True,
    ):
        self.n_bins = n_resolution_bins
        self._xanalysis = xtriage_analyses
        if anomalous:
            intensities = intensities.as_anomalous_array()
        intensities.setup_binner(n_bins=self.n_bins)
        merged = intensities.merge_equivalents()
        self.merged_intensities = merged.array()
        self.multiplicities = merged.redundancies().complete_array(new_data_value=0)
        if not self._xanalysis and run_xtraige_analysis:
            # imports needed here or won't work, unsure why.
            from mmtbx.scaling.xtriage import xtriage_analyses
            from mmtbx.scaling.xtriage import master_params as xtriage_master_params

            xtriage_params = xtriage_master_params.fetch(sources=[]).extract()
            xtriage_params.scaling.input.xray_data.skip_sanity_checks = True
            xanalysis = xtriage_analyses(
                miller_obs=self.merged_intensities,
                unmerged_obs=intensities,
                text_out="silent",
                params=xtriage_params,
            )
            self._xanalysis = xanalysis

    def generate_resolution_dependent_plots(self):
        d = OrderedDict()
        d.update(self.second_moments_plot())
        d.update(self.wilson_plot())
        return d

    def generate_miscellanous_plots(self):
        d = OrderedDict()
        d.update(self.cumulative_intensity_distribution_plot())
        d.update(self.l_test_plot())
        return d

    def wilson_plot(self):
        if not self._xanalysis or not self._xanalysis.wilson_scaling:
            return {}
        wilson_scaling = self._xanalysis.wilson_scaling
        tickvals_wilson, ticktext_wilson = self._d_star_sq_to_d_ticks(
            wilson_scaling.d_star_sq, nticks=5
        )

        return {
            "wilson_intensity_plot": {
                "data": (
                    [
                        {
                            "x": list(wilson_scaling.d_star_sq),
                            "y": list(wilson_scaling.mean_I_obs_data),
                            "type": "scatter",
                            "name": "Observed",
                        },
                        {
                            "x": list(wilson_scaling.d_star_sq),
                            "y": list(wilson_scaling.mean_I_obs_theory),
                            "type": "scatter",
                            "name": "Expected",
                        },
                        {
                            "x": list(wilson_scaling.d_star_sq),
                            "y": list(wilson_scaling.mean_I_normalisation),
                            "type": "scatter",
                            "name": "Smoothed",
                        },
                    ]
                ),
                "layout": {
                    "title": "Wilson intensity plot",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": tickvals_wilson,
                        "ticktext": ticktext_wilson,
                    },
                    "yaxis": {"type": "log", "title": "Mean(I)", "rangemode": "tozero"},
                },
            }
        }

    def cumulative_intensity_distribution_plot(self):
        if not self._xanalysis or not self._xanalysis.twin_results:
            return {}
        nz_test = self._xanalysis.twin_results.nz_test
        return {
            "cumulative_intensity_distribution": {
                "data": [
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.ac_obs),
                        "type": "scatter",
                        "name": "Acentric observed",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)"},
                    },
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.c_obs),
                        "type": "scatter",
                        "name": "Centric observed",
                        "mode": "lines",
                        "line": {"color": "rgb(255, 127, 14)"},
                    },
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.ac_untwinned),
                        "type": "scatter",
                        "name": "Acentric theory",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dot"},
                        "opacity": 0.8,
                    },
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.c_untwinned),
                        "type": "scatter",
                        "name": "Centric theory",
                        "mode": "lines",
                        "line": {"color": "rgb(255, 127, 14)", "dash": "dot"},
                        "opacity": 0.8,
                    },
                ],
                "layout": {
                    "title": "Cumulative intensity distribution",
                    "xaxis": {"title": "z", "range": (0, 1)},
                    "yaxis": {"title": "P(Z <= Z)", "range": (0, 1)},
                },
            }
        }

    def l_test_plot(self):
        if not self._xanalysis or not self._xanalysis.twin_results:
            return {}
        l_test = self._xanalysis.twin_results.l_test
        return {
            "l_test": {
                "data": [
                    {
                        "x": list(l_test.l_values),
                        "y": list(l_test.l_cumul_untwinned),
                        "type": "scatter",
                        "name": "Untwinned",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dashdot"},
                    },
                    {
                        "x": list(l_test.l_values),
                        "y": list(l_test.l_cumul_perfect_twin),
                        "type": "scatter",
                        "name": "Perfect twin",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dot"},
                        "opacity": 0.8,
                    },
                    {
                        "x": list(l_test.l_values),
                        "y": list(l_test.l_cumul),
                        "type": "scatter",
                        "name": "Observed",
                        "mode": "lines",
                        "line": {"color": "rgb(255, 127, 14)"},
                    },
                ],
                "layout": {
                    "title": "L test (Padilla and Yeates)",
                    "xaxis": {"title": "|l|", "range": (0, 1)},
                    "yaxis": {"title": "P(L >= l)", "range": (0, 1)},
                },
            }
        }

    def second_moments_plot(self):

        acentric = self.merged_intensities.select_acentric()
        centric = self.merged_intensities.select_centric()
        if acentric.size():
            acentric.setup_binner(n_bins=self.n_bins)
            second_moments_acentric = acentric.second_moment_of_intensities(
                use_binning=True
            )
        else:
            second_moments_acentric = None
        if centric.size():
            centric.setup_binner(n_bins=self.n_bins)
            second_moments_centric = centric.second_moment_of_intensities(
                use_binning=True
            )
        else:
            second_moments_centric = None

        second_moment_d_star_sq = []
        if acentric.size():
            second_moment_d_star_sq.extend(
                second_moments_acentric.binner.bin_centers(2)
            )
        if centric.size():
            second_moment_d_star_sq.extend(second_moments_centric.binner.bin_centers(2))
        tickvals_2nd_moment, ticktext_2nd_moment = self._d_star_sq_to_d_ticks(
            second_moment_d_star_sq, nticks=5
        )

        return {
            "second_moments": {
                "data": [
                    (
                        {
                            "x": list(
                                second_moments_acentric.binner.bin_centers(2)
                            ),  # d_star_sq
                            "y": second_moments_acentric.data[1:-1],
                            "type": "scatter",
                            "name": "<I^2> acentric",
                        }
                        if acentric.size()
                        else {}
                    ),
                    (
                        {
                            "x": list(
                                second_moments_centric.binner.bin_centers(2)
                            ),  # d_star_sq
                            "y": second_moments_centric.data[1:-1],
                            "type": "scatter",
                            "name": "<I^2> centric",
                        }
                        if centric.size()
                        else {}
                    ),
                ],
                "layout": {
                    "title": "Second moment of I",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": tickvals_2nd_moment,
                        "ticktext": ticktext_2nd_moment,
                    },
                    "yaxis": {"title": "<I^2>", "rangemode": "tozero"},
                },
            }
        }


class ResolutionPlotsAndStats(ResolutionPlotterMixin):

    """
    Use iotbx dataset statistics objects to make plots and tables for reports.

    This class allows the generation of plots of various properties as a
    function of resolution as well as a statistics table and summary table,
    using the data from two iotbx.dataset_statistics objects, with
    anomalous=False/True.
    """

    def __init__(
        self, dataset_statistics, anomalous_dataset_statistics, is_centric=False
    ):
        self.dataset_statistics = dataset_statistics
        self.anomalous_dataset_statistics = anomalous_dataset_statistics
        self.d_star_sq_bins = [
            (1 / bin_stats.d_min ** 2) for bin_stats in self.dataset_statistics.bins
        ]
        self.d_star_sq_tickvals, self.d_star_sq_ticktext = self._d_star_sq_to_d_ticks(
            self.d_star_sq_bins, nticks=5
        )
        self.is_centric = is_centric

    def make_all_plots(self):
        """Make a dictionary containing all available resolution-dependent plots."""
        d = OrderedDict()
        d.update(self.cc_one_half_plot())
        d.update(self.i_over_sig_i_plot())
        d.update(self.completeness_plot())
        d.update(self.multiplicity_vs_resolution_plot())
        return d

    def cc_one_half_plot(self, method=None):
        """Make a plot of cc half against resolution."""
        if method == "sigma_tau":
            cc_one_half_bins = [
                bin_stats.cc_one_half_sigma_tau
                for bin_stats in self.dataset_statistics.bins
            ]
            cc_one_half_critical_value_bins = [
                bin_stats.cc_one_half_sigma_tau_critical_value
                for bin_stats in self.dataset_statistics.bins
            ]
        else:
            cc_one_half_bins = [
                bin_stats.cc_one_half for bin_stats in self.dataset_statistics.bins
            ]
            cc_one_half_critical_value_bins = [
                bin_stats.cc_one_half_critical_value
                for bin_stats in self.dataset_statistics.bins
            ]
        cc_anom_bins = [bin_stats.cc_anom for bin_stats in self.dataset_statistics.bins]
        cc_anom_critical_value_bins = [
            bin_stats.cc_anom_critical_value
            for bin_stats in self.dataset_statistics.bins
        ]

        return {
            "cc_one_half": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,  # d_star_sq
                        "y": cc_one_half_bins,
                        "type": "scatter",
                        "name": "CC-half",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)"},
                    },
                    {
                        "x": self.d_star_sq_bins,  # d_star_sq
                        "y": cc_one_half_critical_value_bins,
                        "type": "scatter",
                        "name": "CC-half critical value (p=0.01)",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dot"},
                    },
                    (
                        {
                            "x": self.d_star_sq_bins,  # d_star_sq
                            "y": cc_anom_bins,
                            "type": "scatter",
                            "name": "CC-anom",
                            "mode": "lines",
                            "line": {"color": "rgb(255, 127, 14)"},
                        }
                        if not self.is_centric
                        else {}
                    ),
                    (
                        {
                            "x": self.d_star_sq_bins,  # d_star_sq
                            "y": cc_anom_critical_value_bins,
                            "type": "scatter",
                            "name": "CC-anom critical value (p=0.01)",
                            "mode": "lines",
                            "line": {"color": "rgb(255, 127, 14)", "dash": "dot"},
                        }
                        if not self.is_centric
                        else {}
                    ),
                ],
                "layout": {
                    "title": "CC-half vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {
                        "title": "CC-half",
                        "range": [min(cc_one_half_bins + cc_anom_bins + [0]), 1],
                    },
                },
                "help": """\
    The correlation coefficients, CC1/2, between random half-datasets. A correlation
    coefficient of +1 indicates good correlation, and 0 indicates no correlation.
    CC1/2 is typically close to 1 at low resolution, falling off to close to zero at
    higher resolution. A typical resolution cutoff based on CC1/2 is around 0.3-0.5.

    [1] Karplus, P. A., & Diederichs, K. (2012). Science, 336(6084), 1030-1033.
        https://doi.org/10.1126/science.1218231
    [2] Diederichs, K., & Karplus, P. A. (2013). Acta Cryst D, 69(7), 1215-1222.
        https://doi.org/10.1107/S0907444913001121
    [3] Evans, P. R., & Murshudov, G. N. (2013). Acta Cryst D, 69(7), 1204-1214.
        https://doi.org/10.1107/S0907444913000061
    """,
            }
        }

    def i_over_sig_i_plot(self):
        """Make a plot of <I/sigI> against resolution."""
        i_over_sig_i_bins = [
            bin_stats.i_over_sigma_mean for bin_stats in self.dataset_statistics.bins
        ]

        return {
            "i_over_sig_i": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,  # d_star_sq
                        "y": i_over_sig_i_bins,
                        "type": "scatter",
                        "name": "I/sigI vs resolution",
                    }
                ],
                "layout": {
                    "title": "<I/sig(I)> vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {"title": "<I/sig(I)>", "rangemode": "tozero"},
                },
            }
        }

    def completeness_plot(self):
        """Make a plot of completeness against resolution."""
        completeness_bins = [
            bin_stats.completeness for bin_stats in self.dataset_statistics.bins
        ]
        anom_completeness_bins = [
            bin_stats.anom_completeness
            for bin_stats in self.anomalous_dataset_statistics.bins
        ]

        return {
            "completeness": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,
                        "y": completeness_bins,
                        "type": "scatter",
                        "name": "Completeness",
                    },
                    (
                        {
                            "x": self.d_star_sq_bins,
                            "y": anom_completeness_bins,
                            "type": "scatter",
                            "name": "Anomalous completeness",
                        }
                        if not self.is_centric
                        else {}
                    ),
                ],
                "layout": {
                    "title": "Completeness vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {"title": "Completeness", "range": (0, 1)},
                },
            }
        }

    def multiplicity_vs_resolution_plot(self):
        """Make a plot of multiplicity against resolution."""
        multiplicity_bins = [
            bin_stats.mean_redundancy for bin_stats in self.dataset_statistics.bins
        ]
        anom_multiplicity_bins = [
            bin_stats.mean_redundancy
            for bin_stats in self.anomalous_dataset_statistics.bins
        ]

        return {
            "multiplicity_vs_resolution": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,
                        "y": multiplicity_bins,
                        "type": "scatter",
                        "name": "Multiplicity",
                    },
                    (
                        {
                            "x": self.d_star_sq_bins,
                            "y": anom_multiplicity_bins,
                            "type": "scatter",
                            "name": "Anomalous multiplicity",
                        }
                        if not self.is_centric
                        else {}
                    ),
                ],
                "layout": {
                    "title": "Multiplicity vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {"title": "Multiplicity"},
                },
            }
        }

    def merging_statistics_table(self, cc_half_method=None):

        headers = [
            u"Resolution (Å)",
            "N(obs)",
            "N(unique)",
            "Multiplicity",
            "Completeness",
            "Mean(I)",
            "Mean(I/sigma)",
            "Rmerge",
            "Rmeas",
            "Rpim",
            "CC1/2",
        ]
        if not self.is_centric:
            headers.append("CCano")
        rows = []

        def safe_format(format_str, item):
            return format_str % item if item is not None else ""

        for bin_stats in self.dataset_statistics.bins:
            row = [
                "%.2f - %.2f" % (bin_stats.d_max, bin_stats.d_min),
                bin_stats.n_obs,
                bin_stats.n_uniq,
                "%.2f" % bin_stats.mean_redundancy,
                "%.2f" % (100 * bin_stats.completeness),
                "%.1f" % bin_stats.i_mean,
                "%.1f" % bin_stats.i_over_sigma_mean,
                safe_format("%.3f", bin_stats.r_merge),
                safe_format("%.3f", bin_stats.r_meas),
                safe_format("%.3f", bin_stats.r_pim),
            ]
            if cc_half_method == "sigma_tau":
                row.append(
                    "%.3f%s"
                    % (
                        bin_stats.cc_one_half_sigma_tau,
                        "*" if bin_stats.cc_one_half_sigma_tau_significance else "",
                    )
                )
            else:
                row.append(
                    "%.3f%s"
                    % (
                        bin_stats.cc_one_half,
                        "*" if bin_stats.cc_one_half_significance else "",
                    )
                )

            if not self.is_centric:
                row.append(
                    "%.3f%s"
                    % (bin_stats.cc_anom, "*" if bin_stats.cc_anom_significance else "")
                )
            rows.append(row)

        merging_stats_table = [headers]
        merging_stats_table.extend(rows)

        return merging_stats_table

    def overall_statistics_table(self, cc_half_method=None):

        headers = ["", "Overall", "Low resolution", "High resolution"]

        stats = (
            self.dataset_statistics.overall,
            self.dataset_statistics.bins[0],
            self.dataset_statistics.bins[-1],
        )

        rows = [
            [u"Resolution (Å)"] + ["%.2f - %.2f" % (s.d_max, s.d_min) for s in stats],
            ["Observations"] + ["%i" % s.n_obs for s in stats],
            ["Unique reflections"] + ["%i" % s.n_uniq for s in stats],
            ["Multiplicity"] + ["%.1f" % s.mean_redundancy for s in stats],
            ["Completeness"] + ["%.2f%%" % (s.completeness * 100) for s in stats],
            # ['Mean intensity'] + ['%.1f' %s.i_mean for s in stats],
            ["Mean I/sigma(I)"] + ["%.1f" % s.i_over_sigma_mean for s in stats],
            ["Rmerge"] + ["%.3f" % s.r_merge for s in stats],
            ["Rmeas"] + ["%.3f" % s.r_meas for s in stats],
            ["Rpim"] + ["%.3f" % s.r_pim for s in stats],
        ]

        if cc_half_method == "sigma_tau":
            rows.append(["CC1/2"] + ["%.3f" % s.cc_one_half_sigma_tau for s in stats])
        else:
            rows.append(["CC1/2"] + ["%.3f" % s.cc_one_half for s in stats])
        rows = [[u"<strong>%s</strong>" % r[0]] + r[1:] for r in rows]

        overall_stats_table = [headers]
        overall_stats_table.extend(rows)

        return overall_stats_table

    def statistics_tables(self):
        """Generate the overall and by-resolution tables."""
        return (self.overall_statistics_table(), self.merging_statistics_table())
