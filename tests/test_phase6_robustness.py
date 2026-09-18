import numpy as np
import pandas as pd

from scripts.run_phase6_robustness import block_bootstrap, daily_mean


def test_daily_mean_clusters_by_signal_day():
    z=pd.DataFrame({"signal_day":pd.to_datetime(["2024-01-01","2024-01-01","2024-01-02"]),
                    "return_R":[1.0,3.0,2.0]})
    out=daily_mean(z)
    assert np.allclose(out.to_numpy(),[2.0,2.0])


def test_block_bootstrap_is_reproducible():
    x=np.arange(40,dtype=float)
    a=block_bootstrap(x,200,5,seed=123)
    b=block_bootstrap(x,200,5,seed=123)
    assert a==b
    assert a[1] <= a[0] <= a[2]


def test_perturbation_is_symmetric_around_baseline():
    from scripts.run_phase6_robustness import PERTURBATIONS
    assert PERTURBATIONS == ((0.40,0.80),(0.50,1.00),(0.60,1.20))
