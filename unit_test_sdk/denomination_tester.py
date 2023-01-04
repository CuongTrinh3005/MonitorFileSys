from unittest import TestCase
from unittest.mock import Mock

from contract_tester.smart_contract_tester import run
from contract_tester.smart_contract_tester.types import PostingInstruction, Rejected


class MyProductTest(TestCase):
    def setUp(self):
        with open('/Users/cgth/PycharmProjects/test/contracts/temp.py', 'r') as content_file:
            self.smart_contract = content_file.read()

    def test_pre_posting_code_rejects_wrong_denomination(self):
        def mock_get_parameter_timeseries(name):
            mock_at = Mock()
            mock_at.at.return_value = 'EUR'
            return mock_at

        mock_vault = Mock()
        mock_vault.get_parameter_timeseries.side_effect = mock_get_parameter_timeseries
        test_postings = [PostingInstruction(denomination='GBP')]
        with self.assertRaises(Rejected) as e:
            run(
                self.smart_contract,
                'pre_posting_code',
                mock_vault,
                test_postings,  # `postings` in `pre_posting_code`
                None,  # `effective_date` in `pre_posting_code`
            )
        self.assertEqual(str(e.exception), 'Cannot make payments in this denomination')
