from unittest.mock import patch

import pytest

from apps.etl_monitor.tasks import XYZ_DAGS, sync_all_dag_runs


class TestSyncAllDagRunsTask:
    def test_xyz_dags_list(self):
        assert "portfolio_etl_dag" in XYZ_DAGS
        assert "market_data_dag" in XYZ_DAGS
        assert "risk_report_dag" in XYZ_DAGS
        assert len(XYZ_DAGS) == 3

    @pytest.mark.django_db
    @patch("apps.etl_monitor.tasks.services.sync_dag_runs")
    def test_syncs_all_dags(self, mock_sync):
        mock_sync.return_value = 5
        result = sync_all_dag_runs()
        assert result["synced"] == 15
        assert result["dags"] == XYZ_DAGS
        assert mock_sync.call_count == 3

    @pytest.mark.django_db
    @patch("apps.etl_monitor.tasks.services.sync_dag_runs")
    def test_calls_with_limit(self, mock_sync):
        mock_sync.return_value = 0
        sync_all_dag_runs()
        for call in mock_sync.call_args_list:
            assert call.kwargs.get("limit", call.args[1] if len(call.args) > 1 else 20) == 20
