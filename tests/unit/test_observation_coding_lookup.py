from ucl_stavrinides.transformers.simple import ADDITIONAL_CODINGS


def test_observation_coding_lookup():
    """Ensure we can load using configuration of extra codings."""
    assert ADDITIONAL_CODINGS, "should have loaded ADDITIONAL_CODINGS"
    expected_keys = ['EPI_Count', 'Lymphocyte_Count', 'Lymphocyte_Percentage', 'focality', 'gleason', 'likert',
                     'pirads', 'ppsa', 'prvol']

    assert expected_keys == sorted(ADDITIONAL_CODINGS.keys()), "should have expected keys"
