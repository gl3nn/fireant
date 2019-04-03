from unittest import (
    TestCase,
    skip,
)

import numpy as np
import pandas as pd
import pandas.testing

from fireant.dataset.modifiers import Rollup
from fireant.dataset.totals import get_totals_marker_for_dtype
from fireant.queries.execution import reduce_result_set
from .mocks import (
    dimx0_metricx1_df,
    dimx1_date_df,
    dimx1_str_df,
    dimx1_str_totals_df,
    dimx2_date_str_df,
    dimx2_date_str_totals_df,
    dimx2_date_str_totalsx2_df,
    dimx2_str_num_df,
    dimx3_date_str_str_df,
    dimx3_date_str_str_totalsx3_df,
    mock_dataset,
)

pd.set_option('display.expand_frame_repr', False)


def replace_totals(data_frame):
    index_names = data_frame.index.names

    raw = data_frame.reset_index()
    for name in index_names:
        marker = get_totals_marker_for_dtype(raw[name].dtype)
        raw[name].replace(marker, np.nan, inplace=True)

    return raw


class ReduceResultSetsTests(TestCase):
    def test_reduce_single_result_set_no_dimensions(self):
        expected = dimx0_metricx1_df
        raw_df = expected

        dimensions = ()
        result = reduce_result_set([raw_df], (), dimensions, ())
        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_cont_dimension(self):
        expected = dimx1_date_df
        raw_df = replace_totals(expected)

        dimensions = (mock_dataset.fields.timestamp,)
        result = reduce_result_set([raw_df], (), dimensions, ())
        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_1x_dimension(self):
        expected = dimx1_str_df
        raw_df = replace_totals(expected)

        dimensions = (mock_dataset.fields.political_party,)
        result = reduce_result_set([raw_df], (), dimensions, ())
        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_date_str_dimensions_dates(self):
        expected = dimx2_date_str_df
        raw_df = replace_totals(expected)

        dimensions = (mock_dataset.fields.timestamp, mock_dataset.fields.political_party)
        result = reduce_result_set([raw_df], (), dimensions, ())
        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_str_num_dimensions(self):
        expected = dimx2_str_num_df.sort_index()
        raw_df = replace_totals(expected)

        dimensions = (mock_dataset.fields.political_party, mock_dataset.fields['candidate-id'])
        result = reduce_result_set([raw_df], (), dimensions, ())
        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_date_str_str_dimensions(self):
        expected = dimx3_date_str_str_df
        raw_df = replace_totals(expected)

        dimensions = (mock_dataset.fields.timestamp, mock_dataset.fields.political_party, mock_dataset.fields.state)
        result = reduce_result_set([raw_df], (), dimensions, ())
        pandas.testing.assert_frame_equal(expected, result)


