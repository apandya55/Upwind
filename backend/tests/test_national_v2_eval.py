from scripts.evaluate_national_v2 import fold_for, metrics


def test_site_fold_is_repeatable_for_same_location_cell():
    assert fold_for(35.2, -78.7) == fold_for(39.9, -72.1)  # same 10-degree cell
    assert 0 <= fold_for(64.8, -147.7) < 5


def test_out_of_sample_r2_uses_training_mean_reference():
    result = metrics([0.0, 10.0], [1.0, 9.0], [4.0, 4.0])
    assert result["r2_vs_training_mean"] == 1 - 2 / 52