class ReduceResultSetsWithTotalsTests(TestCase):
    def test_reduce_single_result_set_with_str_dimension(self):
        expected = dimx1_str_totals_df
        raw_df = replace_totals(dimx1_str_df)
        totals_df = pd.merge(pd.DataFrame([None], columns=['$political_party']),
                             pd.DataFrame([raw_df[['$votes', '$wins']].sum(axis=0)]),
                             how='outer',
                             left_index=True,
                             right_index=True)

        dimensions = (Rollup(mock_dataset.fields.political_party),)
        result = reduce_result_set([raw_df, totals_df], (), dimensions, ())

        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_dimx2_date_str_totals_date(self):
        expected = dimx2_date_str_totalsx2_df.loc[(slice(None), slice('Democrat', 'Republican')), :] \
            .append(dimx2_date_str_totalsx2_df.iloc[-1])
        raw_df = replace_totals(dimx2_date_str_df)
        totals_df = pd.merge(pd.DataFrame([[None, None]], columns=['$timestamp', '$political_party']),
                             pd.DataFrame([raw_df[['$votes', '$wins']].sum(axis=0)]),
                             how='outer',
                             left_index=True,
                             right_index=True)

        dimensions = (Rollup(mock_dataset.fields.timestamp),
                      mock_dataset.fields.political_party)
        result = reduce_result_set([raw_df, totals_df], (), dimensions, ())

        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_date_str_dimensions_str_totals(self):
        expected = dimx2_date_str_totals_df
        raw_df = replace_totals(dimx2_date_str_df)
        totals_df = raw_df.groupby('$timestamp').sum().reset_index()
        totals_df['$political_party'] = None
        totals_df = totals_df[['$timestamp', '$political_party', '$votes', '$wins']]

        dimensions = (mock_dataset.fields.timestamp,
                      Rollup(mock_dataset.fields.political_party))
        result = reduce_result_set([raw_df, totals_df], (), dimensions, ())

        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_dimx2_date_str_str_totals_date(self):
        expected = dimx3_date_str_str_totalsx3_df.loc[(slice(None),
                                                       slice('Democrat', 'Republican'),
                                                       slice('California', 'Texas')), :] \
            .append(dimx3_date_str_str_totalsx3_df.iloc[-1])

        raw_df = replace_totals(dimx3_date_str_str_df)
        totals_df = pd.merge(pd.DataFrame([[None, None, None]],
                                          columns=['$timestamp', '$political_party', '$state']),
                             pd.DataFrame([raw_df[['$votes', '$wins']].sum(axis=0)]),
                             how='outer',
                             left_index=True,
                             right_index=True)
        totals_df = totals_df[['$timestamp', '$political_party', '$state',
                               '$votes', '$wins']]

        dimensions = (Rollup(mock_dataset.fields.timestamp),
                      mock_dataset.fields.political_party,
                      mock_dataset.fields.state)
        result = reduce_result_set([raw_df, totals_df], (), dimensions, ())

        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_date_str_str_dimensions_str1_totals(self):
        expected = dimx3_date_str_str_totalsx3_df.loc[(slice(None),
                                                       slice(None),
                                                       slice('California', 'Texas')), :] \
            .append(dimx3_date_str_str_totalsx3_df.loc[(slice(None), '~~totals'), :].iloc[:-1]) \
            .sort_index()

        raw_df = replace_totals(dimx3_date_str_str_df)
        totals_df = raw_df.groupby('$timestamp').sum().reset_index()
        totals_df['$political_party'] = None
        totals_df['$state'] = None
        totals_df = totals_df[['$timestamp', '$political_party', '$state',
                               '$votes', '$wins']]

        dimensions = (mock_dataset.fields.timestamp,
                      Rollup(mock_dataset.fields.political_party),
                      mock_dataset.fields.state)
        result = reduce_result_set([raw_df, totals_df], (), dimensions, ())

        pandas.testing.assert_frame_equal(expected, result)

    def test_reduce_single_result_set_with_date_str_str_dimensions_str2_totals(self):
        expected = dimx3_date_str_str_totalsx3_df.loc[(slice(None), slice('Democrat', 'Republican')), :]
        raw_df = replace_totals(dimx3_date_str_str_df)
        totals_df = raw_df.groupby(['$timestamp', '$political_party']).sum().reset_index()
        totals_df['$state'] = None
        totals_df = totals_df[['$timestamp', '$political_party', '$state',
                               '$votes', '$wins']]

        dimensions = (mock_dataset.fields.timestamp,
                      mock_dataset.fields.political_party,
                      Rollup(mock_dataset.fields.state))
        result = reduce_result_set([raw_df, totals_df], (), dimensions, ())

        pandas.testing.assert_frame_equal(expected, result)

    @skip('BAN-2594')
    def test_reduce_single_result_set_with_date_str_str_dimensions_str1_totals_with_null_in_date_dim(self):
        index_names = list(dimx3_date_str_str_totalsx3_df.index.names)
        nulls = pd.DataFrame([[np.nan, 'd', '1', 'Texas', 5, 0], [np.nan, 'd', '2', 'California', 2, 0],
                              [np.nan, 'i', '1', 'Texas', 5, 0], [np.nan, 'i', '2', 'California', 7, 0],
                              [np.nan, 'r', '1', 'Texas', 11, 0], [np.nan, 'r', '2', 'California', 3, 0]],
                             columns=index_names + list(dimx3_date_str_str_totalsx3_df.columns))
        nulls_totals = pd.DataFrame([nulls[['$votes', '$wins']].sum()])
        nulls_totals[index_names[0]] = np.nan
        nulls_totals[index_names[1]] = '~~totals'
        nulls_totals[index_names[2]] = '~~totals'

        expected = dimx3_date_str_str_totalsx3_df.loc[(slice(None), slice(None), slice('1', '2')), :] \
            .append(dimx3_date_str_str_totalsx3_df.loc[(slice(None), '~~totals'), :].iloc[:-1]) \
            .append(nulls.set_index(index_names)) \
            .append(nulls_totals.set_index(index_names)) \
            .sort_index()
        raw_df = replace_totals(dimx3_date_str_str_df)
        raw_df = nulls \
            .append(raw_df) \
            .sort_values(['$timestamp', '$political_party', '$state'])

        totals_df = raw_df.groupby('$timestamp').sum().reset_index()
        null_totals_df = pd.DataFrame([raw_df[raw_df['$timestamp'].isnull()]
                                       [['$votes', '$wins']].sum()])
        null_totals_df['$timestamp'] = None
        totals_df = totals_df.append(null_totals_df)
        totals_df['$political_party'] = None
        totals_df['$state'] = None
        totals_df = totals_df[['$timestamp', '$political_party', '$state',
                               '$votes', '$wins']]

        dimensions = (mock_dataset.fields.timestamp,
                      Rollup(mock_dataset.fields.political_party),
                      mock_dataset.fields.state)
        result = reduce_result_set([raw_df, totals_df], (), dimensions, ())

        pandas.testing.assert_frame_equal(expected, result)